import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import s3fs
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Firmographie - Secteurs", layout="wide")

@st.cache_data
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
            df_loaded = pd.read_parquet(f)
        
        if "Date_fermeture_finale" in df_loaded.columns:
            df_loaded["Date_fermeture_finale"] = pd.to_datetime(df_loaded["Date_fermeture_finale"], errors='coerce')
        return df_loaded
    except Exception as e:
        st.error(f"Erreur S3 : {e}")
        return None

# Récupération du DF
if 'df' in st.session_state and st.session_state['df'] is not None:
    df = st.session_state['df']
else:
    with st.spinner("🔄 Chargement des données..."):
        df = load_data_fallback()
        st.session_state['df'] = df

if df is None:
    st.error("❌ Impossible de charger les données.")
    st.stop()

# --- 2. FILTRES SIDEBAR ---
with st.sidebar:
    st.header("📍 Périmètre géographique")
    dept_options = ["Toute la France"] + sorted(df["Code du département de l'établissement"].unique().tolist())
    dept_sel = st.selectbox("Choisir un département :", options=dept_options, index=0)
    
    if dept_sel == "Toute la France":
        df_selection = df
        st.caption(f"🌍 Global : {len(df):,} établissements".replace(',', ' '))
    else:
        df_selection = df[df["Code du département de l'établissement"] == dept_sel]
        st.caption(f"📍 Dept {dept_sel} : {len(df_selection):,} établissements".replace(',', ' '))
    st.divider()

# --- 3. PRÉPARATION DES DONNÉES COMMUNES ---
df_fermes_only = df_selection[df_selection["fermeture"] == 1]
top_secteurs_list = df_fermes_only['libelle_section_ape'].value_counts().head(10).index.tolist()

# --- 4. TITRE ET TOP SECTEURS ---
st.title("📊 2. Les Secteurs d'Activité")
st.divider()

st.subheader("| 🏭 Les 10 secteurs les plus touchés")
st.markdown("Identification des secteurs enregistrant le plus grand nombre de fermetures.")

if not df_fermes_only.empty:
    top_ape = (
        df_fermes_only["code_ape"].value_counts().head(10).reset_index()
        .rename(columns={"count": "nb_fermetures"})
        .merge(df_selection[['code_ape', 'libelle_section_ape']].drop_duplicates('code_ape'), on='code_ape', how='left')
        .assign(label = lambda x: x["code_ape"].astype(str) + " – " + x["libelle_section_ape"])
    )

    fig_sectors = px.bar(
        top_ape, x="nb_fermetures", y="label", orientation='h', 
        template='plotly_white', color_discrete_sequence=['firebrick'], height=500
    )
    # HOVER ET TEXTE PROPRE
    fig_sectors.update_traces(
        hovertemplate="<b>%{y}</b><br>Fermetures : %{x}<extra></extra>",
        texttemplate="%{x}",
        textposition="outside"
    )
    fig_sectors.update_layout(xaxis_title="Nombre de fermetures", yaxis_title=None)
    fig_sectors.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_sectors, use_container_width=True)

    top_secteur_nom = top_ape.iloc[0]["libelle_section_ape"]
    st.info(f"**🔍 Note de l'expert :** Le secteur **{top_secteur_nom}** apparaît en tête.")
else:
    st.info("Aucune fermeture enregistrée.")

st.divider()

# --- 5. COMPARATIF DU RISQUE ---
st.subheader("⚖️ Comparatif du risque de fermeture par secteur")
st.info("🖱️ **Analyse Comparative :** Sélectionnez un ou plusieurs secteurs ci-dessous.")

if top_secteurs_list:
    secteurs_choisis = st.multiselect("🔍 Secteurs à comparer :", options=top_secteurs_list, default=[top_secteurs_list[0]])

    if secteurs_choisis:
        df_stats = (
            df_selection[df_selection['libelle_section_ape'].isin(secteurs_choisis) & df_selection["age_estime"].between(0, 35)]
            .groupby(["libelle_section_ape", "age_estime"])["fermeture"]
            .agg(fermetures="sum", obs="count")
            .assign(proba=lambda x: (x["fermetures"] / x["obs"]) * 100)
            .reset_index()
        )

        fig_comp_risk = px.line(
            df_stats, x="age_estime", y="proba", color="libelle_section_ape",
            template="plotly_white", height=500,
            labels={"age_estime": "Âge", "proba": "Taux (%)", "libelle_section_ape": "Secteur"}
        )
        # HOVER PROPRE
        fig_comp_risk.update_traces(
            mode="lines", line=dict(width=3),
            hovertemplate="<b>%{fullData.name}</b><br>Âge : %{x} ans<br>Risque : %{y:.1f}%<extra></extra>"
        )
        fig_comp_risk.update_layout(legend=dict(orientation="h", y=-0.3, x=0.5, xanchor="center"))
        st.plotly_chart(fig_comp_risk, use_container_width=True)

st.divider()

# --- 6. HEATMAP ---
st.subheader("🌡️ Heatmap : Intensité des fermetures par mois (2024)")
st.markdown("Pics d'activité de fermeture par secteur au cours de l'année 2024.")

mois_labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]

if top_secteurs_list:
    df_2024 = df_selection[
        (df_selection["fermeture"] == 1) & 
        (df_selection["Date_fermeture_finale"].dt.year == 2024) &
        (df_selection["libelle_section_ape"].isin(top_secteurs_list))
    ]

    if not df_2024.empty:
        df_pivot_heat = (
            df_2024.assign(Mois_num = lambda x: x["Date_fermeture_finale"].dt.month)
            .groupby(["libelle_section_ape", "Mois_num"]).size().reset_index(name="Nb")
            .pivot(index="libelle_section_ape", columns="Mois_num", values="Nb").fillna(0)
            .reindex(columns=range(1, 13), fill_value=0)
        )

        max_val = df_pivot_heat.max().max()

        fig_heat = px.imshow(
            df_pivot_heat, x=mois_labels, color_continuous_scale="YlOrRd", text_auto=True, aspect="auto"
        )
        
        # SUPPRESSION DES LABELS D'ÉCHELLES ET HOVER PROPRE
        fig_heat.update_layout(
            height=500, 
            margin=dict(l=200), 
            coloraxis_showscale=False,
            xaxis_title=None,
            yaxis_title=None
        )
        fig_heat.update_traces(
            hovertemplate="Secteur : %{y}<br>Mois : %{x}<br>Fermetures : %{z}<extra></extra>"
        )
        
        st.plotly_chart(fig_heat, use_container_width=True)

        st.info(f"""
        **🔍 Analyse de la concentration des risques :**
        - Les zones **rouges** identifient une forte **concentration** (pic à {int(max_val)} unités). 
        - Une **lecture horizontale** détecte une fragilité persistante.
        - Une **lecture verticale** met en évidence la saisonnalité.
        """)
    else:
        st.info("ℹ️ Données 2024 insuffisantes pour la Heatmap.")

st.divider()
st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em;'>Source : Base SIRENE & Bilans Publics | Focus méthodologique : SAS & SARL.</div>", unsafe_allow_html=True)