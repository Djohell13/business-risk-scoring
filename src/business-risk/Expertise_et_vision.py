import streamlit as st
import pandas as pd
import pyarrow.parquet as pq
import s3fs
import os
import requests
from PIL import Image
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Projet Égide | Expertise & Vision", layout="wide")

# CSS (inchangé)
st.markdown("""
    <style>
    .main-title { color: #FFFFFF; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); margin-top: 0; }
    .intro-text { font-size: 1.25rem; line-height: 1.6; color: #E0E7FF; margin-bottom: 25px; }
    .card-pilier { background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid #1E3A8A; height: 180px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }
    .card-title { color: #1E3A8A; font-size: 0.85rem; font-weight: bold; margin-bottom: 5px; text-transform: uppercase; }
    .card-value { color: #000000; font-size: 1.2rem; font-weight: bold; margin-bottom: 10px; }
    .card-desc { color: #444444; font-size: 0.85rem; line-height: 1.3; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONCTIONS DE CHARGEMENT ---
@st.cache_data(show_spinner=False)
def load_global_dataset_s3():
    """Moteur unique de chargement de la base Parquet globale"""
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID") or st.secrets.get("AWS_ACCESS_KEY_ID")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY") or st.secrets.get("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("AWS_BUCKET_NAME") or st.secrets.get("AWS_BUCKET_NAME")
    file_path = os.environ.get("AWS_FILE_PATH") or st.secrets.get("AWS_FILE_PATH")

    if not aws_key: return None
    try:
        fs = s3fs.S3FileSystem(key=aws_key, secret=aws_secret, anon=False)
        s3_path = f"s3://{bucket_name}/{file_path}"
        with fs.open(s3_path, mode='rb') as f:
            df_loaded = pd.read_parquet(f)
        
        # Formatage de sécurité pour les dates
        if "Date_fermeture_finale" in df_loaded.columns:
            df_loaded["Date_fermeture_finale"] = pd.to_datetime(df_loaded["Date_fermeture_finale"], errors='coerce')
        return df_loaded
    except Exception as e:
        st.error(f"Erreur critique S3 lors du chargement initial : {e}")
        return None

@st.cache_data(show_spinner=False)
def load_s3_image(file_key_name):
    keys = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_BUCKET_NAME"]
    creds = {k: os.environ.get(k) or st.secrets.get(k) for k in keys}
    file_path = os.environ.get(file_key_name) or st.secrets.get(file_key_name)
    try:
        fs = s3fs.S3FileSystem(key=creds["AWS_ACCESS_KEY_ID"], secret=creds["AWS_SECRET_ACCESS_KEY"], anon=False)
        with fs.open(f"s3://{creds['AWS_BUCKET_NAME']}/{file_path}", mode='rb') as f:
            return Image.open(io.BytesIO(f.read()))
    except: return None

def check_space(space_id, token):
    if not space_id or not token: return "OFFLINE"
    try:
        res = requests.get(f"https://huggingface.co/api/spaces/{space_id}", headers={"Authorization": f"Bearer {token}"}, timeout=3)
        return res.json().get("runtime", {}).get("stage", "UNKNOWN")
    except: return "OFFLINE"

# --- 3. INITIALISATION CENTRALISÉE ---
if 'initialized' not in st.session_state:
    with st.status("🔮 Initialisation de l'intelligence économique...", expanded=True) as status:
        hf_token = os.environ.get("HF_TOKEN") or st.secrets.get("HF_TOKEN")
        
        st.write("📡 1. Connexion aux infrastructures d'API...")
        st.session_state['status_api'] = check_space(os.environ.get("SPACE_API_ID") or st.secrets.get("SPACE_API_ID"), hf_token)
        st.session_state['status_mlflow'] = check_space(os.environ.get("SPACE_MLFLOW_ID") or st.secrets.get("SPACE_MLFLOW_ID"), hf_token)
        
        st.write("🗂️ 2. Téléchargement et indexation de la base de données globale S3...")
        df_global = load_global_dataset_s3()
        
        if df_global is not None:
            # 🎯 On injecte la base pour TOUTES les pages de l'application
            st.session_state['df'] = df_global
            st.session_state['total_rows'] = len(df_global)
            status.update(label="Système prêt & Données synchronisées !", state="complete")
        else:
            st.session_state['total_rows'] = 5816238
            status.update(label="⚠️ Base de données S3 indisponible", state="error")
            st.stop()
            
        st.write("📸 3. Chargement des ressources visuelles...")
        st.session_state['user_photo'] = load_s3_image("AWS_MY_PHOTO_PATH")
        
        st.session_state['initialized'] = True
        status.update(label="Système prêt !", state="complete")

# --- 4. SIDEBAR & UI (Identique à ton code) ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=50)
    st.title("Framework")
    with st.container(border=True):
        st.markdown("**Périmètre d'analyse**")
        st.caption(f"• {st.session_state['total_rows']:,}".replace(",", " ") + " Sociétés (SAS/SARL)")
    
    # Affichage dynamique des status
    for key, label in [('status_api', 'API'), ('status_mlflow', 'MLflow')]:
        val = st.session_state[key]
        color = "🟢" if "RUNNING" in val else "🔴"
        st.caption(f"{color} **{label} :** {val}")

# --- 5. CONTENU PRINCIPAL ---
with st.container(border=True):
    c1, c2 = st.columns([1, 3], gap="large")
    
    with c1:
        if st.session_state.get('user_photo'):
            st.image(st.session_state['user_photo'], use_container_width=True)
        st.markdown("### Joël TERMONDJIAN")
        st.caption("🚀 Expert Banque & Data Scientist")
        
    with c2:
        st.markdown("<h1 class='main-title'>🛡️ Projet Égide</h1>", unsafe_allow_html=True)
        st.markdown("""
            <p class='intro-text'>
            Carnet de santé prédictif pour l'entreprise. 
            L'intelligence artificielle analyse les indicateurs structurels pour établir un diagnostic des besoins 
            nécessaires à 1, 2 et 3 ans afin de garantir une croissance pérenne.
            </p>
            """, unsafe_allow_html=True)
        
        # --- SECTION AMBITION ---
        st.markdown("#### 🎯 Ambitions : Planification des leviers de soutien")
        a1, a2 = st.columns(2)
        with a1:
            st.markdown("""
            - **Anticipation de Trésorerie :** Identifier les cycles nécessitant un renforcement des lignes de court terme (indice de besoin financier).
            - **Soutien Social & Fiscal :** Planifier les moments clés pour solliciter des dispositifs d'aide ou d'étalement (ex: URSSAF).
            """)
        with a2:
            st.markdown("""
            - **Conseil Stratégique :** Apporter aux experts-comptables une vision prospective pour un accompagnement adapté et cadencé.
            - **Facilitation d'Investissement :** Détecter les fenêtres d'opportunité pour le financement d'actifs et l'accès aux aides publiques.
            """)

        st.write("") 
        p1, p2, p3 = st.columns(3)
        p1.info("**🏦 Banques**\n\nPasser d'une analyse de risque à une approche de conseil en financement proactif.")
        p2.success("**📊 Experts-comptables**\n\nÉtablir une feuille de route stratégique basée sur les besoins réels de l'entreprise.")
        p3.warning("**🏛️ Institutions**\n\nPiloter la vitalité du tissu local en ciblant les leviers de soutien.")

st.divider()

# --- 6. VISION STRATÉGIQUE ---
st.markdown("### 🎯 Ma Vision de l'Analyse")
st.write("L'analyse ne se limite pas aux chiffres, elle décrypte l'ADN profond de l'entreprise.")
st.write("")
v1, v2, v3, v4 = st.columns(4)

def render_pilier(titre, valeur, desc):
    st.markdown(f"""<div class="card-pilier"><div class="card-title">{titre}</div><div class="card-value">{valeur}</div><div class="card-desc">{desc}</div></div>""", unsafe_allow_html=True)

with v1: render_pilier("⏳ MATURITÉ", "Survie critique", "Analyse des cycles de vie post-création.")
with v2: render_pilier("🏭 SECTEURS", "Tensions Métiers", "Identification des risques systémiques.")
with v3: render_pilier("⚖️ STRUCTURE", "Résilience", "Impact de la forme juridique et des effectifs.")
with v4: render_pilier("📍 TERRITOIRE", "Effet Cluster", "Dynamiques de l'écosystème local.")

st.write("")
st.info("""
**En bref :** Cette méthode combine analyse sectorielle et indicateurs structurels pour une vision préventive du risque. 
L'objectif est de comprendre la mécanique de l'entreprise pour mieux protéger son avenir.
""")
st.caption("✨ Application conçue pour l'aide à la décision et le pilotage des risques d'entreprises.")