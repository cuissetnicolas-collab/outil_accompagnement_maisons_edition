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
    st.header("📘 Générateur d'écritures analytiques – BLDD")

    # Champs communs
    date_ecriture = st.date_input("📅 Date d'écriture")
    journal = st.text_input("📒 Journal", value="VT")
    libelle_base = st.text_input("📝 Libellé", value="VENTES BLDD")

    compte_ca = st.text_input("💰 Compte CA", value="70110000")
    compte_com_dist = st.text_input("💰 Compte commissions distribution", value="62280000")
    compte_com_diff = st.text_input("💰 Compte commissions diffusion", value="62280001")

    taux_dist = st.number_input("Taux distribution (%)", value=12.5) / 100
    taux_diff = st.number_input("Taux diffusion (%)", value=9.0) / 100

    com_distribution_total = st.number_input("Montant total commissions distribution", value=1000.00, format="%.2f")
    com_diffusion_total = st.number_input("Montant total commissions diffusion", value=500.00, format="%.2f")

    # Upload fichier BLDD
    fichier_entree = st.file_uploader("📂 Importer le fichier Excel BLDD", type=["xlsx"])

    if fichier_entree is not None:
        df = pd.read_excel(fichier_entree, header=9, dtype={"ISBN": str})
        df.columns = df.columns.str.strip()
        df = df.dropna(subset=["ISBN"]).copy()
        df["ISBN"] = df["ISBN"].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df["ISBN"] = df["ISBN"].str.replace('-', '', regex=False).str.replace(' ', '', regex=False)

        for c in ["Vente", "Net", "Facture"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).round(2)

        # ----- Calcul commissions -----
        # Distribution
        raw_dist = df["Vente"] * taux_dist
        sum_raw_dist = raw_dist.sum()
        scaled_dist = raw_dist * (com_distribution_total / sum_raw_dist)
        cents_floor = np.floor(scaled_dist * 100).astype(int)
        remainders = (scaled_dist * 100) - cents_floor
        target_cents = int(round(com_distribution_total * 100))
        diff = target_cents - cents_floor.sum()
        idx_sorted = np.argsort(-remainders.values)
        adjust = np.zeros(len(df), dtype=int)
        if diff > 0:
            adjust[idx_sorted[:diff]] = 1
        elif diff < 0:
            adjust[idx_sorted[len(df)+diff:]] = -1
        df["Commission_distribution"] = (cents_floor + adjust) / 100.0

        # Diffusion
        df["Commission_diffusion"] = df["Net"] * (com_diffusion_total / df["Net"].sum())
        cents_floor = np.floor(df["Commission_diffusion"] * 100).astype(int)
        remainders = (df["Commission_diffusion"] * 100) - cents_floor
        target_cents = int(round(com_diffusion_total * 100))
        diff = target_cents - cents_floor.sum()
        idx_sorted = np.argsort(-remainders.values)
        adjust = np.zeros(len(df), dtype=int)
        if diff > 0:
            adjust[idx_sorted[:diff]] = 1
        elif diff < 0:
            adjust[idx_sorted[len(df)+diff:]] = -1
        df["Commission_diffusion"] = (cents_floor + adjust) / 100.0

        # ----- Construction écritures -----
        ecritures = []
        total_facture_global = df["Facture"].sum().round(2)

        # CA global
        ecritures.append({
            "Date": date_ecriture.strftime("%d/%m/%Y"), "Journal": journal, "Compte": compte_ca,
            "Libelle": f"{libelle_base} - CA global", "ISBN": "",
            "Débit": total_facture_global, "Crédit": 0.0
        })

        # CA par ISBN
        for _, r in df.iterrows():
            ecritures.append({
                "Date": date_ecriture.strftime("%d/%m/%Y"), "Journal": journal, "Compte": compte_ca,
                "Libelle": f"{libelle_base} - CA ISBN", "ISBN": r["ISBN"],
                "Débit": 0.0, "Crédit": round(float(r["Facture"]), 2)
            })

        # Commissions distribution
        total_dist = df["Commission_distribution"].sum().round(2)
        ecritures.append({
            "Date": date_ecriture.strftime("%d/%m/%Y"), "Journal": journal, "Compte": compte_com_dist,
            "Libelle": f"{libelle_base} - Com. distribution global", "ISBN": "",
            "Débit": 0.0, "Crédit": total_dist
        })
        for _, r in df.iterrows():
            ecritures.append({
                "Date": date_ecriture.strftime("%d/%m/%Y"), "Journal": journal, "Compte": compte_com_dist,
                "Libelle": f"{libelle_base} - Com. distribution ISBN", "ISBN": r["ISBN"],
                "Débit": round(float(r["Commission_distribution"]), 2), "Crédit": 0.0
            })

        # Commissions diffusion
        total_diff = df["Commission_diffusion"].sum().round(2)
        ecritures.append({
            "Date": date_ecriture.strftime("%d/%m/%Y"), "Journal": journal, "Compte": compte_com_diff,
            "Libelle": f"{libelle_base} - Com. diffusion global", "ISBN": "",
            "Débit": 0.0, "Crédit": total_diff
        })
        for _, r in df.iterrows():
            ecritures.append({
                "Date": date_ecriture.strftime("%d/%m/%Y"), "Journal": journal, "Compte": compte_com_diff,
                "Libelle": f"{libelle_base} - Com. diffusion ISBN", "ISBN": r["ISBN"],
                "Débit": round(float(r["Commission_diffusion"]), 2), "Crédit": 0.0
            })

        df_ecr = pd.DataFrame(ecritures)

        # Vérification équilibre
        total_debit = round(df_ecr["Débit"].sum(), 2)
        total_credit = round(df_ecr["Crédit"].sum(), 2)
        if total_debit != total_credit:
            st.error(f"⚠️ Écriture déséquilibrée : Débit={total_debit}, Crédit={total_credit}")
        else:
            st.success("✅ Écritures équilibrées !")

        # Export Excel
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_ecr.to_excel(writer, index=False, sheet_name="Ecritures")
        buffer.seek(0)

        st.download_button(
            label="📥 Télécharger les écritures (Excel)",
            data=buffer,
            file_name="Ecritures_Pennylane.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.subheader("👀 Aperçu des écritures générées")
        st.dataframe(df_ecr)

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
