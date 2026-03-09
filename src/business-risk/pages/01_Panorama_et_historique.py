import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import s3fs
import os

# 1. CONFIGURATION 
st.set_page_config(page_title="Firmographie - Diagnostic", layout="wide")

@st.cache_data(show_spinner=False)
def load_data_fallback():
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID") or st.secrets.get("AWS_ACCESS_KEY_ID")
    aws_secret = os.environ.get("AWS_SECRET_ACCESS_KEY") or st.secrets.get("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("AWS_BUCKET_NAME") or st.secrets.get("AWS_BUCKET_NAME")
    file_path = os.environ.get("AWS_FILE_PATH") or st.secrets.get("AWS_FILE_PATH")

    if not aws_key:
        return None

    try:
        fs = s3fs.S3FileSystem(key=aws_key, secret=aws_secret, anon=False)
        s3_path = f"s3://{bucket_name}/{file_path}"
        with fs.open(s3_path, mode='rb') as f:
            df_loaded = pd.read_parquet(f)
        
        if "Date_fermeture_finale" in df_loaded.columns:
            df_loaded["Date_fermeture_finale"] = pd.to_datetime(df_loaded["Date_fermeture_finale"], errors='coerce')
        return df_loaded
    except Exception as e:
        st.error(f"Erreur de connexion S3 : {e}")
        return None

# --- LOGIQUE DE RÉCUPÉRATION ---
if 'df' not in st.session_state or st.session_state['df'] is None:
    with st.status("🚀 Connexion au Cloud AWS S3...", expanded=True) as status:
        st.write("Vérification des accès S3...")
        df = load_data_fallback()
        if df is not None:
            st.session_state['df'] = df
            st.write("Analyse du fichier Parquet effectuée.")
            status.update(label="Données synchronisées avec succès !", state="complete", expanded=False)
        else:
            status.update(label="Échec de la connexion", state="error")
            st.stop()
else:
    df = st.session_state['df']

# --- 2. FILTRES SIDEBAR (Design : Ajout d'icônes et structure claire) ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=60)
    st.title("Observatoire")
    st.markdown("---")
    
    st.header("📍 Périmètre Géo")
    dept_options = ["Toute la France"] + sorted(df["Code du département de l'établissement"].unique().tolist())
    dept_sel = st.selectbox(
        "Choisir un département :", 
        options=dept_options,
        index=0
    )
    
    df_selection = df if dept_sel == "Toute la France" else df[df["Code du département de l'établissement"] == dept_sel]
    label_zone = "l'ensemble de la France" if dept_sel == "Toute la France" else f"le département {dept_sel}"
    
    st.markdown("---")
    st.caption(f"🌍 **Base de données :** {len(df_selection):,} établissements")

# --- 3. ENTÊTE (Design : Utilisation de colonnes et containers) ---
st.title("📊 1. Panorama & Dynamiques Historiques")
st.markdown("""
Cette section analyse la trajectoire des fermetures d'entreprises sur les deux dernières décennies 
pour identifier les cycles de rupture et définir notre périmètre d'intervention.
""")

with st.container(border=True):
    col_a, col_b = st.columns([1, 1], gap="large")

    with col_a:
        st.markdown("#### 🛠️ Cadre Technique")
        st.info("""
        * 🏛️ **Structures :** Focus sur les **SAS & SARL**.
        * 📂 **Source :** Données Insee / Bilans publics.
        * 🌍 **Géo :** France Métropolitaine & DOM.
        """)

    with col_b:
        st.markdown("#### 💡 Vision Métier")
        st.success("""
        * 🎯 **Données qualifiée :** Base contrôlée (Pappers/INSEE).
        * ⚖️ **Rigueur :** Historique consolidé depuis **2008**.
        * 📉 **Sémantique :** Étude des conditions de fermeture.
        """)

# --- 4. CALCULS & KPI (Design : Metrics alignées) ---
annee_min = df_selection["Date_fermeture_finale"].dt.year.min()
annee_max = df_selection["Date_fermeture_finale"].dt.year.max()
nb_annees = (annee_max - annee_min + 1) if pd.notna(annee_min) else 1

df_fermes = df_selection[df_selection["fermeture"] == 1]
total_fermetures = len(df_fermes)
taux_annuel = (df_selection["fermeture"].mean() * 100) / nb_annees
age_moyen = df_fermes["age_estime"].mean() if total_fermetures > 0 else 0

with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Fermetures", f"{total_fermetures:,}".replace(",", " "))
    c2.metric("Taux Annuel", f"{taux_annuel:.2f} %")
    c3.metric("Âge moyen au dépôt", f"{age_moyen:.1f} ans")

# --- 5. GRAPHIQUES (Design : Encapsulés dans des containers) ---

# Graphique 1 : Âge
st.subheader("🕰️ Analyse de la pérennité")

with st.container(border=True):

    st.markdown("""
    Cette analyse compare l'âge des sociétés **actuellement en activité** avec l'âge qu'avaient les sociétés **disparues** au moment de leur fermeture. 
    """)
    
    df_plot = df_selection.assign(Statut = df_selection["fermeture"].map({0: "Ouvertes", 1: "Fermées"}))
    
    fig_age = px.histogram(
        df_plot, x="age_estime", color="Statut", barmode="group",
        color_discrete_map={"Ouvertes": "#178F49", "Fermées": "#FFFFFF"}, 
        category_orders={"Statut": ["Ouvertes", "Fermées"]},
        template='plotly_white', height=400
    )
    
    # --- PERSONNALISATION AVANCÉE DU HOVER ET DES AXES ---
    fig_age.update_traces(

        hovertemplate="<b>Âge :</b> %{x} ans<br><b>Total :</b> %{y} entités<extra></extra>"
    )

    fig_age.update_layout(
        margin=dict(l=20, r=20, t=10, b=20),
        legend_title_text="Statut",
        hovermode="x unified",
        xaxis_title="Âge de l'entreprise (en années)",
        yaxis_title="",
        bargap=0.1
    )
    
    st.plotly_chart(fig_age, use_container_width=True)

    with st.chat_message("assistant"):
        st.write(f"**Analyse :** On observe la fameuse 'vallée de la mort' entre 2 et 5 ans. L'âge moyen ({age_moyen:.1f} ans) est un indicateur de fragilité structurelle précoce.")
# --- Graphique 2 : Probabilité ---
st.subheader("📈 Dynamique du risque : Taux de fermeture par âge")

with st.container(border=True):
    st.markdown("""
    Ce graphique mesure la **fragilité relative** des entreprises. 
    Il répond à la question : *Si l'entreprise a X années, quel est son risque statistique de fermer dans l'année ?*
    """)
    
    # --- Logique de données ---
    df_age_events = (
        df_selection.loc[df_selection["age_estime"].ge(0)]
        .assign(age_estime=lambda x: x["age_estime"].astype(int))
        .groupby("age_estime")["fermeture"]
        .agg(fermetures="sum", observations="count")
        .assign(proba_fermeture=lambda x: (x["fermetures"] / x["observations"]) * 100)
        .reset_index()
    )
    df_age_events = df_age_events[df_age_events["age_estime"] <= 35]

    # --- Création du Graphique ---
    fig_proba = go.Figure()
    
    fig_proba.add_trace(go.Scatter(
        x=df_age_events["age_estime"], 
        y=df_age_events["proba_fermeture"],
        mode="lines+markers", 
        line=dict(width=4, color='#E67E22'),
        fill='tozeroy', 
        fillcolor='rgba(230, 57, 70, 0.1)',
        name="Risque statistique",
        hovertemplate="<b>Âge :</b> %{x} ans<br><b>Risque :</b> %{y:.1f}%<extra></extra>"
    ))
    
    fig_proba.update_layout(
        template="plotly_white", 
        height=400, 
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Âge de l'entreprise (années)",
        yaxis_title="Risque de fermeture (%)",
        hovermode="x unified",
        yaxis=dict(rangemode="tozero")
    )
    
    st.plotly_chart(fig_proba, use_container_width=True)

    # --- AJOUT DU COMMENTAIRE DYNAMIQUE ---

    if not df_age_events.empty:
        peak_risk = df_age_events.loc[df_age_events['proba_fermeture'].idxmax()]
        
        with st.chat_message("assistant"):
            st.markdown(f"""
            **Lecture du risque :** La courbe montre que le risque de fermeture atteint son maximum à **{peak_risk['age_estime']:.0f} ans** (taux de **{peak_risk['proba_fermeture']:.1f}%**). 
            
            Passé ce cap de maturité, on observe généralement une **décroissance du risque**, signe d'une résilience structurelle acquise. 
            C'est ce qu'on appelle la courbe d'apprentissage du marché.
            """)

# Graphique 3 : Mensuel 
st.subheader("📅 Dynamique mensuelle et comparaison annuelle")

with st.container(border=True):
    st.markdown("""
    Cette analyse permet de visualiser si les fermetures s'accélèrent ou ralentissent d'un mois sur l'autre par rapport aux années précédentes. 
    """)

    # 1. Filtrage strict des données
    df_comp = df_selection[(df_selection["fermeture"] == 1) & (df_selection["Date_fermeture_finale"].notna())].copy()
    
    if not df_comp.empty:
  
        df_comp['Année'] = df_comp["Date_fermeture_finale"].dt.year
        df_comp['Mois'] = df_comp["Date_fermeture_finale"].dt.month


        mask_incomplet = (df_comp['Année'] == 2025) & (df_comp['Mois'] >= 10)
        df_clean = df_comp[~mask_incomplet].query("Année >= 2023")

        df_pivot = df_clean.pivot_table(
            index="Mois", columns="Année", values="fermeture", aggfunc="count", fill_value=0
        )
        
        mois_labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]

        fig_comp = px.bar(
            df_pivot, 
            barmode='group', 
            template='plotly_white', 
            height=400,
            labels={"value": "Nombre de fermetures", "Mois": "Mois"},
            color_discrete_sequence = ["#4C759F", "#94A3B8", "#6B2C6B"]
        )
        
        fig_comp.update_layout(
            xaxis=dict(tickmode='array', tickvals=list(range(1,13)), ticktext=mois_labels),
            yaxis_title="Nombre de fermetures",
            legend_title_text="Année",
            margin=dict(l=20, r=20, t=20, b=20)
        )
        
        st.plotly_chart(fig_comp, use_container_width=True)

        # --- COMMENTAIRE DYNAMIQUE (Logique 2023 vs 2024) ---
        if 2023 in df_pivot.columns and 2024 in df_pivot.columns:
            total_23 = df_pivot[2023].sum()
            total_24 = df_pivot[2024].sum()
            var_23_24 = ((total_24 - total_23) / total_23) * 100
            
            # Analyse courte pour 2025
            msg_2025 = ""
            if 2025 in df_pivot.columns:
                total_25_sept = df_pivot[2025].sum()
                msg_2025 = f" Sur les 9 premiers mois de **2025**, on recense déjà **{total_25_sept}** fermetures."

            st.markdown(f"""
            > **Analyse du flux :** Le volume de fermetures a évolué de **{var_23_24:+.1f}%** entre 2023 et 2024.{msg_2025}
            """)

        with st.expander("📝 Note sur la saisonnalité et les données"):
            st.write("""
            * Les données 2025 sont arrêtées au **30 septembre** pour garantir l'intégrité de l'analyse (données INPI en cours de traitement pour le T4).
            * Les pics de fin d'année (visibles en 2023/2024) sont structurels et liés aux régularisations administratives de fin d'exercice.
            """)
st.divider()
st.caption("ℹ️ Source : Base SIRENE & Bilans Publics | Focus méthodologique : SAS & SARL.")