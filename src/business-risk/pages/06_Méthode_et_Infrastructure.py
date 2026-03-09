import streamlit as st

# --- CONFIGURATION ---
st.set_page_config(page_title="Audit & Méthodologie", layout="wide")

# --- TITRE ---
st.title("⚙️ 6. Infrastructure & Ingénierie des Données")
st.markdown("""
Analyse de la chaîne de valeur : du signal brut à la prédiction affinée. 
Cette page détaille la rigueur méthodologique appliquée pour garantir la fiabilité du score **Bouclier**.
""")

st.divider()

# --- SECTION 1 : LE PIPELINE DE DONNÉES ---
st.subheader("🚀 Le Pipeline d'Ingénierie")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 📥 1. Acquisition")
    st.write("**Source :** Flux SIRENE (Insee).")
    st.write("**Volume Brut :** 3,4 Millions de sociétés analysées.")
    st.caption("Récupération en temps réel des créations, modifications et radiations.")

with col2:
    st.markdown("### 🔍 2. Filtrage")
    st.write("**Population cible :** 1,2 Millions d'entités.")
    st.write("**Critères :** SAS & SARL, < 50 salariés, Bilans publics.")
    st.caption("Focus sur le segment le plus dynamique et le plus exposé du tissu français.")

with col3:
    st.markdown("### 🧹 3. Raffinement")
    st.write("**Nettoyage :** Imputation des données manquantes.")
    st.write("**Spécificité :** Intégration complète de l'ESS (Économie Sociale et Solidaire).")
    st.caption("Traitement des valeurs aberrantes et normalisation sectorielle.")

with col4:
    st.markdown("### 🧪 4. Validation")
    st.write("**Cross-check :** Pappers.")
    st.write("**Qualité :** Audit de cohérence sur les derniers statuts juridiques.")
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
        """)
        
        st.info("💡 **Pourquoi l'AFT ?** Cela permet de prédire non seulement le risque, mais surtout l'échéance du risque (1, 2 ou 3 ans).")

with right_col:
    with st.container(border=True):
        st.markdown("#### Distribution de la Population")
        st.markdown(f"""
        - **Total SIRENE :** 3 400 000
        - **Filtre Forme Juridique (SAS/SARL) :** - 1 200 000
        - **Filtre Taille (< 50 sal) :** - 800 000
        - **Filtre Bilans Publics :** - 200 000
        ---
        - **Population Finale Étudiée : 1 200 000**
        """)
        st.progress(0.35)
        st.caption("Ratio de sélection : 35% du tissu économique global.")

st.divider()

# --- SECTION 3 : EXPLORATORY DATA ANALYSIS (EDA) ---
st.subheader("📊 Analyse Exploratoire (EDA)")
st.write("""
Avant la mise en production, chaque variable a subi un audit statistique complet pour isoler 
les corrélations réelles des faux signaux (biais géographiques ou saisonniers).
""")

# Rappel des piliers
eda1, eda2, eda3, eda4 = st.columns(4)
eda1.metric("Géographie", "95 Dépts", "Analysés")
eda2.metric("Secteurs", "21 Sections", "APE")
eda3.metric("Effectifs", "Signaux Faibles", "RH")
eda4.metric("Juridique", "Gouvernance", "Pérennité")

st.divider()
st.caption("ℹ️ Méthodologie certifiée interne - Mise à jour des modèles : Mars 2026")