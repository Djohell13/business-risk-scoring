import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import s3fs
import os
from plotly.subplots import make_subplots

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Formes et Effectifs", layout="wide")

@st.cache_data(show_spinner=False)
def load_data_fallback():
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID") or st.secrets.get("AWS_ACCESS_KEY_ID")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY") or st.secrets.get("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("AWS_BUCKET_NAME") or st.secrets.get("AWS_BUCKET_NAME")
    file_path = os.environ.get("AWS_FILE_PATH") or st.secrets.get("AWS_FILE_PATH")
    if not aws_key: return None
    try:
        fs = s3fs.S3FileSystem(key=aws_key, secret=aws_secret, anon=False)
        s3_path = f"s3://{bucket_name}/{file_path}"
        with fs.open(s3_path, mode='rb') as f:
            return pd.read_parquet(f)
    except Exception as e:
        st.error(f"Erreur S3 : {e}")
        return None

# Récupération du DF
if 'df' in st.session_state and st.session_state['df'] is not None:
    df = st.session_state['df']
else:
    with st.status("📡 Analyse de la structure légale...", expanded=False) as status:
        df = load_data_fallback()
        st.session_state['df'] = df
        status.update(label="Données structurelles prêtes !", state="complete")

if df is None:
    st.error("❌ Impossible de charger les données.")
    st.stop()

# --- 2. FILTRES SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/briefcase.png", width=60)
    st.title("Structure")
    st.header("📍 Géographie")
    dept_options = ["Toute la France"] + sorted(df["Code du département de l'établissement"].unique().tolist())
    dept_sel = st.selectbox("Département :", options=dept_options, index=0)
    
    df_selection = df if dept_sel == "Toute la France" else df[df["Code du département de l'établissement"] == dept_sel]
    
    st.divider()
    st.caption(f"📊 {len(df_selection):,} entités analysées")

# --- 3. TITRE ---
st.title("📊 3. Formes Juridiques et Effectifs")
st.markdown("Analyse de la répartition structurelle du parc : typologie des statuts et poids des effectifs salariés.")

# --- PARTIE 1 : FORMES JURIDIQUES ---
st.subheader("⚖️ Répartition par forme juridique (SARL vs SAS)")

with st.container(border=True):
    st.markdown("""
    Cette analyse compare la prédominance des deux statuts majeurs du commerce français. 
    L'objectif est de détecter si une forme juridique est plus exposée au risque qu'une autre.
    """)

    mapping = {5499: "SARL", 5710: "SAS"}

    color_map = {"SARL": "#627D98", "SAS": "#E63946"} 

    df_statuts = df_selection[df_selection["Catégorie juridique de l'unité légale"].isin([5499, 5710])].copy()
    df_statuts["statut_nom"] = df_statuts["Catégorie juridique de l'unité légale"].map(mapping)

    def get_statut_data(data):
        return data["statut_nom"].value_counts().sort_index()

    data_list = [
        get_statut_data(df_statuts),
        get_statut_data(df_statuts[df_statuts["fermeture"] == 0]),
        get_statut_data(df_statuts[df_statuts["fermeture"] == 1])
    ]

    fig_pie = make_subplots(rows=1, cols=3, specs=[[{'type':'domain'}]*3], 
                             subplot_titles=["Parc Total", "Ouvertes", "Fermées"])

    for i, data in enumerate(data_list, 1):
        if not data.empty:
            fig_pie.add_trace(
                go.Pie(
                    labels=data.index, values=data.values, 
                    marker=dict(colors=[color_map.get(l, "gray") for l in data.index]),
                    textinfo='percent', hole=0.5,
                    hovertemplate="<b>%{label}</b><br>Volume : %{value}<extra></extra>"
                ), row=1, col=i
            )

    fig_pie.update_layout(height=400, margin=dict(t=50, b=0, l=0, r=0), showlegend=True, 
                          legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"))
    st.plotly_chart(fig_pie, use_container_width=True)

    # Analyse Expert
    fermes = data_list[2]
    if not fermes.empty and fermes.sum() > 0:
        top_statut = fermes.idxmax()
        pct_top = (fermes.max() / fermes.sum()) * 100
        with st.chat_message("assistant"):
            st.write(f"**Analyse Juridique :** La forme **{top_statut}** représente **{pct_top:.1f}%** des fermetures. "
                     f"Comparez ce chiffre au 'Parc Total' : si la part dans les fermées est supérieure à la part du parc, "
                     f"cela indique une vulnérabilité propre à ce statut.")

# --- PARTIE 2 : EFFECTIFS ---
st.subheader("👥 Impact selon la taille de l'entreprise")

with st.container(border=True):
    st.markdown("""
    Analyse de la résilience selon la force salariale. Les structures sans salarié (TPE) sont historiquement les plus fragiles.
    """)

    tranche_map = {
        "0": "0 salarié", "1": "1-2 sal.", "3": "3-5 sal.", 
        "6": "6-9 sal.", "10": "10-19 sal.", "20": "20-49 sal."
    }
    order = sorted(df_selection["Tranche_effectif_num"].unique())

    def get_eff_data(data):
        return data["Tranche_effectif_num"].value_counts().reindex(order, fill_value=0)

    eff_data_list = [
        get_eff_data(df_selection),
        get_eff_data(df_selection[df_selection["fermeture"] == 0]),
        get_eff_data(df_selection[df_selection["fermeture"] == 1])
    ]

    fig_eff = make_subplots(rows=1, cols=3, specs=[[{'type':'domain'}]*3],
                             subplot_titles=["Parc Total", "Ouvertes", "Fermées"])

    colors_scale = ["#D9E2EC", "#BCCCDC", "#9FB3C8", "#829AB1", "#627D98", "#486581"]

    for i, data in enumerate(eff_data_list, 1):
        if not data.empty and data.sum() > 0:
            labels_lisibles = [tranche_map.get(str(x), f"Tranche {x}") for x in data.index]
            fig_eff.add_trace(
                go.Pie(
                    labels=labels_lisibles, values=data.values, 
                    marker=dict(colors=colors_scale),
                    textinfo='percent', hole=0.5,
                    hovertemplate="<b>%{label}</b><br>Volume: %{value}<extra></extra>"
                ), row=1, col=i
            )

    fig_eff.update_layout(height=400, margin=dict(t=50, b=0, l=0, r=0), 
                          legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"))
    st.plotly_chart(fig_eff, use_container_width=True)

# Analyse Expert
    counts_fermes = eff_data_list[2]
    if not counts_fermes.empty and counts_fermes.sum() > 0:
        tpe_fermes = counts_fermes.loc[counts_fermes.index.isin([0, 1])].sum()
        part_tpe = (tpe_fermes / counts_fermes.sum()) * 100
        with st.chat_message("assistant"):
            st.write(f"**Focus TPE :** Les structures de moins de 3 salariés représentent **{part_tpe:.1f}%** des radiations. "
                     f"Cela confirme que la micro-structure reste le premier terrain de risque par manque de capitalisation.")

st.divider()
st.caption("ℹ️ Source : Base SIRENE & Bilans Publics | Focus méthodologique : SAS & SARL.")