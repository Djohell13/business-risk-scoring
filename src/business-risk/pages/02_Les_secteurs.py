import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import s3fs
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Firmographie - Secteurs", layout="wide")

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
            df_loaded = pd.read_parquet(f)
        
        # Conversion Date impérative pour les colonnes catégorielles
        if "Date_fermeture_finale" in df_loaded.columns:
            df_loaded["Date_fermeture_finale"] = pd.to_datetime(df_loaded["Date_fermeture_finale"], errors='coerce')
        return df_loaded
    except Exception as e:
        st.error(f"Erreur S3 : {e}")
        return None

# --- LOGIQUE DE RÉCUPÉRATION ---
if 'df' not in st.session_state or st.session_state['df'] is None:
    with st.status("📡 Synchronisation des données sectorielles...", expanded=False) as status:
        df = load_data_fallback()
        st.session_state['df'] = df
        status.update(label="Base sectorielle chargée !", state="complete")
else:
    df = st.session_state['df']

if df is None:
    st.error("❌ Données indisponibles.")
    st.stop()

# --- 2. FILTRES SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/factory.png", width=60)
    st.title("Filtres")
    st.header("📍 Géographie")
    
    # Gestion du tri sur catégories
    depts = sorted(df["Code du département de l'établissement"].unique().astype(str).tolist())
    dept_options = ["Toute la France"] + depts
    dept_sel = st.selectbox("Département :", options=dept_options, index=0)
    
    # Filtrage (on convertit en str pour la comparaison si besoin)
    if dept_sel == "Toute la France":
        df_selection = df
    else:
        df_selection = df[df["Code du département de l'établissement"].astype(str) == dept_sel]
    
    st.divider()
    st.metric("Périmètre", f"{len(df_selection):,}".replace(',', ' '), delta="Unités")

# --- 3. PRÉPARATION ---
df_fermes_only = df_selection[df_selection["fermeture"] == 1].copy()

top_secteurs_list = df_fermes_only['libelle_section_ape'].value_counts().head(10).index.astype(str).tolist()

# --- 4. TITRE ET TOP SECTEURS ---
st.title("📊 2. Dynamique des Secteurs d'Activité")
st.markdown("Identification des zones de fragilité par code APE et section d'activité.")

st.subheader("🏭 Top 10 des secteurs les plus exposés")

with st.container(border=True):
    st.markdown("*Volume total de fermetures enregistrées sur la période.*")
    if not df_fermes_only.empty:

        top_ape = (
            df_fermes_only["code_ape"].value_counts().head(10).reset_index()
            .rename(columns={"count": "nb_fermetures"})
            .merge(df_selection[['code_ape', 'libelle_section_ape']].drop_duplicates('code_ape'), on='code_ape', how='left')
            .assign(label = lambda x: x["code_ape"].astype(str) + " – " + x["libelle_section_ape"].astype(str))
        )

        fig_sectors = px.bar(
            top_ape, x="nb_fermetures", y="label", orientation='h', 
            template='plotly_white', color="nb_fermetures", 
            color_continuous_scale="Reds", height=500
        )
        fig_sectors.update_traces(
            hovertemplate="<b>%{y}</b><br>Fermetures : %{x}<extra></extra>",
            texttemplate="%{x}", textposition="outside"
        )
        fig_sectors.update_layout(xaxis_title="Nombre de fermetures", yaxis_title=None, coloraxis_showscale=False)
        fig_sectors.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_sectors, use_container_width=True)

        top_secteur_nom = str(top_ape.iloc[0]["libelle_section_ape"])
        with st.chat_message("assistant"):
            st.write(f"**Analyse :** Le secteur **{top_secteur_nom}** concentre le plus grand volume de cessations. Cette donnée doit être pondérée par la densité totale d'entreprises dans ce secteur.")
    else:
        st.info("Aucune fermeture enregistrée sur ce périmètre.")

# --- 5. COMPARATIF DU RISQUE ---
st.subheader("⚖️ Comparatif du risque de fermeture")

with st.container(border=True):
    st.markdown("Visualisez la **probabilité statistique** de fermeture selon l'âge pour chaque secteur sélectionné.")
    
    if top_secteurs_list:
        secteurs_choisis = st.multiselect("🔍 Comparer les secteurs :", options=top_secteurs_list, default=[top_secteurs_list[0]])

        if secteurs_choisis:

            df_stats_raw = df_selection[
                df_selection['libelle_section_ape'].isin(secteurs_choisis) & 
                df_selection["age_estime"].between(0, 35)
            ].copy()
            
            df_stats_raw['libelle_section_ape'] = df_stats_raw['libelle_section_ape'].cat.remove_unused_categories()

            df_stats = (
                df_stats_raw.groupby(["libelle_section_ape", "age_estime"], observed=True)["fermeture"]
                .agg(fermetures="sum", obs="count")
                .assign(proba=lambda x: (x["fermetures"] / x["obs"]) * 100)
                .reset_index()
            )

            fig_comp_risk = px.line(
                df_stats, x="age_estime", y="proba", color="libelle_section_ape",
                template="plotly_white", height=500,
                labels={"age_estime": "Âge de l'entreprise", "proba": "Risque (%)", "libelle_section_ape": "Secteur"}
            )
            fig_comp_risk.update_traces(mode="lines", line=dict(width=3), hovertemplate="<b>%{fullData.name}</b><br>Âge : %{x} ans<br>Risque : %{y:.1f}%<extra></extra>")
            fig_comp_risk.update_layout(legend=dict(orientation="h", y=-0.3, x=0.5, xanchor="center"))
            st.plotly_chart(fig_comp_risk, use_container_width=True)

# --- 6. HEATMAP ---
st.subheader("🌡️ Heatmap : Intensité des fermetures par mois (2024)")

with st.container(border=True):
    st.markdown("Détection de la **saisonnalité sectorielle**.")
    
    mois_labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]

    if top_secteurs_list:
        df_2024_raw = df_selection[
            (df_selection["fermeture"] == 1) & 
            (df_selection["Date_fermeture_finale"].dt.year == 2024) &
            (df_selection["libelle_section_ape"].isin(top_secteurs_list))
        ].copy()

        df_2024_raw['libelle_section_ape'] = df_2024_raw['libelle_section_ape'].cat.remove_unused_categories()

        if not df_2024_raw.empty:
            df_pivot_heat = (
                df_2024_raw.assign(Mois_num = lambda x: x["Date_fermeture_finale"].dt.month)
                .groupby(["libelle_section_ape", "Mois_num"], observed=True).size().reset_index(name="Nb")
                .pivot(index="libelle_section_ape", columns="Mois_num", values="Nb").fillna(0)
                .reindex(columns=range(1, 13), fill_value=0)
            )

            fig_heat = px.imshow(
                df_pivot_heat, 
                x=mois_labels, 
                color_continuous_scale="YlOrRd", 
                text_auto=True, 
                aspect="auto",
                labels=dict(x="Mois", y="Secteur", color="Fermetures")
            )
            
            fig_heat.update_traces(
                hovertemplate="<b>Secteur :</b> %{y}<br><b>Mois :</b> %{x}<br><b>Fermetures :</b> %{z} entités<extra></extra>"
            )

            fig_heat.update_layout(
                height=500, 
                margin=dict(l=200, r=20, t=20, b=20), 
                coloraxis_showscale=False, 
                xaxis_title=None, 
                yaxis_title=None
            )
            st.plotly_chart(fig_heat, use_container_width=True)

            with st.chat_message("assistant"):
                st.markdown("**Analyse :** La heatmap met en évidence les périodes critiques par secteur. Les pics de fermeture peuvent coïncider avec les fins de trimestres civils.")
        else:
            st.info("ℹ️ Données 2024 insuffisantes pour générer la Heatmap.")

st.divider()
st.caption("ℹ️ Source : Base SIRENE & Bilans Publics | Focus méthodologique : SAS & SARL.")