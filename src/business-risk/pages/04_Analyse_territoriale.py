import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import s3fs
import os
import requests

# 1. Configuration de la page
st.set_page_config(page_title="Analyse territoriale", layout="wide")

@st.cache_data
def load_data_fallback():
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID") or st.secrets.get("AWS_ACCESS_KEY_ID")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY") or st.secrets.get("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("AWS_BUCKET_NAME") or st.secrets.get("AWS_BUCKET_NAME")
    file_path = os.environ.get("AWS_FILE_PATH") or st.secrets.get("AWS_FILE_PATH")

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
            st.stop()

# --- CHARGEMENT DU GEOJSON ---
@st.cache_data
def get_geojson():
    repo_url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
    try:
        return requests.get(repo_url).json()
    except: return None

geojson_france = get_geojson()

# --- HARMONISATION TEMPORELLE ET NETTOYAGE ---
df["Date_fermeture_finale"] = pd.to_datetime(df["Date_fermeture_finale"], errors='coerce')
df["Code du département de l'établissement"] = df["Code du département de l'établissement"].astype(str).str.zfill(2)

annee_min = df["Date_fermeture_finale"].dt.year.min()
annee_max = df["Date_fermeture_finale"].dt.year.max()
nb_annees = max(1, (annee_max - annee_min + 1)) if not pd.isna(annee_min) else 1

# ---------------------------------------------------------------------
# CARTE 1 : INDICE DE ROTATION (ANNUALISÉ)
# ---------------------------------------------------------------------
st.header("📊 Diagnostic Territorial National")
st.info(f"ℹ️ Les taux sont exprimés en moyenne annuelle sur la période {int(annee_min) if not pd.isna(annee_min) else ''}-{int(annee_max) if not pd.isna(annee_max) else ''}.")

df_dept_stats = df.groupby("Code du département de l'établissement").agg(taux_brut=("fermeture", "mean")).reset_index()
df_dept_stats["taux_pct"] = ((df_dept_stats["taux_brut"] * 100) / nb_annees).round(2)
moy_nat_annuelle = ((df["fermeture"].mean() * 100) / nb_annees)

st.subheader("📍 Indice de rotation annuelle par département")
if geojson_france:
    fig_map = px.choropleth(
        df_dept_stats, geojson=geojson_france, locations="Code du département de l'établissement",
        featureidkey="properties.code", color="taux_pct", 
        color_continuous_scale="RdBu_r", 
        color_continuous_midpoint=moy_nat_annuelle, 
        scope="europe", height=700,
        title=f"Rotation annuelle moyenne (National : {moy_nat_annuelle:.2f}%)",
        labels={'taux_pct': 'Taux (%)'}
    )
    
    fig_map.update_geos(fitbounds="locations", visible=False)
    
    fig_map.update_layout(
        margin={"r":0, "t":80, "l":0, "b":0},
        coloraxis_colorbar=dict(
            title="<b>Taux (%)</b>", 
            ticksuffix="%",
            thicknessmode="pixels", thickness=15,
            lenmode='fraction', len=0.6,
            yanchor="middle", y=0.5
        )
    )
    st.plotly_chart(fig_map, use_container_width=True)

    # Classements
    df_metro = df_dept_stats[df_dept_stats["Code du département de l'établissement"].str[:2] < '97']
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("🟢 **Top 3 Résilience**")
        for i, (idx, row) in enumerate(df_metro.sort_values("taux_pct").head(3).iterrows()):
            d = row["Code du département de l'établissement"]
            st.metric(f"{i+1}. Dept {d}", f"{row['taux_pct']}%")
    with c2:
        st.markdown("🔴 **Top 3 Rotation**")
        for i, (idx, row) in enumerate(df_metro.sort_values("taux_pct", ascending=False).head(3).iterrows()):
            d = row["Code du département de l'établissement"]
            st.metric(f"{i+1}. Dept {d}", f"{row['taux_pct']}%", delta_color="inverse")

st.divider()

# ---------------------------------------------------------------------
# CARTE 2 : RÉSILIENCE (STOCK DE +10 ANS)
# ---------------------------------------------------------------------
st.subheader("🛡️ Analyse de la Résilience (Longévité)")
df_resilience = df[df["fermeture"] == 0].groupby("Code du département de l'établissement").agg(
    total=("age_estime", "count"), 
    plus_de_10ans=("age_estime", lambda x: (x > 10).sum())
).reset_index()
df_resilience["taux_vieux"] = (df_resilience["plus_de_10ans"] / df_resilience["total"] * 100).round(2)

if not df_resilience.empty:
    fig_res = px.choropleth(
        df_resilience,
        geojson=geojson_france,
        locations="Code du département de l'établissement",
        featureidkey="properties.code",
        color="taux_vieux",
        color_continuous_scale="Cividis_r", 
        scope="europe",
        height=700,
        title="🛡️ Part des entreprises de plus de 10 ans (Stock Actif)",
        labels={'taux_vieux': '% > 10 ans'}
    )
    
    fig_res.update_geos(fitbounds="locations", visible=False)
    
    fig_res.update_layout(
        margin={"r":0, "t":80, "l":0, "b":0},
        coloraxis_colorbar=dict(
            title="<b>Taux (%)</b>", 
            ticksuffix="%",
            thicknessmode="pixels", thickness=15,
            lenmode='fraction', len=0.6,
            yanchor="middle", y=0.5
        )
    )
    st.plotly_chart(fig_res, use_container_width=True)

    # Classements Résilience
    df_res_metro = df_resilience[df_resilience["Code du département de l'établissement"].str[:2] < '97']
    col_top, col_flop = st.columns(2)
    with col_top:
        st.markdown("🏆 **Top 3 : Tissus les plus matures**")
        for i, (idx, row) in enumerate(df_res_metro.sort_values("taux_vieux", ascending=False).head(3).iterrows()):
            d = row["Code du département de l'établissement"]
            st.metric(f"{i+1}. Dept {d}", f"{row['taux_vieux']}%")
    with col_flop:
        st.markdown("⚠️ **Top 3 : Renouvellement / Fragilité**")
        for i, (idx, row) in enumerate(df_res_metro.sort_values("taux_vieux", ascending=True).head(3).iterrows()):
            d = row["Code du département de l'établissement"]
            st.metric(f"{i+1}. Dept {d}", f"{row['taux_vieux']}%", delta_color="inverse")

# ---------------------------------------------------------------------
# CARTE 3 : DURÉE DE VIE MOYENNE (FERMÉES)
# ---------------------------------------------------------------------
st.subheader("⏳ Durée de vie moyenne avant fermeture")
df_life = df[df["fermeture"] == 1].groupby("Code du département de l'établissement")["age_estime"].mean().reset_index()

if not df_life.empty:
    df_life["decile"] = pd.qcut(df_life["age_estime"], 10, labels=False, duplicates='drop')
    
    fig_life = px.choropleth(
        df_life, geojson=geojson_france, locations="Code du département de l'établissement",
        featureidkey="properties.code", color="decile", 
        color_continuous_scale="Blues", height=700,
        title="Âge moyen au moment de la fermeture (par décile)",
        labels={'decile': 'Niveau Longévité'}
    )
    
    # AJUSTEMENT POUR ÉVITER L'ÉTIREMENT
    fig_life.update_geos(
        fitbounds="locations", 
        visible=False,
        projection_type="mercator"
    )
    fig_life.update_layout(
        margin={"r":150,"t":80,"l":150,"b":0},
        coloraxis_colorbar=dict(
            title="Déciles",
            tickvals=[0, 9],
            ticktext=["Plus court", "Plus long"]
        )
    )
    st.plotly_chart(fig_life, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------
# CARTE 4 : GROS EMPLOYEURS
# ---------------------------------------------------------------------
st.subheader("🏢 Densité des Employeurs Structurants")
df_emp = df[df["Tranche_effectif_num"] >= 10].groupby("Code du département de l'établissement").size().reset_index(name="nb")

if not df_emp.empty:
    fig_emp = px.choropleth(
        df_emp, geojson=geojson_france, locations="Code du département de l'établissement",
        featureidkey="properties.code", color="nb", 
        color_continuous_scale="YlGnBu", height=700,
        title="Nombre d'établissements de 10 salariés et plus",
        labels={'nb': 'Effectif'}
    )
    
    # AJUSTEMENT POUR ÉVITER L'ÉTIREMENT
    fig_emp.update_geos(
        fitbounds="locations", 
        visible=False,
        projection_type="mercator"
    )
    fig_emp.update_layout(
        margin={"r":150,"t":80,"l":150,"b":0}
    )
    st.plotly_chart(fig_emp, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------
# CARTE 5 : SYNTHÈSE (FOCUS DÉTAILLÉ)
# ---------------------------------------------------------------------
st.subheader("🔍 Focus Détaillé par Département")
liste_depts = sorted(df["Code du département de l'établissement"].unique())
col_sel, _ = st.columns([1, 2])
with col_sel:
    dep_cible = st.selectbox("Choisir un département :", options=liste_depts)

if dep_cible:
    df_loc = df[df["Code du département de l'établissement"] == dep_cible].copy()
    t_loc = ((df_loc["fermeture"].mean() * 100) / nb_annees).round(2)
    s_loc = round(df_loc[df_loc["fermeture"] == 1]["age_estime"].mean(), 1) if not df_loc[df_loc["fermeture"] == 1].empty else 0

    st.info(f"""
        **📍 Observation du tissu local (Dept {dep_cible})** : Cette cartographie recense les établissements actifs 
        selon des critères de **dimension** (effectifs) et de **maturité** (âge). 
        Il s'agit d'une vue descriptive de l'écosystème territorial destinée à identifier les bassins d'emploi, 
        sans jugement sur la santé financière individuelle des entités citées.
    """)

    fig_mapbox = px.scatter_mapbox(
        df_loc, lat="latitude", lon="longitude", color="age_estime", size="Tranche_effectif_num",
        color_continuous_scale="Viridis", size_max=12, hover_name="Dénomination",
        mapbox_style="carto-positron", height=700
    )
fig_mapbox.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        annotations=[dict(
            x=0.02, y=0.95, 
            xref="paper", yref="paper",

            text=(
                f"<b style='color:#1f2937; font-size:16px;'>📍 DEPT {dep_cible}</b><br>"
                f"<span style='color:#374151; font-size:14px;'>"
                f"Rotation : <b>{t_loc}%/an</b><br>"
                f"Âge moyen : <b>{s_loc} ans</b>"
                f"</span>"
            ),
            showarrow=False, 
            bgcolor="rgba(255, 255, 255, 1)", 
            bordercolor="#4682B4", 
            borderwidth=2, 
            borderpad=10, 
            align="left",
            font=dict(family="Arial", size=14, color="black") 
        )]
    )
st.plotly_chart(fig_mapbox, use_container_width=True, config={'scrollZoom': True})