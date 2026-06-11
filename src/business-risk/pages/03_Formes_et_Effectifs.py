import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Formes et Effectifs", layout="wide")

if 'df' in st.session_state and st.session_state['df'] is not None:
    df = st.session_state['df']
else:
    st.warning("⚠️ Session rafraîchie. Veuillez repasser par la page d'accueil.")
    st.stop()

# --- 2. FILTRES SIDEBAR ---
with st.sidebar:
    
    st.header("📍 Secteur Géographique")
    depts = sorted(df["Code du département de l'établissement"].dropna().astype(str).unique().tolist())
    dept_options = ["Toute la France"] + depts
    dept_sel = st.selectbox("Département :", options=dept_options, index=0, key="sb_struct_dept")
    
    st.header("📅 Période Choisie")
    options_periode = {
        "3 dernières années": 3,
        "2 dernières années": 2,
        "Année de référence (2025)": 1,
        "Tout l'historique": 0
    }
    periode_sel = st.radio("Horizon temporel :", list(options_periode.keys()), key="sb_periode")
    
    # --- FILTRAGE INTELLIGENT ---
    df_temp = df.copy()
    if dept_sel != "Toute la France":
        df_temp = df_temp[df_temp["Code du département de l'établissement"].astype(str) == dept_sel]
    
    if options_periode[periode_sel] > 0:
        annee_limite = 2025 - options_periode[periode_sel] + 1
        mask = (df_temp["fermeture"] == 0) | (
            (df_temp["fermeture"] == 1) & (df_temp["Date_fermeture_finale"].dt.year >= annee_limite)
        )
        df_selection = df_temp[mask]
    else:
        df_selection = df_temp
        
    st.divider()
    st.metric("Périmètre", f"{len(df_selection):,}".replace(',', ' '))

# --- 3. TITRE ---
st.title("📊 3. Formes Juridiques et Effectifs")
annees_presentes = sorted(df_selection["Date_fermeture_finale"].dt.year.dropna().unique().astype(int))
if annees_presentes:
    st.caption(f"Analyse sur la période : {min(annees_presentes)} - {max(annees_presentes)}")

# --- PARTIE 1 : FORMES JURIDIQUES ---
st.subheader("⚖️ Répartition par forme juridique (SARL vs SAS)")

with st.container(border=True):
    df_statuts = df_selection.copy()
    df_statuts["Catégorie juridique de l'unité légale"] = pd.to_numeric(df_statuts["Catégorie juridique de l'unité légale"], errors='coerce')
    df_statuts = df_statuts[df_statuts["Catégorie juridique de l'unité légale"].isin([5499, 5710])].copy()

    mapping = {5499: "SARL", 5710: "SAS"}
    color_map = {"SARL": "#4C759F", "SAS": "#6B2C6B"} 
    df_statuts["statut_nom"] = df_statuts["Catégorie juridique de l'unité légale"].map(mapping)

    data_list = [
        df_statuts["statut_nom"].value_counts(),
        df_statuts[df_statuts["fermeture"] == 1]["statut_nom"].value_counts(),
        df_statuts[df_statuts["fermeture"] == 0]["statut_nom"].value_counts()
    ]

    fig_pie = make_subplots(1, 3, specs=[[{'type':'domain'}]*3], subplot_titles=["Parc Total", "Fermées", "Ouvertes"])

    for i, data in enumerate(data_list, 1):
        if not data.empty:
            fig_pie.add_trace(go.Pie(labels=data.index, values=data.values, marker=dict(colors=[color_map.get(l, "gray") for l in data.index]), 
                                     hole=0.5, sort=False, textinfo='percent', hovertemplate="<b>%{label}</b><br>Volume: %{value:,.0f}<extra></extra>"), row=1, col=i)

    fig_pie.update_layout(height=400, showlegend=True, legend=dict(orientation="h", y=-0.1))
    st.plotly_chart(fig_pie, use_container_width=True)

    fermes = data_list[1] 
    if not fermes.empty:
        with st.chat_message("assistant"):
            st.write(f"**Analyse :** La forme **{fermes.idxmax()}** représente **{(fermes.max() / fermes.sum())*100:.1f}%** des fermetures sur cette période.")

# --- PARTIE 2 : EFFECTIFS ---

st.subheader("👥 Impact selon la taille de l'entreprise")

with st.container(border=True):
    tranche_labels = {
        0: "Non employeur / 0 sal.", 1: "1-2 sal.", 2: "3-5 sal.", 3: "6-9 sal.",
        4: "10-19 sal.", 5: "20-49 sal.", 6: "50-99 sal.", 7: "100-199 sal.",
        8: "200-249 sal.", 9: "250-499 sal.", 10: "500-999 sal.", 11: "1000+ sal."
    }

    eff_data_list = [
        df_selection["Tranche_effectif_num"].value_counts().sort_index(),
        df_selection[df_selection["fermeture"] == 1]["Tranche_effectif_num"].value_counts().sort_index(),
        df_selection[df_selection["fermeture"] == 0]["Tranche_effectif_num"].value_counts().sort_index()
    ]

    fig_eff = make_subplots(
        rows=1, cols=3, 
        specs=[[{'type':'domain'}]*3],
        subplot_titles=["Parc Total", "Fermées", "Ouvertes"]
    )

    colors_scale = px.colors.sequential.Blues_r 

    for i, data in enumerate(eff_data_list, 1):
        if not data.empty:
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
                    hovertemplate="<b>%{label}</b><br>Volume: %{value:,.0f}<extra></extra>"
                ), row=1, col=i
            )

    fig_eff.update_layout(
        height=450, 
        showlegend=True, 
        legend=dict(orientation="h", y=-0.2),
        margin=dict(t=50, b=50, l=0, r=0)
    )
    st.plotly_chart(fig_eff, use_container_width=True)

    counts_fermes = eff_data_list[1]
    if not counts_fermes.empty:
        tpe_fermes = counts_fermes.loc[counts_fermes.index.isin([0, 1])].sum()
        part_tpe = (tpe_fermes / counts_fermes.sum()) * 100
        
        with st.chat_message("assistant"):
            st.write(f"**Focus TPE :** Les structures de très petite taille (moins de 3 salariés) représentent **{part_tpe:.1f}%** des radiations observées sur la période.")

st.divider()
st.caption("ℹ️ Source : Base SIRENE & Infogreffe | Focus méthodologique : SAS & SARL.")