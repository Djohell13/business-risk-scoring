import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import s3fs
import os
import requests

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Analyse territoriale", layout="wide")

@st.cache_data(show_spinner=False)
def load_data_optimized():
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID") or st.secrets.get("AWS_ACCESS_KEY_ID")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY") or st.secrets.get("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("AWS_BUCKET_NAME") or st.secrets.get("AWS_BUCKET_NAME")
    file_path = os.environ.get("AWS_FILE_PATH") or st.secrets.get("AWS_FILE_PATH")
    try:
        fs = s3fs.S3FileSystem(key=aws_key, secret=aws_secret, anon=False)
        s3_path = f"s3://{bucket_name}/{file_path}"
        with fs.open(s3_path, mode='rb') as f:
            df_loaded = pd.read_parquet(f)
        
        # Nettoyage et conversion des dates
        df_loaded["Date_fermeture_finale"] = pd.to_datetime(df_loaded["Date_fermeture_finale"], errors='coerce')
        
        # Harmonisation du code département dès le chargement
        df_loaded = df_loaded.rename(columns={"Code du département de l'établissement": "dept_code"})
        df_loaded["dept_code"] = df_loaded["dept_code"].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(2)
        
        return df_loaded
    except Exception as e:
        st.error(f"Erreur S3 : {e}")
        return None

# --- RÉCUPÉRATION ET SÉCURISATION DU DF ---

if 'df' in st.session_state and st.session_state['df'] is not None:
    df = st.session_state['df']
else:
    with st.status("📡 Chargement de la cartographie...", expanded=False) as status:
        df = load_data_optimized()
        st.session_state['df'] = df
        status.update(label="Cartographie prête !", state="complete")

# Sécurité : On s'assure que le format est bien du texte sur 2 caractères (gestion des catégories)
col_brute = "Code du département de l'établissement"
if col_brute in df.columns:
    df = df.rename(columns={col_brute: "dept_code"})

if "dept_code" in df.columns:
    df["dept_code"] = df["dept_code"].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(2)

@st.cache_data
def get_geojson():
    repo_url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
    try: return requests.get(repo_url).json()
    except: return None

geojson_france = get_geojson()

# Calculs de base
annee_min = df["Date_fermeture_finale"].dt.year.min()
annee_max = df["Date_fermeture_finale"].dt.year.max()
nb_annees = max(1, (annee_max - annee_min + 1)) if not pd.isna(annee_min) else 1

# --- TITRE ---
st.title("🗺️ 4. Analyse Territoriale")
st.markdown(f"Analyse comparative des dynamiques de fermeture et de la maturité des tissus économiques par département.")

# --- CARTE 1 : INDICE DE FERMETURE ---
df_dept_stats = df.groupby("dept_code").agg(taux_brut=("fermeture", "mean")).reset_index()
df_dept_stats["taux_pct"] = ((df_dept_stats["taux_brut"] * 100) / nb_annees).round(2)
moy_nat_annuelle = ((df["fermeture"].mean() * 100) / nb_annees)

st.subheader("📍 Indice de Fermeture annuelle par département")

with st.container(border=True):
    st.markdown(f"**Moyenne Nationale : {moy_nat_annuelle:.2f}%**")
    if geojson_france:

        fig_map = px.choropleth(
            df_dept_stats, geojson=geojson_france, locations="dept_code",
            featureidkey="properties.code", color="taux_pct", 
            color_continuous_scale="RdBu_r", 
            color_continuous_midpoint=moy_nat_annuelle, 
            scope="europe", height=600
        )
        fig_map.update_geos(fitbounds="locations", visible=False)
        fig_map.update_traces(
            hovertemplate="<b>Département %{location}</b><br>Taux de fermeture : %{z:.2f}%<extra></extra>"
        )
        fig_map.update_layout(margin={"r":0, "t":0, "l":0, "b":0}, coloraxis_colorbar=dict(title="%"))
        st.plotly_chart(fig_map, use_container_width=True)

# --- ANALYSE DES DISPARITÉS (Version Cards) ---

with st.chat_message("assistant"):
    st.markdown("### 🔍 Analyse de l'écart à la moyenne")
    st.markdown(f"Comparaison des dynamiques locales par rapport au référentiel national de **{moy_nat_annuelle:.2f}%**.")
    
    col_stable, col_fragile = st.columns(2)
    
    # Préparation des données métropole (on exclut les codes longs type DOM-TOM pour le top 3)
    df_metro = df_dept_stats[df_dept_stats["dept_code"].str.len() <= 2].copy()
    
    with col_stable:
        st.markdown("#### 🟢 Zones de Haute Stabilité")
        top_3_stable = df_metro.sort_values("taux_pct").head(3)
        
        for i, (idx, r) in enumerate(top_3_stable.iterrows(), 1):
            delta = r['taux_pct'] - moy_nat_annuelle
            with st.container(border=True):

                c_label, c_val = st.columns([2, 1])
                c_label.markdown(f"**{i}er : Dept {r['dept_code']}**")
                c_val.markdown(f"#### :green[{r['taux_pct']}%]")
                st.caption(f"📉 {delta:.2f} pts sous la moyenne nationale")

    with col_fragile:
        st.markdown("#### 🔴 Zones de Vigilance")
        top_3_fragile = df_metro.sort_values("taux_pct", ascending=False).head(3)
        
        for i, (idx, r) in enumerate(top_3_fragile.iterrows(), 1):
            delta = r['taux_pct'] - moy_nat_annuelle
            with st.container(border=True):
                c_label, c_val = st.columns([2, 1])
                c_label.markdown(f"**{i}er : Dept {r['dept_code']}**")
                c_val.markdown(f"#### :red[{r['taux_pct']}%]")
                st.caption(f"📈 +{delta:.2f} pts au-dessus de la moyenne")

st.divider()

# --- CARTES 2 & 3 : MATURITÉ & LONGÉVITÉ (VERSION CONTEXTUALISÉE) ---
st.subheader("🛡️ Résilience et Longévité")

# Bloc de contexte narratif
st.markdown("""
Cette section analyse la **solidité structurelle** des territoires. 
* **La Maturité** observe le stock actuel : quelle part du tissu économique a déjà survécu aux 10 premières années ?
* **La Longévité** analyse les fermetures : à quel âge moyen les entreprises de ce département finissent-elles par s'arrêter ?
""")

tab1, tab2 = st.tabs(["🛡️ Taux de Maturité (+10 ans)", "⏳ Durée de vie moyenne"])

with tab1:
    with st.container(border=True):
        df_resilience = df[df["fermeture"] == 0].groupby("dept_code").agg(
            total=("age_estime", "count"), 
            plus_de_10ans=("age_estime", lambda x: (x > 10).sum())
        ).reset_index()
        df_resilience["taux_vieux"] = (df_resilience["plus_de_10ans"] / df_resilience["total"] * 100).round(2)
        moy_maturite = df_resilience["taux_vieux"].mean()

        # Carte
        fig_res = px.choropleth(
            df_resilience, geojson=geojson_france, locations="dept_code",
            featureidkey="properties.code", color="taux_vieux",
            color_continuous_scale="YlGn",
            scope="europe", height=600
        )
        fig_res.update_geos(fitbounds="locations", visible=False)
        fig_res.update_traces(hovertemplate="<b>Département %{location}</b><br>Part +10 ans : %{z:.1f}%<extra></extra>")
        fig_res.update_layout(margin={"r":0, "t":0, "l":0, "b":0}, coloraxis_colorbar=dict(title="%"))
        st.plotly_chart(fig_res, use_container_width=True)


        top_mat = df_resilience[df_resilience["dept_code"].str.len() <= 2].sort_values("taux_vieux", ascending=False).head(3)
        st.write(f"💡 **Note :** La moyenne nationale de maturité est de **{moy_maturite:.1f}%**. Les tissus les plus ancrés se trouvent en : " + 
                  ", ".join([f"**Dept {r['dept_code']}** ({r['taux_vieux']}%)" for _, r in top_mat.iterrows()]))

with tab2:
    with st.container(border=True):
        df_life = df[df["fermeture"] == 1].groupby("dept_code")["age_estime"].mean().reset_index()
        moy_longevite = df_life["age_estime"].mean()


        fig_life = px.choropleth(
            df_life, geojson=geojson_france, locations="dept_code",
            featureidkey="properties.code", color="age_estime", 
            color_continuous_scale="Purples", 
            scope="europe", height=600
        )
        fig_life.update_geos(fitbounds="locations", visible=False, projection_scale=1)
        fig_life.update_traces(hovertemplate="<b>Département %{location}</b><br>Âge moyen fermeture : %{z:.1f} ans<extra></extra>")
        fig_life.update_layout(margin={"r":0, "t":0, "l":0, "b":0}, coloraxis_colorbar=dict(title="Ans"))
        st.plotly_chart(fig_life, use_container_width=True)


        top_life = df_life[df_life["dept_code"].str.len() <= 2].sort_values("age_estime", ascending=False).head(3)
        st.write(f"⏳ **Analyse :** En moyenne, une entreprise ferme après **{moy_longevite:.1f} ans** d'existence. Record de longévité constaté en : " + 
                  ", ".join([f"**Dept {r['dept_code']}** ({r['age_estime']:.1f} ans)" for _, r in top_life.iterrows()]))

st.divider()

# --- 4. ZOOM MAPBOX DÉTAILLÉ  ---
st.subheader("🎯 Explorateur de proximité")

st.markdown("_Identifiez les dynamiques de quartier en zoomant directement sur la carte. Plus le point est large, plus l'entreprise est solide en effectifs._")

with st.container(border=True):

    c_dep, c_sec, c_info = st.columns([1, 2, 1])
    
    with c_dep:
        dep_cible = st.selectbox("📍 Département", options=sorted(df["dept_code"].unique()))
    
    with c_sec:
        df_dep_only = df[df["dept_code"] == dep_cible].copy()
        
        secteurs_df = df_dep_only[['code_ape', 'libelle_section_ape']].drop_duplicates().dropna()
        secteurs_df["label"] = secteurs_df["code_ape"].astype(str) + " – " + secteurs_df["libelle_section_ape"].astype(str)
        secteurs = secteurs_df.sort_values("label")
        
        secteur_choisi = st.selectbox("🏭 Secteur d'activité", options=["Tous Secteurs"] + secteurs["label"].tolist())

    df_loc = df_dep_only.copy()
    if secteur_choisi != "Tous Secteurs":

        ape_code_extract = secteur_choisi.split(" – ")[0]
        df_loc = df_loc[df_loc["code_ape"].astype(str) == ape_code_extract]

    if not df_loc.empty:

        df_loc["code_ape_clean"] = df_loc["code_ape"].astype(str).replace(r'\.0$', '', regex=True)

        df_loc["age_hover"] = df_loc["age_estime"].fillna(0).round(0).astype(int)

        df_loc["effectif_val"] = df_loc["Tranche_effectif_num"].fillna(1)
        df_loc["effectif_hover"] = df_loc["effectif_val"].astype(int)
        
        # Calculs des metrics
        t_loc = ((df_loc["fermeture"].mean() * 100) / nb_annees).round(2)
        s_loc = round(df_loc[df_loc["fermeture"] == 1]["age_estime"].mean(), 1) if not df_loc[df_loc["fermeture"] == 1].empty else 0

        with c_info:
            st.metric("Établissements", f"{len(df_loc):,}", help="Nombre total d'unités légales identifiées sur cette zone.")

        # --- AJOUT CONVIVIALITÉ : NOTE DE SYNTHÈSE ---
        st.info(
            f"💡 **Analyse locale :** Dans le département **{dep_cible}**, "
            f"le secteur **{secteur_choisi.split(' – ')[-1] if secteur_choisi != 'Tous Secteurs' else 'global'}** "
            f"affiche une durée de vie moyenne de **{s_loc:.1f} ans**. "
            f"Explorez les points ci-dessous pour voir les détails par établissement."
        )

        # Carte
        fig_mapbox = px.scatter_mapbox(
            df_loc, 
            lat="latitude", 
            lon="longitude", 
            color="age_estime", 
            size="effectif_val",
            color_continuous_scale="Viridis", 
            size_max=12, 
            hover_name="Dénomination",
            custom_data=["age_hover", "code_ape_clean", "effectif_hover"],
            mapbox_style="carto-positron", 
            zoom=8, 
            height=650
        )

        # 3. Template de Hover (0=age, 1=APE, 2=Effectif)
        fig_mapbox.update_traces(
            hovertemplate=(
                "<b>%{hovertext}</b><br>"
                "Effectif : %{customdata[2]}<br>"
                "Âge : %{customdata[0]} ans<br>"
                "APE : %{customdata[1]}"
                "<extra></extra>"
            )
        )

        fig_mapbox.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0},
            annotations=[dict(
                x=0.01, y=0.99,
                xref="paper", yref="paper",
                text=(
                    f"<span style='font-size:16px; font-weight:bold; color:#1f2937;'>📍 DEPT {dep_cible}</span><br>"
                    f"<span style='font-size:4px;'> </span><br>" 
                    f"<span style='font-size:13px; color:#4b5563;'>Rotation :</span> "
                    f"<span style='font-size:13px; font-weight:bold; color:#1f2937;'>{t_loc:.2f}% /an</span><br>"
                    f"<span style='font-size:13px; color:#4b5563;'>Âge moyen :</span> "
                    f"<span style='font-size:13px; font-weight:bold; color:#1f2937;'>{s_loc:.1f} ans</span><br>"
                    f"<span style='font-size:13px; color:#4b5563;'>Établissements :</span> "
                    f"<span style='font-size:13px; font-weight:bold; color:#10b981;'>{len(df_loc):,}</span>"
                ),
                showarrow=False, align="left",
                bgcolor="rgba(255, 255, 255, 0.95)", 
                bordercolor="#d1d5db", borderwidth=1, borderpad=12
            )]
        )
        
        st.plotly_chart(fig_mapbox, use_container_width=True, config={'scrollZoom': True})
        
        st.caption("🔍 _Astuce : Survolez un point pour découvrir l'identité et les caractéristiques de l'entreprise._")
        
    else:
        st.warning("⚠️ Aucune donnée disponible pour cette sélection spécifique. Essayez un autre secteur ou département.")

st.divider()
st.caption("ℹ️ Source : Base SIRENE & Bilans Publics | Focus méthodologique : SAS & SARL.")