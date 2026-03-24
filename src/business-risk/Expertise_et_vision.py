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

# --- 3. CHARGEMENT AVEC STATUS ---

if 'df' not in st.session_state:
    with st.status("🔮 Initialisation de l'Observatoire...", expanded=False) as status:
        st.write("Connexion au bucket S3...")

        master_data = load_s3_file("AWS_FILE_PATH")
        
        if master_data is not None:
            st.write("Calcul des univers d'analyse...")

            st.session_state['df'] = master_data

            df_active = master_data[master_data['Statut_Expert'] != '⚫ FERMÉ'].copy()

            if 'Statut_Expert' in df_active.columns:
                df_active['Statut_Expert'] = df_active['Statut_Expert'].cat.remove_unused_categories()
            
            st.session_state['df_preds'] = df_active

            st.write("Récupération de l'identité visuelle...")
            st.session_state['user_photo'] = load_s3_image("AWS_MY_PHOTO_PATH")

            st.write("✅ Tous les modules sont opérationnels.")
            st.write(f"📊 {len(master_data):,} entreprises indexées.")
            
            status.update(label="Système prêt !", state="complete")
        else:
            status.update(label="⚠️ Erreur : Impossible de charger le fichier Master", state="error")
            st.error("Vérifiez la configuration de la clé AWS_FILE_PATH dans vos secrets.")

# --- 4. BARRE LATÉRALE ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=60)
    st.title("Framework")
    with st.container(border=True):
        st.markdown("**Scope d'analyse**")
        st.caption("• SAS & SARL France\n• Bilans Publics\n• 2008-2026")
    
    st.divider()

# --- 5. CONTENU PRINCIPAL ---
with st.container(border=True):

    col1, col2 = st.columns([1, 4], gap="large")
    
    with col1:
 
        if st.session_state.get('user_photo'):
 
            st.image(st.session_state['user_photo'], width=220) 
        else:

            st.container(height=220) 
            st.info("Photo Provider")
        
        st.subheader("Joël TERMONDJIAN")
        st.markdown("🎓 **20 ans d'Expertise Bancaire & Data Analyst**")

    with col2:

        st.markdown("<h1 style='margin-top:0;'>🛡️ Bouclier Entreprises : SAS & SARL</h1>", unsafe_allow_html=True)
        st.markdown("### **Intelligence Risque & Sauvegarde du Tissu Économique**")
        
        st.markdown("### *« Le scoring doit être un levier d'accompagnement et non pas une sentence. »*")
        
        st.write("""
    Fort de deux décennies dans l'octroi de crédits, j'ai conçu cet outil pour combler le fossé 
    entre la donnée brute et la réalité du terrain. 
    **Sa mission est triple :**
    """)

        with st.container():
            p1, p2, p3 = st.columns(3)
            p1.info("**🏦 Banques**\n\nOptimiser le risque relationnel et anticiper les défauts pour **protéger son PNB**.")
            p2.success("**📊 Comptables**\n\nCibler les dossiers critiques pour transformer le risque client en **mission d'accompagnement à haute valeur ajoutée**.")
            p3.warning("**🏛️ Institutions**\n\nAppuyer les décisions macro pour limiter les fermetures et **soutenir l'économie**.")

st.divider()

# Section avec Onglets
tab1, tab2 = st.tabs(["🎯 Ma Vision de l'Analyse", "🛠️ Stack & Engagement"])


with tab1:
    st.markdown("#### 🔍 Les 4 Piliers de l'Analyse Structurelle")
    
    # --- LES 4 ITEMS ---
    p1, p2, p3, p4 = st.columns(4)
    
    with p1:
        with st.container(border=True):
            st.markdown("#### ⏳ Ancienneté")
            st.write("**Maturité & Survie**")
            st.caption("Dépasser le 'Cap des 3 ans' : analyse de la courbe de survie critique.")
    
    with p2:
        with st.container(border=True):
            st.markdown("#### 🏭 Secteurs")
            st.write("**Dynamiques Métiers**")
            st.caption("Cycles de défaillance spécifiques et identification des secteurs sous tension.")

    with p3:
        with st.container(border=True):
            st.markdown("#### ⚖️ Structure")
            st.write("**Poids de l'Entité**")
            st.caption("L'impact de la forme juridique et des effectifs sur la résilience réelle.")

    with p4:
        with st.container(border=True):
            st.markdown("#### 📍 Territoire")
            st.write("**Écosystème Local**")
            st.caption("Analyse des clusters : pourquoi certains départements résistent mieux ?")

    st.info("""
    **En bref :** Mon approche balaye les signaux faibles qui précipitent réellement la fermeture. 
    L'analyse ne se limite pas aux chiffres comptables, elle décortique la structure même de l'entreprise.
    """)

    st.divider()

    # --- ANALYSE & SCORING (Plus petits en bas) ---
    st.markdown("##### ⚙️ Méthodologie & Objectifs")
    c1, c2 = st.columns(2, gap="medium")
    
    with c1:
        with st.container(border=True):
            st.markdown("###### 📊 Analyse Rétrospective")
            st.caption("""
            **Comprendre le passé.**
            - Étude des cycles depuis 2008.
            - Secteurs "atypiques" post-COVID.
            - Pipeline ETL robuste (Data INPI).
            """)
            
    with c2:
        with st.container(border=True):
            st.markdown("###### 🔮 Scoring Prédictif")
            st.caption("""
            **Anticiper l'avenir.**
            - Variables réelles (Effectifs, Âge).
            - Horizon de risque à 3 ans.
            - Aide à la décision préventive.
            """)

with tab2:
    with st.container(border=True):
        st.markdown("""
        **🚀 Engagement de développement** :
        L'outil évolue en continu. Prochaine étape : intégration d'une couche d'analyse financière approfondie via API.
        """)
    st.caption("✨ Je vous invite à explorer cet outil conçu pour les professionnels exigeants.")