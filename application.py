import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import plotly.express as px

st.set_page_config(page_title="Outils Édition - Suite analytique comptable", layout="wide")

# =====================
# AUTHENTIFICATION SIMPLE (modifiable)
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
# HEADER
# =====================
st.sidebar.success(f"👤 {st.session_state.get('name','Utilisateur')}")

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
    "RETURNS EDITION",
    "SYNTHÈSE GÉNÉRALE"
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
    - Consulter une synthèse des indicateurs clés (**SYNTHÈSE GÉNÉRALE**)  

    Utilisez le menu à gauche pour naviguer entre les modules.
    """)
    st.stop()

# =====================
# DATA EDITION
# =====================
if page == "DATA EDITION":
    st.header("📂 DATA EDITION - Import des données analytiques")
    st.markdown("Importez un export comptable (Excel) incluant : compte, date, débit/crédit, libellé, code analytique (ISBN).")
    fichier_comptables = st.file_uploader("Sélectionnez votre fichier Excel", type=["xlsx", "xls"])
    if fichier_comptables:
        try:
            df = pd.read_excel(fichier_comptables, header=0)
            df.columns = df.columns.str.strip()
            st.write("Colonnes détectées :", list(df.columns))
            # On ne force pas de mapping automatique ici, on laisse l'utilisateur vérifier / renommer dans SOCLE
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
        df_src = st.session_state["df_comptables"].copy()
        colonnes_dispo = df_src.columns.tolist()
        st.markdown("### 🧭 Indiquez les colonnes correspondantes dans votre fichier")
        col_date = st.selectbox("Colonne date", colonnes_dispo, index=0)
        col_compte = st.selectbox("Colonne compte", colonnes_dispo, index=1 if len(colonnes_dispo)>1 else 0)
        col_debit = st.selectbox("Colonne débit", colonnes_dispo, index=2 if len(colonnes_dispo)>2 else 0)
        col_credit = st.selectbox("Colonne crédit", colonnes_dispo, index=3 if len(colonnes_dispo)>3 else 0)
        col_libelle = st.selectbox("Colonne libellé / intitulé", colonnes_dispo, index=4 if len(colonnes_dispo)>4 else 0)
        col_analytique = st.selectbox("Colonne code analytique / ISBN", colonnes_dispo, index=5 if len(colonnes_dispo)>5 else 0)

        if st.button("Générer le SOCLE"):
            df_pivot = df_src.rename(columns={
                col_date: "Date",
                col_compte: "Compte",
                col_debit: "Débit",
                col_credit: "Crédit",
                col_libelle: "Libellé",
                col_analytique: "Code_Analytique"
            })
            # Assurance colonnes
            for c in ["Compte","Date","Débit","Crédit","Code_Analytique","Libellé"]:
                if c not in df_pivot.columns:
                    df_pivot[c] = ""
            df_pivot["Date"] = pd.to_datetime(df_pivot["Date"], errors="coerce")
            df_pivot["Débit"] = pd.to_numeric(df_pivot["Débit"], errors="coerce").fillna(0)
            df_pivot["Crédit"] = pd.to_numeric(df_pivot["Crédit"], errors="coerce").fillna(0)
            # Optional: remplir familles analytiques si existantes
            if "Famille_Analytique" not in df_pivot.columns:
                df_pivot["Famille_Analytique"] = ""
            if "Code_Analytique" not in df_pivot.columns:
                df_pivot["Code_Analytique"] = ""
            st.session_state["df_pivot"] = df_pivot
            st.success("✅ SOCLE EDITION généré.")
            st.dataframe(df_pivot.head())

# =====================
# VISION EDITION
# =====================
elif page == "VISION EDITION":
    st.header("📈 VISION EDITION - Dashboard analytique")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        # Nettoyage rapide
        df["Débit"] = pd.to_numeric(df["Débit"], errors="coerce").fillna(0)
        df["Crédit"] = pd.to_numeric(df["Crédit"], errors="coerce").fillna(0)
        df["Résultat"] = df["Crédit"] - df["Débit"]

        st.subheader("🔢 Indicateurs globaux")
        ca_brut = df[df["Compte"].astype(str).str.startswith("701")]["Crédit"].sum() - df[df["Compte"].astype(str).str.startswith("701")]["Débit"].sum()
        total_retours = df[df["Compte"].astype(str).str.startswith("709")]["Débit"].sum() - df[df["Compte"].astype(str).str.startswith("709")]["Crédit"].sum()
        st.metric("CA brut total (approx)", f"{ca_brut:,.0f} €")
        st.metric("Retours totaux (approx)", f"{total_retours:,.0f} €")

        st.subheader("Top ISBN par résultat net")
        top_isbn = df.groupby("Code_Analytique", as_index=False)["Résultat"].sum().sort_values("Résultat", ascending=False).head(10)
        st.dataframe(top_isbn)
        fig = px.bar(top_isbn, x="Code_Analytique", y="Résultat", title="Top 10 ISBN par résultat net", labels={"Code_Analytique":"ISBN","Résultat":"Résultat net"})
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Évolution CA vs Retours (mensuel)")
        df_temp = df.copy()
        df_temp["Mois"] = df_temp["Date"].dt.to_period("M").astype(str)
        mois_ca = df_temp.groupby("Mois")["Crédit"].sum().reset_index().rename(columns={"Crédit":"CA_brut"})
        mois_ret = df_temp[df_temp["Compte"].astype(str).str.startswith("709")].groupby("Mois")["Débit"].sum().reset_index().rename(columns={"Débit":"Retours"})
        mois = pd.merge(mois_ca, mois_ret, on="Mois", how="outer").fillna(0).sort_values("Mois")
        if not mois.empty:
            fig2 = px.line(mois, x="Mois", y=["CA_brut","Retours"], title="CA brut et Retours (mensuel)")
            st.plotly_chart(fig2, use_container_width=True)

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
        st.dataframe(df_cr.sort_values("Résultat", ascending=False).head(200))
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_cr.to_excel(writer, index=False, sheet_name="Mini_CR_ISBN")
        buffer.seek(0)
        st.download_button("📥 Télécharger le mini compte de résultat par ISBN", buffer, file_name="Mini_Compte_Resultat_ISBN.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =====================
# CASH EDITION (TRÉSORERIE PRÉVISIONNELLE)
# =====================
elif page == "CASH EDITION":
    st.header("💰 CASH EDITION - Trésorerie prévisionnelle")

    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Vous devez d'abord générer le SOCLE EDITION.")
    else:
        df_pivot = st.session_state["df_pivot"].copy()

        # Date de départ
        date_debut = st.date_input("Date de départ de la trésorerie", pd.to_datetime("2025-04-01"))

        # Nettoyage et conversion des types
        df_pivot["Compte"] = df_pivot["Compte"].astype(str).str.strip()
        df_pivot["Date"] = pd.to_datetime(df_pivot["Date"], errors="coerce")
        df_pivot["Débit"] = pd.to_numeric(df_pivot["Débit"], errors="coerce").fillna(0)
        df_pivot["Crédit"] = pd.to_numeric(df_pivot["Crédit"], errors="coerce").fillna(0)

        # Calcul du solde de départ (comptes bancaires)
        comptes_bancaires = df_pivot[df_pivot["Compte"].str.startswith("5")]
        solde_depart_df = comptes_bancaires[comptes_bancaires["Date"] <= pd.to_datetime(date_debut)]
        solde_depart_total = solde_depart_df["Crédit"].sum() - solde_depart_df["Débit"].sum()
        st.info(f"Solde de départ : {solde_depart_total:,.2f} €")

        # Paramètres pour prévision
        horizon = st.slider("Horizon de projection (en mois)", 3, 24, 12)
        croissance_ca = st.number_input("Croissance mensuelle du CA (%)", value=2.0) / 100
        evolution_charges = st.number_input("Évolution mensuelle des charges (%)", value=1.0) / 100

        # Flux hors comptes bancaires
        df_flux = df_pivot[~df_pivot["Compte"].str.startswith("5")].copy()
        df_flux = df_flux.dropna(subset=["Date"])
        df_flux = df_flux[df_flux["Date"] >= pd.to_datetime(date_debut)]  # Seulement flux après date départ
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
        fig = px.line(
            df_tresorerie,
            x="Mois",
            y="Trésorerie_cumulée",
            title="📈 Évolution prévisionnelle de la trésorerie",
            markers=True
        )
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

# =====================
# ROYALTIES EDITION
# =====================
elif page == "ROYALTIES EDITION":
    st.header("📚 ROYALTIES EDITION - Droits d’auteurs")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        st.markdown("Source des exemplaires vendus :")
        source = st.radio("Source des données", ["Compta analytique", "Importer fichier BLDD"])
        ventes_par_isbn = None

        if source == "Compta analytique":
            ventes_par_isbn = df.groupby("Code_Analytique", as_index=False)["Crédit"].sum().rename(columns={"Crédit":"Ventes_brutes"})
            st.info("Les montants sont extraits du SOCLE (Crédit agrégé par ISBN).")
        else:
            fichier_bldd = st.file_uploader("Importer votre fichier BLDD (exemplaires vendus)", type=["xlsx", "xls"])
            if fichier_bldd:
                df_bldd = pd.read_excel(fichier_bldd)
                # L'utilisateur devra préciser la colonne ISBN et quantité
                cols = df_bldd.columns.tolist()
                col_isbn = st.selectbox("Colonne ISBN dans BLDD", cols)
                col_q = st.selectbox("Colonne quantité vendue dans BLDD", cols)
                ventes_par_isbn = df_bldd.groupby(col_isbn, as_index=False)[col_q].sum().rename(columns={col_q:"Exemplaires_vendus", col_isbn:"Code_Analytique"})
                st.session_state["df_bldd"] = ventes_par_isbn
                st.success("Fichier BLDD importé.")

        st.markdown("Mode de calcul des royalties :")
        mode_royalties = st.radio("Choix", ["Taux fixe (%)", "Grille par auteur/ISBN (fichier)"])

        if mode_royalties == "Taux fixe (%)":
            taux_fixe = st.number_input("Taux fixe de droits (%)", value=10.0)
            if ventes_par_isbn is not None:
                ventes_par_isbn["Droits"] = ventes_par_isbn.get("Ventes_brutes", ventes_par_isbn.get("Exemplaires_vendus", 0)) * (taux_fixe/100)
                st.dataframe(ventes_par_isbn.sort_values("Droits", ascending=False).head(50))
        else:
            fichier_grille = st.file_uploader("Importer fichier grille auteurs/ISBN", type=["xlsx", "xls"])
            if fichier_grille:
                df_grille = pd.read_excel(fichier_grille)
                st.write("Assurez-vous que le fichier contient une colonne 'Code_Analytique' (ISBN) et 'Taux_%'.")
                if "Code_Analytique" in df_grille.columns and "Taux_%" in df_grille.columns:
                    if ventes_par_isbn is None:
                        ventes_par_isbn = df.groupby("Code_Analytique", as_index=False)["Crédit"].sum().rename(columns={"Crédit":"Ventes_brutes"})
                    merged = ventes_par_isbn.merge(df_grille[["Code_Analytique","Taux_%"]], on="Code_Analytique", how="left").fillna(0)
                    merged["Droits"] = merged["Ventes_brutes"] * merged["Taux_%"] / 100
                    st.dataframe(merged.sort_values("Droits", ascending=False).head(50))
                else:
                    st.error("Colonnes requises absentes du fichier grille.")

# =====================
# RETURNS EDITION
# =====================
elif page == "RETURNS EDITION":
    st.header("📦 RETURNS EDITION - Analyse des retours et remises libraires")

    st.info("""
    💡 **Note importante**  
    Les indicateurs s’appuient sur les **numéros de comptes** ou **libellés** présents dans votre SOCLE.  
    Veillez à paramétrer les comptes correctement (ventes / remises / retours) pour garantir la fiabilité.
    """)

    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Vous devez d'abord générer le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        st.subheader("⚙️ Paramétrage des comptes comptables")
        mode = st.radio("Méthode d’identification :", ["Par libellé", "Par numéro de compte"])

        if mode == "Par libellé":
            col_libelle = st.selectbox("Colonne contenant le libellé :", df.columns, index=list(df.columns).index("Libellé") if "Libellé" in df.columns else 0)
            mots_ventes = st.text_input("🔸 Mots-clés pour les ventes (séparés par des virgules)", "vente, bldd")
            mots_retours = st.text_input("🔹 Mots-clés pour les retours (séparés par des virgules)", "retour")
            mots_remises = st.text_input("🟠 Mots-clés pour les remises libraires (séparés par des virgules)", "remise, ristourne")
            mots_ventes = [m.strip().lower() for m in mots_ventes.split(",")]
            mots_retours = [m.strip().lower() for m in mots_retours.split(",")]
            mots_remises = [m.strip().lower() for m in mots_remises.split(",")]

            def classer(texte):
                if pd.isna(texte): return "Autres"
                t = str(texte).lower()
                if any(m in t for m in mots_retours): return "Retours"
                if any(m in t for m in mots_remises): return "Remises"
                if any(m in t for m in mots_ventes): return "Ventes"
                return "Autres"

            df["Type_Ligne"] = df[col_libelle].apply(classer)

        else:
            comptes_uniques = sorted(df["Compte"].astype(str).unique())
            comptes_ventes = st.multiselect("🔸 Comptes de ventes", comptes_uniques, default=[c for c in comptes_uniques if str(c).startswith("701")][:3])
            comptes_retours = st.multiselect("🔹 Comptes de retours", comptes_uniques, default=[c for c in comptes_uniques if str(c).startswith("709")][:3])
            comptes_remises = st.multiselect("🟠 Comptes de remises libraires", comptes_uniques, default=[c for c in comptes_uniques if str(c).startswith("7091")][:3])

            def classer_compte(compte):
                if str(compte) in comptes_retours: return "Retours"
                if str(compte) in comptes_remises: return "Remises"
                if str(compte) in comptes_ventes: return "Ventes"
                return "Autres"

            df["Type_Ligne"] = df["Compte"].apply(classer_compte)

        # Agrégation
        ventes = df[df["Type_Ligne"] == "Ventes"].groupby("Code_Analytique", as_index=False)["Crédit"].sum().rename(columns={"Crédit":"Ventes_brutes"})
        retours = df[df["Type_Ligne"] == "Retours"].groupby("Code_Analytique", as_index=False)["Débit"].sum().rename(columns={"Débit":"Retours"})
        remises = df[df["Type_Ligne"] == "Remises"].groupby("Code_Analytique", as_index=False)["Débit"].sum().rename(columns={"Débit":"Remises_libraires"})

        df_result = ventes.merge(retours, on="Code_Analytique", how="outer")
        df_result = df_result.merge(remises, on="Code_Analytique", how="outer").fillna(0)

        df_result["CA_net_commercial"] = df_result["Ventes_brutes"] - df_result["Remises_libraires"]
        df_result["CA_net_retour"] = df_result["CA_net_commercial"] - df_result["Retours"]
        df_result["Taux_remise_%"] = np.where(df_result["Ventes_brutes"] > 0, df_result["Remises_libraires"] / df_result["Ventes_brutes"] * 100, 0)
        df_result["Taux_retour_%"] = np.where(df_result["Ventes_brutes"] > 0, df_result["Retours"] / df_result["Ventes_brutes"] * 100, 0)

        st.subheader("📊 Synthèse par ISBN")
        st.dataframe(df_result.sort_values("CA_net_retour", ascending=False).head(200))

        st.subheader("📉 Top taux de retour")
        fig1 = px.bar(df_result.sort_values("Taux_retour_%", ascending=False).head(15),
                      x="Code_Analytique", y="Taux_retour_%", title="Top 15 des ouvrages avec le plus fort taux de retour",
                      labels={"Code_Analytique": "ISBN", "Taux_retour_%": "Taux de retour (%)"})
        st.plotly_chart(fig1, use_container_width=True)

        # Projection simple (taux moyen derniers 6 mois)
        st.subheader("🔮 Projection simple (taux moyen)")
        df["Mois"] = pd.to_datetime(df["Date"], errors="coerce").dt.to_period("M").astype(str)
        df_temps_ventes = df[df["Type_Ligne"]=="Ventes"].groupby("Mois", as_index=False)["Crédit"].sum()
        df_temps_retours = df[df["Type_Ligne"]=="Retours"].groupby("Mois", as_index=False)["Débit"].sum()
        df_temps = pd.merge(df_temps_ventes, df_temps_retours, on="Mois", how="outer").fillna(0)
        df_temps["Taux_retour_%"] = np.where(df_temps["Crédit"]>0, df_temps["Débit"]/df_temps["Crédit"]*100, 0)
        taux_moyen = round(df_temps["Taux_retour_%"].tail(6).mean(),2) if not df_temps.empty else 0
        st.info(f"Taux moyen de retour observé sur les 6 derniers mois : {taux_moyen}%")

        # Export
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_result.to_excel(writer, index=False, sheet_name="Analyse_Retours_Remises")
            if not df_temps.empty:
                df_temps.to_excel(writer, index=False, sheet_name="Historique_Taux_Retour")
        buffer.seek(0)
        st.download_button("📥 Télécharger le rapport retours/remises", buffer, file_name="Analyse_Retours_Remises.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =====================
# SYNTHÈSE GÉNÉRALE
# =====================
elif page == "SYNTHÈSE GÉNÉRALE":
    st.header("📊 SYNTHÈSE GÉNÉRALE - Indicateurs clés")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        df["Débit"] = pd.to_numeric(df["Débit"], errors="coerce").fillna(0)
        df["Crédit"] = pd.to_numeric(df["Crédit"], errors="coerce").fillna(0)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

        # CA brut approximatif (comptes commençant par 701)
        ca_brut = df[df["Compte"].astype(str).str.startswith("701")]["Crédit"].sum() - df[df["Compte"].astype(str).str.startswith("701")]["Débit"].sum()
        retours = df[df["Compte"].astype(str).str.startswith("709")]["Débit"].sum() - df[df["Compte"].astype(str).str.startswith("709")]["Crédit"].sum()
        remises = df[df["Compte"].astype(str).str.startswith("7091")]["Débit"].sum() - df[df["Compte"].astype(str).str.startswith("7091")]["Crédit"].sum()

        ca_net = ca_brut - retours - remises

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("CA brut (approx)", f"{ca_brut:,.0f} €")
        col2.metric("Retours (approx)", f"{retours:,.0f} €")
        col3.metric("Remises (approx)", f"{remises:,.0f} €")
        col4.metric("CA net (approx)", f"{ca_net:,.0f} €")

        st.markdown("### Top 5 ISBN par CA net")
        df_isbn = df.groupby("Code_Analytique", as_index=False).agg({"Crédit":"sum","Débit":"sum"})
        df_isbn["CA_net"] = df_isbn["Crédit"] - df_isbn["Débit"]
        st.dataframe(df_isbn.sort_values("CA_net", ascending=False).head(10))

        st.markdown("### Évolution de la trésorerie (approximation depuis SOCLE)")
        # Reuse trésorerie calc (simple): somme des comptes 5
        comptes_bancaires = df[df["Compte"].astype(str).str.startswith("5")]
        if not comptes_bancaires.empty:
            solde = comptes_bancaires.groupby("Compte").apply(lambda x: x["Crédit"].sum()-x["Débit"].sum()).sum()
            st.metric("Solde bancaire (comptes 5)", f"{solde:,.0f} €")
        else:
            st.info("Aucun compte bancaire détecté (comptes commençant par '5').")

        st.markdown("### Graphiques synthèse")
        top_isbn = df_isbn.sort_values("CA_net", ascending=False).head(5)
        if not top_isbn.empty:
            fig = px.bar(top_isbn, x="Code_Analytique", y="CA_net", title="Top 5 ISBN par CA net")
            st.plotly_chart(fig, use_container_width=True)

# =====================
# FIN
# =====================
