import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Egide - Diagnostic Firmographique", layout="wide")

# --- LOGIQUE DE RÉCUPÉRATION CENTRALISÉE ---
if 'df' in st.session_state and st.session_state['df'] is not None:
    df = st.session_state['df']
else:
    st.warning("⚠️ Session rafraîchie ou expirée. Veuillez repasser brièvement par la page d'accueil pour réinitialiser l'intelligence économique.")
    st.info("💡 *Pourquoi ? Le dataset global est volumineux et s'initialise uniquement sur la page principale pour optimiser les performances.*")
    st.stop()

# --- 2. FILTRES SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=60)
    st.title("Observatoire")
    st.markdown("---")
    
    st.header("📍 Périmètre Géo")
    dept_options = ["Toute la France"] + sorted(df["Code du département de l'établissement"].dropna().unique().tolist())
    dept_sel = st.selectbox(
        "Choisir un département :", 
        options=dept_options,
        index=0,
        key="sb_panorama_departement"
    )
    
    df_selection = df if dept_sel == "Toute la France" else df[df["Code du département de l'établissement"] == dept_sel]
    
    st.markdown("---")
    st.caption(f"🌍 **Base analysée :** {len(df_selection):,} établissements")

# --- 3. ENTÊTE ---
st.title("📊 1. Historiques & Dynamiques")
st.markdown("""
Cette section analyse la trajectoire des fermetures d'entreprises depuis 1975 
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
        * 🎯 **Données qualifiées :** Base contrôlée (Pappers/INSEE).
        * ⚖️ **Rigueur :** Historique consolidé depuis **1975**.
        * 📉 **Sémantique :** Étude des conditions de fermeture.
        """)

# --- 4. CALCULS & KPI ---
annee_min_global = df_selection[df_selection["fermeture"] == 1]["Date_fermeture_finale"].dt.year.min()
annee_max_global = df_selection[df_selection["fermeture"] == 1]["Date_fermeture_finale"].dt.year.max()
nb_annees_global = (annee_max_global - annee_min_global + 1) if pd.notna(annee_min_global) else 1

df_fermes = df_selection[df_selection["fermeture"] == 1]
total_fermetures = len(df_fermes)
taux_annuel = (df_selection["fermeture"].mean() * 100) / nb_annees_global
age_moyen = df_fermes["age_estime"].mean() if total_fermetures > 0 else 0

with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Fermetures", f"{total_fermetures:,}".replace(",", " "))
    c2.metric("Taux Annuel Moyen", f"{taux_annuel:.2f} %")
    c3.metric("Âge moyen au dépôt", f"{age_moyen:.1f} ans")

# --- 5. GRAPHIQUES ---

# =====================================================================
# Graphique 1 : Âge (Volume) -> LIMITÉ À 50 ANS
# =====================================================================
st.subheader("🕰️ Analyse de la pérennité")

with st.container(border=True):
    st.markdown("""
    Cette analyse compare l'âge des sociétés **actuellement en activité** avec l'âge qu'avaient les sociétés **disparues** au moment de leur fermeture. 
    """)
    
    df_plot = df_selection.assign(
        Statut = df_selection["fermeture"].map({0: "Ouvertes", 1: "Fermées"}),
        age_arrondi = df_selection["age_estime"].round(0)
    )
    
    df_plot_50 = df_plot[df_plot["age_arrondi"] <= 50]
    
    fig_age = px.histogram(
        df_plot_50, x="age_arrondi", color="Statut", barmode="group",
        color_discrete_map={"Ouvertes": "#178F49", "Fermées": "#FFFFFF"}, 
        category_orders={"Statut": ["Ouvertes", "Fermées"]},
        template='plotly_white', height=400
    )
    
    fig_age.update_traces(
        hovertemplate="<b>Âge :</b> %{x} ans<br><b>Total :</b> %{y} entités<extra></extra>"
    )
    
    fig_age.update_layout(
        margin=dict(l=20, r=20, t=10, b=20),
        legend_title_text="Statut",
        hovermode="x unified",
        xaxis_title="Âge de l'entreprise (en années)",
        yaxis_title="",
        bargap=0.1,
        xaxis=dict(
            tickmode="linear",
            tick0=0,
            dtick=5,
            range=[-0.7, 35.7]
        )
    )
    
    st.plotly_chart(fig_age, use_container_width=True, key="chart_age_histogram")

    with st.chat_message("assistant"):
        st.markdown(f"""
        **Analyse :** On observe un **pic de sinistralité** entre 2 et 5 ans, phase charnière dite de la 'vallée de la mort'. 
        L'âge moyen ({age_moyen:.1f} ans) souligne une **fragilité structurelle précoce** et une difficulty à pérenniser les structures au-delà du premier cycle de croissance.
        """)

# --- SYNTHÈSE PÉDAGOGIQUE RÉALIGNÉE ---
st.info("""
    💡 **Corrélation Volume vs Intensité**
    
    Les deux analyses convergent vers le même constat : **le facteur de risque est intrinsèquement lié à la jeunesse de l'entreprise.**
    
    1. **En Volume (Graphique ci-dessus) :** Les disparitions d'entreprises touchent massivement les structures de moins de 10 ans. 
    2. **En Intensité (Graphique ci-dessous) :** La probabilité statistique individuelle de fermer au cours de l'année est elle aussi maximale au départ, puis elle décroît continuellement avec l'âge. 
    
    **Conclusion :** Plus une structure accumule de l'ancienneté, plus son modèle se solidifie, réduisant à la fois le volume global des défaillances et le risque individuel de fermeture.
    """)

# =====================================================================
# Graphique 2 : Probabilité (INDICE DE VULNÉRABILITÉ JUSQU'À 49 ANS)
# =====================================================================
st.subheader("📈 Dynamique de fermeture : l'indice de vulnérabilité par âge")

with st.container(border=True):
    st.markdown("""
    Ce graphique mesure la **fragilité relative** des entreprises. 
    Il répond à la question : *Si l'entreprise a atteint l'âge X, quel est son risque statistique d'enregistrer une fermeture au cours de l'exercice ?*
    """)
    
    age_ans_temp = df_selection["age_estime"].round(0).astype(int)

    annee_min = df_selection[df_selection["fermeture"] == 1]["Date_fermeture_finale"].dt.year.min()
    annee_max = df_selection[df_selection["fermeture"] == 1]["Date_fermeture_finale"].dt.year.max()
    nb_annees = (annee_max - annee_min + 1) if pd.notna(annee_min) else 1

    fermetures_par_age = df_selection[df_selection["fermeture"] == 1].groupby(age_ans_temp).size()
    flux_annuel_fermetures = fermetures_par_age / nb_annees

    stock_actif_par_age = df_selection[df_selection["fermeture"] == 0].groupby(age_ans_temp).size()

    df_age_events = (
        pd.DataFrame(
            {"flux_fermetures": flux_annuel_fermetures, "stock_actif": stock_actif_par_age}
        )
        .fillna(0)
        .rename_axis('age_ans')
        .reset_index()
    )

    df_age_events["proba_fermeture"] = (
        df_age_events["flux_fermetures"]
        / (df_age_events["stock_actif"] + df_age_events["flux_fermetures"]).replace(0, 1)
    ) * 100

    df_graph = df_age_events[df_age_events["age_ans"] <= 49]
    
    if not df_graph.empty:
        max_sain = df_graph["proba_fermeture"].max()
        limite_haute_y = max_sain * 1.15

        fig_courbe = go.Figure()
        
        fig_courbe.add_trace(
            go.Scatter(
                x=df_graph["age_ans"],
                y=df_graph["proba_fermeture"],
                mode="lines+markers", 
                line=dict(color="#E67E22", width=3), 
                marker=dict(
                    size=6,
                    color="#B8651B",
                    symbol="circle",
                    line=dict(color="white", width=1),
                ),
                fill='tozeroy', 
                fillcolor='rgba(230, 126, 34, 0.1)',
                name="Risque annuel",
                hovertemplate="<b>Âge de l'entreprise :</b> %{x} ans<br><b>Risque :</b> %{y:.2f}%<extra></extra>"
            )
        )
        
        fig_courbe.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)',  
            height=500,
            hovermode="x unified",
            margin=dict(l=20, r=20, t=10, b=20),
            xaxis=dict(
                title=dict(text="Âge de l'entreprise (années)", font=dict(color="#A3AED0")),
                tickfont=dict(color="#A3AED0"),
                tickmode="linear",
                tick0=0,
                dtick=5,
                range=[-1, 50],
                showgrid=True,
                gridcolor="rgba(255, 255, 255, 0.15)", 
            ),
            yaxis=dict(
                title=dict(text="Risque de fermeture (%)", font=dict(color="#A3AED0")),
                tickfont=dict(color="#A3AED0"),
                range=[0, limite_haute_y],
                showgrid=True,
                gridcolor="rgba(255, 255, 255, 0.15)", 
            ),
        )
        
        st.plotly_chart(fig_courbe, use_container_width=True, key="chart_vulnerability_curve")

        peak_risk = df_graph.loc[df_graph['proba_fermeture'].idxmax()]
        peak_age = peak_risk['age_ans']
        peak_val = peak_risk['proba_fermeture']

        with st.chat_message("assistant"):
            if peak_age < 7:
                st.markdown(f"""
                **Analyse : La Mortalité de Maturité, un risque silencieux.** Si le *volume* de fermetures décroît continuellement avec l'âge (Graphique 1), **l'intensité du risque**, elle, ne suit pas la même trajectoire linéaire (Graphique 2).

                * 🚨 **Le cap de consolidation (0-6 ans) :** Le risque culmine très tôt, avec un pic majeur à 3 ans, matérialisant l'épuisement du capital de départ et la phase critique de validation du modèle économique.
                * 📈 **Le "Rebond de maturité" (après 35 ans) :** Après une phase de stabilité maximale vers 30 ans, le risque statistique de fermer **cesse de descendre et remonte passé 35-37 ans**. 

                Ce phénomène relate de manière flagrante la **mortalité de maturité** : il ne concerne plus des problèmes de gestion courante, mais des enjeux critiques de fin de cycle, comme l'obsolescence d'un modèle non pivoté ou, plus fréquemment, les difficultés liées à la **cession/transmission d'entreprise**.
                """)
            elif peak_age > 25:
                st.markdown(f"""
                **Analyse : Risque de Fin de Cycle Détecté.** La perspective étendue à 50 ans met en lumière un pic à **{peak_age} ans** ({peak_val:.2f}%). 
                Ce rebond caractérise de manière flagrante les enjeux de **transmission d'entreprise**, de départ à la retraite des fondateurs historiques, ou d'obsolescence d'un modèle non pivoté.
                """)
            else:
                st.markdown(f"""
                **Analyse : Risque de Maturité.** Le pic se situe à **{peak_age} ans** ({peak_val:.2f}%). 
                L'exposition au risque est ici liée à des enjeux de second cycle de croissance ou à un besoin de pivot stratégique du modèle économique.
                """)

# =====================================================================
# Graphique 3 : Mensuel -> S'ARRÊTE EN MARS 2026 DE MANIÈRE NATURELLE
# =====================================================================
st.subheader("📅 Dynamique mensuelle et comparaison annuelle")

with st.container(border=True):
    st.markdown("""
    Cette analyse permet de visualiser si les fermetures s'accélèrent ou ralentissent d'un mois sur l'autre par rapport aux années précédentes. 
    """)

    df_comp = df_selection[(df_selection["fermeture"] == 1) & (df_selection["Date_fermeture_finale"].notna())].copy()
    
    if not df_comp.empty:
        df_comp['Année'] = df_comp["Date_fermeture_finale"].dt.year
        df_comp['Mois'] = df_comp["Date_fermeture_finale"].dt.month

        df_clean = df_comp.query("Année >= 2023")

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
            color_discrete_sequence=["#4C759F", "#94A3B8", "#6B2C6B", "#E67E22"]
        )
        
        fig_comp.update_layout(
            xaxis=dict(tickmode='array', tickvals=list(range(1, 13)), ticktext=mois_labels),
            yaxis_title="Nombre de fermetures",
            legend_title_text="Année",
            margin=dict(l=20, r=20, t=20, b=20)
        )
        
        st.plotly_chart(fig_comp, use_container_width=True, key="chart_monthly_comparison")

        if 2023 in df_pivot.columns and 2024 in df_pivot.columns:
            total_23 = df_pivot[2023].sum()
            total_24 = df_pivot[2024].sum()
            var_23_24 = ((total_24 - total_23) / total_23) * 100
            
            msg_complement = ""
            if 2025 in df_pivot.columns:
                total_25 = df_pivot[2025].sum()
                msg_complement += f" L'année **2025** affiche un total consolidé de **{total_25:,}** fermetures.".replace(",", " ")
            
            if 2026 in df_pivot.columns:
                total_26_t1 = df_pivot[2026].sum()
                msg_complement += f" Pour **2026**, le premier trimestre (Janvier-Mars) enregistre déjà **{total_26_t1:,}** cessations.".replace(",", " ")

            st.markdown(f"""
            > **Analyse du flux :** Le volume de fermetures a évolué de **{var_23_24:+.1f}%** entre 2023 et 2024.{msg_complement}
            """)

        with st.expander("📝 Note sur la saisonnalité et les données"):
            st.write("""
            * L'année **2025** est présentée dans son intégralité.
            * Les données pour l'année en cours (**2026**) s'arrêtent au **31 mars** conformément aux dernières données injectées dans le pipeline.
            * Les pics de fin d'année restent structurellement liés aux clôtures comptables et régularisations administratives.
            """)

st.divider()
st.caption("ℹ️ Source : Base SIRENE & Infogreffe | Focus méthodologique : SAS & SARL.")