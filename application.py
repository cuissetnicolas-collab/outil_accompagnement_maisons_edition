import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import glob, os
import plotly.express as px

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

    fichier_entree = st.file_uploader("📂 Importer le fichier Excel BLDD", type=["xlsx"])
    date_ecriture = st.date_input("📅 Date d'écriture")
    journal = st.text_input("📒 Journal", value="VT")
    libelle_base = st.text_input("📝 Libellé", value="VENTES BLDD")

    compte_ca = st.text_input("💰 Compte CA", value="70110000")
    compte_com_dist = st.text_input("💰 Compte commissions distribution", value="62280000")
    compte_com_diff = st.text_input("💰 Compte commissions diffusion", value="62280001")

    taux_dist = st.number_input("Taux distribution (%)", value=12.5) / 100
    taux_diff = st.number_input("Taux diffusion (%)", value=9.0) / 100

    com_distribution_total = st.number_input("Montant total commissions distribution", value=1000.0)
    com_diffusion_total = st.number_input("Montant total commissions diffusion", value=500.0)

    st.markdown("---")
    famille_analytique = st.text_input("🧭 Famille analytique (obligatoire)", value="ISBN")
    if not famille_analytique:
        st.warning("⚠️ Merci de renseigner la famille analytique.")

    if fichier_entree is not None and famille_analytique:
        df = pd.read_excel(fichier_entree, header=9, dtype={"ISBN": str})
        df.columns = df.columns.str.strip()
        df = df.dropna(subset=["ISBN"]).copy()
        df["ISBN"] = df["ISBN"].astype(str).str.strip().str.replace(r'\.0$', '', regex=True).str.replace('-', '', regex=False).str.replace(' ', '', regex=False)
        for c in ["Vente", "Net", "Facture"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).round(2)

        # --- Commissions distribution ---
        raw_dist = df["Vente"] * taux_dist
        scaled_dist = raw_dist * (com_distribution_total / raw_dist.sum())
        cents_floor = np.floor(scaled_dist*100).astype(int)
        remainders = (scaled_dist*100) - cents_floor
        diff = int(round(com_distribution_total*100)) - cents_floor.sum()
        idx_sorted = np.argsort(-remainders.values)
        adjust = np.zeros(len(df), dtype=int)
        if diff > 0:
            adjust[idx_sorted[:diff]] = 1
        elif diff < 0:
            adjust[idx_sorted[len(df)+diff:]] = -1
        df["Commission_distribution"] = (cents_floor + adjust)/100

        # --- Commissions diffusion ---
        raw_diff = df["Net"] * taux_diff
        scaled_diff = raw_diff * (com_diffusion_total / raw_diff.sum())
        cents_floor = np.floor(scaled_diff*100).astype(int)
        remainders = (scaled_diff*100) - cents_floor
        diff = int(round(com_diffusion_total*100)) - cents_floor.sum()
        idx_sorted = np.argsort(-remainders.values)
        adjust = np.zeros(len(df), dtype=int)
        if diff > 0:
            adjust[idx_sorted[:diff]] = 1
        elif diff < 0:
            adjust[idx_sorted[len(df)+diff:]] = -1
        df["Commission_diffusion"] = (cents_floor + adjust)/100

        # --- Génération écritures ---
        ecritures = []
        total_facture_global = df["Facture"].sum().round(2)
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
        for _, r in df.iterrows():
            ecritures.append({
                "Date": date_ecriture.strftime("%d/%m/%Y"),
                "Journal": journal,
                "Compte": compte_ca,
                "Libelle": f"{libelle_base} - CA ISBN",
                "Famille_Analytique": famille_analytique,
                "Code_Analytique": r["ISBN"],
                "Débit": 0.0,
                "Crédit": r["Facture"]
            })
        # Commissions
        for compte, col, libelle in zip([compte_com_dist, compte_com_diff], ["Commission_distribution","Commission_diffusion"], ["distribution","diffusion"]):
            total = df[col].sum().round(2)
            ecritures.append({
                "Date": date_ecriture.strftime("%d/%m/%Y"),
                "Journal": journal,
                "Compte": compte,
                "Libelle": f"{libelle_base} - Com. {libelle} global",
                "Famille_Analytique": famille_analytique,
                "Code_Analytique": "",
                "Débit": 0.0,
                "Crédit": total
            })
            for _, r in df.iterrows():
                ecritures.append({
                    "Date": date_ecriture.strftime("%d/%m/%Y"),
                    "Journal": journal,
                    "Compte": compte,
                    "Libelle": f"{libelle_base} - Com. {libelle} ISBN",
                    "Famille_Analytique": famille_analytique,
                    "Code_Analytique": r["ISBN"],
                    "Débit": r[col],
                    "Crédit": 0.0
                })
        df_ecr = pd.DataFrame(ecritures)

        if round(df_ecr["Débit"].sum(),2) != round(df_ecr["Crédit"].sum(),2):
            st.error("⚠️ Écritures déséquilibrées !")
        else:
            st.success("✅ Écritures équilibrées !")
        # Export
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_ecr.to_excel(writer, index=False, sheet_name="Ecritures")
        buffer.seek(0)
        st.download_button("📥 Télécharger Excel", buffer, "Ecritures_Pennylane.xlsx")
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

    if mode_import.startswith("1"):
        st.info("🧩 Mode fichier Excel")
        fichier_comptables = st.file_uploader("📂 Sélectionne ton fichier Excel Pennylane Connect", type=["xlsx"])
        if fichier_comptables is not None:
            try:
                df = pd.read_excel(fichier_comptables, header=0)
                st.session_state["df_comptables"] = df
                st.success(f"✅ Fichier chargé : {df.shape[0]} lignes")
                st.dataframe(df.head())
            except Exception as e:
                st.error(f"❌ Impossible de lire le fichier : {e}")

    elif mode_import.startswith("2"):
        st.info("📁 Mode dossier synchronisé")
        dossier_path = st.text_input("Chemin du dossier synchronisé")
        if st.button("Charger les fichiers du dossier"):
            fichiers = glob.glob(os.path.join(dossier_path, "*.xlsx"))
            if fichiers:
                dfs = [pd.read_excel(f) for f in fichiers]
                df_all = pd.concat(dfs, ignore_index=True)
                st.session_state["df_comptables"] = df_all
                st.success(f"{len(fichiers)} fichiers chargés")
                st.dataframe(df_all.head())
            else:
                st.warning("Aucun fichier trouvé")

    elif mode_import.startswith("3"):
        st.info("🔗 Mode API directe")
        st.warning("⚠️ Fonctionnalité avancée, nécessite API key et paramétrage")


# =====================
# MODULE 3 : SOCLE PIVOT ANALYTIQUE
# =====================
elif menu == "Socle pivot analytique":
    st.header("🔄 Socle pivot analytique")
    if "df_comptables" not in st.session_state:
        st.warning("⚠️ Importer d'abord les données comptables.")
        st.stop()

    df_compta = st.session_state["df_comptables"].copy()
    if st.button("🛠️ Générer le socle pivot complet"):
        # Préparation colonnes
        for col in ["Numéro de compte", "Débit", "Crédit", "Familles de catégories", "Catégories", "Date"]:
            if col not in df_compta.columns:
                df_compta[col] = np.nan
        df_compta.rename(columns={
            "Numéro de compte": "Compte",
            "Débit": "Débit",
            "Crédit": "Crédit",
            "Familles de catégories": "Famille_Analytique",
            "Catégories": "Code_Analytique",
            "Date": "Date"
        }, inplace=True)
        df_compta["Famille_Analytique"] = df_compta["Famille_Analytique"].fillna("")
        df_compta["Code_Analytique"] = df_compta["Code_Analytique"].fillna("")

        pivot = df_compta.groupby(
            ["Compte","Famille_Analytique","Code_Analytique","Date"], as_index=False
        ).agg({"Débit":"sum","Crédit":"sum"})
        st.session_state["df_pivot"] = pivot
        st.success("✅ Socle pivot complet généré")
        st.dataframe(pivot.head(20))


# =====================
# MODULE 4 : TABLEAUX & ANALYSES
# =====================
elif menu == "Tableaux & analyses":
    st.header("📊 Tableaux & analyses")

    # Vérifier que le socle pivot est généré
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le socle pivot depuis le module Import données comptables.")
        st.stop()
    else:
        df_pivot = st.session_state["df_pivot"].copy()

    # Choix de l'analyse
    sous_menu = st.selectbox(
        "Choix de l'analyse",
        [
            "Dashboard analytique",
            "Mini compte de résultat par ISBN",
            "Trésorerie prévisionnelle"
        ]
    )

    # ----------------------------
    # Dashboard analytique
    # ----------------------------
    if sous_menu == "Dashboard analytique":
        st.subheader("📈 Top 10 ISBN par résultat net")
        df_pivot["Résultat"] = df_pivot["Crédit"] - df_pivot["Débit"]
        top_isbn = df_pivot.groupby("Code_Analytique", as_index=False)["Résultat"].sum()
        top_isbn = top_isbn.sort_values(by="Résultat", ascending=False).head(10)
        if top_isbn.empty:
            st.warning("⚠️ Aucun résultat disponible pour générer le dashboard.")
        else:
            st.dataframe(top_isbn)
            import plotly.express as px
            fig = px.bar(
                top_isbn,
                x="Code_Analytique",
                y="Résultat",
                title="Top 10 ISBN par résultat net",
                labels={"Code_Analytique": "ISBN", "Résultat": "Résultat net"}
            )
            st.plotly_chart(fig, use_container_width=True)

    # ----------------------------
    # Mini compte de résultat par ISBN
    # ----------------------------
    elif sous_menu == "Mini compte de résultat par ISBN":
        st.subheader("💼 Mini compte de résultat par ISBN")
        df_cr = df_pivot.groupby("Code_Analytique", as_index=False).agg({
            "Débit": "sum",
            "Crédit": "sum"
        })
        df_cr["Résultat"] = df_cr["Crédit"] - df_cr["Débit"]
        st.dataframe(df_cr)

        # Export Excel
        from io import BytesIO
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_cr.to_excel(writer, index=False, sheet_name="Mini_CR_ISBN")
        buffer.seek(0)
        st.download_button(
            label="📥 Télécharger le mini compte de résultat par ISBN",
            data=buffer,
            file_name="Mini_Compte_Resultat_ISBN.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # ----------------------------
    # Trésorerie prévisionnelle
    # ----------------------------
    elif sous_menu == "Trésorerie prévisionnelle":
        st.subheader("💰 Trésorerie prévisionnelle")
        # Paramètres
        date_debut = st.date_input("Date de départ", pd.to_datetime("2025-04-01"))
        horizon = st.slider("Horizon de projection (mois)", 3, 24, 12)
        croissance_ca = st.number_input("Croissance mensuelle du CA (%)", value=2.0)
        evolution_charges = st.number_input("Évolution mensuelle des charges (%)", value=1.0)

        # Calcul solde départ à partir de toutes les lignes bancaires
        comptes_bancaires = df_pivot[df_pivot["Compte"].astype(str).str.startswith("5")]
        comptes_avant_debut = comptes_bancaires[comptes_bancaires["Date"] < pd.to_datetime(date_debut)]
        solde_depart = comptes_avant_debut["Crédit"].sum() - comptes_avant_debut["Débit"].sum()
        st.info(f"Solde de départ calculé automatiquement : {solde_depart:,.2f} €")

        if st.button("📊 Générer la prévision"):
            df_flux = df_pivot[df_pivot["Date"] >= pd.to_datetime(date_debut)]
            df_flux["Mois"] = df_flux["Date"].dt.to_period("M").astype(str)
            flux_mensuel = df_flux.groupby("Mois").agg({"Débit": "sum", "Crédit": "sum"}).reset_index()
            flux_mensuel["Solde_mensuel"] = flux_mensuel["Crédit"] - flux_mensuel["Débit"]

            dernier_mois = pd.Period(flux_mensuel["Mois"].max(), freq="M") if not flux_mensuel.empty else pd.Period(date_debut, freq="M")
            ca_actuel = flux_mensuel["Crédit"].iloc[-1] if not flux_mensuel.empty else 0
            charges_actuelles = flux_mensuel["Débit"].iloc[-1] if not flux_mensuel.empty else 0

            # Projection future
            previsions = []
            for i in range(1, horizon + 1):
                prochain_mois = (dernier_mois + i).strftime("%Y-%m")
                ca_actuel *= (1 + croissance_ca / 100)
                charges_actuelles *= (1 + evolution_charges / 100)
                solde_prevu = ca_actuel - charges_actuelles
                previsions.append({
                    "Mois": prochain_mois,
                    "Débit": charges_actuelles,
                    "Crédit": ca_actuel,
                    "Solde_mensuel": solde_prevu
                })

            df_prev = pd.DataFrame(previsions)
            df_tresorerie = pd.concat([flux_mensuel, df_prev], ignore_index=True)
            df_tresorerie["Trésorerie_cumulée"] = solde_depart + df_tresorerie["Solde_mensuel"].cumsum()

            # Graphique
            import plotly.express as px
            fig = px.line(df_tresorerie, x="Mois", y="Trésorerie_cumulée", title="📈 Trésorerie prévisionnelle")
            st.plotly_chart(fig, use_container_width=True)

            # Tableau détaillé
            st.dataframe(df_tresorerie)

            # Export Excel
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_tresorerie.to_excel(writer, index=False, sheet_name="Trésorerie prévisionnelle")
            buffer.seek(0)
            st.download_button(
                label="📥 Télécharger la trésorerie prévisionnelle",
                data=buffer,
                file_name="Tresorerie_previsionnelle.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
