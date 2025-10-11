import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import plotly.express as px

# =====================
# CONFIG PAGE
# =====================
st.set_page_config(page_title="Outil Édition", page_icon="📚")
st.sidebar.markdown("**Auteur : Nicolas CUISSET**")

# =====================
# AUTHENTIFICATION
# =====================
if "login" not in st.session_state:
    st.session_state["login"] = False

def login(username, password):
    users = {"aurore": {"password": "12345", "name": "Aurore Demoulin"}}
    if username in users and password == users[username]["password"]:
        st.session_state["login"] = True
        st.session_state["username"] = username
        st.session_state["name"] = users[username]["name"]
        return True
    return False

if not st.session_state["login"]:
    st.title("🔑 Connexion espace expert-comptable")
    username_input = st.text_input("Identifiant")
    password_input = st.text_input("Mot de passe", type="password")
    if st.button("Connexion"):
        if login(username_input, password_input):
            st.success(f"Bienvenue {st.session_state['name']} 👋")
        else:
            st.error("❌ Identifiants incorrects")
    st.stop()

st.sidebar.success(f"👤 {st.session_state['name']}")

# =====================
# MENU PRINCIPAL
# =====================
pages = [
    "Accueil",
    "DATA EDITION",
    "SOCLE EDITION",
    "REPARTITION CHARGES FIXES",
    "VISION EDITION",
    "ISBN VIEW",
    "ROYALTIES EDITION",
    "RETURNS EDITION",
    "CASH EDITION",
    "SYNTHESE GLOBALE"
]
page = st.sidebar.selectbox("📂 Menu principal", pages)
if st.sidebar.button("Déconnexion"):
    st.session_state["login"] = False
    st.experimental_rerun()

# =====================
# ACCUEIL
# =====================
if page == "Accueil":
    st.title("👋 Bienvenue dans votre outil d'accompagnement éditorial")
    st.markdown("""
    Cet outil permet de :
    - Importer vos données comptables analytiques (**DATA EDITION**)  
    - Générer un socle pivot multi-logiciels (**SOCLE EDITION**)  
    - Imputer vos charges fixes (**REPARTITION CHARGES FIXES**)  
    - Analyser vos ventes et résultats par ISBN (**VISION EDITION & ISBN VIEW**)  
    - Piloter les droits d’auteurs sur vos livres (**ROYALTIES EDITION**)  
    - Gérer les retours éditeurs/distributeurs (**RETURNS EDITION**)  
    - Suivre la trésorerie (**CASH EDITION**)  
    - Obtenir une synthèse globale des indicateurs (**SYNTHESE GLOBALE**)  
    """)
    st.stop()

# =====================
# DATA EDITION
# =====================
if page == "DATA EDITION":
    st.header("📂 DATA EDITION - Import des données analytiques")
    fichier_comptables = st.file_uploader("Sélectionnez votre fichier Excel", type=["xlsx"])
    if fichier_comptables:
        try:
            df = pd.read_excel(fichier_comptables, header=0)
            df.columns = df.columns.str.strip()
            st.write("Colonnes détectées :", list(df.columns))
            col_mapping = {}
            if "Numéro de compte" in df.columns: col_mapping["Numéro de compte"] = "Compte"
            if "Débit" in df.columns: col_mapping["Débit"] = "Débit"
            if "Crédit" in df.columns: col_mapping["Crédit"] = "Crédit"
            if "Familles de catégories" in df.columns: col_mapping["Familles de catégories"] = "Famille_Analytique"
            if "Catégories" in df.columns: col_mapping["Catégories"] = "Code_Analytique"
            if "Date" in df.columns: col_mapping["Date"] = "Date"
            elif "Date opération" in df.columns: col_mapping["Date opération"] = "Date"
            if "Compte" not in col_mapping.values() or "Date" not in col_mapping.values():
                st.error("⚠️ Colonnes 'Compte' et/ou 'Date' manquantes !")
            else:
                df.rename(columns=col_mapping, inplace=True)
                st.session_state["df_comptables"] = df
                st.success(f"✅ Fichier chargé : {df.shape[0]} lignes")
                st.dataframe(df.head())
        except Exception as e:
            st.error(f"❌ Erreur lors de l'importation : {e}")

# =====================
# SOCLE EDITION
# =====================
elif page == "SOCLE EDITION":
    st.header("🛠️ SOCLE EDITION - Génération du pivot analytique")
    if "df_comptables" not in st.session_state:
        st.warning("⚠️ Importer d'abord les données via DATA EDITION.")
    else:
        df = st.session_state["df_comptables"].copy()
        st.info("⚙️ Paramétrez vos numéros de comptes clés avant de générer le SOCLE.")
        comptes_ventes = st.text_input("Numéros de comptes VENTES (ex: 701,706)", value="701")
        comptes_retours = st.text_input("Numéros de comptes RETOURS (ex:7097,7098)", value="709000000")
        comptes_remises = st.text_input("Numéros de comptes REMISES LIBRAIRES (ex:7091)", value="709100000")
        comptes_banques = st.text_input("Numéros de comptes BANQUES (ex:512)", value="512")
        comptes_charges = st.text_input("Numéros de comptes CHARGES (ex:6)", value="6")
        
        if st.button("Générer le SOCLE"):
            for col in ["Famille_Analytique","Code_Analytique"]:
                if col not in df.columns: df[col] = ""
                else: df[col] = df[col].fillna("")
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            pivot = df.groupby(["Compte","Famille_Analytique","Code_Analytique","Date"], as_index=False).agg({"Débit":"sum","Crédit":"sum"})
            st.session_state["df_pivot"] = pivot
            st.session_state["param_comptes"] = {
                "ventes": [x.strip() for x in comptes_ventes.split(",")],
                "retours": [x.strip() for x in comptes_retours.split(",")],
                "remises": [x.strip() for x in comptes_remises.split(",")],
                "banques": [x.strip() for x in comptes_banques.split(",")],
                "charges": [x.strip() for x in comptes_charges.split(",")]
            }
            st.success("✅ SOCLE EDITION généré et comptes paramétrés.")
            st.dataframe(pivot.head(20))

# =====================
# REPARTITION CHARGES FIXES
# =====================
elif page == "REPARTITION CHARGES FIXES":
    st.header("📊 Répartition Charges Fixes")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df_pivot = st.session_state["df_pivot"].copy()
        deja_reparti = st.radio("Avez-vous déjà imputé vos charges fixes ?", ["Oui", "Non"])
        if deja_reparti == "Oui":
            st.info("Les charges fixes existantes seront utilisées.")
        else:
            total_charges = st.number_input("Montant total des charges fixes (€)", value=10000.0)
            cle_repartition = st.radio("Clé de répartition", ["Proportionnel CA par ISBN", "Égalitaire par ISBN"])
            df_cr = df_pivot.groupby("Code_Analytique", as_index=False).agg({"Crédit":"sum"})
            if cle_repartition == "Proportionnel CA par ISBN":
                df_cr["Part"] = df_cr["Crédit"]/df_cr["Crédit"].sum()
            else:
                df_cr["Part"] = 1/len(df_cr)
            df_cr["Charges_Fixes"] = df_cr["Part"] * total_charges
            st.session_state["df_charges_fixes"] = df_cr[["Code_Analytique","Charges_Fixes"]]
            st.success("✅ Charges fixes réparties par ISBN.")
            st.dataframe(st.session_state["df_charges_fixes"])

# =====================
# VISION EDITION
# =====================
elif page == "VISION EDITION":
    st.header("📈 VISION EDITION - Dashboard analytique")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        df["Résultat"] = df["Crédit"] - df["Débit"]
        top_isbn = df.groupby("Code_Analytique", as_index=False)["Résultat"].sum().sort_values("Résultat", ascending=False).head(10)
        st.dataframe(top_isbn)
        fig = px.bar(top_isbn, x="Code_Analytique", y="Résultat", title="Top 10 ISBN par résultat net", labels={"Code_Analytique":"ISBN","Résultat":"Résultat net"})
        st.plotly_chart(fig, use_container_width=True)

# =====================
# ISBN VIEW
# =====================
elif page == "ISBN VIEW":
    st.header("💼 ISBN VIEW - Mini compte de résultat par ISBN")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        df_cr = df.groupby("Code_Analytique", as_index=False).agg({"Débit":"sum","Crédit":"sum"})
        df_cr["Résultat"] = df_cr["Crédit"] - df_cr["Débit"]
        st.dataframe(df_cr)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_cr.to_excel(writer, index=False, sheet_name="Mini_CR_ISBN")
        buffer.seek(0)
        st.download_button("📥 Télécharger le mini compte de résultat par ISBN", buffer, file_name="Mini_Compte_Resultat_ISBN.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =====================
# ROYALTIES EDITION
# =====================
elif page == "ROYALTIES EDITION":
    st.header("📚 ROYALTIES EDITION - Droits d’auteurs")
    st.markdown("Choisissez la source pour le nombre d'exemplaires vendus :")
    source = st.radio("Source des données", ["Compta analytique", "Importer fichier BLDD"])
    if source == "Compta analytique":
        st.info("Les données seront récupérées depuis le SOCLE EDITION.")
    else:
        fichier_bldd = st.file_uploader("Importer votre fichier BLDD", type=["xlsx"])
        if fichier_bldd:
            df_bldd = pd.read_excel(fichier_bldd)
            st.session_state["df_bldd"] = df_bldd
            st.success("Fichier BLDD importé.")
    taux_fixe = st.number_input("Taux fixe de droits (%)", value=10.0)
    st.info(f"Taux sélectionné : {taux_fixe}%")

# =====================
# RETURNS EDITION
# =====================
elif page == "RETURNS EDITION":
    st.header("📦 RETURNS EDITION - Gestion des retours")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        param = st.session_state.get("param_comptes", {})

        # Comptes paramétrés dans SOCLE EDITION
        comptes_ventes = [c.strip() for c in param.get("ventes", []) if c.strip()]
        comptes_retours = [c.strip() for c in param.get("retours", []) if c.strip()]
        comptes_remises = [c.strip() for c in param.get("remises", []) if c.strip()]

        if not comptes_retours or not comptes_remises:
            st.warning("⚠️ Veuillez définir les comptes retours et remises dans SOCLE EDITION (ex: 709000000, 709100000).")
            st.stop()

        # Nettoyage
        df["Compte"] = df["Compte"].astype(str).str.strip()
        df["Débit"] = pd.to_numeric(df["Débit"], errors="coerce").fillna(0)
        df["Crédit"] = pd.to_numeric(df["Crédit"], errors="coerce").fillna(0)

        # Calcul du chiffre d'affaires brut (soldes des comptes de ventes)
        df_ventes = df[df["Compte"].isin(comptes_ventes)]
        ca_brut = (df_ventes["Crédit"].sum() - df_ventes["Débit"].sum()) if not df_ventes.empty else 0

        # Calcul des retours (comptes paramétrés pour retours)
        df_retours = df[df["Compte"].isin(comptes_retours)]
        total_retours = (df_retours["Débit"].sum() - df_retours["Crédit"].sum()) if not df_retours.empty else 0

        # Calcul des remises (comptes paramétrés pour remises)
        df_remises = df[df["Compte"].isin(comptes_remises)]
        total_remises = (df_remises["Débit"].sum() - df_remises["Crédit"].sum()) if not df_remises.empty else 0

        # Affichage des indicateurs
        st.metric("💰 CA Brut", f"{ca_brut:,.0f} €")
        st.metric("📦 Retours", f"{total_retours:,.0f} €")
        st.metric("🏷️ Remises libraires", f"{total_remises:,.0f} €")

        # Détail par ISBN pour les retours
        if not df_retours.empty:
            top_retours = (
                df_retours.groupby("Code_Analytique", as_index=False)["Débit"]
                .sum()
                .sort_values("Débit", ascending=False)
            )
            st.subheader("📚 Détail des retours par ISBN")
            st.dataframe(top_retours)
        else:
            st.info("Aucun retour détecté pour les comptes spécifiés.")
# =====================
# SYNTHESE GLOBALE
# =====================
elif page == "SYNTHESE GLOBALE":
    st.header("📊 SYNTHESE GLOBALE - Indicateurs clés")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
        st.stop()
    
    df = st.session_state["df_pivot"].copy()
    param = st.session_state.get("param_comptes", {})

    comptes_ventes = param.get("ventes", ["701"])
    comptes_retours = ["709000000"]
    comptes_remises = ["709100000"]

    def match_compte(compte, target):
        if pd.isna(compte):
            return False
        try:
            compte_int = int(float(compte))
            return compte_int == int(target)
        except:
            return str(compte).strip().lstrip("0") == str(int(target))

    def filter_comptes(df, comptes):
        return df[df["Compte"].apply(lambda x: any(match_compte(x, c) for c in comptes))]

    ca = filter_comptes(df, comptes_ventes)["Crédit"].sum() - filter_comptes(df, comptes_ventes)["Débit"].sum()
    retours = filter_comptes(df, comptes_retours)["Crédit"].sum() - filter_comptes(df, comptes_retours)["Débit"].sum()
    remises = filter_comptes(df, comptes_remises)["Crédit"].sum() - filter_comptes(df, comptes_remises)["Débit"].sum()

    df["Résultat"] = df["Crédit"] - df["Débit"]
    if "df_charges_fixes" in st.session_state:
        df_charges = st.session_state["df_charges_fixes"]
        df = df.merge(df_charges, on="Code_Analytique", how="left")
        df["Résultat"] -= df["Charges_Fixes"].fillna(0)
    resultat_net = df["Résultat"].sum()

    tresorerie = st.session_state.get("df_tresorerie", pd.DataFrame()).get("Trésorerie_cumulée", pd.Series([np.nan])).iloc[-1]

    st.metric("💰 Chiffre d'affaires brut", f"{ca:,.0f} €")
    st.metric("📦 Retours", f"{retours:,.0f} €")
    st.metric("🏷️ Remises libraires", f"{remises:,.0f} €")
    st.metric("📊 Résultat net total", f"{resultat_net:,.0f} €")
    st.metric("💸 Trésorerie cumulée", f"{tresorerie:,.0f} €" if not np.isnan(tresorerie) else "N/A")
    
    st.subheader("Détail par ISBN")
    df_isbn = df.groupby("Code_Analytique", as_index=False).agg({"Crédit":"sum","Débit":"sum","Résultat":"sum"})
    if "df_charges_fixes" in st.session_state:
        df_isbn = df_isbn.merge(st.session_state["df_charges_fixes"], on="Code_Analytique", how="left")
    st.dataframe(df_isbn)
