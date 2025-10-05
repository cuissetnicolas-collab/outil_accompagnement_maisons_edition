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
elif menu == "Import données comptables":
    st.header("📂 Import des données comptables")

    # 1️⃣ Choix de la source
    choix = st.radio("Choisis la source des données :", ["Fichier Excel", "API Pennylane"])

    # 2️⃣ Import Excel
    if choix == "Fichier Excel":
        fichier = st.file_uploader("Importer un fichier comptable (.xlsx)", type=["xlsx"])
        if fichier:
            try:
                df_compte = pd.read_excel(fichier, dtype=str)
                st.success(f"✅ Fichier importé : {df_compte.shape[0]} lignes")
                st.dataframe(df_compte.head())

                # Mapping standard minimal
                colonnes_dispo = list(df_compte.columns)
                st.write("🧩 Colonnes détectées :", colonnes_dispo)

                # Sélection manuelle des colonnes utiles
                col_date = st.selectbox("🗓️ Colonne Date", colonnes_dispo)
                col_journal = st.selectbox("📒 Colonne Journal", colonnes_dispo)
                col_compte = st.selectbox("💰 Colonne Compte", colonnes_dispo)
                col_libelle = st.selectbox("📝 Colonne Libellé", colonnes_dispo)
                col_debit = st.selectbox("📈 Colonne Débit", colonnes_dispo)
                col_credit = st.selectbox("📉 Colonne Crédit", colonnes_dispo)

                if st.button("Nettoyer et standardiser"):
                    df_clean = df_compte.rename(columns={
                        col_date: "Date",
                        col_journal: "Journal",
                        col_compte: "Compte",
                        col_libelle: "Libelle",
                        col_debit: "Debit",
                        col_credit: "Credit"
                    })

                    # Typage
                    df_clean["Debit"] = pd.to_numeric(df_clean["Debit"], errors="coerce").fillna(0)
                    df_clean["Credit"] = pd.to_numeric(df_clean["Credit"], errors="coerce").fillna(0)
                    df_clean["Date"] = pd.to_datetime(df_clean["Date"], errors="coerce")

                    # Nettoyage
                    df_clean = df_clean.dropna(subset=["Compte", "Libelle"])
                    st.success("✨ Données standardisées !")
                    st.dataframe(df_clean.head())

                    # Contrôle équilibre
                    total_debit = df_clean["Debit"].sum()
                    total_credit = df_clean["Credit"].sum()
                    st.write(f"**Contrôle équilibre :** Débit = {total_debit:,.2f} / Crédit = {total_credit:,.2f}")

                    # Export
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                        df_clean.to_excel(writer, index=False, sheet_name="Comptabilite_standard")
                    buffer.seek(0)
                    st.download_button(
                        label="📥 Télécharger le fichier standardisé",
                        data=buffer,
                        file_name="Compta_standardisee.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            except Exception as e:
                st.error(f"Erreur lors de la lecture du fichier : {e}")

    # 3️⃣ API Pennylane
    elif choix == "API Pennylane":
        st.info("🔗 Connexion à l’API Pennylane")

        api_key = st.text_input("🔐 API Key Pennylane", type="password")
        start_date = st.date_input("📆 Date de début")
        end_date = st.date_input("📆 Date de fin")

        if st.button("Importer depuis Pennylane"):
            if not api_key:
                st.warning("Merci de renseigner ton API Key Pennylane.")
            else:
                st.info("Connexion simulée (mode démo) — les endpoints API seront ajoutés ultérieurement.")
                # Exemple de structure attendue
                df_demo = pd.DataFrame({
                    "Date": pd.date_range(start=start_date, end=end_date, freq="M"),
                    "Journal": "VT",
                    "Compte": ["701100"]*3,
                    "Libelle": ["Ventes mensuelles"]*3,
                    "Debit": [0]*3,
                    "Credit": [15000, 12000, 18000],
                })
                st.success("✅ Données simulées depuis API Pennylane")
                st.dataframe(df_demo)

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
