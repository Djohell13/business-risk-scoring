import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import s3fs
import os
from plotly.subplots import make_subplots

# 1. Ajustement du titre de l'onglet
st.set_page_config(page_title="Formes et Effectifs", layout="wide")

@st.cache_data
def load_data_fallback():
    # Priorité Environnement (Docker/HF)
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("AWS_BUCKET_NAME")
    file_path = os.environ.get("AWS_FILE_PATH")

    # Fallback Local (Secrets)
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

# Rappel visuel en haut de la page principale
st.header("📊 Diagnostic Territorial National")
st.markdown(f"🚩 **Périmètre actuel :** :blue[{label_zone}]")
st.divider()

# ------- Graph 1 

# 1. Configuration
mapping = {5499: "SARL", 5710: "SAS"}
color_map = {"SARL": "#1f77b4", "SAS": "#ff7f0e"}

# 2. Préparation des données sur la sélection filtrée
def get_counts(filter_condition=None):

    base = df_selection[df_selection["Catégorie juridique de l'unité légale"].isin([5499, 5710])]
    
    if filter_condition is not None:
        base = base[base["fermeture"] == filter_condition]
    
    counts = base["Catégorie juridique de l'unité légale"].map(mapping).value_counts()
    return counts.sort_index()

data_list = [get_counts(), get_counts(0), get_counts(1)]
titles = ["Répartition Totale", "Sociétés Ouvertes", "Sociétés Fermées"]

# 3. Création de la figure
fig = make_subplots(
    rows=1, cols=3, 
    specs=[[{'type':'domain'}]*3],
    subplot_titles=titles
)

for i, data in enumerate(data_list, 1):
    if not data.empty:
        fig.add_trace(
            go.Pie(
                labels=data.index, 
                values=data.values, 
                marker=dict(colors=[color_map[l] for l in data.index]),
                textinfo='percent+label',
                hole=0.4,
            ), 
            row=1, col=i
        )

fig.update_layout(
    title_text="⚖️ Comparaison Structurelle SARL vs SAS",
    width=1100,
    height=450,
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
)

# 4. Affichage dans Streamlit
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ----- Graph 2 

# 1. Préparation des données

order = sorted(df_selection["Tranche_effectif_num"].unique())

def get_effectif_counts(filter_condition=None):

    base = df_selection.copy()
    if filter_condition is not None:
        base = base[base["fermeture"] == filter_condition]
    
    # Comptage par tranche avec réindexation pour garder l'ordre numérique
    counts = base["Tranche_effectif_num"].value_counts().reindex(order, fill_value=0)
    return counts

eff_data_list = [get_effectif_counts(), get_effectif_counts(0), get_effectif_counts(1)]
eff_titles = ["Effectifs : Répartition Totale", "Sociétés Ouvertes", "Sociétés Fermées"]

tranche_map = {
    "0": "0 salarié",
    "1": "1 à 2 salariés",
    "3": "3 à 5 salariés",
    "6": "6 à 9 salariés",
    "10": "10 à 19 salariés",
    "20": "20 à 49 salariés",

}

# 2. Création de la figure
fig_eff = make_subplots(
    rows=1, cols=3, 
    specs=[[{'type':'domain'}]*3],
    subplot_titles=eff_titles
)

colors_scale = px.colors.sequential.Blues_r

for i, data in enumerate(eff_data_list, 1):
    if not data.empty and data.sum() > 0:

        labels_lisibles = [tranche_map.get(str(x), f"Tranche {x}") for x in data.index]
        
        fig_eff.add_trace(
            go.Pie(
                labels=labels_lisibles,
                values=data.values, 
                marker=dict(colors=colors_scale),
                textinfo='percent',
                hole=0.4,
                hovertemplate="<b>%{label}</b><br>Nombre: %{value}<br>Part: %{percent}<extra></extra>"
            ), 
            row=1, col=i
        )

# 3. Layout
fig_eff.update_layout(
    title_text="👥 Analyse par Taille d'Entreprise (Tranches d'effectifs)",
    width=1100,
    height=550,
    legend_title="Détail des tranches",
    legend=dict(
        orientation="h", 
        yanchor="bottom", 
        y=-0.3,
        xanchor="center", 
        x=0.5
    )
)

st.plotly_chart(fig_eff, use_container_width=True)

st.divider()

# 1. Calcul du taux sur la SELECTION filtrée
df_size_risk = (
    df_selection.groupby("Tranche_effectif_num")
    .agg(
        total=("fermeture", "size"),
        nb_fermes=("fermeture", "sum")
    )
    .reset_index()
)

# Calcul du taux
df_size_risk["taux_fermeture"] = (df_size_risk["nb_fermes"] / df_size_risk["total"] * 100).round(2)

# MODIFICATION : On remplace les codes par les noms lisibles pour l'axe X
df_size_risk["label_effectif"] = df_size_risk["Tranche_effectif_num"].astype(str).map(tranche_map)

# 2. Visualisation
fig_risk = px.bar(
    df_size_risk,
    x="label_effectif",
    y="taux_fermeture",
    text="taux_fermeture",
    title="⚡ Répartition des fermetures selon le nombre de salariés",
    labels={"label_effectif": "Taille de l'entreprise", "taux_fermeture": "Taux de fermeture (%)"},
    color="taux_fermeture",
    color_continuous_scale="Reds"
)

# Réglage de l'échelle
max_taux = df_size_risk["taux_fermeture"].max() if not df_size_risk.empty else 100

fig_risk.update_traces(
    texttemplate='%{text}%', 
    textposition='outside',
    cliponaxis=False 
)

fig_risk.update_layout(
    xaxis_type='category',
    yaxis=dict(range=[0, max_taux * 1.2]),
    width=900,  
    height=700,
    showlegend=False
)

# 4. Affichage Streamlit
st.plotly_chart(fig_risk, use_container_width=True)

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
    "Source : Base SIRENE & Bilans Publics | Méthodologie limitée aux formes juridiques SAS et SARL."
    "</div>", 
    unsafe_allow_html=True
)