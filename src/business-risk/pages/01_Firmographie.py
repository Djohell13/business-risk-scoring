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
        
        # OPTIMISATION PERFORMANCE :
        if "Date_fermeture_finale" in df_loaded.columns:
            df_loaded["Date_fermeture_finale"] = pd.to_datetime(df_loaded["Date_fermeture_finale"], errors='coerce')
        return df_loaded
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
    st.header("📍 Choix du périmètre géographique :")
    
    dept_options = ["Toute la France"] + sorted(df["Code du département de l'établissement"].unique().tolist())
    dept_sel = st.selectbox(
        "Choisir un département :", 
        options=dept_options,
        index=0
    )
    
    if dept_sel == "Toute la France":
        df_selection = df
        label_zone = "l'ensemble de la France"
        count_ent = len(df)
    else:
        df_selection = df[df["Code du département de l'établissement"] == dept_sel]
        label_zone = f"le département {dept_sel}"
        count_ent = len(df_selection)

    st.caption(f"🌍 Périmètre : {count_ent:,} établissements".replace(',', ' '))
    st.divider()

# --- 3. CONTENU DE LA PAGE (ACCUEIL & CONTEXTE) ---
st.title("📊 1. État des lieux & Périmètre")

with st.container():
    col_a, col_b = st.columns([1, 1], gap="large")

    with col_a:
        st.markdown("#### 🛠️ Cadre Technique")
        st.info("""
        **Périmètre d'analyse :**
        * 🏛️ **Structures :** Focus sur les **SAS & SARL (80% des Entreprises en France**.
        * 📂 **Source :** Données Insee / Bilans publics.
        * 🌍 **Géo :** France Métropolitaine & Départements d'Outre-mer.
        * ⏳ **Profondeur :** Historique depuis **2008**.
        """)

    with col_b:
        st.markdown("#### 💡 Vision Métier")
        st.success("""
        **Une approche holistique :**
        * 🎯 **Données qualifiée :** Base INSEE contrôlée via Pappers.
        * ⚖️ **Rigueur :** Bases de données homogène pour des projections fiables.
        * 📉 **Sémantique :** Étude des **causes de fermeture**.
        """)

with st.expander("🔍 Méthodologie : Mon approche repose sur la complémentarité de deux piliers."):
    st.markdown("""
    Actuellement, l'Observatoire exploite le premier : 
    
    **1. L'Analyse de Survie (Actif) :** J'isole les facteurs de risque liés au profil intrinsèque de l'entreprise :
    * **La maturité** : Analyse des cycles de vie (mortalité infantile vs structures établies).
    * **L'inertie sectorielle** : Dynamique de résilience propre à chaque métier.
    * **La morphologie** : Impact de la forme juridique et du territoire.

    **2. L'Analyse Financière (En cours de développement) :** À terme, l'outil intégrera les ratios de solvabilité et de rentabilité pour affiner le scoring. 
    
    *Ce diagnostic de profil constitue la base de connaissance du modèle de projection (Page 5).*
    """)

# On calcule les années sur les dates déjà converties dans le cache
annee_min = df_selection["Date_fermeture_finale"].dt.year.min()
annee_max = df_selection["Date_fermeture_finale"].dt.year.max()

if pd.isna(annee_min) or pd.isna(annee_max):
    periode_label = "Période actuelle"
    nb_annees = 1 
else:
    periode_label = f"{int(annee_min)} — {int(annee_max)}"
    nb_annees = (annee_max - annee_min + 1)

# --- CALCULS DES INDICATEURS ---
df_fermes = df_selection[df_selection["fermeture"] == 1]
total_fermetures = len(df_fermes)
taux_annuel = (df_selection["fermeture"].mean() * 100) / nb_annees
age_moyen = df_fermes["age_estime"].mean() if total_fermetures > 0 else 0

# --- AFFICHAGE DES KPI ---
st.subheader(f"📊 Etat des lieux :")
st.markdown(f"🗺️ **Choix du périmètre géographique (menu de gauche) :** {label_zone}")
st.markdown(f"🗓️ **Période d'analyse :** {periode_label} ({int(nb_annees)} ans)")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Fermetures", f"{total_fermetures:,}".replace(",", " "), 
              help=f"Nombre total de cessations enregistrées sur {int(nb_annees)} ans.")
with col2:
    st.metric("Taux de Fermeture Annuel", f"{taux_annuel:.2f} %", 
              help="Moyenne annuelle du taux de fermeture sur la période.")
with col3:
    st.metric("Âge moyen au dépôt", f"{age_moyen:.1f} ans")

st.divider()

# --- 5. GRAPHIQUES ---

# Graphique 1 : Âge
st.subheader("🕰️ Analyse de la pérennité : Entreprises actives vs fermées")
st.markdown("""
Cette analyse compare l'âge des sociétés actuellement en activité avec l'âge qu'avaient les sociétés disparues au moment de leur fermeture. 
""")

df_plot = df_selection.assign(Statut = df_selection["fermeture"].map({0: "Ouvertes", 1: "Fermées"}))

fig_age = px.histogram(
    df_plot, x="age_estime", color="Statut", barmode="group",
    color_discrete_map={"Ouvertes": "#2ecc71", "Fermées": "#e74c3c"}, 
    category_orders={"Statut": ["Ouvertes", "Fermées"]},
    labels={"age_estime": "Âge", "count": "Total", "Statut": "État"}, 
    template='plotly_white', height=450
)

fig_age.update_layout(
    xaxis_title="Âge de la société",
    yaxis_title="Nombre de sociétés (Total)",
    legend_title_text="État de la société",
    hovermode="x unified"
)
fig_age.update_traces(hovertemplate="Total : %{y}")
st.plotly_chart(fig_age, use_container_width=True)

# COMMENTAIRE VALLÉE DE LA MORT
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
st.subheader("📈 Dynamique du risque : Taux de fermeture par âge")
st.markdown("""
Ce graphique mesure la **fragilité relative** des entreprises. 
Il répond à la question : *Si l'entreprise a X années, quel est son risque statistique de fermer dans l'année ?*
""")

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
    mode="lines+markers", line=dict(width=3, color='#e67e22'),
    name="Risque de fermeture",
    hovertemplate="Âge : %{x} ans<br>Risque : %{y:.2f}%<extra></extra>" 
))

fig_proba.update_layout(
    template="plotly_white", height=450, 
    xaxis_title="Âge de l'entreprise (en années)", 
    yaxis_title="Taux de fermeture (%)", hovermode="x"
)
st.plotly_chart(fig_proba, use_container_width=True)

st.divider()

# Graphique 3 : Mensuel
st.subheader("📅 Dynamique mensuelle et comparaison annuelle")
st.markdown("""
Cette analyse permet de visualiser si les fermetures s'accélèrent ou ralentissent d'un mois sur l'autre par rapport aux années précédentes. 
Les pourcentages affichés au-dessus des barres indiquent la **variation annuelle**.
""")

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
            x=mois_labels[:len(df_pivot)], y=df_pivot[year], name=f"Année {year}",
            text=[f"{v:+.1f}%" if year != df_pivot.columns[0] and v != 0 else "" for v in df_pct[year]],
            textposition='outside'
        ))
        
    fig_comp.update_layout(barmode='group', template='plotly_white', height=500, xaxis_title="Mois de l'année", yaxis_title="Nombre de fermetures")

    # ANALYSE DYNAMIQUE MÉTIER
    mois_max = df_pivot.mean(axis=1).idxmax()
    nom_mois_max = mois_labels[mois_max - 1]
    
    st.markdown(f"#### 🔍 Analyse de l'expert")
    if nom_mois_max == "Déc":
        st.success(f"""**Observation :** On constate une concentration des fermetures en **Décembre**. 
        D'un point de vue métier, cela confirme une corrélation forte avec la **clôture des exercices comptables**. 
        Plutôt que des défaillances subies, cela traduit souvent des **cessations d'activité organisées** et des fins de cycles de vie "propres".""")
    else:
        st.info(f"**Observation :** Le pic de fermeture se situe actuellement en **{nom_mois_max}**.")

    st.plotly_chart(fig_comp, use_container_width=True)

st.markdown("<div style='text-align: center; color: gray; font-size: 0.8em;'>Source : Base SIRENE & Bilans Publics | Focus méthodologique : SAS & SARL.</div>", unsafe_allow_html=True)