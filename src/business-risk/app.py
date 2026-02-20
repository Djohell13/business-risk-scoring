import streamlit as st
import pandas as pd
import s3fs
import os

# 1. Configuration de la page
st.set_page_config(page_title="Observatoire Entreprises", layout="wide")

# --- 2. FONCTION DE CHARGEMENT GÉNÉRIQUE ---
@st.cache_data
def load_s3_file(file_key_name):
    # Récupération hybride (HF / Local)
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID") or st.secrets.get("AWS_ACCESS_KEY_ID")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY") or st.secrets.get("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("AWS_BUCKET_NAME") or st.secrets.get("AWS_BUCKET_NAME")
    file_path = os.environ.get(file_key_name) or st.secrets.get(file_key_name)

    if not all([aws_key, aws_secret, bucket_name, file_path]):
        st.error(f"❌ Configuration AWS incomplète pour {file_key_name}.")
        st.stop()

    # --- PARTIE À NE PAS OUBLIER : LA LECTURE RÉELLE ---
    try:
        # Connexion au système de fichiers S3
        fs = s3fs.S3FileSystem(key=aws_key, secret=aws_secret, anon=False)
        s3_full_path = f"s3://{bucket_name}/{file_path}"
        
        with fs.open(s3_full_path, mode='rb') as f:
            return pd.read_parquet(f)
            
    except Exception as e:
        st.error(f"Erreur lors de la lecture de {file_path} : {e}")
        st.stop()

# --- 3. LOGIQUE DE CHARGEMENT (AVANT LA SIDEBAR) ---
if 'df' not in st.session_state:
    with st.spinner("Chargement de l'Observatoire..."):
        st.session_state['df'] = load_s3_file("AWS_FILE_PATH")

if 'df_preds' not in st.session_state:
    with st.spinner("Chargement des Projections..."):
        st.session_state['df_preds'] = load_s3_file("AWS_PREDS_PATH")

# --- 4. BARRE LATÉRALE (MAINTENANT LES DONNÉES EXISTENT) ---
with st.sidebar:
    st.divider()
    st.markdown("### 📂 Périmètre de l'étude")
    st.warning("""
    **Scope :** SAS & SARL uniquement.  
    **Données :** Entités avec bilans publics.
    """)
    
    st.success(f"📦 Data: {len(st.session_state['df']):,} | 🔮 Preds: {len(st.session_state['df_preds']):,}")

    st.caption("Source des données :")
    st.markdown("[Base SIRENE V3 (Insee)](https://public.opendatasoft.com/explore/dataset/economicref-france-sirene-v3/)")
    
    st.divider()
    st.caption("Stack technique :")
    st.markdown("`Python` | `XGBoost` | `Docker`")
    st.info("Ce dashboard est une vitrine technique de scoring de risque (Survival Analysis).")

# --- 5. CONTENU DE LA PAGE ---
st.title("🚀 Bienvenue sur l'Observatoire des Fermetures")

st.markdown("""
### Décrypter la santé économique du territoire
Cette application permet d'analyser la dynamique des entreprises françaises à travers des indicateurs de survie, de résilience et de risque.
""")

st.info("💡 **Périmètre de l'analyse** : L'étude est basée sur les données des **SAS et SARL** publiant leurs bilans. "
        "Ce focus a pour but d'apporter une fiabilité accrue durant son développement.")

st.divider()
st.write("👈 **Utilisez le menu à gauche** pour explorer les données par région ou consulter les projections de risque.")

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #808495; font-size: 0.85em;'>
        © 2026 Observatoire des Défaillances | <b>Périmètre d'étude :</b> SAS et SARL avec bilans publics uniquement <br>
        <i>Source des données : Base SIRENE & Traitements internes (Modèle V3)</i>
    </div>
    """, 
    unsafe_allow_html=True
)