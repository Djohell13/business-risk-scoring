import streamlit as st
import pandas as pd
import s3fs
import os
from PIL import Image
import io

# --- 1. CONFIGURATION DE LA PAGE ---

st.set_page_config(page_title="Observatoire Entreprises", layout="wide")

# --- 2. FONCTIONS DE CHARGEMENT GÉNÉRIQUES ---

@st.cache_data
def load_s3_file(file_key_name):
    """Charge un fichier Parquet depuis S3"""
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID") or st.secrets.get("AWS_ACCESS_KEY_ID")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY") or st.secrets.get("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("AWS_BUCKET_NAME") or st.secrets.get("AWS_BUCKET_NAME")
    file_path = os.environ.get(file_key_name) or st.secrets.get(file_key_name)

    if not all([aws_key, aws_secret, bucket_name, file_path]):
        st.error(f"❌ Configuration AWS incomplète pour {file_key_name}.")
        st.stop()

    try:
        fs = s3fs.S3FileSystem(key=aws_key, secret=aws_secret, anon=False)
        s3_full_path = f"s3://{bucket_name}/{file_path}"
        with fs.open(s3_full_path, mode='rb') as f:
            return pd.read_parquet(f)
    except Exception as e:
        st.error(f"Erreur lors de la lecture de {file_path} : {e}")
        st.stop()

@st.cache_data
def load_s3_image(file_key_name):
    """Charge une image depuis S3"""
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID") or st.secrets.get("AWS_ACCESS_KEY_ID")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY") or st.secrets.get("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("AWS_BUCKET_NAME") or st.secrets.get("AWS_BUCKET_NAME")
    file_path = os.environ.get(file_key_name) or st.secrets.get(file_key_name)

    if not all([aws_key, aws_secret, bucket_name, file_path]):
        return None 

    try:
        fs = s3fs.S3FileSystem(key=aws_key, secret=aws_secret, anon=False)
        s3_full_path = f"s3://{bucket_name}/{file_path}"
        with fs.open(s3_full_path, mode='rb') as f:
            image_data = f.read()
            return Image.open(io.BytesIO(image_data))
    except Exception:
        return None

# --- 3. LOGIQUE DE CHARGEMENT CENTRALISÉE ---

# Chargement du DataFrame Principal
if 'df' not in st.session_state:
    with st.spinner("Chargement des données..."):
        st.session_state['df'] = load_s3_file("AWS_FILE_PATH")

# Chargement des Prédictions
if 'df_preds' not in st.session_state:
    with st.spinner("Chargement des projections..."):
        st.session_state['df_preds'] = load_s3_file("AWS_PREDS_PATH")

# Chargement de la Photo
if 'user_photo' not in st.session_state:
    st.session_state['user_photo'] = load_s3_image("AWS_MY_PHOTO_PATH")

# --- 4. BARRE LATÉRALE  ---
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
st.title("🚀 Observatoire des Fermetures d'Entreprises")

st.subheader("La donnée haute fidélité pour une analyse de risque sans angle mort.")

st.divider()

# Tentative de chargement de la photo
user_photo = load_s3_image("AWS_MY_PHOTO_PATH")

# --- Section Présentation & Objectifs ---
col1, col2 = st.columns([1, 3], gap="large")

with col1:
    st.markdown("### 👤 L'Auteur")
    if st.session_state.get('user_photo'):
        st.image(st.session_state['user_photo'], width=200)
    else:
        st.warning("Photo non disponible")
    
    st.subheader("Joël TERMONDJIAN")
    st.info("**Expert Bancaire & Data Analyst**")
    st.write("20 ans d'expertise bancaire")

with col2:
    st.markdown("### 🎯 Professionnaliser l'Analyse du Risque")
    
    st.markdown("""
    ### *"Le scoring doit refléter la réalité du terrain et ne plus être une boîte noire."*
    
    Deux décennies au cœur de l'octroi de crédits me permettent de constater que les outils standards manquent souvent de finesse pour capter la trajectoire réelle d'une entreprise. 
    
    La mission de cet Observatoire est de **Démocratiser la donnée haute fidélité** : 
                
    - J'exploite les bilans publics des **SAS et SARL** représentant 80% du tissu économique Français, à travers un outil
    capable de transformer des données complexes en leviers décisionnels limitant les risques.
    """)

    st.markdown("#### 🔍 Une analyse structurée pour des décisions éclairées :")
    
    sub_c1, sub_c2 = st.columns(2)
    with sub_c1:
        st.markdown("""
        * **Analyse Historique** : Comprendre les cycles de fermeture depuis 2008 pour mieux anticiper demain.
        * **Expertise Sectorielle** : Décrypter les zones de fragilité propres à chaque métier.
        """)
    with sub_c2:
        st.markdown("""
        * **Intelligence Territoriale** : Un zoom départemental pour une lecture précise de votre écosystème.
        * **Modélisation Prospective** : Ne plus seulement constater, mais projeter le risque à 3 ans.
        """)

st.warning("🚀 **Engagement de développement** : Evolution prochaine avec l'intégration d'un moteur prédictif interactif et d'une couche d'analyse financière approfondie.")

st.divider()

st.write("✨ *Je vous invite à explorer cet outil conçu pour les professionnels exigeants.*")
