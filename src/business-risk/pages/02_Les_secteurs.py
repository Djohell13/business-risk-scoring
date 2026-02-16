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

# Rappel visuel en haut de la page principale
st.header("📊 Diagnostic Territorial National")
st.markdown(f"🚩 **Périmètre actuel :** :blue[{label_zone}]")

# 4. TITRE ET KPIs

st.divider()


st.subheader("🏭 Top 10 des secteurs les plus touchés")

# 1. Pipeline synthétisé : Filtrage -> Comptage -> Merge -> Label
top_ape = (
    df_selection[df_selection["fermeture"] == 1]["code_ape"]
    .value_counts()
    .head(10)
    .reset_index()
    .rename(columns={"count": "nb_fermetures"})
    .merge(df_selection[['code_ape', 'libelle_section_ape']].drop_duplicates(), on='code_ape', how='left')
    .assign(label = lambda x: x["code_ape"].astype(str) + " – " + x["libelle_section_ape"])
)

if not top_ape.empty:
    # 2. Création du graphique
    fig_sectors = px.bar(
        top_ape,
        x="nb_fermetures",
        y="label",
        orientation='h',
        text="nb_fermetures",
        template='plotly_white',
        color_discrete_sequence=['firebrick']
    )

    # 3. Ajustements Layout
    val_max = top_ape["nb_fermetures"].max()
    
    fig_sectors.update_traces(
        textposition='outside',
        cliponaxis=False
    )

    fig_sectors.update_layout(
        height=500,
        xaxis=dict(range=[0, val_max * 1.2]),
        xaxis_title="Nombre de fermetures",
        yaxis_title=None,
        margin=dict(l=250, r=50),
    )

    fig_sectors.update_yaxes(autorange="reversed")

    st.plotly_chart(fig_sectors, use_container_width=True)
else:
    st.info("Aucune fermeture enregistrée pour cette sélection.")

st.divider()

st.subheader("⚖️ Comparatif du risque de fermeture par secteur sur les 10 secteurs les plus touchés")

# 1. Sélectionner les secteurs les plus représentés dans la sélection actuelle

top_secteurs = df_selection['libelle_section_ape'].value_counts().head(10).index.tolist()

if top_secteurs:
    fig_comp_risk = go.Figure()

    for secteur in top_secteurs:

        df_secteur = (
            df_selection[df_selection["libelle_section_ape"] == secteur]
            .loc[df_selection["age_estime"].between(0, 35)]
            .groupby("age_estime")["fermeture"]
            .agg(fermetures="sum", obs="count")
            .assign(proba=lambda x: (x["fermetures"] / x["obs"]) * 100)
            .reset_index()
        )

        fig_comp_risk.add_trace(go.Scatter(
            x=df_secteur["age_estime"],
            y=df_secteur["proba"],
            mode="lines",
            name=secteur,
            line=dict(width=2.5),
            hovertemplate="<b>" + secteur + "</b><br>Âge: %{x} ans<br>Risque: %{y:.1f}%<extra></extra>"
        ))

    fig_comp_risk.update_layout(
        xaxis_title="Âge de l'entreprise (années)",
        yaxis_title="Probabilité de fermeture (%)",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(
            orientation="h", 
            yanchor="bottom",
            y=-0.4,
            xanchor="center",
            x=0.5
        ),
        height=600,
        margin=dict(b=100)
    )

    st.plotly_chart(fig_comp_risk, use_container_width=True)
else:
    st.info("Données insuffisantes pour générer le comparatif sectoriel.")

st.info("🖱️ **Astuce :** Vous pouvez double-cliquer sur la légende pour isoler un secteur d'activité en particulier.")

st.divider()

# ----- Graph 5

st.subheader("🌡️ Heatmap : Intensité des fermetures par mois (2024)")

mois_labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]

# Identifier les 10 secteurs les plus touchés (basé sur la sélection de région)
top_10_secteurs = (
    df_selection[df_selection["fermeture"] == 1]["libelle_section_ape"]
    .value_counts()
    .head(10)
    .index.tolist()
)

if top_10_secteurs:

    df_heatmap = (
        df_selection[
            (df_selection["fermeture"] == 1) & 
            (df_selection["libelle_section_ape"].isin(top_10_secteurs)) &
            (df_selection["Date_fermeture_finale"].dt.year == 2024)
        ]
        .assign(Mois_num = lambda x: x["Date_fermeture_finale"].dt.month)
        .groupby(["libelle_section_ape", "Mois_num"])
        .size()
        .reset_index(name="Nb_Fermetures")
    )

    if not df_heatmap.empty:

        df_pivot_top = df_heatmap.pivot(
            index="libelle_section_ape", 
            columns="Mois_num", 
            values="Nb_Fermetures"
        ).fillna(0)

        for m in range(1, 13):
            if m not in df_pivot_top.columns:
                df_pivot_top[m] = 0
        df_pivot_top = df_pivot_top.reindex(columns=range(1, 13))

        # Création du graphique
        fig_heat = px.imshow(
            df_pivot_top,
            labels=dict(x="Mois", y="Secteur", color="Fermetures"),
            x=mois_labels, 
            color_continuous_scale="YlOrRd",
            aspect="auto",
            text_auto=True
        )

        fig_heat.update_layout(
            height=600,
            xaxis_title=None,
            yaxis_title=None,
            margin=dict(l=200)
        )

        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("Pas assez de données pour générer la Heatmap 2024 sur cette sélection.")
else:
    st.warning("Aucune donnée disponible.")

    st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
    "Source : Base SIRENE & Bilans Publics | Méthodologie limitée aux formes juridiques SAS et SARL."
    "</div>", 
    unsafe_allow_html=True
)