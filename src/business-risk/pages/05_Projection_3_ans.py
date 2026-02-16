import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import s3fs
import os
import requests

# 1. Configuration de la page
st.set_page_config(page_title="Projection sur les 3 prochaines années", layout="wide")

# --- RÉCUPÉRATION DU DF ---
@st.cache_data
def load_data_fallback():
    try:
        aws_key = st.secrets["AWS_ACCESS_KEY_ID"]
        aws_secret = st.secrets["AWS_SECRET_ACCESS_KEY"]
        bucket_name = st.secrets["AWS_BUCKET_NAME"]
        file_path = st.secrets["AWS_FILE_PATH"]

        fs = s3fs.S3FileSystem(key=aws_key, secret=aws_secret, anon=False)
        s3_path = f"s3://{bucket_name}/{file_path}"
        with fs.open(s3_path, mode='rb') as f:
            return pd.read_parquet(f)
    except Exception as e:
        st.error(f"Erreur S3 : {e}")
        return None

if 'df' in st.session_state and st.session_state['df'] is not None:
    df = st.session_state['df']
else:
    df = load_data_fallback()
    st.session_state['df'] = df

# --- 1. CHARGEMENT DU GEOJSON ---
@st.cache_data
def get_geojson():
    repo_url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
    return requests.get(repo_url).json()

geojson_france = get_geojson()

# --- 2. TRAITEMENT DES DONNÉES ---
df["Code du département de l'établissement"] = df["Code du département de l'établissement"].astype(str).str.zfill(2)

# --- 3. DÉBUT DE LA PAGE ---
st.header("🔮 Projection des Risques à 3 ans")
st.info("Cette page présente une vision prédictive basée sur le modèle de scoring de survie.")

# KPI globaux en ligne
nb_total = len(df)
nb_alerte = len(df[df['Statut_Expert'].isin(['🔴 CRITIQUE', '🟠 VIGILANCE'])])
c1, c2, c3 = st.columns(3)
c1.metric("Portefeuille total", f"{nb_total:,}")
c2.metric("Sociétés sous alerte (🔴+🟠)", f"{nb_alerte:,}")
c3.metric("Risque moyen", f"{(nb_alerte/nb_total*100):.2f}%")

st.markdown("---")

# --- 4. GRAPHIQUE 1 : BARRES (PLEINE LARGEUR) ---
st.subheader("📊 Répartition Globale du Risque")
counts = df['Statut_Expert'].value_counts().reset_index()
counts.columns = ['Statut', 'Effectif']
counts['Pourcentage'] = (counts['Effectif'] / counts['Effectif'].sum() * 100)

fig_bar = px.bar(
    counts, x='Statut', y='Effectif', text='Pourcentage',
    color='Statut',
    color_discrete_map={'🟢 SAIN': '#2ecc71', '🟡 OBSERVATION': '#f1c40f', '🟠 VIGILANCE': '#e67e22', '🔴 CRITIQUE': '#e74c3c'},
    height=500
)
fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
fig_bar.update_layout(showlegend=False, plot_bgcolor='rgba(0,0,0,0)', font=dict(size=14))
st.plotly_chart(fig_bar, use_container_width=True)

# --- AJOUT DU COMMENTAIRE SUR LES 4 PROFILS ---

st.info(f"""
**🧐 Comprendre la répartition du risque (Seuil de bascule : 50%)**

Le modèle segmente le portefeuille en **4 profils types** basés sur des critères de structure (âge, effectifs, forme juridique, zone géographique) :

* **🟢 SAIN :** Profils présentant les caractéristiques historiques de longévité les plus fortes.
* **🟡 OBSERVATION :** Entreprises stables, mais présentant un premier signal de fragilité statistique (souvent lié à l'ancienneté ou à la taille de la structure).
* **🟠 VIGILANCE :** Profils dont la configuration structurelle est corrélée à un taux de rotation élevé. 
* **🔴 CRITIQUE :** Entreprises cumulant plusieurs facteurs de vulnérabilité "native".

**Note :** En l'absence de données comptables, ce graphique mesure la **résilience du modèle économique** plutôt que la solvabilité immédiate. Un taux élevé signifie que le portefeuille est composé de structures statistiquement plus exposées aux aléas du marché.
""")
st.markdown("---")

# --- 5. GRAPHIQUE 2 : CARTE CHOROPLÈTHE (PLEINE LARGEUR) ---

st.subheader("🗺️ Intensité Géographique du Risque")
stats_dep = df.groupby("Code du département de l'établissement")['Statut_Expert'].value_counts(normalize=True).unstack().fillna(0)
stats_dep['Taux_Alerte'] = (stats_dep.get('🔴 CRITIQUE', 0) + stats_dep.get('🟠 VIGILANCE', 0)) * 100
df_map = stats_dep.reset_index()

fig_map = px.choropleth(
    df_map,
    geojson=geojson_france,
    locations="Code du département de l'établissement",
    featureidkey="properties.code",
    color='Taux_Alerte',
    color_continuous_scale="RdYlGn_r",
    range_color=(df_map['Taux_Alerte'].min(), df_map['Taux_Alerte'].max()),
    scope='europe',
    height=750 # Carte très grande pour voir les départements
)
fig_map.update_geos(fitbounds="locations", visible=False)
fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
st.plotly_chart(fig_map, use_container_width=True)

# --- AJOUT DU COMMENTAIRE SUR LA CARTE ---
st.info(f"""
**🗺️ Analyse de la répartition territoriale :**

L'intensité du risque affichée sur cette carte (cumul des profils **Vigilance** et **Critique**) met en lumière les disparités régionales basées sur la démographie des entreprises :

* **Zones de forte intensité :** Souvent corrélées aux bassins d'emploi très dynamiques (ex: Île-de-France, Gironde) où le taux de création d'entreprises est élevé. Mathématiquement, une forte concentration de structures jeunes augmente l'indice de risque local.
* **Zones de stabilité :** Territoires présentant un tissu économique plus "mature" avec des entreprises ayant une ancienneté moyenne supérieure, ce qui renforce leur score de résilience structurelle.

**Objectif :** Cette vue permet d'identifier les zones géographiques où le renouvellement économique est le plus fragile et où un accompagnement de proximité pourrait être priorisé.
""")

st.markdown("---")

# --- 6. TENDANCES TOP 5 ---
st.subheader("🔥 Focus : Les zones de tension majeure")
t1, t2 = st.columns(2)

with t1:
    st.write("**📍 Top 5 Départements (Taux d'alerte max)**")
    top_dep = df_map.sort_values('Taux_Alerte', ascending=False).head(5)
    st.table(top_dep.set_index("Code du département de l'établissement")[["Taux_Alerte"]].rename(columns={"Taux_Alerte": "Taux %"}))

with t2:
    st.write("**🏢 Top 5 Secteurs APE (Risque Prédit max)**")
    
    # 1. Calcul des stats
    stats_ape = df.groupby('libelle_section_ape')['Statut_Expert'].value_counts(normalize=True).unstack().fillna(0)
    
    # 2. Sécurité colonnes
    for cat in ['🔴 CRITIQUE', '🟠 VIGILANCE']:
        if cat not in stats_ape.columns: stats_ape[cat] = 0
    
    # 3. Calcul du taux
    stats_ape['Risque (%)'] = (stats_ape['🔴 CRITIQUE'] + stats_ape['🟠 VIGILANCE']) * 100
    
    # 4. Préparation du tableau final pour l'affichage
    top_ape = stats_ape[['Risque (%)']].sort_values('Risque (%)', ascending=False).head(5)
    
    # --- LES DEUX RENOMMAGES ICI ---
    top_ape.index.name = "Secteur d'Activité" 
    top_ape = top_ape.rename(columns={'Risque (%)': 'Risque Prédit (%)'})
    
    st.table(top_ape)

# --- AJOUT DU COMMENTAIRE SUR LES TOP 5 ---
st.info(f"""
**🔍 Décryptage des Zones de Tension :**

Ces classements isolent les segments du portefeuille où la concentration de profils **Vigilance** et **Critique** est la plus forte.

* **Côté Départements :** Les taux élevés signalent des zones où le tissu économique local est composé d'une majorité de structures statistiquement exposées (forte densité de créations récentes ou de micro-structures).
* **Côté Secteurs :** Les scores proches de 90% ne signifient pas une faillite généralisée, mais indiquent que la quasi-totalité des entreprises de ce secteur partagent des caractéristiques de **fragilité structurelle** (ex: absence de capital physique, forte volatilité du métier, ou structures unipersonnelles).

**En résumé :** Ce focus permet de prioriser les actions de surveillance sur les catégories d'entreprises qui, par leur nature même, disposent des plus faibles barrières de protection face aux retournements de conjoncture.
""")

st.divider()