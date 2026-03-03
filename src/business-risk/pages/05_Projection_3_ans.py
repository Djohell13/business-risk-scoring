import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# 1. Configuration de la page
st.set_page_config(page_title="Projection sur les 3 prochaines années", layout="wide")

if 'df_preds' in st.session_state:
    df_prediction = st.session_state['df_preds']
else:
    st.warning("⚠️ Les données de projection ne sont pas chargées.")
    st.stop()

# --- GEOJSON ---
@st.cache_data
def get_geojson():
    repo_url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
    return requests.get(repo_url).json()

geojson_france = get_geojson()

st.title("🔮 6.Projection des Risques à 3 ans")

# Bloc méthodologique compatible Mode Clair / Mode Sombre
st.markdown("""
    <div style="
        background-color: rgba(70, 130, 180, 0.1); 
        padding: 20px; 
        border-radius: 10px; 
        border-left: 5px solid #4682B4; 
        margin-bottom: 25px;
        color: inherit;
    ">
        <h4 style="margin-top: 0; color: #4682B4;">🔍 Méthodologie : Analyse de Résilience Structurelle</h4>
        <p style="font-size: 1.05em;">L'indice de risque présenté ici est le résultat d'une analyse <b>statistique</b> basée sur la démographie des entreprises françaises. 
        En l'absence de données financières, le modèle évalue la solidité du projet à travers <b>trois piliers structurels</b> :</p>
        <ul style="line-height: 1.6;">
            <li><b>Maturité :</b> Analyse de l'ancienneté (les premières années étant les plus critiques).</li>
            <li><b>Configuration Statutaire :</b> Impact de la forme juridique et de la taille de la structure.</li>
            <li><b>Ancrage Écosystémique :</b> Dynamique de survie propre à chaque secteur d'activité et département.</li>
        </ul>
        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(0,0,0,0.1); font-size: 0.85em; opacity: 0.8;">
            <i>Note : Ce score mesure la vulnérabilité structurelle (le profil "génétique") plutôt que la solvabilité bancaire immédiate.</i>
        </div>
    </div>
    """, unsafe_allow_html=True)


# --- KPI ---
nb_total = len(df_prediction)
nb_critique_vigilance = len(df_prediction[df_prediction['Statut_Expert'].isin(['🔴 CRITIQUE', '🟠 VIGILANCE'])])
nb_observation = len(df_prediction[df_prediction['Statut_Expert'] == '🟡 OBSERVATION'])
risque_total_pct = ((nb_critique_vigilance + nb_observation) / nb_total) * 100

c1, c2, c3, c4 = st.columns(4)
c1.metric("Portefeuille Actif", f"{nb_total:,}")
c2.metric("Sous Alerte (🔴+🟠)", f"{nb_critique_vigilance:,}")
c3.metric("En Observation (🟡)", f"{nb_observation:,}")
c4.metric("Indice de Fragilité", f"{risque_total_pct:.2f}%", help="Moyenne nationale des profils hors 'Sain'")

st.markdown("---")

# --- CARTE (VERSION AMÉLIORÉE) ---
st.subheader("🗺️ Carte de Chaleur : Intensité du Risque par Département")

# 1. Préparation des données par département

df_prediction['is_fragile'] = df_prediction['Statut_Expert'].isin(['🔴 CRITIQUE', '🟠 VIGILANCE', '🟡 OBSERVATION'])
map_data = df_prediction.groupby("Code du département de l'établissement")['is_fragile'].mean().reset_index()
map_data['Taux_Fragilite'] = map_data['is_fragile'] * 100

# 2. CALCUL DE L'INDICE RELATIF (Base 100 = Moyenne Nationale)

moyenne_nat = map_data['Taux_Fragilite'].mean()
map_data['Indice_Relatif'] = (map_data['Taux_Fragilite'] / moyenne_nat) * 100

# 3. AFFICHAGE DE LA CARTE
fig_map = px.choropleth(
    map_data,
    geojson=geojson_france,
    locations="Code du département de l'établissement",
    featureidkey="properties.code",
    color='Indice_Relatif',
    color_continuous_scale="RdYlGn_r",
    range_color=(70, 130), 
    hover_data={"Code du département de l'établissement": True, 'Taux_Fragilite': ':.2f', 'Indice_Relatif': ':.0f'},
    scope='europe', height=700
)

fig_map.update_geos(fitbounds="locations", visible=False)
fig_map.update_layout(
    margin={"r":0,"t":0,"l":0,"b":0},
    coloraxis_colorbar=dict(
        title="Niveau de Risque",
        tickvals=[80, 100, 120],
        ticktext=["Faible (80)", "Moyenne (100)", "Élevé (120)"]
    )
)
st.plotly_chart(fig_map, use_container_width=True)

st.info(f"""
**💡 Comment lire cette carte ?** L'indice est basé sur la moyenne nationale (**{risque_total_pct:.2f}%**). 
* Un département en **rouge (ex: 120)** a un taux de sociétés fragiles 20% plus élevé que la moyenne.
* Un département en **vert (ex: 80)** est 20% plus stable que la moyenne.
""")

st.markdown("---")

# --- 6. GRAPHIQUE 1 : RÉPARTITION GLOBALE (EN BARRES) ---
st.subheader("📊 Profil de Risque du Portefeuille")

# On recalcule les counts pour être sûr d'utiliser df_prediction
counts = df_prediction['Statut_Expert'].value_counts().reset_index()
counts.columns = ['Statut', 'Effectif']
counts['Pourcentage'] = (counts['Effectif'] / counts['Effectif'].sum() * 100)

fig_bar = px.bar(
    counts, x='Statut', y='Effectif', text='Pourcentage',
    color='Statut',
    color_discrete_map={
        '🟢 SAIN': '#2ecc71', 
        '🟡 OBSERVATION': '#f1c40f', 
        '🟠 VIGILANCE': '#e67e22', 
        '🔴 CRITIQUE': '#e74c3c'
    },
    category_orders={"Statut": ["🟢 SAIN", "🟡 OBSERVATION", "🟠 VIGILANCE", "🔴 CRITIQUE"]},
    height=600
)
fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
fig_bar.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', font=dict(size=14))
st.plotly_chart(fig_bar, use_container_width=True)

# --- 7. TENDANCES TOP 5 ---
st.subheader("🔥 Focus : Zones et Secteurs sous tension")
t1, t2 = st.columns(2)

with t1:
    st.write("**📍 Top 5 Départements (Indice le plus élevé)**")

    top_dep = map_data.sort_values('Indice_Relatif', ascending=False).head(5)
    
    # Mise en forme pour le tableau
    top_dep_display = top_dep[["Code du département de l'établissement", 'Taux_Fragilite', 'Indice_Relatif']].copy()
    top_dep_display.columns = ['Dépt', 'Fragilité (%)', 'Indice (Base 100)']
    st.table(top_dep_display.set_index('Dépt').style.format("{:.2f}"))

with t2:
    st.write("**🏢 Top 5 Secteurs APE (Risque Prédit max)**")
    
    # Calcul de la fragilité par secteur
    stats_ape = df_prediction.groupby('libelle_section_ape')['is_fragile'].mean() * 100
    top_ape = stats_ape.sort_values(ascending=False).head(5).reset_index()
    top_ape.columns = ["Secteur d'Activité", "Taux de Fragilité (%)"]
    
    st.table(top_ape.set_index("Secteur d'Activité").style.format("{:.2f}"))

st.markdown("---")
st.markdown("""
    <div style="
        background-color: rgba(70, 130, 180, 0.05); 
        padding: 25px; 
        border-radius: 12px; 
        border-left: 6px solid #4682B4; 
        margin-top: 20px;
        margin-bottom: 25px;
        font-family: sans-serif;
    ">
        <h4 style="margin-top: 0; color: #4682B4; display: flex; align-items: center;">
            ⚖️ Note sur la neutralité des données
        </h4>
        <p style="font-size: 1.1em; line-height: 1.6; color: inherit; margin-bottom: 15px;">
            Ces indicateurs de tension et de fragilité sont issus d'une <b>analyse purement statistique</b>. 
            Ils reflètent des dynamiques de marché et des contextes territoriaux spécifiques :
        </p>
        <ul style="line-height: 1.6; font-size: 1.05em;">
            <li><b>Effets de structure :</b> Typologies d'entreprises prédominantes selon les zones.</li>
            <li><b>Saisonnalité :</b> Variations cycliques propres à certains secteurs.</li>
            <li><b>Ancrage local :</b> Spécificités des écosystèmes départementaux.</li>
        </ul>
        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(70, 130, 180, 0.2); font-size: 0.95em; font-style: italic; opacity: 0.9;">
            ⚠️ <b>Interprétation :</b> Ce diagnostic ne doit pas être interprété comme une évaluation de la valeur économique intrinsèque des départements ou des secteurs mentionnés, mais comme un outil de vigilance statistique.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")