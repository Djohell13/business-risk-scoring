import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Analyse territoriale", layout="wide")

@st.cache_data
def get_geojson():
    repo_url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
    try: return requests.get(repo_url).json()
    except: return None

if 'df' in st.session_state and st.session_state['df'] is not None:
    df = st.session_state['df']
else:
    st.warning("⚠️ Session rafraîchie. Veuillez repasser par la page d'accueil.")
    st.stop()

geojson_france = get_geojson()

# --- SÉCURISATION & HARMONISATION ---
df_geo = df.copy()
if "Code du département de l'établissement" in df_geo.columns:
    df_geo = df_geo.rename(columns={"Code du département de l'établissement": "dept_code"})
df_geo["dept_code"] = df_geo["dept_code"].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(2)

# --- 2. FILTRE TEMPOREL (Sidebar) ---
with st.sidebar:
    st.header("📅 Période choisie")
    options_periode = {
        "Tout l'historique": 0,
        "3 dernières années": 3,
        "2 dernières années": 2,
        "Année de référence (2025)": 1
    }
    periode_sel = st.radio("Horizon pour les cartes nationales :", list(options_periode.keys()))

    df_stats = df_geo.copy()
    if options_periode[periode_sel] > 0:
        annee_limite = 2025 - options_periode[periode_sel] + 1
        mask = (df_stats["fermeture"] == 0) | (
            (df_stats["fermeture"] == 1) & (df_stats["Date_fermeture_finale"].dt.year >= annee_limite)
        )
        df_stats = df_stats[mask]

annee_min = df_stats["Date_fermeture_finale"].dt.year.min()
annee_max = df_stats["Date_fermeture_finale"].dt.year.max()
nb_annees = max(1, (annee_max - annee_min + 1)) if not pd.isna(annee_min) else 1

# --- TITRE ---
st.title("🗺️ 4. Analyse Territoriale")
st.markdown("Analyse comparative des dynamiques de fermeture et de la maturité des tissus économiques par département.")

# --- CARTE 1 ---
df_dept_stats = df_stats.groupby("dept_code").agg(taux_brut=("fermeture", "mean")).reset_index()
df_dept_stats["taux_pct"] = ((df_dept_stats["taux_brut"] * 100) / nb_annees).round(2)
moy_nat_annuelle = ((df_stats["fermeture"].mean() * 100) / nb_annees)
vmin, vmax = df_dept_stats["taux_pct"].quantile(0.05), df_dept_stats["taux_pct"].quantile(0.95)

st.subheader("📍 Indice de Fermeture annuelle par département")
with st.container(border=True):
    st.markdown(f"**Moyenne Nationale : {moy_nat_annuelle:.2f}%**")
    if geojson_france:
        fig_map = px.choropleth(df_dept_stats, geojson=geojson_france, locations="dept_code", featureidkey="properties.code", color="taux_pct",
                                color_continuous_scale=[[0.0, "#1E3A8A"], [0.3, "#93C5FD"], [0.5, "#FFFFFF"], [0.7, "#FDBA74"], [1.0, "#B91C1C"]], 
                                range_color=[vmin, vmax], scope="europe", height=600, custom_data=[df_dept_stats["taux_pct"].round(2)])
        fig_map.update_geos(fitbounds="locations", visible=False)
        fig_map.update_traces(hovertemplate="<b>Département %{location}</b><br>Taux de fermeture : %{customdata[0]:.2f}%<extra></extra>")
        fig_map.update_layout(margin={"r":0, "t":0, "l":0, "b":0}, coloraxis_colorbar=dict(title="Taux (%)", tickvals=[vmin, moy_nat_annuelle, vmax], ticktext=[f"Sain ({vmin:.1f}%)", "Moyenne", f"Alerte ({vmax:.1f}%)"], len=0.7))
        st.plotly_chart(fig_map, use_container_width=True)

# --- ANALYSE DES DISPARITÉS ---
with st.chat_message("assistant"):
    st.markdown("### 🔍 Analyse de l'écart à la moyenne")
    col_stable, col_fragile = st.columns(2)
    df_metro = df_dept_stats[df_dept_stats["dept_code"].str.len() <= 2].copy()
    with col_stable:
        st.markdown("#### 🟢 Zones de Haute Stabilité")
        for i, (idx, r) in enumerate(df_metro.sort_values("taux_pct").head(3).iterrows(), 1):
            st.markdown(f"**{i}er : Dept {r['dept_code']}** : :green[{r['taux_pct']}%]")
    with col_fragile:
        st.markdown("#### 🔴 Zones de Vigilance")
        for i, (idx, r) in enumerate(df_metro.sort_values("taux_pct", ascending=False).head(3).iterrows(), 1):
            st.markdown(f"**{i}er : Dept {r['dept_code']}** : :red[{r['taux_pct']}%]")

# --- 4. ZOOM MAPBOX DÉTAILLÉ ---
st.subheader("🎯 Explorateur de proximité")

with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    
    with c1:
        dep_cible = st.selectbox("📍 Département", options=sorted(df_geo["dept_code"].unique()), key="map_dept")
    with c2:
        df_dep_only = df_geo[df_geo["dept_code"] == dep_cible].copy()
        secteurs_df = df_dep_only[['code_ape', 'libelle_section_ape']].drop_duplicates().dropna()
        secteurs_df["label"] = secteurs_df["code_ape"].astype(str) + " – " + secteurs_df["libelle_section_ape"].astype(str)
        secteur_choisi = st.selectbox("🏭 Secteur d'activité", options=["Tous Secteurs"] + secteurs_df["label"].sort_values().tolist(), key="map_secteur")
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption(f"Horizon temporel : **{periode_sel}**")

    # --- Calcul des indicateurs ---
    df_taux_filter = df_stats[df_stats["dept_code"] == dep_cible].copy()
    if secteur_choisi != "Tous Secteurs":
        ape_code = secteur_choisi.split(" – ")[0]
        df_taux_filter = df_taux_filter[df_taux_filter["code_ape"].astype(str) == ape_code]
    t_loc = ((df_taux_filter["fermeture"].mean() * 100) / nb_annees).round(2) if not df_taux_filter.empty else 0.0

    df_map = df_dep_only.copy()
    if secteur_choisi != "Tous Secteurs":
        df_map = df_map[df_map["code_ape"].astype(str) == secteur_choisi.split(" – ")[0]]
    
    s_loc = round(df_map["age_estime"].mean(), 1) if not df_map.empty else 0

    # --- Affichage des chiffres en métriques (Fixes et fluides) ---
    m1, m2, m3 = st.columns(3)
    m1.metric("Établissements actifs", f"{len(df_map):,}")
    m2.metric("Rotation annuelle", f"{t_loc:.2f}%")
    m3.metric("Âge moyen", f"{s_loc:.1f} ans")

    # --- Affichage de la carte (Sans l'annotation HTML lourde) ---
    if not df_map.empty:
        df_map["effectif_val"] = df_map["Tranche_effectif_num"].fillna(1)
        df_map["age_hover"] = df_map["age_estime"].fillna(0).round(0).astype(int)
        df_map["ape_hover"] = df_map["code_ape"].astype(str).replace(r'\.0$', '', regex=True)

        fig_mapbox = px.scatter_mapbox(
            df_map, lat="latitude", lon="longitude", color="age_estime", size="effectif_val",
            color_continuous_scale="Viridis", size_max=12, hover_name="Dénomination",
            custom_data=["age_hover", "ape_hover", "effectif_val"],
            mapbox_style="carto-positron", zoom=8, height=600
        )
        fig_mapbox.update_traces(
            hovertemplate="<b>%{hovertext}</b><br>Effectif : %{customdata[2]}<br>Âge : %{customdata[0]} ans<br>APE : %{customdata[1]}<extra></extra>"
        )
        fig_mapbox.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig_mapbox, use_container_width=True, config={'scrollZoom': True})
    else:
        st.warning("⚠️ Aucune donnée disponible pour cette sélection.")