import streamlit as st
import requests
import pandas as pd
import os

# --- 1. CONFIGURATION DE LA PAGE ---
if "set_page_config" not in st.session_state:
    st.set_page_config(layout="wide", page_title="Business Risk Simulator", page_icon="📈")
    st.session_state["set_page_config"] = True

# URL de l'API Hugging Face
API_URL = "https://djohell-api-business-risk.hf.space/predict"

def render_simulation_page():
    st.title("7. 🧪 Projection Personnalisée de Résilience")
    st.markdown("""
    Saisissez les caractéristiques d'une structure pour interroger le moteur d'apprentissage et obtenir une analyse de survie sur-mesure.
    """)
    st.divider()
    
    # --- 2. RÉCUPÉRATION INTELLIGENTE DES DONNÉES ---
    if 'df' in st.session_state and st.session_state['df'] is not None:
        # 🎯 Récupération instantanée du dataset global chargé à l'accueil
        df = st.session_state['df']
    else:
        # Sécurité Hugging Face si la session a sauté en cours de route
        st.warning("⚠️ Session rafraîchie ou expirée. Veuillez repasser brièvement par la page d'accueil pour réinitialiser l'intelligence économique.")
        st.info("💡 *Pourquoi ? Le dataset global est volumineux et s'initialise uniquement sur la page principale pour optimiser les performances.*")
        st.stop()

    # Identification intelligente des colonnes du dataset
    col_dept = next((c for c in df.columns if "dept" in c.lower() or "département" in c.lower()), None)
    col_ape_code = next((c for c in df.columns if "code_ape" in c.lower() or "ape" in c.lower()), None)
    col_ape_label = next((c for c in df.columns if "libelle" in c.lower() and "ape" in c.lower()), col_ape_code)

    if not col_dept or not col_ape_code:
        st.error("❌ Structure de données source incompatible (colonnes APE ou Dept manquantes).")
        return

    try:
        # Préparation des listes dynamiques pour les selectboxes
        series_deps = df[col_dept].dropna().astype(str)
        liste_deps = sorted([
            d.split('.')[0].zfill(2) if d.replace('.0','').isdigit() else d.upper() 
            for d in series_deps.unique()
        ])
        
        df_ape = df[[col_ape_code, col_ape_label]].drop_duplicates().dropna()
        df_ape['display'] = df_ape[col_ape_label].astype(str) + " (" + df_ape[col_ape_code].astype(str) + ")"
        
        dict_ape = pd.Series(df_ape[col_ape_code].values, index=df_ape['display']).to_dict()
        liste_labels_ape = sorted(list(dict_ape.keys()))
    except Exception as e:
        st.error(f"💥 Erreur lors de la préparation des filtres : {e}")
        return

    # --- 3. FORMULAIRE DE SIMULATION ---
    with st.container(border=True):
        with st.form("simulation_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🏢 Identité & Taille")
                age = st.slider("Âge de l'entreprise (années)", 0.0, 8.0, 0.0, 0.5)
                effectif = st.selectbox("Tranche d'effectif", 
                                       options=[0, 1, 2, 3, 11, 12], 
                                       format_func=lambda x: {0:"0 salarié", 1:"1-2 salariés", 2:"3-5 salariés", 
                                                              3:"6-9 salariés", 11:"10-19 salariés", 12:"20-49 salariés"}.get(x, f"Code {x}"),
                                       index=1)
                is_ess = st.selectbox("Structure ESS", options=[0, 1], 
                                    format_func=lambda x: "Oui (Économie Sociale)" if x == 1 else "Non")

            with col2:
                st.subheader("📍 Localisation & Secteur")
                dep_choisi = st.selectbox("Département", options=liste_deps, 
                                        index=liste_deps.index("13") if "13" in liste_deps else 0)
                ape_label = st.selectbox("Secteur d'activité (APE)", options=liste_labels_ape)
                ape_code = str(dict_ape[ape_label]).zfill(2)[:2]
                juridique = st.selectbox("Forme Juridique", options=["5499", "5710"], 
                                       format_func=lambda x: "SARL / EURL" if x == "5499" else "SAS / SASU")

            submit = st.form_submit_button("Lancer le diagnostic prédictif 🚀", use_container_width=True)

    # --- 4. TRAITEMENT ET AFFICHAGE DES RÉSULTATS ---
    if submit:
        # Headers avec authentification sécurisée par Token
        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            try:
                hf_token = st.secrets.get("HF_TOKEN")
            except:
                hf_token = None

        if not hf_token:
            st.error("❌ Clé d'authentification 'HF_TOKEN' manquante. Impossible de contacter l'API.")
            return

        headers = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "age_estime": float(age),
            "Tranche_effectif_num": int(effectif),
            "code_departement": str(dep_choisi),
            "code_ape": ape_code,
            "categorie_juridique": str(juridique),
            "is_ess": int(is_ess)
        }

        try:
            with st.spinner("Analyse par l'IA en cours..."):
                response = requests.post(API_URL, json=payload, headers=headers, timeout=15)
                
            if response.status_code == 200:
                res = response.json()
                diag = res.get("diagnostic", {})
                profil = str(diag.get("profil_global", "INCONNU")).upper().strip()
                
                # --- LOGIQUE D'AFFICHAGE COMPLÈTE ET EFFETS ANIMÉS ---
                color, icon, comment = "grey", "❓", "Diagnostic atypique détecté."
                
                if "SAIN" in profil:
                    st.balloons()
                    color, icon = "green", "✅"
                    comment = "La structure présente des indicateurs favorables de résilience. Votre modèle économique semble solide face aux contraintes actuelles."
                elif "OBSERVATION" in profil:
                    color, icon = "blue", "🧐"
                    comment = "Profil stable, mais certains indicateurs sectoriels suggèrent de rester attentif à l'évolution du marché."
                elif "VIGILANCE" in profil:
                    color, icon = "orange", "⚠️"
                    comment = "Attention : Des facteurs de vulnérabilité (âge, secteur ou zone géographique) pèsent sur la pérennité statistique."
                elif "CRITIQUE" in profil:
                    st.snow()
                    color, icon = "red", "🚨"
                    comment = "Attention : Des éléments laissent à penser que des difficultés pourraient survenir à moyen terme. Il est recommandé de renforcer votre stratégie et de solliciter un accompagnement spécialisé."

                st.divider()
                st.markdown(f"### {icon} Diagnostic : :{color}[{profil}]")
                
                # Bloc des Métriques de Risque Temporel
                probs = res.get("probabilites_fermeture", {})
                m1, m2, m3 = st.columns(3)
                m1.metric("Risque à 1 an", probs.get("1_an", "N/A"))
                m2.metric("Risque à 2 ans", probs.get("2_ans", "N/A"))
                m3.metric("Risque à 3 ans", probs.get("3_ans", "N/A"))

                # Affichage de l'analyse textuelle
                st.subheader("💡 Analyse Stratégique")
                st.info(comment)

            else:
                st.error(f"❌ Erreur API ({response.status_code}) : Impossible de récupérer les prédictions.")
                
        except Exception as e:
            st.error(f"❌ Erreur de connexion avec l'API : {e}")

    # --- 5. MENTION LÉGALE (DISCLAIMER) ---
    st.markdown("---")
    with st.expander("⚖️ Mentions légales et limites de responsabilité", expanded=False):
        st.caption("""
        **Avertissement important :** Ce simulateur est un outil pédagogique basé sur un modèle d'intelligence artificielle entraîné sur des données historiques. 
        
        1. **Nature de l'outil :** Le scoring et les probabilités affichés sont des estimations statistiques et ne constituent en aucun cas un conseil financier, juridique ou une garantie de survie/faillite.
        2. **Responsabilité :** L'auteur de cette application décline toute responsabilité quant aux décisions (investissement, restructuration, etc.) prises sur la base de ces résultats. Chaque entreprise est unique et ce diagnostic automatisé ne remplace pas l'expertise d'un expert-comptable ou d'un conseiller en gestion.
        3. **Données :** Les prédictions dépendent de la qualité des informations saisies et des tendances macro-économiques globales qui peuvent évoluer rapidement.
        
        En utilisant ce simulateur, vous reconnaissez que ces résultats n'engagent que votre propre interprétation.
        """)

if __name__ == "__main__":
    render_simulation_page()