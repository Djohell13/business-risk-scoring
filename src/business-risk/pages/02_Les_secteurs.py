import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Firmographie - Secteurs", layout="wide")

# --- LOGIQUE DE RÉCUPÉRATION CENTRALISÉE ---
if 'df' in st.session_state and st.session_state['df'] is not None:

    df_raw = st.session_state['df']

    required_columns = [
        "Code du département de l'établissement",
        "fermeture",
        "age_estime",
        "Date_fermeture_finale",
        "code_ape",
        "libelle_section_ape"
    ]

    df = df_raw[required_columns].copy()
    for col in ["Code du département de l'établissement", "code_ape", "libelle_section_ape"]:
        if col in df.columns:
            df[col] = df[col].astype("category")
else:
    st.warning("⚠️ Session rafraîchie. Veuillez repasser par la page d'accueil.")
    st.stop()

# --- 2. FILTRES SIDEBAR ---
with st.sidebar:
    
    # 1. GÉOGRAPHIE
    st.header("📍 Secteur Géographique")
    depts = sorted(df["Code du département de l'établissement"].dropna().unique().astype(str).tolist())
    dept_options = ["Toute la France"] + depts
    dept_sel = st.selectbox("Département :", options=dept_options, index=0, key="sb_secteurs_dept")
    
    # 2. PÉRIODE
    st.header("📅 Période Choisie")
    options_periode = {
        "3 dernières années": 3,
        "2 dernières années": 2,
        "Année de référence (2025)": 1,
        "Tout l'historique": 0
    }
    periode_sel = st.radio("Horizon temporel :", list(options_periode.keys()), key="sb_periode")
    
    # --- FILTRAGE ENCHAÎNÉ PROPRE ---
    df_temp = df.copy()
    
    if dept_sel != "Toute la France":
        df_temp = df_temp[df_temp["Code du département de l'établissement"].astype(str) == dept_sel]
    
    if options_periode[periode_sel] > 0:
        annee_limite = 2025 - options_periode[periode_sel] + 1
        df_temp = df_temp[df_temp["Date_fermeture_finale"].dt.year >= annee_limite]
        
    df_selection = df_temp
        
    st.divider()
    st.metric("Périmètre", f"{len(df_selection):,}".replace(',', ' '), delta="Unités")

# --- 3. PRÉPARATION ---
df_fermes_only = df_selection[df_selection["fermeture"] == 1].copy()

top_secteurs_list = df_fermes_only['libelle_section_ape'].value_counts().head(10).index.astype(str).tolist()

# --- 4. TITRE ET TOP SECTEURS ---
st.title("📊 2. Les Secteurs d'Activité")

st.subheader("🏭 Les 10 secteurs les plus exposés selon votre sélection")

with st.container(border=True):

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
            def calculate_sector_hazard(df_full, sectors):
                all_results = []
                for sector in sectors:
                    df_s = df_full[df_full['libelle_section_ape'].astype(str) == sector]
                    for age in range(36):
                        morts = len(df_s[(df_s["age_estime"] == age) & (df_s["fermeture"] == 1)])
                        exposes = len(df_s[df_s["age_estime"] >= age])
                        
                        if exposes > 30:
                            all_results.append({
                                "Secteur": sector,
                                "age_estime": age,
                                "proba": (morts / exposes) * 100
                            })
                return pd.DataFrame(all_results)

            df_stats = calculate_sector_hazard(df_selection, secteurs_choisis)

            if not df_stats.empty:
                fig_comp_risk = px.line(
                    df_stats, x="age_estime", y="proba", color="Secteur",
                    template="plotly_white", height=500,
                    labels={"age_estime": "Âge de l'entreprise", "proba": "Risque annuel (%)"}
                )
                fig_comp_risk.update_traces(mode="lines+markers", line=dict(width=3), hovertemplate="<b>%{fullData.name}</b><br>Âge : %{x} ans<br>Risque : %{y:.2f}%<extra></extra>")
                fig_comp_risk.update_layout(
                    legend=dict(orientation="h", y=-0.3, x=0.5, xanchor="center"),
                    yaxis=dict(rangemode="tozero")
                )
                st.plotly_chart(fig_comp_risk, use_container_width=True)
            else:
                st.warning("Données insuffisantes pour comparer ces secteurs avec cette rigueur statistique.")

# --- 6. HEATMAP DYNAMIQUE ---
st.subheader("🌡️ Heatmap : Saisonnalité des fermetures")

with st.container(border=True):
    # 1. Sélectionner uniquement les années COMPLÈTES pour la moyenne
    from datetime import datetime
    annee_en_cours = datetime.now().year
    annees_selectionnees = sorted(df_selection["Date_fermeture_finale"].dt.year.dropna().unique().astype(int))
    annees_pour_moyenne = [a for a in annees_selectionnees if a < annee_en_cours]
    
    # Si l'utilisateur n'a sélectionné que 2026, on affiche 2026 brut
    if not annees_pour_moyenne:
        df_heatmap_raw = df_selection[df_selection["Date_fermeture_finale"].dt.year == annee_en_cours]
        diviseur = 1
        annee_str = "2026 (données brutes)"
    else:
        df_heatmap_raw = df_selection[df_selection["Date_fermeture_finale"].dt.year.isin(annees_pour_moyenne)]
        diviseur = len(annees_pour_moyenne)
        annee_str = f"moyenne {min(annees_pour_moyenne)}-{max(annees_pour_moyenne)}"

    # 2. Calcul du pivot
    if not df_heatmap_raw.empty:

        df_heatmap_raw = df_heatmap_raw[df_heatmap_raw["libelle_section_ape"].astype(str).isin(top_secteurs_list)]
        
        df_pivot_heat = (
            df_heatmap_raw.assign(Mois_num = lambda x: x["Date_fermeture_finale"].dt.month)
            .groupby(["libelle_section_ape", "Mois_num"], observed=True).size().reset_index(name="Nb")
            .assign(Nb = lambda x: (x["Nb"] / diviseur).round(1))
            .pivot(index="libelle_section_ape", columns="Mois_num", values="Nb").fillna(0)
            .reindex(columns=range(1, 13), fill_value=0)
        )

        fig_heat = px.imshow(
            df_pivot_heat, 
            x=["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"], 
            color_continuous_scale="YlOrRd", 
            text_auto=True, 
            aspect="auto",
            labels=dict(x="Mois", y="Secteur", color="Moy. Mens.")
        )
        
        fig_heat.update_layout(height=500, margin=dict(l=200, r=20, t=20, b=20), coloraxis_showscale=False)
        st.plotly_chart(fig_heat, use_container_width=True)
        
        # Commentaire dynamique
        with st.chat_message("assistant"):
            if len(annees_selectionnees) > 1:
                st.markdown(f"**Analyse :** Cette heatmap affiche une moyenne mensuelle lissée sur la période sélectionnée. Les zones sombres identifient les pics de saisonnalité récurrents.")
            else:
                st.markdown(f"**Analyse :** Cette heatmap présente les données pour **l'année {annees_selectionnees[0]}**. Elle met en lumière les points de friction spécifiques.")
    else:
        st.info("Sélectionnez une période contenant des données pour afficher la Heatmap.")

st.divider()
st.caption("ℹ️ Source : Base SIRENE & Infogreffe | Focus méthodologique : SAS & SARL.")