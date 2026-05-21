import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Formes et Effectifs", layout="wide")

# --- LOGIQUE DE RÉCUPÉRATION CENTRALISÉE ---
if 'df' in st.session_state and st.session_state['df'] is not None:
    # 🎯 Récupération instantanée du dataset chargé par la page main
    df = st.session_state['df']
else:
    # Sécurité contre les pertes de session sur Hugging Face
    st.warning("⚠️ Session rafraîchie ou expirée. Veuillez repasser brièvement par la page d'accueil pour réinitialiser l'intelligence économique.")
    st.info("💡 *Pourquoi ? Le dataset global est volumineux et s'initialise uniquement sur la page principale pour optimiser les performances.*")
    st.stop()

# --- 2. FILTRES SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/briefcase.png", width=60)
    st.title("Structure")
    st.header("📍 Géographie")
    
    # Gestion du tri et conversion propre en str pour éviter les conflits
    depts = sorted(df["Code du département de l'établissement"].dropna().astype(str).unique().tolist())
    dept_options = ["Toute la France"] + depts
    dept_sel = st.selectbox("Département :", options=dept_options, index=0, key="sb_struct_dept")
    
    if dept_sel == "Toute la France":
        df_selection = df
    else:
        df_selection = df[df["Code du département de l'établissement"].astype(str) == dept_sel]
    
    st.divider()
    st.metric("Périmètre", f"{len(df_selection):,}".replace(',', ' '), delta="Unités")

# --- 3. TITRE ---
st.title("📊 3. Formes Juridiques et Effectifs")
st.markdown("Analyse de la répartition structurelle du parc : typologie des statuts et poids des effectifs salariés.")

# --- PARTIE 1 : FORMES JURIDIQUES ---
st.subheader("⚖️ Répartition par forme juridique (SARL vs SAS)")

with st.container(border=True):
    # Nettoyage et filtrage local sur la sélection géographique
    df_local = df_selection.copy()
    df_local["Catégorie juridique de l'unité légale"] = pd.to_numeric(
        df_local["Catégorie juridique de l'unité légale"], errors='coerce'
    )
    
    # Filtrage ciblé SAS (5710) / SARL (5499)
    df_statuts = df_local[df_local["Catégorie juridique de l'unité légale"].isin([5499, 5710])].copy()
    
    st.write(f"Nombre d'entreprises trouvées pour SAS/SARL : **{len(df_statuts):,}**".replace(',', ' '))

    mapping = {5499: "SARL", 5710: "SAS"}
    color_map = {"SARL": "#4C759F", "SAS": "#6B2C6B"} 
    
    df_statuts["statut_nom"] = df_statuts["Catégorie juridique de l'unité légale"].map(mapping)

    def get_statut_data(data):
        return data["statut_nom"].value_counts().sort_index()

    data_list = [
        get_statut_data(df_statuts),
        get_statut_data(df_statuts[df_statuts["fermeture"] == 1]),
        get_statut_data(df_statuts[df_statuts["fermeture"] == 0])
    ]

    fig_pie = make_subplots(
        rows=1, cols=3, 
        specs=[[{'type':'domain'}]*3], 
        subplot_titles=["Parc Total", "Fermées", "Ouvertes"]
    )

    for i, data in enumerate(data_list, 1):
        if not data.empty and data.sum() > 0:
            current_colors = [color_map.get(l, "gray") for l in data.index]
            
            fig_pie.add_trace(
                go.Pie(
                    labels=data.index, 
                    values=data.values, 
                    marker=dict(colors=current_colors),
                    sort=False, 
                    textinfo='percent', 
                    hole=0.5,
                    hovertemplate="<b>%{label}</b><br>Volume : %{value}<extra></extra>"
                ), row=1, col=i
            )

    fig_pie.update_layout(
        height=400, 
        margin=dict(t=50, b=0, l=0, r=0), 
        showlegend=True, 
        legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center")
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    fermes = data_list[1] 
    if not fermes.empty and fermes.sum() > 0:
        top_statut = fermes.idxmax()
        pct_top = (fermes.max() / fermes.sum()) * 100
        with st.chat_message("assistant"):
            st.write(f"**Analyse Juridique :** La forme **{top_statut}** représente **{pct_top:.1f}%** des fermetures historiques. "
                     f"Comparez ce chiffre au 'Parc Total' : si la part dans les fermées est supérieure à la part du parc, "
                     f"cela indique une vulnérabilité propre à ce statut.")

# --- PARTIE 2 : EFFECTIFS ---
st.subheader("👥 Impact selon la taille de l'entreprise")

with st.container(border=True):
    tranche_labels = {
        0: "Non employeur/0 sal.", 1: "1-2 sal.", 2: "3-5 sal.", 3: "6-9 sal.",
        4: "10-19 sal.", 5: "20-49 sal.", 6: "50-99 sal.", 7: "100-199 sal.",
        8: "200-249 sal.", 9: "250-499 sal.", 10: "500-999 sal.", 11: "1000+ sal."
    }
    
    df_eff = df_selection.copy()
    
    def get_eff_data(data):
        if "Tranche_effectif_num" in data.columns:
            return data["Tranche_effectif_num"].value_counts().sort_index()
        return pd.Series(dtype=int)

    eff_data_list = [
        get_eff_data(df_eff),
        get_eff_data(df_eff[df_eff["fermeture"] == 1]), 
        get_eff_data(df_eff[df_eff["fermeture"] == 0])
    ]

    fig_eff = make_subplots(
        rows=1, cols=3, 
        specs=[[{'type':'domain'}]*3],
        subplot_titles=["Parc Total", "Fermées", "Ouvertes"]
    )

    colors_scale = px.colors.sequential.Blues_r 

    for i, data in enumerate(eff_data_list, 1):
        if not data.empty and data.sum() > 0:
            labels_lisibles = [tranche_labels.get(int(x), f"T{x}") for x in data.index]
            
            fig_eff.add_trace(
                go.Pie(
                    labels=labels_lisibles, 
                    values=data.values, 
                    marker=dict(colors=colors_scale), 
                    sort=False, 
                    textinfo='percent', 
                    textposition='inside',
                    hole=0.5,
                    hovertemplate="<b>%{label}</b><br>Volume: %{value}<extra></extra>"
                ), row=1, col=i
            )

    fig_eff.update_layout(height=400, showlegend=True, legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_eff, use_container_width=True)

    counts_fermes = eff_data_list[1]
    if not counts_fermes.empty and counts_fermes.sum() > 0:
        tpe_fermes = counts_fermes.loc[counts_fermes.index.isin([0, 1])].sum()
        part_tpe = (tpe_fermes / counts_fermes.sum()) * 100
        with st.chat_message("assistant"):
            st.write(f"**Focus TPE :** Les structures de moins de 3 salariés représentent **{part_tpe:.1f}%** des radiations. "
                     f"La fragilité est concentrée sur les micro-structures.")

st.divider()
st.caption("ℹ️ Source : Base SIRENE & Bilans Publics | Focus méthodologique : SAS & SARL.")