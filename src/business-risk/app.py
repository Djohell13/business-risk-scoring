import streamlit as st
import pandas as pd
import s3fs
import os

st.set_page_config(page_title="Observatoire Entreprises", layout="wide")

with st.sidebar:
    st.divider()
    st.markdown("### 📂 Périmètre de l'étude")

    st.warning("""
    **Scope :** SAS & SARL uniquement.  
    **Données :** Entités avec bilans publics.
    """)
    
    st.caption("Source des données :")
    st.markdown("[Base SIRENE V3 (Insee)](https://public.opendatasoft.com/explore/dataset/economicref-france-sirene-v3/)")
    
    st.divider()
    st.caption("Stack technique :")
    st.markdown("`Python` | `XGBoost` | `Docker`")

    st.info("Ce dashboard est une vitrine technique de scoring de risque (Survival Analysis).")

@st.cache_data
def load_data():

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
            st.error("Identifiants AWS introuvables (Environnement et Secrets).")
            st.stop()


    try:
        fs = s3fs.S3FileSystem(key=aws_key, secret=aws_secret, anon=False)
        s3_path = f"s3://{bucket_name}/{file_path}"
        
        with fs.open(s3_path, mode='rb') as f:
            return pd.read_parquet(f)
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier S3 : {e}")
        st.stop()

# --- LOGIQUE DE SESSION STATE ---
if 'df' not in st.session_state:
    with st.spinner("Chargement des données depuis S3..."):
        st.session_state['df'] = load_data()

st.title("🚀 Bienvenue sur l'Observatoire des Défaillances")

st.markdown("""
### Décrypter la santé économique du territoire
Cette application permet d'analyser la dynamique des entreprises françaises à travers des indicateurs de survie, de résilience et de risque.
""")

st.info("💡 **Périmètre de l'analyse** : L'étude est basée sur les données des **SAS et SARL** publiant leurs bilans. "
        "Ce focus garantit une fiabilité accrue sur les indicateurs financiers présentés.")

st.divider()
st.write("👈 **Utilisez le menu à gauche** pour explorer les données par région ou par secteur.")

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #808495; font-size: 0.85em;'>
        © 2024 Observatoire des Défaillances | <b>Périmètre d'étude :</b> SAS et SARL avec bilans publics uniquement <br>
        <i>Source des données : Base SIRENE & Traitements internes</i>
    </div>
    """, 
    unsafe_allow_html=True
)