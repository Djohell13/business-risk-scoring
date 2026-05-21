import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Firmographie - Secteurs", layout="wide")

# --- LOGIQUE DE RÉCUPÉRATION CENTRALISÉE ---
if 'df' in st.session_state and st.session_state['df'] is not None:
    # 🎯 On récupère la base globale chargée sur la main
    df_raw = st.session_state['df']
    
    # 🎯 On recrée ton optimisation RAM localement sans re-télécharger le fichier
    required_columns = [
        "Code du département de l'établissement",
        "fermeture",
        "age_estime",
        "Date_fermeture_finale",
        "code_ape",
        "libelle_section_ape"
    ]
    
    # On ne garde que ce qui est nécessaire pour cette page et on convertit en catégorie
    df = df_raw[required_columns].copy()
    for col in ["Code du département de l'établissement", "code_ape", "libelle_section_ape"]:
        if col in df.columns:
            df[col] = df[col].astype("category")
else:
    # Sécurité Hugging Face
    st.warning("⚠️ Session rafraîchie ou expirée. Veuillez repasser brièvement par la page d'accueil pour réinitialiser l'intelligence économique.")
    st.info("💡 *Pourquoi ? Le dataset global s'initialise uniquement sur la page principale pour garantir la fluidité des filtres.*")
    st.stop()

# --- 2. FILTRES SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/factory.png", width=60)
    st.title("Filtres")
    st.header("📍 Géographie")
    
    # Extraction des départements (gestion propre du type category)
    depts = sorted(df["Code du département de l'établissement"].dropna().unique().astype(str).tolist())
    dept_options = ["Toute la France"] + depts
    dept_sel = st.selectbox("Département :", options=dept_options, index=0, key="sb_secteurs_dept")
    
    if dept_sel == "Toute la France":
        df_selection = df
    else:
        df_selection = df[df["Code du département de l'établissement"].astype(str) == dept_sel]
    
    st.divider()
    st.metric("Périmètre", f"{len(df_selection):,}".replace(',', ' '), delta="Unités")

# --- 3. PRÉPARATION ---
df_fermes_only = df_selection[df_selection["fermeture"] == 1].copy()

# Extraction propre des catégories principales
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
if top_secteurs_list:
    # 1. Identifier de manière dynamique la dernière année complète disponible
    annees_fermetures = df_selection["Date_fermeture_finale"].dt.year.dropna().unique().astype(int)
    
    if len(annees_fermetures) > 0:
        max_annee_data = max(annees_fermetures)
        
        # Règle métier : Si l'année la plus récente est 2026 (en cours), on prend 2025 pour avoir un historique complet
        from datetime import datetime
        annee_en_cours = datetime.now().year # Dynamiquement 2026
        
        if max_annee_data == annee_en_cours and (max_annee_data - 1) in annees_fermetures:
            annee_heatmap = max_annee_data - 1
            Explication_annee = f"l'année complète {annee_heatmap} (l'année {max_annee_data} étant en cours)"
        else:
            annee_heatmap = max_annee_data
            Explication_annee = f"l'année {annee_heatmap}"
    else:
        annee_heatmap = 2025 # Fallback de sécurité
        Explication_annee = "l'année 2025"

    st.subheader(f"🌡️ Heatmap : Intensité des fermetures par mois ({annee_heatmap})")

    with st.container(border=True):
        st.markdown(f"Détection de la **saisonnalité sectorielle** basée sur {Explication_annee}.")
        
        mois_labels = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]

        # Cast en str pour la robustesse avec les catégories
        df_selection_copy = df_selection.copy()
        df_selection_copy['libelle_section_ape_str'] = df_selection_copy['libelle_section_ape'].astype(str)
        
        # Filtrage basé sur l'année calculée dynamiquement
        df_heatmap_raw = df_selection_copy[
            (df_selection_copy["fermeture"] == 1) & 
            (df_selection_copy["Date_fermeture_finale"].dt.year == annee_heatmap) &
            (df_selection_copy["libelle_section_ape_str"].isin(top_secteurs_list))
        ].copy()

        if not df_heatmap_raw.empty:
            df_pivot_heat = (
                df_heatmap_raw.assign(Mois_num = lambda x: x["Date_fermeture_finale"].dt.month)
                .groupby(["libelle_section_ape_str", "Mois_num"], observed=True).size().reset_index(name="Nb")
                .pivot(index="libelle_section_ape_str", columns="Mois_num", values="Nb").fillna(0)
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
                st.markdown(f"**Analyse :** La heatmap met en évidence les périodes critiques par secteur sur **{annee_heatmap}**. Les pics structurels de fermeture observés à intervalles réguliers révèlent l'effet des échéances comptables et déclaratives de fin de trimestre.")
        else:
            st.info(f"ℹ️ Données {annee_heatmap} insuffisantes pour générer la Heatmap.")

st.divider()
st.caption("ℹ️ Source : Base SIRENE & Bilans Publics | Focus méthodologique : SAS & SARL.")