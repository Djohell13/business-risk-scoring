import streamlit as st
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="Audit & Méthodologie", layout="wide")

# --- LOGIQUE DE RÉCUPÉRATION CENTRALISÉE ---
if 'df' in st.session_state and st.session_state['df'] is not None:
    df_preds = st.session_state['df'].copy()
else:
    st.warning("⚠️ Session rafraîchie. Veuillez repasser par la page d'accueil.")
    st.stop()

# --- HARMONISATION DES COLONNES ---

mapping = {
    "Code du département de l'établissement": "dept_code",
    "Economie sociale et solidaire unité légale": "ess_val"
}
df_preds = df_preds.rename(columns=mapping)

# --- TITRE ---
st.title("⚙️ 6. Infrastructure & Ingénierie des Données")
st.markdown("""
Analyse de la chaîne de valeur : du signal brut à la prédiction affinée. 
Cette page détaille la rigueur méthodologique appliquée pour garantir la fiabilité du score **Bouclier**.
""")

st.divider()

# --- SECTION 1 : LE PIPELINE DE DONNÉES ---
st.subheader("🚀 Le Pipeline d'Ingénierie")

# Calculs dynamiques
total_brut = len(df_preds)
nb_vivantes = len(df_preds[df_preds['fermeture'] == 0])
nb_fermees = len(df_preds[df_preds['fermeture'] == 1])
nb_ess = len(df_preds[df_preds['ess_val'] == 1])

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 📥 1. Acquisition")
    st.write("**Source :** Flux SIRENE (Insee).")
    st.write(f"**Volume Brut :** {total_brut:,}".replace(',', ' '), " sociétés analysées.")
    st.caption("Récupération en temps réel des créations, modifications et radiations.")

with col2:
    st.markdown("### 🔍 2. Filtrage")
    st.write(f"**Population cible :** {nb_vivantes:,}".replace(',', ' '), " entités.")
    st.write("**Critères :** SAS & SARL.")
    st.caption("Focus sur le segment le plus dynamique et le plus exposé du tissu français.")

with col3:
    st.markdown("### 🧹 3. Raffinement")
    st.write("**Nettoyage :** Imputation des données manquantes.")
    st.write(f"**Spécificité :** {nb_ess:,}".replace(',', ' '), " acteurs de l'ESS intégrés.")
    st.caption("Traitement des valeurs aberrantes et normalisation sectorielle.")

with col4:
    st.markdown("### 🧪 4. Validation")
    st.write("**Cross-check :** Pappers.")
    st.write(f"**Qualité :** {nb_fermees:,}".replace(',', ' '), " signaux validés.")
    st.caption("Vérification de la véracité des signaux de fermeture.")

st.divider()

# --- SECTION 2 : ARCHITECTURE DU MODÈLE ---
st.subheader("🧠 Intelligence Prédictive")

left_col, right_col = st.columns([1.5, 1])

with left_col:
    with st.container(border=True):
        st.markdown("#### Modélisation AFT (Accelerated Failure Time)")
        st.write("""
        Contrairement à un modèle de classification classique qui dit 'Oui' ou 'Non', notre moteur 
        **XGBoost appliqué à l'Analyse de Survie** mesure la 'vitesse' à laquelle le temps s'écoule pour une entreprise.
        """)
        
        st.markdown("""
        - **Algorithme :** Gradient Boosting (XGBoost)
        - **Fonction de perte :** NLogLik (Negative Log-Likelihood)
        - **Précision :** 1.36 (Capture 86% des trajectoires de dégradation)
        - **Horizon cible :** Dynamique temporelle à 1, 2 et 3 ans.
        """)
        
        st.info("💡 **Pourquoi l'AFT ?** Cela permet de prédire non seulement le risque, mais surtout l'échéance du risque (1, 2 ou 3 ans).")

with right_col:
    with st.container(border=True):
        st.markdown("#### 📊 État du Périmètre Étudié")
        
        # Calcul du ratio réel d'établissements actifs
        ratio = nb_vivantes / total_brut if total_brut > 0 else 0
        
        st.markdown(f"""
        - **Volume total traité :** **{total_brut:,}**
        - **Établissements actifs (Scorés) :** **{nb_vivantes:,}**
        - **Historique de défaillances :** **{nb_fermees:,}**
        """)
        
        st.progress(ratio)
        st.caption(f"Taux d'activité réel du périmètre : {ratio*100:.1f}%")

st.divider()

# --- SECTION 3 : EXPLORATORY DATA ANALYSIS (EDA) ---
st.subheader("📊 Analyse Exploratoire (EDA)")
st.write("""
Avant la mise en production, chaque variable a subi un audit statistique complet pour isoler 
les corrélations réelles des faux signaux (biais géographiques ou saisonniers).
""")

# Calculs dynamiques
nb_depts = df_preds['dept_code'].nunique()
nb_secteurs = df_preds['libelle_section_ape'].nunique()

eda1, eda2, eda3, eda4 = st.columns(4)
eda1.metric("Géographie", f"{nb_depts} Dépts", "Analysés")
eda2.metric("Secteurs", f"{nb_secteurs} Sections", "APE")
eda3.metric("Effectifs", "Signaux Faibles", "RH")
eda4.metric("Juridique", "Gouvernance", "Pérennité")

st.divider()
st.caption("ℹ️ Méthodologie certifiée interne - Mise à jour des modèles : Mars 2026")