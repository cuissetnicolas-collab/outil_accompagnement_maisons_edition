import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import glob, os

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
        df = pd.read_excel(fichier_entree, header=9, dtype={"ISBN": str})
        df.columns = df.columns.str.strip()
        df = df.dropna(subset=["ISBN"]).copy()

        df["ISBN"] = df["ISBN"].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df["ISBN"] = df["ISBN"].str.replace('-', '', regex=False).str.replace(' ', '', regex=False)

        for c in ["Vente", "Net", "Facture"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).round(2)

        # --- Distribution ---
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

        # --- Diffusion ---
        raw_diff = df["Net"] * taux_diff
        sum_raw_diff = raw_diff.sum()
        scaled_diff = raw_diff * (com_diffusion_total / sum_raw_diff)
        cents_floor = np.floor(scaled_diff * 100.0).astype(int)
        remainders = (scaled_diff * 100.0) - cents_floor
        target_cents = int(round(com_diffusion_total * 100))
        diff = target_cents - cents_floor.sum()
        idx_sorted = np.argsort(-remainders.values)
        adjust = np.zeros(len(df), dtype=int)
        if diff > 0:
            adjust[idx_sorted[:diff]] = 1
        elif diff < 0:
            adjust[idx_sorted[len(df)+diff:]] = -1
        df["Commission_diffusion"] = (cents_floor + adjust) / 100.0

        # --- Construction écritures ---
        ecritures = []
        total_facture_global = df["Facture"].sum().round(2)

        # CA global
        ecritures.append({
            "Date": date_ecriture.strftime("%d/%m/%Y"),
            "Journal": journal,
            "Compte": compte_ca,
            "Libelle": f"{libelle_base} - CA global",
            "Famille_Analytique": famille_analytique,
            "Code_Analytique": "",
            "Débit": total_facture_global,
            "Crédit": 0.0
        })

        # CA par ISBN
        for _, r in df.iterrows():
            ecritures.append({
                "Date": date_ecriture.strftime("%d/%m/%Y"),
                "Journal": journal,
                "Compte": compte_ca,
                "Libelle": f"{libelle_base} - CA ISBN",
                "Famille_Analytique": famille_analytique,
                "Code_Analytique": r["ISBN"],
                "Débit": 0.0,
                "Crédit": round(float(r["Facture"]), 2)
            })

        # Commissions distribution
        total_dist = df["Commission_distribution"].sum().round(2)
        ecritures.append({
            "Date": date_ecriture.strftime("%d/%m/%Y"),
            "Journal": journal,
            "Compte": compte_com_dist,
            "Libelle": f"{libelle_base} - Com. distribution global",
            "Famille_Analytique": famille_analytique,
            "Code_Analytique": "",
            "Débit": 0.0,
            "Crédit": total_dist
        })
        for _, r in df.iterrows():
            ecritures.append({
                "Date": date_ecriture.strftime("%d/%m/%Y"),
                "Journal": journal,
                "Compte": compte_com_dist,
                "Libelle": f"{libelle_base} - Com. distribution ISBN",
                "Famille_Analytique": famille_analytique,
                "Code_Analytique": r["ISBN"],
                "Débit": round(float(r["Commission_distribution"]), 2),
                "Crédit": 0.0
            })

        # Commissions diffusion
        total_diff = df["Commission_diffusion"].sum().round(2)
        ecritures.append({
            "Date": date_ecriture.strftime("%d/%m/%Y"),
            "Journal": journal,
            "Compte": compte_com_diff,
            "Libelle": f"{libelle_base} - Com. diffusion global",
            "Famille_Analytique": famille_analytique,
            "Code_Analytique": "",
            "Débit": 0.0,
            "Crédit": total_diff
        })
        for _, r in df.iterrows():
            ecritures.append({
                "Date": date_ecriture.strftime("%d/%m/%Y"),
                "Journal": journal,
                "Compte": compte_com_diff,
                "Libelle": f"{libelle_base} - Com. diffusion ISBN",
                "Famille_Analytique": famille_analytique,
                "Code_Analytique": r["ISBN"],
                "Débit": round(float(r["Commission_diffusion"]), 2),
                "Crédit": 0.0
            })

        df_ecr = pd.DataFrame(ecritures)

        # --- Vérification équilibre ---
        total_debit = round(df_ecr["Débit"].sum(), 2)
        total_credit = round(df_ecr["Crédit"].sum(), 2)

        if total_debit != total_credit:
            st.error(f"⚠️ Écriture déséquilibrée : Débit={total_debit}, Crédit={total_credit}")
        else:
            st.success("✅ Écritures équilibrées et prêtes à l’import Pennylane !")

        # --- Export & téléchargement ---
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

        # Aperçu
        st.subheader("👀 Aperçu des écritures générées")
        st.dataframe(df_ecr)

# =====================
# MODULE 2 : IMPORT COMPTABLE
# =====================
elif menu == "Import données comptables":
    st.header("📂 Importation des données comptables")

    mode_import = st.selectbox(
        "Choisis ton mode d’extraction :",
        [
            "1️⃣ Pennylane Connect (fichier manuel)",
            "2️⃣ Dossier partagé (Drive / OneDrive)",
            "3️⃣ API directe (mode expert)"
        ]
    )

    fichier_comptables = None

    # --- Option 1 : Pennylane Connect ---
    if mode_import.startswith("1"):
        st.info("🧩 Mode fichier Excel : télécharge ton export depuis Pennylane Connect")
        fichier_comptables = st.file_uploader("📂 Sélectionne ton fichier Excel Pennylane Connect", type=["xlsx"])
        if fichier_comptables is not None:
            try:
                df = pd.read_excel(fichier_comptables, header=0)
                st.session_state["df_comptables"] = df
                st.success(f"✅ Fichier chargé : {df.shape[0]} lignes")
                st.dataframe(df.head())
            except Exception as e:
                st.error(f"❌ Impossible de lire le fichier : {e}")

    # --- Option 2 : Dossier partagé ---
    elif mode_import.startswith("2"):
        st.info("📁 Mode dossier synchronisé : Streamlit accède automatiquement aux fichiers")
        dossier_path = st.text_input("Chemin du dossier synchronisé :", placeholder="ex: C:/Users/EC/OneDrive/Pennylane_Connect")
        
        if st.button("Charger les fichiers du dossier"):
            fichiers = glob.glob(os.path.join(dossier_path, "*.xlsx"))
            if fichiers:
                dfs = [pd.read_excel(f) for f in fichiers]
                df_all = pd.concat(dfs, ignore_index=True)
                st.session_state["df_comptables"] = df_all
                st.success(f"{len(fichiers)} fichiers chargés automatiquement depuis {dossier_path}")
                st.dataframe(df_all.head())
            else:
                st.warning("Aucun fichier trouvé dans le dossier indiqué.")

    # --- Option 3 : API directe ---
    elif mode_import.startswith("3"):
        st.info("🔗 Mode API : connexion directe à Pennylane, MyUnisoft, QuickBooks, etc.")
        st.subheader("⚙️ Paramètres API")
        api_url = st.text_input("URL de l'API", placeholder="https://api.pennylane.com/...")
        api_key = st.text_input("Clé API", type="password")
        api_secret = st.text_input("Secret API", type="password")
        compte_id = st.text_input("ID du compte / société", placeholder="Ex: 123456")

        if st.button("Tester la connexion API"):
            if api_url and api_key and api_secret:
                st.success("✅ Connexion test OK (simulation pour l'instant)")
            else:
                st.error("❌ Merci de renseigner tous les champs pour tester la connexion")
        st.info("⚠️ Module API en développement – les données ne sont pas encore importées automatiquement.")

    # --- Bouton pour générer le socle pivot ---
    if "df_comptables" in st.session_state:
        if st.button("🛠️ Générer le socle pivot analytique"):
            df_compta = st.session_state["df_comptables"]
            # Ajuster les noms de colonnes selon Pennylane Connect
            df_compta.rename(columns={
                "Numéro de compte": "Compte",
                "Débit": "Débit",
                "Crédit": "Crédit",
                "Familles de catégories": "Famille_Analytique",
                "Catégories": "Code_Analytique"
            }, inplace=True)
            pivot = df_compta.groupby(
                ["Compte", "Famille_Analytique", "Code_Analytique"], as_index=False
            ).agg({"Débit": "sum", "Crédit": "sum"})
            st.session_state["df_pivot"] = pivot
            st.success("✅ Socle pivot analytique généré !")
            st.dataframe(pivot.head(20))

            # Export Excel
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                pivot.to_excel(writer, index=False, sheet_name="Socle_Pivot")
            buffer.seek(0)
            st.download_button(
                label="📥 Télécharger le socle pivot analytique",
                data=buffer,
                file_name="Socle_Pivot_Analytique.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# =====================
# MODULE 3 : SOCLE PIVOT
# =====================
elif menu == "Socle pivot analytique":
    st.header("🏗️ Socle pivot analytique")
    if "df_pivot" in st.session_state:
        st.success("✅ Socle pivot disponible")
        st.dataframe(st.session_state["df_pivot"].head(20))
    else:
        st.warning("⚠️ Générer d'abord le socle pivot depuis le module Import données comptables.")

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
    if "df_pivot" in st.session_state:
        st.info(f"📌 Module {sous_menu} utilisant le socle pivot (en développement)")
        st.dataframe(st.session_state["df_pivot"].head(20))
    else:
        st.warning("⚠️ Générer d'abord le socle pivot depuis le module Import données comptables.")
