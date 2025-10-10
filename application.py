import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import plotly.express as px

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

# =====================
# HEADER NOM UTILISATEUR
# =====================
st.sidebar.success(f"👤 {st.session_state['name']}")

# =====================
# MENU PRINCIPAL
# =====================
pages = [
    "Accueil",
    "DATA EDITION",
    "SOCLE EDITION",
    "VISION EDITION",
    "ISBN VIEW",
    "CASH EDITION",
    "ROYALTIES EDITION",
    "RETURNS EDITION"
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
    - Analyser vos ventes et résultats par ISBN (**VISION EDITION & ISBN VIEW**)  
    - Suivre la trésorerie (**CASH EDITION**)  
    - Piloter les droits d’auteurs (**ROYALTIES EDITION**)  
    - Gérer les retours éditeurs/distributeurs (**RETURNS EDITION**)  

    👉 Utilisez le menu à gauche pour naviguer entre les modules.
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
        if st.button("Générer le SOCLE"):
            for col in ["Famille_Analytique","Code_Analytique"]:
                if col not in df.columns: df[col] = ""
                else: df[col] = df[col].fillna("")
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            pivot = df.groupby(["Compte","Famille_Analytique","Code_Analytique","Date"], as_index=False).agg({"Débit":"sum","Crédit":"sum"})
            st.session_state["df_pivot"] = pivot
            st.success("✅ SOCLE EDITION généré.")
            st.dataframe(pivot.head(20))

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
# CASH EDITION
# =====================
elif page == "CASH EDITION":
    st.header("💰 CASH EDITION - Trésorerie prévisionnelle")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        st.info("Module CASH EDITION prêt. Implémentation des projections de trésorerie...")

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

        # Export Excel
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_merge.to_excel(writer, index=False, sheet_name="Analyse_Retours")
        buffer.seek(0)
        st.download_button("📥 Télécharger l'analyse des retours", buffer,
                           file_name="Analyse_Retours_ISBN.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
