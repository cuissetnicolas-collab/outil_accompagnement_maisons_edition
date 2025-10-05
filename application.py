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

    # Sélection du mode
    choix = st.radio(
        "Source des données :",
        ["Pennylane Connect (Excel)", "Connexion API (multi-logiciels)"]
    )

    # ================================================================
    # MODE 1 : Import Excel (Pennylane Connect)
    # ================================================================
    if choix == "Pennylane Connect (Excel)":
        st.info("💡 Importe ici les fichiers Excel exportés depuis Pennylane Connect (GL, Journaux, Balance...)")

        fichiers = st.file_uploader(
            "Importer un ou plusieurs fichiers Excel (.xlsx)",
            type=["xlsx"],
            accept_multiple_files=True
        )

        if fichiers:
            dfs = []
            for fichier in fichiers:
                try:
                    df = pd.read_excel(fichier, dtype=str)
                    df.columns = df.columns.str.strip().str.lower()

                    # Détection du type
                    nom = fichier.name.lower()
                    if "grand" in nom or "gl" in nom:
                        type_fichier = "Grand livre"
                    elif "balance" in nom:
                        type_fichier = "Balance"
                    elif "journal" in nom:
                        type_fichier = "Journaux"
                    else:
                        type_fichier = "Inconnu"

                    # Normalisation colonnes
                    mapping = {
                        "date": "Date",
                        "journal": "Journal",
                        "compte": "Compte",
                        "libellé": "Libelle",
                        "libelle": "Libelle",
                        "debit": "Debit",
                        "crédit": "Credit",
                        "credit": "Credit"
                    }
                    df = df.rename(columns={c: mapping.get(c, c) for c in df.columns})

                    for col in ["Date", "Journal", "Compte", "Libelle", "Debit", "Credit"]:
                        if col not in df.columns:
                            df[col] = None

                    df["Debit"] = pd.to_numeric(df["Debit"], errors="coerce").fillna(0)
                    df["Credit"] = pd.to_numeric(df["Credit"], errors="coerce").fillna(0)
                    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                    df["Source"] = type_fichier
                    dfs.append(df[["Date", "Journal", "Compte", "Libelle", "Debit", "Credit", "Source"]])
                    st.success(f"✅ {fichier.name} importé ({type_fichier}) — {len(df)} lignes")

                except Exception as e:
                    st.error(f"Erreur lecture {fichier.name} : {e}")

            if dfs:
                df_final = pd.concat(dfs, ignore_index=True)
                st.dataframe(df_final.head(10))
                st.info(f"Équilibre global : Débit = {df_final['Debit'].sum():,.2f} / Crédit = {df_final['Credit'].sum():,.2f}")

                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    df_final.to_excel(writer, index=False, sheet_name="Comptabilite_fusionnee")
                buffer.seek(0)
                st.download_button(
                    label="📥 Télécharger les données standardisées",
                    data=buffer,
                    file_name="Compta_Fusionnee.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    # ================================================================
    # MODE 2 : Connexion API générique
    # ================================================================
    elif choix == "Connexion API (multi-logiciels)":
        st.info("🔗 Mode expert : connecte-toi à l'API d’un logiciel comptable (Pennylane, Sage, MyUnisoft, Tiime, etc.)")

        logiciel = st.selectbox("Choisir le logiciel :", ["Pennylane", "MyUnisoft", "Sage", "QuickBooks", "Autre"])

        api_key = st.text_input("🔐 Clé API ou Token d’accès", type="password")
        url_base = st.text_input("🌐 URL de l’API (endpoint base)", placeholder="https://api.logiciel.com/v1/")

        start_date = st.date_input("📆 Date de début")
        end_date = st.date_input("📆 Date de fin")

        if st.button("Importer via API"):
            if not api_key or not url_base:
                st.warning("Merci de renseigner la clé API et l’URL de l’API.")
            else:
                # Simulation (à adapter par logiciel)
                st.info(f"Connexion simulée à l’API {logiciel}")

                df_demo = pd.DataFrame({
                    "Date": pd.date_range(start=start_date, end=end_date, freq="M"),
                    "Journal": ["VT"]*3,
                    "Compte": ["701000", "707000", "622000"],
                    "Libelle": ["Ventes Livres", "Ventes Services", "Commissions"],
                    "Debit": [0, 0, 1500],
                    "Credit": [12000, 2000, 0],
                    "Source": f"API {logiciel}"
                })

                st.success(f"✅ Données simulées récupérées depuis {logiciel}")
                st.dataframe(df_demo)

                st.download_button(
                    label=f"📥 Télécharger données API {logiciel}",
                    data=df_demo.to_csv(index=False).encode("utf-8"),
                    file_name=f"{logiciel}_API_Demo.csv",
                    mime="text/csv"
                )

    # ================================================================
    # 🟩 MODE 2 : API Pennylane (option avancée)
    # ================================================================
    elif choix == "API Pennylane (option avancée)":
        st.info("""
        🔗 Ce mode permet d'accéder directement aux écritures comptables via l'API Pennylane.
        Il nécessite une clé API et des droits d'accès spécifiques (mode expert).
        """)

        api_key = st.text_input("🔐 Clé API Pennylane", type="password")
        start_date = st.date_input("📆 Date de début")
        end_date = st.date_input("📆 Date de fin")

        if st.button("Importer via API Pennylane"):
            if not api_key:
                st.warning("Merci de renseigner la clé API Pennylane.")
            else:
                # Exemple simulé pour mémoire (à remplacer si l'API est accessible)
                st.info("Connexion simulée à l’API Pennylane (mode démo).")

                df_demo = pd.DataFrame({
                    "Date": pd.date_range(start=start_date, end=end_date, freq="M"),
                    "Journal": ["VT", "VT", "VT"],
                    "Compte": ["701100", "707000", "706000"],
                    "Libelle": ["Ventes livres", "Ventes numériques", "Prestation conseil"],
                    "Debit": [0, 0, 0],
                    "Credit": [12500, 1800, 4500],
                    "Source": "API Pennylane"
                })
                st.success("✅ Données simulées récupérées via API")
                st.dataframe(df_demo)

                st.download_button(
                    "📥 Télécharger données API simulées",
                    data=df_demo.to_csv(index=False).encode("utf-8"),
                    file_name="Pennylane_API_Demo.csv",
                    mime="text/csv"
                )

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
