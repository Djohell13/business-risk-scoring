import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import s3fs
import os
import requests

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Analyse territoriale", layout="wide")

@st.cache_data
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
        
        # Harmonisation immédiate
        df_loaded["Date_fermeture_finale"] = pd.to_datetime(df_loaded["Date_fermeture_finale"], errors='coerce')
        df_loaded = df_loaded.rename(columns={"Code du département de l'établissement": "dept_code"})
        df_loaded["dept_code"] = df_loaded["dept_code"].astype(str).str.zfill(2)
        return df_loaded
    except Exception as e:
        st.error(f"Erreur de connexion S3 : {e}")
        return None

# --- RÉCUPÉRATION DU DF ---
if 'df' in st.session_state and st.session_state['df'] is not None:
    df = st.session_state['df']
else:
    with st.spinner("🔄 Récupération des données..."):
        df = load_data_optimized()
        if df is not None:
            st.session_state['df'] = df
        else:
            st.stop()

# --- CHARGEMENT DU GEOJSON ---
@st.cache_data
def get_geojson():
    repo_url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
    try:
        return requests.get(repo_url).json()
    except: return None

geojson_france = get_geojson()

# Constantes temporelles
annee_min = df["Date_fermeture_finale"].dt.year.min()
annee_max = df["Date_fermeture_finale"].dt.year.max()
nb_annees = max(1, (annee_max - annee_min + 1)) if not pd.isna(annee_min) else 1

# --- TITRE PRINCIPAL ---
st.title("📊 4. Analyse Territoriale")
st.info(f"ℹ️ Les taux sont exprimés en moyenne annuelle sur la période {int(annee_min) if not pd.isna(annee_min) else ''}-{int(annee_max) if not pd.isna(annee_max) else ''}.")

# CARTE 1 : INDICE DE FERMETURE

df_dept_stats = df.groupby("dept_code").agg(taux_brut=("fermeture", "mean")).reset_index()
df_dept_stats["taux_pct"] = ((df_dept_stats["taux_brut"] * 100) / nb_annees).round(2)
moy_nat_annuelle = ((df["fermeture"].mean() * 100) / nb_annees)

st.subheader(f"📍 Indice de Fermeture annuelle par département : (Moyenne Nationale : {moy_nat_annuelle:.2f}%)")

if geojson_france:
    fig_map = px.choropleth(
        df_dept_stats, geojson=geojson_france, locations="dept_code",
        featureidkey="properties.code", color="taux_pct", 
        color_continuous_scale="RdBu_r", color_continuous_midpoint=moy_nat_annuelle, 
        scope="europe", height=700
    )
    fig_map.update_traces(hovertemplate="<b>Département %{location}</b><br>Taux : %{z:.2f}%<extra></extra>")
    fig_map.update_geos(fitbounds="locations", visible=False)
    fig_map.update_layout(margin={"r":0, "t":50, "l":0, "b":0})
    st.plotly_chart(fig_map, use_container_width=True)

    st.info(" 🔍**Focus sur les disparités territoriales** : Voici les départements s'écartant le plus de la moyenne nationale.")

    with st.container(border=True):
        df_metro = df_dept_stats[df_dept_stats["dept_code"].str[:2] < '97'].copy()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🟢 Les 3 départements les plus stables")
            for i, r in df_metro.sort_values("taux_pct").head(3).iterrows():
                delta = r['taux_pct'] - moy_nat_annuelle
                st.markdown(f"**Dept {r['dept_code']}** | **{r['taux_pct']}%** | :green[{delta:.2f} pts vs moy.]")
        with c2:
            st.markdown("#### 🔴 Les 3 départements les moins stables")
            for i, r in df_metro.sort_values("taux_pct", ascending=False).head(3).iterrows():
                delta = r['taux_pct'] - moy_nat_annuelle
                st.markdown(f"**Dept {r['dept_code']}** | **{r['taux_pct']}%** | :red[+{delta:.2f} pts vs moy.]")

st.divider()

# CARTE 2 : RÉSILIENCE (+10 ANS)

df_resilience = df[df["fermeture"] == 0].groupby("dept_code").agg(
    total=("age_estime", "count"), 
    plus_de_10ans=("age_estime", lambda x: (x > 10).sum())
).reset_index()
df_resilience["taux_vieux"] = (df_resilience["plus_de_10ans"] / df_resilience["total"] * 100).round(2)
moy_nat_vieux = df_resilience["taux_vieux"].mean()

st.subheader(f"🛡️ Part des entreprises de plus de 10 ans : (Moyenne nationale : **{moy_nat_vieux:.2f}%**)")

if geojson_france:
    fig_res = px.choropleth(
        df_resilience, geojson=geojson_france, locations="dept_code",
        featureidkey="properties.code", color="taux_vieux",
        color_continuous_scale="Cividis_r", scope="europe", height=700
    )
    fig_res.update_traces(hovertemplate="<b>Département %{location}</b><br>Taux : %{z:.2f}%<extra></extra>")
    fig_res.update_geos(fitbounds="locations", visible=False)
    fig_res.update_layout(margin={"r":0, "t":50, "l":0, "b":0})
    st.plotly_chart(fig_res, use_container_width=True)
    
    st.info(f"🔍 **Analyse de la maturité des tissus territoriaux** : ")
    with st.container(border=True):
        df_res_metro = df_resilience[df_resilience["dept_code"].str[:2] < '97'].copy()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🏆 Top 3 : Tissus les plus matures")
            for i, r in df_res_metro.sort_values("taux_vieux", ascending=False).head(3).iterrows():
                st.markdown(f"**Dept {r['dept_code']}** | **{r['taux_vieux']}%** | :green[+{r['taux_vieux']-moy_nat_vieux:.2f} pts]")
        with c2:
            st.markdown("#### ⚠️ Top 3 : Tissus les plus jeunes")
            for i, r in df_res_metro.sort_values("taux_vieux", ascending=True).head(3).iterrows():
                st.markdown(f"**Dept {r['dept_code']}** | **{r['taux_vieux']}%** | :red[{r['taux_vieux']-moy_nat_vieux:.2f} pts]")

st.divider()

# CARTE 3 : LONGÉVITÉ (DÉCILES)

st.subheader("⏳ Durée de vie moyenne avant fermeture")
st.info("> **💡 Comprendre la carte** : J'ai divisé la France en 10 groupes égaux (déciles). Plus le bleu est foncé, plus la longévité est élevée.")

df_life = df[df["fermeture"] == 1].groupby("dept_code")["age_estime"].mean().reset_index()

if not df_life.empty:
    df_life["decile"] = pd.qcut(df_life["age_estime"], 10, labels=False, duplicates='drop')
    fig_life = px.choropleth(
        df_life, geojson=geojson_france, locations="dept_code",
        featureidkey="properties.code", color="decile", 
        color_continuous_scale="Blues", height=700
    )
    fig_life.update_traces(
        hovertemplate="<b>Département %{location}</b><br>Âge moyen : %{customdata[0]:.1f} ans<extra></extra>",
        customdata=df_life[["age_estime"]]
    )

    fig_life.update_geos(
        fitbounds="locations", 
        visible=False,
        projection_type="mercator"
    )

    fig_life.update_layout(
        margin={"r":0,"t":50,"l":0,"b":0},
        height=700,
        xaxis=dict(scaleanchor="y", scaleratio=1),
        yaxis=dict(constrain="domain")
    )

    st.plotly_chart(fig_life, use_container_width=True)

    moy_nat_life = df_life["age_estime"].mean()
    st.info(f"🔍 **Focus sur la longévité :** Moyenne nationale de **{moy_nat_life:.1f} ans** avant fermeture.")

    with st.container(border=True):
        df_life_metro = df_life[df_life["dept_code"].str[:2] < '97'].copy()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🏆 Top 3 : Longévité la plus forte")
            for i, r in df_life_metro.sort_values("age_estime", ascending=False).head(3).iterrows():
                st.markdown(f"**Dept {r['dept_code']}** | **{r['age_estime']:.1f} ans**")
        with c2:
            st.markdown("#### ⚠️ Top 3 : Fermetures les plus précoces")
            for i, r in df_life_metro.sort_values("age_estime", ascending=True).head(3).iterrows():
                st.markdown(f"**Dept {r['dept_code']}** | **{r['age_estime']:.1f} ans**")

st.divider()

# CARTE 4 : ZOOM MAPBOX DÉTAILLÉ

st.markdown("### 🎯 **A vous de jouer ! Identifiez les dynamiques territoriales**")

with st.expander("🚀 Comment utiliser cet outil ?", expanded=False):
    st.write("1. Choisissez votre département. 2. Filtrez par secteur. 3. Survolez les points.")

c_sel1, c_sel2 = st.columns(2)
with c_sel1:
    dep_cible = st.selectbox("📍 Choisir un département :", options=sorted(df["dept_code"].unique()))
with c_sel2:
    df_dep_only = df[df["dept_code"] == dep_cible]
    secteurs = df_dep_only[['code_ape', 'libelle_section_ape']].drop_duplicates().dropna().assign(
        label = lambda x: x["code_ape"].astype(str) + " – " + x["libelle_section_ape"]
    ).sort_values("label")
    secteur_choisi = st.selectbox("🏭 Filtrer par Secteur :", options=["Tous Secteurs"] + secteurs["label"].tolist())

df_loc = df_dep_only.copy()
if secteur_choisi != "Tous Secteurs":
    df_loc = df_loc[df_loc["code_ape"] == secteur_choisi.split(" – ")[0]]

if not df_loc.empty:
    # 1. Préparation des données spécifiques pour le hover (pour éviter les .0 et les NaN)
    df_loc["code_ape_clean"] = df_loc["code_ape"].astype(str).replace(r'\.0$', '', regex=True)
    df_loc["age_entier"] = df_loc["age_estime"].round(0)
    df_loc["effectif_val"] = df_loc["Tranche_effectif_num"].fillna(1)
    
    # Calculs pour l'annotation
    t_loc = ((df_loc["fermeture"].mean() * 100) / nb_annees).round(2)
    s_loc = round(df_loc[df_loc["fermeture"] == 1]["age_estime"].mean(), 1) if not df_loc[df_loc["fermeture"] == 1].empty else 0
    
    st.info(f"📍 **Département {dep_cible}** | Analyse de **{len(df_loc)}** établissements.")

# 2. Création de la carte
    fig_mapbox = px.scatter_mapbox(
        df_loc, 
        lat="latitude", 
        lon="longitude", 
        color="age_estime", 
        size="effectif_val",
        color_continuous_scale="Viridis", 
        size_max=12, 
        hover_name="Dénomination",
 
        hover_data={
            "age_entier": True,      
            "code_ape_clean": True,    
            "effectif_val": True,    
            "latitude": False,
            "longitude": False,
            "age_estime": False
        },
        mapbox_style="carto-positron", 
        height=700
    )

    # LA CORRECTION EST ICI :

    fig_mapbox.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br><br>"
            "👥 Effectif : <b>%{customdata[2]}</b><br>"
            "⏳ Âge : <b>%{customdata[0]} ans</b><br>"
            "🏭 Code APE : <b>%{customdata[1]}</b>"
            "<extra></extra>"
        )
    )
    
# 4. Annotation et mise en page
    fig_mapbox.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        annotations=[dict(
            x=0.01, y=0.99,
            xref="paper", yref="paper",
            text=(
                f"<span style='font-size:16px; font-weight:bold; color:#1f2937;'>📍 DEPT {dep_cible}</span><br>"
                f"<span style='font-size:3px;'> </span><br>" 
                f"<span style='font-size:13px; color:#4b5563;'>Rotation :</span> "
                f"<span style='font-size:13px; font-weight:bold; color:#e11d48;'>{t_loc}% /an</span><br>"
                f"<span style='font-size:13px; color:#4b5563;'>Âge moyen :</span> "
                f"<span style='font-size:13px; font-weight:bold; color:#2563eb;'>{s_loc} ans</span><br>"
                f"<span style='font-size:13px; color:#4b5563;'>Établissements :</span> "
                f"<span style='font-size:13px; font-weight:bold; color:#10b981;'>{len(df_loc):,}</span>"
            ),
            showarrow=False,
            align="left",
            bgcolor="rgba(255, 255, 255, 0.9)", 
            bordercolor="#d1d5db",
            borderwidth=1,
            borderpad=12,
            font=dict(family="Arial, sans-serif")
        )]
    )
    st.plotly_chart(fig_mapbox, use_container_width=True, config={'scrollZoom': True})

st.divider()
st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em;'>Source : Base SIRENE & Bilans Publics | Focus méthodologique : SAS & SARL.</div>", unsafe_allow_html=True)
