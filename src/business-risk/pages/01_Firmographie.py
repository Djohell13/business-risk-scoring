import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import s3fs
import os

# 1. CONFIGURATION
st.set_page_config(page_title="Firmographie - Diagnostic", layout="wide")

@st.cache_data
def load_data_fallback():
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
            return None

    try:
        fs = s3fs.S3FileSystem(key=aws_key, secret=aws_secret, anon=False)
        s3_path = f"s3://{bucket_name}/{file_path}"
        with fs.open(s3_path, mode='rb') as f:
            return pd.read_parquet(f)
    except Exception as e:
        st.error(f"Erreur de connexion S3 : {e}")
        return None

# --- LOGIQUE DE RÉCUPÉRATION DU DF ---
if 'df' in st.session_state and st.session_state['df'] is not None:
    df = st.session_state['df']
else:
    with st.spinner("🔄 Récupération des données depuis S3..."):
        df = load_data_fallback()
        if df is not None:
            st.session_state['df'] = df
        else:
            st.error("❌ Impossible de charger les données. Vérifiez vos secrets AWS.")
            st.stop()

# --- 2. FILTRES SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuration")
    st.write("Personnalisez l'affichage")
    st.divider() 
    
    dept_options = ["Toute la France"] + sorted(df["Code du département de l'établissement"].unique().tolist())
    dept_sel = st.selectbox(
        "Choisir un département :", 
        options=dept_options,
        index=0
    )
    
    if dept_sel == "Toute la France":
        df_selection = df.copy()
        label_zone = "l'ensemble de la France"
        count_ent = len(df)
    else:
        df_selection = df[df["Code du département de l'établissement"] == dept_sel]
        label_zone = f"le département {dept_sel}"
        count_ent = len(df_selection)

    st.caption(f"📍 Périmètre : {count_ent:,} établissements".replace(',', ' '))
    st.divider()

# --- 3. CONTENU DE LA PAGE (ACCUEIL & CONTEXTE) ---
st.title("🚀 Observatoire des Fermetures : Analyse & Diagnostic")

with st.container():
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.markdown(f"""
        ### Bienvenue sur l'outil d'aide à la décision
        Cet observatoire a été conçu pour décrypter la dynamique économique sur **{label_zone}** en se concentrant sur la **résilience structurelle** des entreprises.
        
        **L'objectif :** Comprendre les cycles de défaillance passés pour mieux identifier les signaux faibles de demain.
        """)
    with col_b:
        st.info("""
        **Périmètre de l'étude :**
        - 🏛️ **Formes :** SAS & SARL
        - 📄 **Données :** Bilans publics (SIRENE)
        - 📍 **Zone :** France Entière & DOM
        """)

# --- SECTION MÉTHODOLOGIE ---
st.markdown("""
    <div style="
        background-color: rgba(70, 130, 180, 0.1); 
        padding: 20px; 
        border-radius: 10px; 
        border-left: 5px solid #4682B4; 
        margin-bottom: 25px;
    ">
        <h4 style="margin-top: 0; color: #4682B4;">🔍 Note Méthodologique</h4>
        <p>Contrairement aux analyses financières classiques, cet observatoire repose sur un <b>modèle de Diagnostic de Survie</b>. 
        L'analyse se concentre sur la <b>solidité du profil</b> (âge, structure juridique, taille, secteur) pour isoler les facteurs de risque intrinsèques.</p>
        <small><i>Ce diagnostic historique sert de base de connaissance au modèle de projection (Page 5).</i></small>
    </div>
    """, unsafe_allow_html=True)

st.divider()

df_selection["Date_fermeture_finale"] = pd.to_datetime(df_selection["Date_fermeture_finale"], errors='coerce')

# On calcule les années min et max sur les dates valides de la sélection
annee_min = df_selection["Date_fermeture_finale"].dt.year.min()
annee_max = df_selection["Date_fermeture_finale"].dt.year.max()

# Sécurité : définition du label et gestion des cas vides
if pd.isna(annee_min) or pd.isna(annee_max):
    periode_label = "Période actuelle"
    nb_annees = 1 
else:
    periode_label = f"{int(annee_min)} — {int(annee_max)}"
    nb_annees = (annee_max - annee_min + 1)


# --- 2. CALCULS DES INDICATEURS ---
df_fermes = df_selection[df_selection["fermeture"] == 1]
total_fermetures = len(df_fermes)

# TAUX JUDICIEUX : Taux de défaillance ANNUEL moyen

taux_annuel = (df_selection["fermeture"].mean() * 100) / nb_annees
age_moyen = df_fermes["age_estime"].mean() if total_fermetures > 0 else 0


# --- 3. AFFICHAGE DES KPI ---
st.subheader(f"📊 État des lieux : {label_zone}")
st.markdown(f"🗓️ **Période d'analyse :** {periode_label} ({int(nb_annees)} ans)")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Fermetures", f"{total_fermetures:,}".replace(",", " "), 
              help=f"Nombre total de cessations enregistrées sur {int(nb_annees)} ans.")
with col2:
    st.metric("Taux de Défaillance Annuel", f"{taux_annuel:.2f} %", 
              help="Moyenne annuelle du taux de fermeture sur la période.")
with col3:
    st.metric("Âge moyen au dépôt", f"{age_moyen:.1f} ans")

st.divider()

# --- 5. GRAPHIQUES ---

# Graphique 1 : Âge
st.subheader("🕰️ Analyse de la survie selon l'âge")
df_plot = df_selection.assign(Statut = df_selection["fermeture"].map({0: "Ouvertes", 1: "Fermées"}))
fig_age = px.histogram(
    df_plot, x="age_estime", color="Statut", barmode="group",
    color_discrete_map={"Ouvertes": "#2ecc71", "Fermées": "#e74c3c"}, 
    category_orders={"Statut": ["Ouvertes", "Fermées"]},
    template='plotly_white', height=450
)
st.plotly_chart(fig_age, use_container_width=True)

st.markdown(f"""
    <div style="background-color: rgba(230, 126, 34, 0.05); padding: 15px; border-radius: 8px; border-left: 4px solid #e67e22;">
        💡 <b>Observation clé :</b> On remarque une concentration des fermetures entre <b>2 et 5 ans d'existence</b>. 
        Cette période critique, souvent appelée "vallée de la mort", correspond statistiquement à l'épuisement des aides à la création 
        et au besoin de renouvellement du modèle économique initial. L'âge moyen au dépôt (<b>{age_moyen:.1f} ans</b>) confirme cette tendance 
        de fragilité précoce.
    </div>
""", unsafe_allow_html=True)

st.divider()

# Graphique 2 : Probabilité
st.subheader("📈 Courbe de risque : Probabilité de fermeture par âge")
df_age_events = (
    df_selection.loc[df_selection["age_estime"].ge(0)]
    .assign(age_estime=lambda x: x["age_estime"].astype(int))
    .groupby("age_estime")["fermeture"]
    .agg(fermetures="sum", observations="count")
    .assign(proba_fermeture=lambda x: (x["fermetures"] / x["observations"]) * 100)
    .reset_index()
)
df_age_events = df_age_events[df_age_events["age_estime"] <= 35]

fig_proba = go.Figure()
fig_proba.add_trace(go.Scatter(
    x=df_age_events["age_estime"], y=df_age_events["proba_fermeture"],
    mode="lines+markers", line=dict(width=3, color='#e67e22')
))
fig_proba.update_layout(template="plotly_white", height=450, xaxis_title="Âge (ans)", yaxis_title="Proba (%)")
st.plotly_chart(fig_proba, use_container_width=True)

# Graphique 3 : Mensuel
st.subheader("📅 Comparaison mensuelle des défaillances (2023-2025)")
df_comp = df_selection[(df_selection["fermeture"] == 1) & (df_selection["Date_fermeture_finale"].notna())].copy()

if not df_comp.empty:
    df_pivot = (
        df_comp.assign(Année=df_comp["Date_fermeture_finale"].dt.year, Mois=df_comp["Date_fermeture_finale"].dt.month)
        .query("Année >= 2023")
        .pivot_table(index="Mois", columns="Année", values="fermeture", aggfunc="count", fill_value=0)
    )
    df_pct = df_pivot.pct_change(axis=1).fillna(0) * 100
    mois_labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]
    
    fig_comp = go.Figure()
    for year in df_pivot.columns:
        fig_comp.add_trace(go.Bar(
            x=mois_labels[:len(df_pivot)], y=df_pivot[year], name=str(year),
            text=[f"{v:+.1f}%" if year != df_pivot.columns[0] else "" for v in df_pct[year]],
            textposition='outside'
        ))
    fig_comp.update_layout(barmode='group', template='plotly_white', height=500)
    st.plotly_chart(fig_comp, use_container_width=True)
else:
    st.info("Données mensuelles insuffisantes pour cette sélection.")
