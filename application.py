import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# =====================
# AUTHENTIFICATION
# =====================
if "login" not in st.session_state:
    st.session_state["login"] = False

def login(username, password):
    users = {
        "aurore": {"password": "12345", "name": "Aurore Demoulin"},
    }
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
# MENU PRINCIPAL
# =====================
st.sidebar.success(f"Bienvenue {st.session_state['name']} 👋")
if st.sidebar.button("Déconnexion"):
    st.session_state["login"] = False
    st.experimental_rerun()

menu = st.sidebar.radio(
    "Menu principal",
    [
        "Générateur d'écritures BLDD",
        "Import données comptables",
        "Socle pivot analytique",
        "Tableaux & analyses"
    ]
)

# =====================
# MODULE 1 : BLDD
# =====================
if menu == "Générateur d'écritures BLDD":
    st.title("📊 Générateur d'écritures analytiques - BLDD")

    # --- Import fichier BLDD ---
    fichier_entree = st.file_uploader("📂 Importer le fichier Excel BLDD", type=["xlsx"])

    # --- Paramètres de base ---
    date_ecriture = st.date_input("📅 Date d'écriture")
    journal = st.text_input("📒 Journal", value="VT")
    libelle_base = st.text_input("📝 Libellé", value="VENTES BLDD")

    compte_ca = st.text_input("💰 Compte CA", value="70110000")
    compte_com_dist = st.text_input("💰 Compte commissions distribution", value="62280000")
    compte_com_diff = st.text_input("💰 Compte commissions diffusion", value="62280001")

    # --- Taux ---
    taux_dist = st.number_input("Taux distribution (%)", value=12.5) / 100
    taux_diff = st.number_input("Taux diffusion (%)", value=9.0) / 100

    # --- Montants totaux ---
    com_distribution_total = st.number_input("Montant total commissions distribution", value=1000.00, format="%.2f")
    com_diffusion_total = st.number_input("Montant total commissions diffusion", value=500.00, format="%.2f")

    # --- Famille analytique obligatoire ---
    st.markdown("---")
    famille_analytique = st.text_input(
        "🧭 Famille analytique (obligatoire pour Pennylane)",
        value="ISBN"
    )
    st.caption("Exemples : ISBN / Collection / Client / Projet / Auteur")

    if not famille_analytique:
        st.warning("⚠️ Merci de renseigner la famille analytique avant de générer les écritures.")

    # ========== Traitement ==========  
    if fichier_entree is not None and famille_analytique:
        # ... tout le reste du code BLDD ...
# =====================
# MODULE 2 : IMPORT COMPTABLE
# =====================
st.header("📂 Importation des données comptables")

mode_import = st.selectbox(
    "Choisis ton mode d’extraction :",
    [
        "1️⃣ Fichier Excel (Pennylane Connect, Sage, etc.)",
        "2️⃣ API directe (mode expert)",
        "3️⃣ Synchronisation automatique (dossier partagé)"
    ]
)

if mode_import.startswith("1"):
    st.info("🧩 Mode fichier Excel : télécharge tes exports depuis Pennylane Connect ou ton logiciel comptable.")
    # (ici tu gardes le code d’import Excel standardisé vu précédemment)

elif mode_import.startswith("2"):
    st.info("🔗 Mode API : connexion directe à Pennylane, MyUnisoft, QuickBooks, etc.")
    # (ici tu gardes le code d’import API multi-logiciels vu précédemment)

elif mode_import.startswith("3"):
    st.info("📁 Mode dossier synchronisé : l’application surveille un dossier partagé (OneDrive, Drive...)")
    dossier_path = st.text_input("Chemin du dossier synchronisé :", placeholder="ex: C:/Users/EC/OneDrive/Pennylane_Connect")
    
    if st.button("Charger les fichiers du dossier"):
        import glob, os
        fichiers = glob.glob(os.path.join(dossier_path, "*.xlsx"))
        if fichiers:
            dfs = [pd.read_excel(f) for f in fichiers]
            df_all = pd.concat(dfs, ignore_index=True)
            st.success(f"{len(fichiers)} fichiers chargés automatiquement depuis {dossier_path}")
            st.dataframe(df_all.head())
        else:
            st.warning("Aucun fichier trouvé dans le dossier indiqué.")
# =====================
# MODULE 3 : SOCLE PIVOT
# =====================
elif menu == "Socle pivot analytique":
    st.header("🏗️ Construction du socle pivot analytique")
    st.info("Ici on fusionnera BLDD + Comptabilité + Données internes pour créer une base unique exploitable.")

# =====================
# MODULE 4 : TABLEAUX & ANALYSES
# =====================
elif menu == "Tableaux & analyses":
    st.header("📊 Tableaux & analyses")
    sous_menu = st.selectbox("Choix de l'analyse", [
        "Dashboard analytique",
        "Trésorerie prévisionnelle",
        "Seuil de rentabilité",
        "Droits d’auteur",
        "Contrôle TVA / Dépôt légal"
    ])
    st.info(f"📌 Module {sous_menu} en cours de développement…")
