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
        "Tableaux & analyses",
        "Trésorerie prévisionnelle"
    ]
)

# =====================
# MODULE 1 : BLDD
# =====================
if menu == "Générateur d'écritures BLDD":
    st.title("📊 Générateur d'écritures analytiques - BLDD")
    # --- Import fichier BLDD ---
    fichier_entree = st.file_uploader("📂 Importer le fichier Excel BLDD", type=["xlsx"])
    
    date_ecriture = st.date_input("📅 Date d'écriture")
    journal = st.text_input("📒 Journal", value="VT")
    libelle_base = st.text_input("📝 Libellé", value="VENTES BLDD")
    
    compte_ca = st.text_input("💰 Compte CA", value="70110000")
    compte_com_dist = st.text_input("💰 Compte commissions distribution", value="62280000")
    compte_com_diff = st.text_input("💰 Compte commissions diffusion", value="62280001")
    
    taux_dist = st.number_input("Taux distribution (%)", value=12.5)/100
    taux_diff = st.number_input("Taux diffusion (%)", value=9.0)/100
    
    com_distribution_total = st.number_input("Montant total commissions distribution", value=1000.0, format="%.2f")
    com_diffusion_total = st.number_input("Montant total commissions diffusion", value=500.0, format="%.2f")
    
    famille_analytique = st.text_input("🧭 Famille analytique (obligatoire pour Pennylane)", value="ISBN")
    st.caption("Exemple : ISBN / Collection / Client / Projet / Auteur")
    
    if fichier_entree is not None and famille_analytique:
        df = pd.read_excel(fichier_entree, header=9, dtype={"ISBN": str})
        df.columns = df.columns.str.strip()
        df = df.dropna(subset=["ISBN"]).copy()
        df["ISBN"] = df["ISBN"].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df["ISBN"] = df["ISBN"].str.replace('-', '').str.replace(' ', '')
        
        for c in ["Vente", "Net", "Facture"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).round(2)
        
        # --- Calcul commissions distribution ---
        raw_dist = df["Vente"] * taux_dist
        sum_raw_dist = raw_dist.sum()
        scaled_dist = raw_dist * (com_distribution_total / sum_raw_dist)
        cents_floor = np.floor(scaled_dist * 100).astype(int)
        remainders = (scaled_dist * 100) - cents_floor
        diff = int(round(com_distribution_total * 100)) - cents_floor.sum()
        idx_sorted = np.argsort(-remainders.values)
        adjust = np.zeros(len(df), dtype=int)
        if diff > 0: adjust[idx_sorted[:diff]] = 1
        elif diff < 0: adjust[idx_sorted[len(df)+diff:]] = -1
        df["Commission_distribution"] = (cents_floor + adjust)/100.0
        
        # --- Calcul commissions diffusion ---
        raw_diff = df["Net"] * taux_diff
        sum_raw_diff = raw_diff.sum()
        scaled_diff = raw_diff * (com_diffusion_total / sum_raw_diff)
        cents_floor = np.floor(scaled_diff * 100).astype(int)
        remainders = (scaled_diff * 100) - cents_floor
        diff = int(round(com_diffusion_total*100)) - cents_floor.sum()
        idx_sorted = np.argsort(-remainders.values)
        adjust = np.zeros(len(df), dtype=int)
        if diff > 0: adjust[idx_sorted[:diff]] = 1
        elif diff < 0: adjust[idx_sorted[len(df)+diff:]] = -1
        df["Commission_diffusion"] = (cents_floor + adjust)/100.0
        
        # --- Construction écritures ---
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
                "Crédit": round(float(r["Facture"]),2)
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
                "Débit": round(float(r["Commission_distribution"]),2),
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
                "Débit": round(float(r["Commission_diffusion"]),2),
                "Crédit": 0.0
            })
        df_ecr = pd.DataFrame(ecritures)
        # Vérification équilibre
        total_debit = round(df_ecr["Débit"].sum(),2)
        total_credit = round(df_ecr["Crédit"].sum(),2)
        if total_debit != total_credit:
            st.error(f"⚠️ Écriture déséquilibrée : Débit={total_debit}, Crédit={total_credit}")
        else:
            st.success("✅ Écritures équilibrées et prêtes à l’import Pennylane !")
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
    st.header("📂 Importation des données comptables")
    mode_import = st.selectbox(
        "Choisis ton mode d’extraction :",
        ["1️⃣ Pennylane Connect (fichier manuel)", "2️⃣ Dossier partagé", "3️⃣ API directe"]
    )
    fichier_comptables = None
    if mode_import.startswith("1"):
        fichier_comptables = st.file_uploader("📂 Sélectionne ton fichier Excel Pennylane Connect", type=["xlsx"])
        if fichier_comptables is not None:
            df = pd.read_excel(fichier_comptables, header=0)
            st.session_state["df_comptables"] = df
            st.success(f"✅ Fichier chargé : {df.shape[0]} lignes")
            st.dataframe(df.head())

    if "df_comptables" in st.session_state:
        if st.button("🛠️ Générer le socle pivot analytique"):
            df_compta = st.session_state["df_comptables"]
            df_compta.rename(columns={
                "Numéro de compte": "Compte",
                "Débit": "Débit",
                "Crédit": "Crédit",
                "Familles de catégories": "Famille_Analytique",
                "Catégories": "Code_Analytique"
            }, inplace=True)
            pivot = df_compta.groupby(["Compte","Famille_Analytique","Code_Analytique"], as_index=False).agg({"Débit":"sum","Crédit":"sum"})
            st.session_state["df_pivot"] = pivot
            st.success("✅ Socle pivot analytique généré !")
            st.dataframe(pivot.head(20))
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                pivot.to_excel(writer, index=False, sheet_name="Socle_Pivot")
            buffer.seek(0)
            st.download_button("📥 Télécharger le socle pivot analytique", data=buffer, file_name="Socle_Pivot_Analytique.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

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
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le socle pivot depuis le module Import données comptables.")
    else:
        df_pivot = st.session_state["df_pivot"]
        sous_menu = st.selectbox("Choix de l'analyse", ["Dashboard analytique","Mini compte de résultat par ISBN"])
        if sous_menu == "Dashboard analytique":
            st.subheader("📈 Top 10 ISBN par résultat net")
            # Calcul du résultat net : Crédit - Débit
            df_pivot["Résultat"] = df_pivot["Crédit"] - df_pivot["Débit"]
            # Top 10 ISBN
            top_isbn = df_pivot.groupby("Code_Analytique", as_index=False)["Résultat"].sum()
            top_isbn = top_isbn.sort_values(by="Résultat", ascending=False).head(10)
            if top_isbn.empty:
                st.warning("⚠️ Aucun résultat disponible pour générer le dashboard.")
            else:
                st.dataframe(top_isbn)
                fig = px.bar(
                    top_isbn,
                    x="Code_Analytique",
                    y="Résultat",
                    title="Top 10 ISBN par résultat net",
                    labels={"Code_Analytique": "ISBN", "Résultat": "Résultat net"}
                )
                st.plotly_chart(fig, use_container_width=True)

        elif sous_menu == "Mini compte de résultat par ISBN":
            st.subheader("💼 Mini compte de résultat par ISBN")
            # Somme des Débit / Crédit par ISBN
            df_cr = df_pivot.groupby("Code_Analytique", as_index=False).agg({"Débit":"sum","Crédit":"sum"})
            df_cr["Résultat"] = df_cr["Crédit"] - df_cr["Débit"]
            st.dataframe(df_cr)
            # Export Excel
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

# =====================
# MODULE 5 : TRÉSORERIE PRÉVISIONNELLE
# =====================
elif menu == "Trésorerie prévisionnelle":
    st.header("💰 Trésorerie prévisionnelle")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Le socle pivot analytique est requis. Merci de l’importer ou de le générer avant.")
        st.stop()

    df_pivot = st.session_state["df_pivot"]
    
    # Déterminer solde initial à partir du compte bancaire si disponible
    solde_depart = df_pivot[df_pivot["Compte"].str.startswith("5")]  # comptes bancaires
    if not solde_depart.empty:
        tresorerie_initiale = solde_depart["Crédit"].sum() - solde_depart["Débit"].sum()
    else:
        tresorerie_initiale = st.number_input("Trésorerie de départ (€)", value=10000.0, step=500.0)

    st.markdown("### 🔮 Paramètres de projection")
    horizon = st.slider("Horizon de projection (en mois)", 3, 24, 12)
    croissance_ca = st.number_input("Croissance mensuelle du CA (%)", value=2.0)
    evolution_charges = st.number_input("Évolution mensuelle des charges (%)", value=1.0)

    if st.button("📊 Générer la prévision de trésorerie"):
        try:
            df = df_pivot.copy()
            # Normaliser la date
            if "Date" not in df.columns:
                st.error("⚠️ La colonne 'Date' est requise dans le pivot.")
                st.stop()
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.dropna(subset=["Date"])
            df["Mois"] = df["Date"].dt.to_period("M").astype(str)
            # Calcul flux mensuels
            flux_mensuel = df.groupby("Mois").agg({"Débit":"sum","Crédit":"sum"}).reset_index()
            flux_mensuel["Solde_mensuel"] = flux_mensuel["Crédit"] - flux_mensuel["Débit"]
            flux_mensuel = flux_mensuel.sort_values("Mois")
            # Prévision future
            dernier_mois = pd.Period(flux_mensuel["Mois"].max(), freq="M")
            previsions = []
            ca_actuel = flux_mensuel["Crédit"].iloc[-1]
            charges_actuelles = flux_mensuel["Débit"].iloc[-1]
            for i in range(1, horizon+1):
                prochain_mois = (dernier_mois + i).strftime("%Y-%m")
                ca_actuel *= (1 + croissance_ca/100)
                charges_actuelles *= (1 + evolution_charges/100)
                solde_prevu = ca_actuel - charges_actuelles
                previsions.append({
                    "Mois": prochain_mois,
                    "Débit": charges_actuelles,
                    "Crédit": ca_actuel,
                    "Solde_mensuel": solde_prevu
                })
            df_prev = pd.DataFrame(previsions)
            df_tresorerie = pd.concat([flux_mensuel, df_prev], ignore_index=True)
            # Calcul solde cumulé
            df_tresorerie["Trésorerie_cumulée"] = tresorerie_initiale + df_tresorerie["Solde_mensuel"].cumsum()
            solde_final = df_tresorerie["Trésorerie_cumulée"].iloc[-1]
            variation = solde_final - tresorerie_initiale
            st.success(f"✅ Solde final prévisionnel : {solde_final:,.2f} € ({variation:+.2f} € vs départ)")
            # Graphique
            fig = px.line(df_tresorerie, x="Mois", y="Trésorerie_cumulée", title="📈 Évolution prévisionnelle de la trésorerie", markers=True)
            fig.update_layout(xaxis_title="Mois", yaxis_title="Trésorerie (€)")
            st.plotly_chart(fig, use_container_width=True)
            # Tableau
            st.subheader("📋 Détail de la prévision mensuelle")
            st.dataframe(df_tresorerie.style.format({
                "Débit": "{:,.0f}",
                "Crédit": "{:,.0f}",
                "Solde_mensuel": "{:,.0f}",
                "Trésorerie_cumulée": "{:,.0f}"
            }))
            # Export Excel
            buffer_tres = BytesIO()
            with pd.ExcelWriter(buffer_tres, engine="openpyxl") as writer:
                df_tresorerie.to_excel(writer, index=False, sheet_name="Prévision_Trésorerie")
            buffer_tres.seek(0)
            st.download_button(
                label="📥 Télécharger la prévision (Excel)",
                data=buffer_tres,
                file_name="Prevision_Tresorerie.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"❌ Erreur pendant la simulation : {e}")
