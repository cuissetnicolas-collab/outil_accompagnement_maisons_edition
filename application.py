import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Outils Édition - Analyse comptable", layout="wide")

st.title("📘 Outils Édition - Suite analytique comptable")

# ============================
# Navigation principale
# ============================
menu = st.sidebar.selectbox(
    "Navigation",
    [
        "DATA EDITION (Import)",
        "SOCLE EDITION (Base Pivot)",
        "RETURNS EDITION (Retours & Remises)",
        "TRÉSORERIE PRÉVISIONNELLE"
    ]
)

# ============================
# MODULE 1 : DATA EDITION
# ============================
if menu == "DATA EDITION (Import)":
    st.header("📥 DATA EDITION - Import des données comptables")

    fichier = st.file_uploader("Sélectionnez un fichier Excel comptable", type=["xlsx", "xls"])

    if fichier is not None:
        df = pd.read_excel(fichier)
        st.session_state["df_source"] = df
        st.success("✅ Fichier importé avec succès !")
        st.dataframe(df.head())
        st.info("Les données importées seront utilisées pour générer le SOCLE EDITION.")

# ============================
# MODULE 2 : SOCLE EDITION
# ============================
elif menu == "SOCLE EDITION (Base Pivot)":
    st.header("🧩 SOCLE EDITION - Base pivot analytique")

    if "df_source" not in st.session_state:
        st.warning("⚠️ Veuillez d'abord importer un fichier dans DATA EDITION.")
        st.stop()

    df = st.session_state["df_source"].copy()
    colonnes_dispo = df.columns.tolist()

    st.markdown("### 🧭 Sélection des colonnes")
    col_date = st.selectbox("Colonne de la date :", colonnes_dispo)
    col_compte = st.selectbox("Colonne du compte comptable :", colonnes_dispo)
    col_debit = st.selectbox("Colonne du débit :", colonnes_dispo)
    col_credit = st.selectbox("Colonne du crédit :", colonnes_dispo)
    col_libelle = st.selectbox("Colonne du libellé :", colonnes_dispo)
    col_analytique = st.selectbox("Colonne du code analytique / ISBN :", colonnes_dispo)

    if st.button("🔄 Générer le SOCLE EDITION"):
        df_pivot = df.rename(columns={
            col_date: "Date",
            col_compte: "Compte",
            col_debit: "Débit",
            col_credit: "Crédit",
            col_libelle: "Libellé",
            col_analytique: "Code_Analytique"
        })

        df_pivot["Date"] = pd.to_datetime(df_pivot["Date"], errors="coerce")
        df_pivot["Débit"] = pd.to_numeric(df_pivot["Débit"], errors="coerce").fillna(0)
        df_pivot["Crédit"] = pd.to_numeric(df_pivot["Crédit"], errors="coerce").fillna(0)

        st.session_state["df_pivot"] = df_pivot
        st.success("✅ SOCLE EDITION généré avec succès.")
        st.dataframe(df_pivot.head())

# ============================
# MODULE 3 : RETURNS EDITION
# ============================
elif menu == "RETURNS EDITION (Retours & Remises)":
    st.header("📦 RETURNS EDITION - Analyse des retours et remises libraires")

    st.info("""
    💡 **Note importante**  
    Les indicateurs de retours et de chiffre d’affaires s’appuient sur les **numéros de comptes** 
    ou **libellés** présents dans votre fichier comptable.  
    Chaque cabinet doit s’assurer que les comptes suivants sont clairement identifiés :
    - Compte de **ventes brutes** (ex : 701...)  
    - Compte de **remises libraires** (ex : 7091...)  
    - Compte de **retours de livres** (ex : 709...)  
    """)

    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Vous devez d'abord générer le SOCLE EDITION.")
        st.stop()

    df = st.session_state["df_pivot"].copy()

    # 🔹 Paramétrage des comptes
    st.subheader("⚙️ Paramétrage des comptes comptables")
    compte_ventes = st.text_input("Numéro de compte des ventes brutes :", value="701")
    compte_retours = st.text_input("Numéro de compte des retours :", value="709")
    compte_remises = st.text_input("Numéro de compte des remises libraires :", value="7091")

    if st.button("🔍 Lancer l'analyse des retours"):
        df["Résultat"] = df["Crédit"] - df["Débit"]

        ventes = df[df["Compte"].astype(str).str.startswith(compte_ventes)]
        retours = df[df["Compte"].astype(str).str.startswith(compte_retours)]
        remises = df[df["Compte"].astype(str).str.startswith(compte_remises)]

        ca_brut = ventes["Crédit"].sum() - ventes["Débit"].sum()
        total_retours = retours["Débit"].sum() - retours["Crédit"].sum()
        total_remises = remises["Débit"].sum() - remises["Crédit"].sum()
        ca_net = ca_brut - total_retours - total_remises

        st.markdown("### 📊 Résumé global")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("CA brut", f"{ca_brut:,.0f} €")
        col2.metric("Retours", f"{total_retours:,.0f} €")
        col3.metric("Remises", f"{total_remises:,.0f} €")
        col4.metric("CA net", f"{ca_net:,.0f} €")

        # Analyse par ISBN
        st.markdown("### 🔎 Analyse par ISBN")
        ventes_isbn = ventes.groupby("Code_Analytique", as_index=False)["Crédit"].sum().rename(columns={"Crédit": "Ventes"})
        retours_isbn = retours.groupby("Code_Analytique", as_index=False)["Débit"].sum().rename(columns={"Débit": "Retours"})

        df_merge = pd.merge(ventes_isbn, retours_isbn, on="Code_Analytique", how="outer").fillna(0)
        df_merge["Taux_retour_%"] = np.where(df_merge["Ventes"] != 0, (df_merge["Retours"] / df_merge["Ventes"]) * 100, 0)

        st.dataframe(df_merge.sort_values("Taux_retour_%", ascending=False))
        fig = px.bar(df_merge, x="Code_Analytique", y="Taux_retour_%", title="Taux de retour par ISBN")
        st.plotly_chart(fig, use_container_width=True)

# ============================
# MODULE 4 : TRÉSORERIE PRÉVISIONNELLE
# ============================
elif menu == "TRÉSORERIE PRÉVISIONNELLE":
    st.header("💰 Trésorerie prévisionnelle")

    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Vous devez d'abord générer le SOCLE EDITION.")
        st.stop()

    df_pivot = st.session_state["df_pivot"].copy()

    # Date de départ
    date_debut = st.date_input("Date de départ de la trésorerie", pd.to_datetime("2025-04-01"))

    # Nettoyage et conversion
    df_pivot["Compte"] = df_pivot["Compte"].astype(str).str.strip()
    df_pivot["Date"] = pd.to_datetime(df_pivot["Date"], errors="coerce")
    df_pivot["Débit"] = pd.to_numeric(df_pivot["Débit"], errors="coerce").fillna(0)
    df_pivot["Crédit"] = pd.to_numeric(df_pivot["Crédit"], errors="coerce").fillna(0)

    # Calcul du solde de départ (comptes 5)
    comptes_bancaires = df_pivot[df_pivot["Compte"].str.startswith("5")]
    solde_depart_df = comptes_bancaires[comptes_bancaires["Date"] <= pd.to_datetime(date_debut)]
    solde_depart_total = solde_depart_df["Crédit"].sum() - solde_depart_df["Débit"].sum()
    st.info(f"Solde de départ : {solde_depart_total:,.2f} €")

    # Paramètres de projection
    horizon = st.slider("Horizon de projection (en mois)", 3, 24, 12)
    croissance_ca = st.number_input("Croissance mensuelle du CA (%)", value=2.0) / 100
    evolution_charges = st.number_input("Évolution mensuelle des charges (%)", value=1.0) / 100

    # Flux hors comptes bancaires
    df_flux = df_pivot[~df_pivot["Compte"].str.startswith("5")].copy()
    df_flux = df_flux.dropna(subset=["Date"])
    df_flux = df_flux[df_flux["Date"] >= pd.to_datetime(date_debut)]
    df_flux["Mois"] = df_flux["Date"].dt.to_period("M").astype(str)

    flux_mensuel = df_flux.groupby("Mois").agg({"Débit": "sum", "Crédit": "sum"}).reset_index()
    flux_mensuel["Solde_mensuel"] = flux_mensuel["Crédit"] - flux_mensuel["Débit"]
    flux_mensuel = flux_mensuel.sort_values("Mois")

    # Prévisions futures
    dernier_mois = pd.Period(flux_mensuel["Mois"].max(), freq="M") if not flux_mensuel.empty else pd.Period(date_debut, freq="M")
    previsions = []
    ca_actuel = flux_mensuel["Crédit"].iloc[-1] if not flux_mensuel.empty else 0
    charges_actuelles = flux_mensuel["Débit"].iloc[-1] if not flux_mensuel.empty else 0

    for i in range(1, horizon + 1):
        prochain_mois = (dernier_mois + i).strftime("%Y-%m")
        ca_actuel *= (1 + croissance_ca)
        charges_actuelles *= (1 + evolution_charges)
        solde_prevu = ca_actuel - charges_actuelles
        previsions.append({
            "Mois": prochain_mois,
            "Débit": charges_actuelles,
            "Crédit": ca_actuel,
            "Solde_mensuel": solde_prevu
        })

    df_prev = pd.DataFrame(previsions)
    df_tresorerie = pd.concat([flux_mensuel, df_prev], ignore_index=True)
    df_tresorerie["Trésorerie_cumulée"] = solde_depart_total + df_tresorerie["Solde_mensuel"].cumsum()

    # Graphique
    fig = px.line(df_tresorerie, x="Mois", y="Trésorerie_cumulée", title="📈 Évolution prévisionnelle de la trésorerie", markers=True)
    fig.update_layout(xaxis_title="Mois", yaxis_title="Trésorerie (€)")
    st.plotly_chart(fig, use_container_width=True)

    # Détail mensuel
    st.subheader("📋 Détail mensuel")
    st.dataframe(df_tresorerie.style.format({
        "Débit": "{:,.0f}",
        "Crédit": "{:,.0f}",
        "Solde_mensuel": "{:,.0f}",
        "Trésorerie_cumulée": "{:,.0f}"
    }))
