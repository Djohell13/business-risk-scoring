import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import s3fs
import os
import requests
from plotly.subplots import make_subplots

# 1. Configuration de la page
st.set_page_config(page_title="Analyse territoriale", layout="wide")

@st.cache_data
def load_data_fallback():
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("AWS_BUCKET_NAME")
    file_path = os.environ.get("AWS_FILE_PATH")

    if not aws_key:
        try:
            aws_key = st.secrets["AWS_ACCESS_KEY_ID"]
            aws_secret = st.secrets["AWS_SECRET_ACCESS_KEY"]
            bucket_name = st.secrets["AWS_BUCKET_NAME"]
            file_path = st.secrets["AWS_FILE_PATH"]
        except Exception:
            return None

    try:
        fs = s3fs.S3FileSystem(key=aws_key, secret=aws_secret, anon=False)
        s3_path = f"s3://{bucket_name}/{file_path}"
        with fs.open(s3_path, mode='rb') as f:
            return pd.read_parquet(f)
    except Exception as e:
        st.error(f"Erreur de connexion S3 : {e}")
        return None

# --- RÉCUPÉRATION DU DF ---
if 'df' in st.session_state and st.session_state['df'] is not None:
    df = st.session_state['df']
else:
    with st.spinner("🔄 Récupération des données..."):
        df = load_data_fallback()
        if df is not None:
            st.session_state['df'] = df
        else:
            st.error("❌ Erreur de chargement.")
            st.stop()

# --- 1. CHARGEMENT DU GEOJSON ---
@st.cache_data
def get_geojson():
    repo_url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
    try:
        response = requests.get(repo_url)
        return response.json()
    except Exception as e:
        return None

geojson_france = get_geojson()

# --- 2. TRAITEMENT DES DONNÉES (SANS FILTRE) ---
df["Code du département de l'établissement"] = df["Code du département de l'établissement"].astype(str).str.zfill(2)

# Suppression de la sélection : on prend tout le monde
df_selection = df.copy()

# --- 3. PRÉPARATION DES DONNÉES CARTES ---
df_dept_stats = (
    df_selection.groupby("Code du département de l'établissement")
    .agg(taux_fermeture=("fermeture", "mean"))
    .reset_index()
)
df_dept_stats["taux_pct"] = (df_dept_stats["taux_fermeture"] * 100).round(2)
vraie_moyenne = (df_selection["fermeture"].mean() * 100)

# --- 4. AFFICHAGE DES CARTES NATIONALES ---
st.header("📊 Diagnostic Territorial National")
st.info("ℹ️ Les différents graphiques concernent uniquement la France Métropolitaine")
st.subheader("📍 Indice de sinistralité par département")

if geojson_france is not None:
    fig_map = px.choropleth(
        df_dept_stats,
        geojson=geojson_france,
        locations="Code du département de l'établissement",
        featureidkey="properties.code",
        color="taux_pct",
        color_continuous_scale="RdBu_r", 
        color_continuous_midpoint=vraie_moyenne,
        scope="europe",
        title=f"Indice de sinistralité (Moyenne nationale : {vraie_moyenne:.2f}%)",
        labels={'taux_pct': 'Taux (%)'}
    )

    fig_map.update_geos(fitbounds="locations", visible=False)
    fig_map.update_layout(margin={"r":0,"t":80,"l":0,"b":0}, height=700)
    st.plotly_chart(fig_map, use_container_width=True)

# --- 3.5 CLASSEMENT DES DÉPARTEMENTS MÉTROPOLITAINS ---

    df_metropole = df_dept_stats[df_dept_stats["Code du département de l'établissement"].str[:2] < '97']

    # Calcul des classements (Top 3)
    top_alertes = df_metropole.sort_values("taux_pct", ascending=False).head(3)
    top_resilients = df_metropole.sort_values("taux_pct", ascending=True).head(3)

    col_res, col_alt = st.columns(2)

    with col_res:
        st.markdown("🟢 **Top 3 Résilience**")
        for i, (idx, row) in enumerate(top_resilients.iterrows()):
            dept_code = row["Code du département de l'établissement"]
            st.metric(
                label=f"{i+1}. Département {dept_code}", 
                value=f"{row['taux_pct']}%"
            )

    with col_alt:
        st.markdown("🔴 **Top 3 Alertes**")
        for i, (idx, row) in enumerate(top_alertes.iterrows()):
            dept_code = row["Code du département de l'établissement"]
            st.metric(
                label=f"{i+1}. Département {dept_code}", 
                value=f"{row['taux_pct']}%",
                delta_color="inverse"
            )

else:
    st.error("Impossible d'afficher la carte (GeoJSON manquant)")


st.divider()

# ------- Graph 2 -----------------------------------------------------

df_resilience = (
    df_selection[df_selection["fermeture"] == 0]
    .groupby("Code du département de l'établissement")
    .agg(
        total=("age_estime", "count"),
        plus_de_10ans=("age_estime", lambda x: (x > 10).sum())
    )
    .reset_index()
)

# Calcul du taux de "vieilles" entreprises
df_resilience["taux_vieux"] = (df_resilience["plus_de_10ans"] / df_resilience["total"] * 100).round(2)

# 2. Création de la carte

st.subheader("🛡️ Analyse de la Résilience (Longévité)")

# --- CARTE 2 : ANALYSE DE LA RÉSILIENCE ---
if not df_resilience.empty:
    fig_res = px.choropleth(
        df_resilience,
        geojson=geojson_france,
        locations="Code du département de l'établissement",
        featureidkey="properties.code",
        color="taux_vieux",
        color_continuous_scale="Cividis_r", 
        scope="europe",
        title="🛡️ Part des entreprises de plus de 10 ans (Structures ouvertes)",
        labels={'taux_vieux': '% > 10 ans'}
    )

    fig_res.update_geos(fitbounds="locations", visible=False)
    fig_res.update_layout(
        margin={"r":0, "t":80, "l":0, "b":0},
        height=700,
        coloraxis_colorbar=dict(
            title="<b>Taux (%)</b>", 
            ticksuffix="%",
            thicknessmode="pixels", thickness=15,
            lenmode='fraction', len=0.6,
            yanchor="middle", y=0.5
        )
    )

    # Affichage de la carte
    st.plotly_chart(fig_res, use_container_width=True)
    
    # --- CLASSEMENT RÉSILIENCE MÉTROPOLE ---

    df_res_metro = df_resilience[df_resilience["Code du département de l'établissement"].str[:2] < '97']

    if not df_res_metro.empty:
        # Calcul des classements
        top_res = df_res_metro.sort_values("taux_vieux", ascending=False).head(3)
        flop_res = df_res_metro.sort_values("taux_vieux", ascending=True).head(3)

        col_top, col_flop = st.columns(2)

        with col_top:
            st.markdown("🏆 **Top 3 : Tissus les plus matures**")
            for i, (idx, row) in enumerate(top_res.iterrows()):
                dept_code = row["Code du département de l'établissement"]
                st.metric(
                    label=f"{i+1}. Département {dept_code}", 
                    value=f"{row['taux_vieux']}%",
                    delta="Forte maturité", delta_color="normal"
                )

        with col_flop:
            st.markdown("⚠️ **Top 3 : Renouvellement / Fragilité**")
            for i, (idx, row) in enumerate(flop_res.iterrows()):
                dept_code = row["Code du département de l'établissement"]
                st.metric(
                    label=f"{i+1}. Département {dept_code}", 
                    value=f"{row['taux_vieux']}%",
                    delta="Faible maturité", delta_color="inverse"
                )
        
        st.caption("🔍 Un taux élevé indique un tissu économique stable composé d'entreprises pérennes (10 ans+).")
    
else:
    st.warning("⚠️ Données de résilience non disponibles pour la sélection actuelle.")

st.divider()

# --- CARTE 3 : DURÉE DE VIE MOYENNE AVANT FERMETURE ---

# 1. Préparation des données sur la SÉLECTION (Entreprises fermées uniquement)
df_map_ferme = (
    df_selection[df_selection["fermeture"] == 1]
    .groupby("Code du département de l'établissement")["age_estime"]
    .mean()
    .reset_index()
)

if not df_map_ferme.empty:
    # Calcul des déciles pour le contraste visuel
    df_map_ferme["rang_survie"] = pd.qcut(df_map_ferme["age_estime"], 10, labels=False, duplicates='drop')

    # 2. Création de la carte
    fig_life = px.choropleth(
        df_map_ferme,
        geojson=geojson_france,
        locations="Code du département de l'établissement",
        featureidkey="properties.code",
        color="rang_survie",
        color_continuous_scale="Blues", 
        hover_data={"rang_survie": False, "age_estime": ":.2f"},
        scope="europe",
        title="⏳ Durée de vie moyenne avant fermeture (Par décile)",
        labels={'age_estime': 'Âge moyen (ans)'}
    )

    # 3. Ajustements visuels (Alignement "Pixel Perfect")
    fig_life.update_geos(fitbounds="locations", visible=False)
    fig_life.update_layout(
        margin={"r":0, "t":80, "l":0, "b":0}, 
        height=700,                                  
        coloraxis_colorbar=dict(
            title="<b>Longévité</b>", 
            tickvals=[df_map_ferme["rang_survie"].min(), df_map_ferme["rang_survie"].max()], 
            ticktext=["Courte", "Longue"],
            thicknessmode="pixels", thickness=15,
            lenmode='fraction', len=0.6,
            yanchor="middle", y=0.5
        )
    )

    # 4. Affichage de la carte
    st.plotly_chart(fig_life, use_container_width=True)
    
    # --- 3.5 CLASSEMENT LONGÉVITÉ MÉTROPOLE ---

    df_life_metro = df_map_ferme[df_map_ferme["Code du département de l'établissement"].str[:2] < '97']

    if not df_life_metro.empty:
        top_life = df_life_metro.sort_values("age_estime", ascending=False).head(3)
        flop_life = df_life_metro.sort_values("age_estime", ascending=True).head(3)

        col_top, col_flop = st.columns(2)

        with col_top:
            st.markdown("🏆 **Top 3 : Plus forte longévité**")
            for i, (idx, row) in enumerate(top_life.iterrows()):
                dept_code = row["Code du département de l'établissement"]
                st.metric(
                    label=f"{i+1}. Département {dept_code}", 
                    value=f"{row['age_estime']:.1f} ans",
                    delta="Vie longue", delta_color="normal"
                )

        with col_flop:
            st.markdown("⚠️ **Top 3 : Fermetures plus précoces**")
            for i, (idx, row) in enumerate(flop_life.iterrows()):
                dept_code = row["Code du département de l'établissement"]
                st.metric(
                    label=f"{i+1}. Département {dept_code}", 
                    value=f"{row['age_estime']:.1f} ans",
                    delta="Vie courte", delta_color="inverse"
                )
        
        st.caption("🔍 Cette métrique mesure l'âge moyen atteint par les entreprises au moment de leur cessation d'activité.")
    
else:
    st.warning("⚠️ Pas assez de données de fermeture pour générer cette analyse.")

st.divider()

# --- CARTE 4 : CONCENTRATION DES GROS EMPLOYEURS ---

# 1. Préparation des données
seuil_fixe = 10 

df_employeurs = (
    df_selection[df_selection["Tranche_effectif_num"] >= seuil_fixe]
    .groupby("Code du département de l'établissement")
    .size()
    .reset_index(name="nb_gros_employeurs")
)

if not df_employeurs.empty:
    # 2. Création de la carte
    fig_densite = px.choropleth(
        df_employeurs,
        geojson=geojson_france,
        locations="Code du département de l'établissement",
        featureidkey="properties.code",
        color="nb_gros_employeurs",
        color_continuous_scale="YlGnBu",
        scope="europe",
        title=f"🏢 Densité des Employeurs Structurants (Effectifs >= {seuil_fixe})",
        labels={'nb_gros_employeurs': 'Nombre d\'entreprises'}
    )

    # 3. Ajustements visuels et légende
    fig_densite.update_geos(fitbounds="locations", visible=False)
    fig_densite.update_layout(
        margin={"r":0, "t":80, "l":0, "b":0},
        height=700,
        coloraxis_colorbar=dict(
            title="<b>Unités</b>",
            thicknessmode="pixels", thickness=15,
            lenmode="fraction", len=0.6,
            yanchor="middle", y=0.5,
            ticks="outside"
        )
    )

    # 4. Affichage de la carte
    st.plotly_chart(fig_densite, use_container_width=True)
    
# 5. Remplacement du st.info par des indicateurs clés (KPI)
    total_gros = df_employeurs["nb_gros_employeurs"].sum()
    # Calcul du département le plus dense
    top_dept_idx = df_employeurs["nb_gros_employeurs"].idxmax()
    top_dept_code = df_employeurs.loc[top_dept_idx, "Code du département de l'établissement"]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Employeurs", f"{total_gros:,}".replace(',', ' '))
    with col2:
        st.metric("Seuil Effectif", f"≥ {seuil_fixe} sal.")
    with col3:
        st.metric("Top Département", f"Dept {top_dept_code}")
        
    st.caption(f"Analyse basée sur les établissements de {seuil_fixe} salariés et plus publiant leurs bilans.")

# --- CARTE 5 : SYNTHÈSE ÉCONOMIQUE (RÉSILIENCE & EMPLOYEURS) ---

# 1. Préparation des données combinées sur la SÉLECTION
df_final = (
    df_selection[df_selection["fermeture"] == 0]
    .groupby("Code du département de l'établissement")
    .agg(
        total=("age_estime", "count"),
        plus_de_10ans=("age_estime", lambda x: (x > 10).sum()),
        gros_employeurs=("Tranche_effectif_num", lambda x: (x >= 10).sum())
    )
    .reset_index()
)

# Calcul du taux de résilience
df_final["taux_resilience"] = (df_final["plus_de_10ans"] / df_final["total"] * 100).round(2)

if not df_final.empty:
    # 2. Création de la carte
    fig_synthese = px.choropleth(
        df_final,
        geojson=geojson_france,
        locations="Code du département de l'établissement",
        featureidkey="properties.code",
        color="taux_resilience",
        hover_data={
            "Code du département de l'établissement": True,
            "taux_resilience": True,
            "gros_employeurs": True,
            "total": True
        },
        color_continuous_scale="Viridis",
        scope="europe",
        title="💎 Synthèse Économique : Taux de Résilience & Poids des Employeurs",
        labels={
            'taux_resilience': 'Résilience (%)',
            'gros_employeurs': 'Gros Employeurs',
            'total': 'Total Entreprises'
        }
    )

    # 3. Ajustements Pixel Perfect
    fig_synthese.update_geos(fitbounds="locations", visible=False)
    fig_synthese.update_layout(
        margin={"r":0, "t":80, "l":0, "b":0},
        height=700, 
        coloraxis_colorbar=dict(
            title="<b>Résilience (%)</b>",
            ticksuffix="%",
            thicknessmode="pixels", thickness=15,
            lenmode='fraction', len=0.6,
            yanchor="middle", y=0.5
        )
    )

    # 4. Affichage
    st.plotly_chart(fig_synthese, use_container_width=True)
    
    # --- 5. CLASSEMENT SYNTHÈSE MÉTROPOLE ---

    df_syn_metro = df_final[df_final["Code du département de l'établissement"].str[:2] < '97']

    if not df_syn_metro.empty:

        top_syn = df_syn_metro.sort_values("taux_resilience", ascending=False).head(3)
        top_poids = df_syn_metro.sort_values("gros_employeurs", ascending=False).head(3)

        col_mat, col_poids = st.columns(2)

        with col_mat:
            st.markdown("🥇 **Top 3 : Maturité (Résilience)**")
            for i, (idx, row) in enumerate(top_syn.iterrows()):
                dept_code = row["Code du département de l'établissement"]
                st.metric(
                    label=f"{i+1}. Département {dept_code}", 
                    value=f"{row['taux_resilience']}%",
                    delta="Taux résilience"
                )

        with col_poids:
            st.markdown("🏢 **Top 3 : Puissance (Gros Employeurs)**")
            for i, (idx, row) in enumerate(top_poids.iterrows()):
                dept_code = row["Code du département de l'établissement"]
                st.metric(
                    label=f"{i+1}. Département {dept_code}", 
                    value=int(row['gros_employeurs']),
                    delta="Nb employeurs", delta_color="normal"
                )
        
        st.caption("💡 **Interprétation** : La couleur indique la maturité (zones jaunes), tandis que le survol révèle la force de frappe en termes d'emplois.")

else:
    st.warning("⚠️ Données insuffisantes pour la synthèse sur cette sélection.")

st.divider()

# --- SECTION 6 : FOCUS GÉOLOCALISÉ ---
st.subheader("🔍 Focus Détaillé par Département. Pour ces données, les DOM ont été intégrés.")

# 1. Sélection du département via menu déroulant
liste_depts = sorted(df["Code du département de l'établissement"].unique())

col_select, col_empty = st.columns([1, 2])
with col_select:
    dep_cible = st.selectbox("Choisir un département pour en visualiser sa firmographie :", options=liste_depts)

if dep_cible:
    # 2. Calculs des stats comparatives
    df_loc = df[df["Code du département de l'établissement"] == dep_cible]
    
    t_local = (df_loc["fermeture"].mean() * 100).round(2)
    s_local = df_loc[df_loc["fermeture"] == 1]["age_estime"].mean()
    s_local = round(s_local, 1) if not pd.isna(s_local) else 0
        
    # Rappel Moyennes Nationales
    moy_nat_taux = (df["fermeture"].mean() * 100).round(2)
    moy_nat_survie = df[df["fermeture"] == 1]["age_estime"].mean()
    moy_nat_survie = round(moy_nat_survie, 1) if not pd.isna(moy_nat_survie) else 0

    # 3. Création de la carte Mapbox
    fig_mapbox = px.scatter_mapbox(
        df_loc,
        lat="latitude",
        lon="longitude",
        color="age_estime",
        size="Tranche_effectif_num",
        color_continuous_scale="Viridis",
        size_max=12,
        # --- LA CORRECTION EST ICI ---
        hover_name="Dénomination", 
        # -----------------------------
        mapbox_style="carto-positron",
        title=f"Positionnement des Établissements - Dept {dep_cible}",
        height=700
    )

    # 4. ANNOTATION STABLE
    fig_mapbox.update_layout(
        margin={"r":0,"t":60,"l":0,"b":0},
        mapbox=dict(zoom=8), 
        annotations=[dict(
            x=0.02, y=0.98,
            xref="paper", yref="paper",
            text=(
                f"<b>📍 DÉPARTEMENT {dep_cible}</b><br>"
                f"📉 Risque : <b>{t_local}%</b> <span style='font-size:10px'>(Nat: {moy_nat_taux}%)</span><br>"
                f"⏳ Survie : <b>{s_local} ans</b> <span style='font-size:10px'>(Nat: {moy_nat_survie} ans)</span>"
            ),
            showarrow=False,
            bgcolor="rgba(240, 240, 240, 0.85)", 
            bordercolor="rgba(100, 100, 100, 0.3)",
            borderwidth=1,
            align="left",
            font=dict(family="Arial", size=13, color="black")
        )]
    )

    # 5. Affichage Streamlit
    st.plotly_chart(fig_mapbox, use_container_width=True, config={'scrollZoom': True})
    
    st.caption("💡 La taille des points représente l'effectif, la couleur représente l'âge de l'entreprise.")
    st.markdown("---")