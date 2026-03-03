import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# 1. Configuration de la page
st.set_page_config(page_title="Projection Stratégique", layout="wide")

# --- CHARGEMENT & FILTRAGE ---
if 'df_preds' in st.session_state:
    df_prediction = st.session_state['df_preds'].copy()
else:
    st.warning("⚠️ Les données de projection ne sont pas chargées.")
    st.stop()

# --- EXCLUSION DES DOM (97x) ---

df_prediction["Code du département de l'établissement"] = df_prediction["Code du département de l'établissement"].astype(str)
df_prediction = df_prediction[~df_prediction["Code du département de l'établissement"].str.startswith('97')]

@st.cache_data
def get_geojson():
    repo_url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
    try:
        return requests.get(repo_url).json()
    except:
        return None

geojson_france = get_geojson()

# --- TITRE & EN-TÊTE ---
st.title("🔮 6. Projection des Risques à 3 ans")

with st.container(border=True):
    c_icon, c_text = st.columns([1, 10])
    c_icon.write("# 🔍")
    with c_text:
        st.subheader("Méthodologie : Analyse de Résilience Structurelle")
        st.markdown("""
        L'indice de risque évalue la solidité du projet via trois piliers : 
        **Maturité** (ancienneté), **Configuration Statutaire** (forme juridique/taille) et **Ancrage Écosystémique** (dynamique locale).
        *Note : Ce score mesure la vulnérabilité structurelle plutôt que la solvabilité bancaire immédiate.*
        """)

# --- KPI (Cartes de score) ---
nb_total = len(df_prediction)
nb_critique_vigilance = len(df_prediction[df_prediction['Statut_Expert'].isin(['🔴 CRITIQUE', '🟠 VIGILANCE'])])
nb_observation = len(df_prediction[df_prediction['Statut_Expert'] == '🟡 OBSERVATION'])
risque_total_pct = ((nb_critique_vigilance + nb_observation) / nb_total) * 100

st.write("### 📊 État de santé du portefeuille")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    with st.container(border=True):
        st.metric("Portefeuille Actif", f"{nb_total:,}")
with kpi2:
    with st.container(border=True):
        st.metric("Sous Alerte (🔴+🟠)", f"{nb_critique_vigilance:,}", delta_color="inverse")
with kpi3:
    with st.container(border=True):
        st.metric("En Observation (🟡)", f"{nb_observation:,}")
with kpi4:
    with st.container(border=True):
        st.metric("Indice de Fragilité", f"{risque_total_pct:.2f}%", help="Moyenne nationale")

st.divider()

# --- CARTE & RÉPARTITION ---
col_map, col_bar = st.columns([1.5, 1])

with col_map:
    st.subheader("🗺️ Intensité du Risque (Dept)")
    
    # Calculs
    df_prediction['is_fragile'] = df_prediction['Statut_Expert'].isin(['🔴 CRITIQUE', '🟠 VIGILANCE', '🟡 OBSERVATION'])
    map_data = df_prediction.groupby("Code du département de l'établissement")['is_fragile'].mean().reset_index()
    map_data['Taux_Fragilite'] = map_data['is_fragile'] * 100
    moyenne_nat = map_data['Taux_Fragilite'].mean()
    map_data['Indice_Relatif'] = (map_data['Taux_Fragilite'] / moyenne_nat) * 100

    fig_map = px.choropleth(
        map_data, geojson=geojson_france,
        locations="Code du département de l'établissement",
        featureidkey="properties.code",
        color='Indice_Relatif',
        color_continuous_scale="RdYlGn_r",
        range_color=(70, 130), 
        scope='europe', height=500
    )
    fig_map.update_geos(fitbounds="locations", visible=False)
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, coloraxis_colorbar=dict(title="Risque"))
    st.plotly_chart(fig_map, use_container_width=True)
    
    st.info(f"💡 **Indice 100 = Moyenne ({risque_total_pct:.1f}%)**. Un score de 120 indique un risque +20% supérieur à la moyenne.")

with col_bar:
    st.subheader("📊 Profil Global")
    counts = df_prediction['Statut_Expert'].value_counts().reset_index()
    counts.columns = ['Statut', 'Effectif']
    counts['Pourcentage'] = (counts['Effectif'] / counts['Effectif'].sum() * 100)


    max_y = counts['Effectif'].max() * 1.15 

    fig_bar = px.bar(
        counts, x='Statut', y='Effectif', text='Pourcentage',
        color='Statut',
        color_discrete_map={'🟢 SAIN': '#2ecc71', '🟡 OBSERVATION': '#f1c40f', '🟠 VIGILANCE': '#e67e22', '🔴 CRITIQUE': '#e74c3c'},
        category_orders={"Statut": ["🟢 SAIN", "🟡 OBSERVATION", "🟠 VIGILANCE", "🔴 CRITIQUE"]},
        height=400
    )

    fig_bar.update_traces(
        texttemplate='%{text:.1f}%', 
        textposition='outside',
        textfont_size=14,
        cliponaxis=False
    )
    
    fig_bar.update_layout(
        showlegend=False, 
        plot_bgcolor='rgba(0,0,0,0)', 
        xaxis_title="",
        yaxis_title="",
        yaxis_range=[0, max_y], 
        margin=dict(t=50)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with st.container(border=True):
    st.markdown(f"""
    **💡 Lecture du Profil Global :**
    Le portefeuille présente une **solidité structurelle majeure** avec **{counts.loc[counts['Statut']=='🟢 SAIN', 'Pourcentage'].values[0]:.1f}%** de sociétés classées "Saines". 
    
    * **Interprétation :** Ce taux élevé démontre que la majorité du tissu économique analysé possède les attributs "génétiques" de la résilience (ancienneté, forme juridique stable, secteur porteur).
    * **Point d'attention :** L'enjeu de ce scoring n'est pas de prédire une faillite massive, mais d'isoler avec précision les **{100 - counts.loc[counts['Statut']=='🟢 SAIN', 'Pourcentage'].values[0]:.1f}%** de profils atypiques ou fragiles qui nécessitent une surveillance proactive.
    """)

st.divider()

# --- TOPS (Vigilance) ---
st.subheader("🔥 Focus : Zones et Secteurs sous tension")
t1, t2 = st.columns(2)

with t1:
    with st.container(border=True):
        st.write("**📍 Top 5 Départements (Risque Max)**")
        top_dep = map_data.sort_values('Indice_Relatif', ascending=False).head(5)
        top_dep_display = top_dep[["Code du département de l'établissement", 'Taux_Fragilite', 'Indice_Relatif']].copy()
        top_dep_display.columns = ['Dépt', 'Fragilité %', 'Indice']
        st.dataframe(top_dep_display.set_index('Dépt').style.format("{:.2f}"), use_container_width=True)

with t2:
    with st.container(border=True):
        st.write("**🏢 Top 5 Secteurs APE (Risque Max)**")
        stats_ape = df_prediction.groupby('libelle_section_ape')['is_fragile'].mean() * 100
        top_ape = stats_ape.sort_values(ascending=False).head(5).reset_index()
        top_ape.columns = ["Secteur", "Taux %"]
        st.dataframe(top_ape.set_index("Secteur").style.format("{:.2f}"), use_container_width=True)

# --- NOTE DE NEUTRALITÉ ---
st.divider()
with st.expander("⚖️ Note sur la neutralité et l'interprétation des données"):
    st.markdown("""
    Ces indicateurs reflètent des dynamiques de marché et des contextes territoriaux :
    * **Effets de structure :** Typologies d'entreprises prédominantes.
    * **Saisonnalité :** Variations cycliques sectorielles.
    * **Ancrage local :** Spécificités des écosystèmes.
    
    *Ce diagnostic est un outil de vigilance statistique et non une évaluation de la valeur intrinsèque.*
    """)