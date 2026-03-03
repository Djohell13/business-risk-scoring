import streamlit as st
import pandas as pd
import s3fs
import os
from PIL import Image
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Expertise & Vision", layout="wide")

# --- 2. FONCTIONS DE CHARGEMENT ---
@st.cache_data(show_spinner=False)
def load_s3_file(file_key_name):
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID") or st.secrets.get("AWS_ACCESS_KEY_ID")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY") or st.secrets.get("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("AWS_BUCKET_NAME") or st.secrets.get("AWS_BUCKET_NAME")
    file_path = os.environ.get(file_key_name) or st.secrets.get(file_key_name)

    if not aws_key: return None
    try:
        fs = s3fs.S3FileSystem(key=aws_key, secret=aws_secret, anon=False)
        s3_path = f"s3://{bucket_name}/{file_path}"
        with fs.open(s3_path, mode='rb') as f:
            return pd.read_parquet(f)
    except Exception: return None

@st.cache_data(show_spinner=False)
def load_s3_image(file_key_name):
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID") or st.secrets.get("AWS_ACCESS_KEY_ID")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY") or st.secrets.get("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("AWS_BUCKET_NAME") or st.secrets.get("AWS_BUCKET_NAME")
    file_path = os.environ.get(file_key_name) or st.secrets.get(file_key_name)

    if not aws_key: return None
    try:
        fs = s3fs.S3FileSystem(key=aws_key, secret=aws_secret, anon=False)
        s3_path = f"s3://{bucket_name}/{file_path}"
        with fs.open(s3_path, mode='rb') as f:
            return Image.open(io.BytesIO(f.read()))
    except Exception: return None

# --- 3. CHARGEMENT AVEC STATUS  ---

if 'df' not in st.session_state:
    with st.status("🔮 Initialisation de l'Observatoire...", expanded=False) as status:
        st.write("Connexion au bucket S3...")
        st.session_state['df'] = load_s3_file("AWS_FILE_PATH")
        
        st.write("Chargement des modèles prédictifs...")
        st.session_state['df_preds'] = load_s3_file("AWS_PREDS_PATH")
        
        st.write("Récupération de l'identité visuelle...")
        st.session_state['user_photo'] = load_s3_image("AWS_MY_PHOTO_PATH")

        st.write("✅ Tous les modules sont opérationnels.")
        st.write(f"📊 {len(st.session_state['df']):,} lignes indexées.")
        
        status.update(label="Système prêt !", state="complete")

# --- 4. BARRE LATÉRALE ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=60)
    st.title("Framework")
    with st.container(border=True):
        st.markdown("**Scope d'analyse**")
        st.caption("• SAS & SARL France\n• Bilans Publics\n• 2008-2026")
    
    st.divider()
    st.markdown("`Python 3.12` | `XGBoost` | `Docker` | `S3` ")

# --- 5. CONTENU PRINCIPAL ---
with st.container(border=True):

    col1, col2 = st.columns([1, 2.5], gap="large")
    
    with col1:
 
        if st.session_state.get('user_photo'):
 
            st.image(st.session_state['user_photo'], width=220) 
        else:

            st.container(height=220) 
            st.info("Photo Provider")
        
        st.subheader("Joël TERMONDJIAN")
        st.markdown("🎓 **Expert Bancaire & Data Analyst**")
        st.caption("⚡ 20 ans d'expertise en gestion du risque")

    with col2:

        st.markdown("<h1 style='margin-top:0;'>🚀 Observatoire des Fermetures</h1>", unsafe_allow_html=True)
        
        st.markdown("### *'Le scoring doit refléter la réalité du terrain et ne plus être une boîte noire.'*")
        
        st.write("""
        Deux décennies au cœur de l'octroi de crédits me permettent de constater que les outils standards 
        manquent souvent de finesse pour capter la trajectoire réelle d'une entreprise.
        """)

        with st.container():
            p1, p2, p3 = st.columns(3)
            p1.info("**Démocratiser**\nLa donnée haute fidélité.")
            p2.success("**Transformer**\nLe complexe en levier.")
            p3.warning("**Anticiper**\n pour sortir de l'historique.")

st.divider()

# Section avec Onglets
tab1, tab2 = st.tabs(["🎯 Ma Vision de l'Analyse", "🛠️ Stack & Engagement"])

with tab1:
    st.markdown("#### Une analyse structurée pour des décisions éclairées")

    c1, c2 = st.columns(2, gap="medium")
    
    with c1:
        with st.container(border=True):

            st.markdown("### 📊 ANALYSE")
            st.markdown("""
            **Rétrospective & Sectorielle**
            * Comprendre les cycles depuis 2008.
            * Décrypter les fragilités métiers.
            """)
            
    with c2:
        with st.container(border=True):
            st.markdown("### 🔮 PROSPECTIVE")
            st.markdown("""
            **Territoriale & Prédictive**
            * Zoom départemental haute précision.
            * Scoring de risque à 3 ans (XGBoost).
            """)

with tab2:
    with st.container(border=True):
        st.markdown("""
        **🚀 Engagement de développement**
        L'outil évolue en continu. Prochaine étape : intégration d'un moteur prédictif 
        interactif et d'une couche d'analyse financière approfondie via API.
        """)
    st.caption("✨ Je vous invite à explorer cet outil conçu pour les professionnels exigeants.")