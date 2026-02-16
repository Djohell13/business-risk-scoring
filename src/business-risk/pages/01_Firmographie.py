import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import s3fs
import os

st.set_page_config(page_title="Firmographie", layout="wide")

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
            st.error("❌ Impossible de charger les données. Vérifiez vos secrets AWS sur Hugging Face.")
            st.stop()


# --- 2. FILTRES SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuration")
    st.write("Personnalisez l'affichage des données")
    st.divider() 
    st.subheader("📍 Périmètre Géographique")
    
    # Préparation des options
    dept_options = ["Toute la France"] + sorted(df["Code du département de l'établissement"].unique().tolist())

    # Sélecteur mis en avant
    dept_sel = st.selectbox(
        "Choisir un département :", 
        options=dept_options,
        index=0,
        help="Sélectionnez un département spécifique pour filtrer l'ensemble des graphiques et indicateurs de la page."
    )
    
    # Indicateur de volume en sidebar
    if dept_sel == "Toute la France":
        count_ent = len(df)
        st.caption(f"🌍 Analyse globale sur {count_ent:,} établissements".replace(',', ' '))
    else:
        count_ent = len(df[df["Code du département de l'établissement"] == dept_sel])
        st.caption(f"📍 Focus Dept {dept_sel} : {count_ent:,} établissements".replace(',', ' '))

    st.divider()

# --- 3. SÉLECTION FINALE & RÉSUMÉ ---
if dept_sel == "Toute la France":
    df_selection = df.copy()
    label_zone = "l'ensemble de la France y compris les DOM"
else:
    df_selection = df[df["Code du département de l'établissement"] == dept_sel]
    label_zone = f"le département {dept_sel}"

st.header("📊 Diagnostic Territorial National")
st.markdown(f"🚩 **Périmètre actuel :** :blue[{label_zone}]")

# 4. TITRE ET KPIs

st.divider()

# --- 1. CALCUL DE LA PÉRIODE (basé sur les dates de fermeture) ---

df_selection["Date_fermeture_finale"] = pd.to_datetime(df_selection["Date_fermeture_finale"], errors='coerce')

# On calcule les années min et max sur les dates valides (non nulles)
annee_min = df_selection["Date_fermeture_finale"].dt.year.min()
annee_max = df_selection["Date_fermeture_finale"].dt.year.max()

# Sécurité : si aucune date n'est trouvée
if pd.isna(annee_min) or pd.isna(annee_max):
    periode_label = "Période actuelle"
else:
    periode_label = f"{int(annee_min)} — {int(annee_max)}"

# --- 2. CALCULS DES INDICATEURS ---
df_fermes = df_selection[df_selection["fermeture"] == 1]
total_fermetures = len(df_fermes)
taux_moyen = (df_selection["fermeture"].mean() * 100)
age_moyen = df_fermes["age_estime"].mean() if total_fermetures > 0 else 0

# --- 3. AFFICHAGE ---
st.markdown(f"🗓️ **Période d'analyse :** {periode_label}")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Fermetures", f"{total_fermetures:,}".replace(",", " "))
with col2:
    st.metric("Taux de Défaillance", f"{taux_moyen:.2f} %")
with col3:
    st.metric("Âge moyen au dépôt", f"{age_moyen:.1f} ans")

st.divider()

# --- Graphique 1 : Comparatif selon l'âge ---
st.subheader("🕰️ Analyse de la survie selon l'âge")

df_plot = df_selection.assign(Statut = df_selection["fermeture"].map({0: "Ouvertes", 1: "Fermées"}))

fig_age = px.histogram(
    df_plot, 
    x="age_estime", 
    color="Statut",
    barmode="group",
    color_discrete_map={"Ouvertes": "#2ecc71", "Fermées": "#e74c3c"}, 
    category_orders={"Statut": ["Ouvertes", "Fermées"]},
    template='plotly_white'
)

fig_age.update_layout(
    xaxis_title="Âge estimé (ans)",
    yaxis_title="Nombre de sociétés",
    xaxis=dict(dtick=1), 
    legend_title_text='État actuel',
    height=500
)


st.plotly_chart(fig_age, use_container_width=True)

st.divider()

# --- Graphique 2 : Courbe de probabilité de fermeture ---
st.subheader("📈 Courbe de risque : Probabilité de fermeture par âge")

# 1. Calcul des probas sur les données filtrées (df_selection)
df_age_events = (
    df_selection
    .loc[df_selection["age_estime"].ge(0)]
    .assign(age_estime=lambda x: x["age_estime"].astype(int))
    .groupby("age_estime")["fermeture"]
    .agg(fermetures="sum", observations="count")
    .assign(proba_fermeture=lambda x: (x["fermetures"] / x["observations"]) * 100)
    .reset_index()
)

df_age_events = df_age_events[df_age_events["age_estime"] <= 35]

fig_proba = go.Figure()

fig_proba.add_trace(go.Scatter(
    x=df_age_events["age_estime"],
    y=df_age_events["proba_fermeture"],
    mode="lines+markers",
    name="Taux de fermeture",
    line=dict(width=3, color='#e67e22'),
    marker=dict(size=6),
    hovertemplate="Âge: %{x} ans<br>Proba: %{y:.2f}%<extra></extra>"
))

# 3. Ajustements
fig_proba.update_layout(
    xaxis_title="Années d'existence",
    yaxis_title="Probabilité de fermeture (%)",
    template="plotly_white",
    hovermode="x unified",
    height=500
)

st.plotly_chart(fig_proba, use_container_width=True)

st.divider()

# ------ Graph 3 

st.subheader("📅 Comparaison mensuelle de 2023 à 2025")

# 1. Pipeline de données

df_comp = df_selection[(df_selection["fermeture"] == 1) & (df_selection["Date_fermeture_finale"].notna())].copy()

if not df_comp.empty:
    df_pivot = (
        df_comp.assign(
            Année=df_comp["Date_fermeture_finale"].dt.year, 
            Mois=df_comp["Date_fermeture_finale"].dt.month
        )
        .query("Année >= 2023")
        .pivot_table(index="Mois", columns="Année", values="fermeture", aggfunc="count", fill_value=0)
    )

    # 2. Calcul des pourcentages (variation annuelle)
    df_pct = df_pivot.pct_change(axis=1).fillna(0) * 100

    # 3. Graphique
    mois_labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]
    fig_comp = go.Figure()

    for year in df_pivot.columns:

        labels = [f"{v:+.1f}%" if year != df_pivot.columns[0] else "" for v in df_pct[year]]
        
        fig_comp.add_trace(go.Bar(
            x=mois_labels[:len(df_pivot)],
            y=df_pivot[year],
            name=str(year),
            text=labels,
            textposition='outside',
            textfont=dict(size=10)
        ))

    # 4. Ajustements Layout
    fig_comp.update_layout(
        barmode='group',
        template='plotly_white',
        xaxis_title="Mois",
        yaxis_title="Nombre de fermetures",
        height=500,
        margin=dict(t=50),
        yaxis=dict(range=[0, df_pivot.values.max() * 1.2]) 
    )

    st.plotly_chart(fig_comp, use_container_width=True)
else:
    st.info("Données insuffisantes pour la comparaison annuelle sur ces régions.")

st.divider()
