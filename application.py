import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import plotly.express as px

# =====================
# AUTHENTIFICATION
# =====================
import streamlit as st

if "login" not in st.session_state:
    st.session_state["login"] = False
if "page" not in st.session_state:
    st.session_state["page"] = "Accueil"  # page par défaut

def login(username, password):
    users = {
        "aurore": {"password": "12345", "name": "Aurore Demoulin"},
        "laure.froidefond": {"password": "Laure2019$", "name": "Laure Froidefond"},
        "Bruno": {"password": "Toto1963$", "name": "Toto El Gringo"}
    }
    if username in users and password == users[username]["password"]:
        st.session_state["login"] = True
        st.session_state["username"] = username
        st.session_state["name"] = users[username]["name"]
        st.session_state["page"] = "Accueil"  # ✅ redirection automatique vers Accueil
        st.success(f"Bienvenue {st.session_state['name']} 👋")
        st.rerun()  # ✅ recharge immédiate de l'app vers la page d'accueil
    else:
        st.error("❌ Identifiants incorrects")

if not st.session_state["login"]:
    st.title("🔑 Connexion espace expert-comptable")
    username_input = st.text_input("Identifiant")
    password_input = st.text_input("Mot de passe", type="password")
    if st.button("Connexion"):
        login(username_input, password_input)
    st.stop()


# =====================
# HEADER NOM UTILISATEUR
# =====================
st.sidebar.success(f"👤 {st.session_state['name']}")

# =====================
# MENU PRINCIPAL
# =====================
pages = ["Accueil", "DATA EDITION", "SOCLE EDITION", "VISION EDITION", "ISBN VIEW",
         "CASH EDITION", "ROYALTIES EDITION", "RETURNS EDITION", "SYNTHESE GLOBALE"]
page = st.sidebar.selectbox("📂 Menu principal", pages)

# Bouton de déconnexion
if st.sidebar.button("🚪 Déconnexion"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

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
    - Piloter les droits d’auteurs sur vos livres (**ROYALTIES EDITION**)  
    - Gérer les retours éditeurs/distributeurs (**RETURNS EDITION**)  
    - Obtenir une synthèse globale (**SYNTHESE GLOBALE**)  
    Utilisez le menu à gauche pour naviguer entre les modules.
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
            st.session_state["df_comptables"] = df
            st.success(f"✅ Fichier chargé avec succès ({df.shape[0]} lignes)")

            st.dataframe(df.head())

            # 👉 Message d'étape suivante
            st.info("""
            ✅ Votre fichier a bien été importé !  
            Prochaine étape : rendez-vous dans **SOCLE EDITION** pour :
            - Sélectionner les colonnes (Compte, Débit, Crédit, etc.)  
            - Paramétrer vos comptes (ventes, retours, remises, charges)  
            - Et générer le **socle pivot analytique**.  
            """)

        except Exception as e:
            st.error(f"❌ Erreur lors de l'importation du fichier : {e}")

    else:
        st.warning("Veuillez importer un fichier Excel pour continuer.")

# =====================
# SOCLE EDITION
# =====================
elif page == "SOCLE EDITION":
    st.header("🛠️ SOCLE EDITION - Génération du pivot analytique")
    
    if "df_comptables" not in st.session_state:
        st.warning("⚠️ Importer d'abord les données via DATA EDITION.")
    else:
        df = st.session_state["df_comptables"].copy()
        st.subheader("Mapping des colonnes")
        columns = list(df.columns)
        
        compte_col = st.selectbox("Colonne des comptes", columns)
        debit_col = st.selectbox("Colonne Débit", columns)
        credit_col = st.selectbox("Colonne Crédit", columns)
        famille_col = st.selectbox("Colonne Famille analytique (optionnel)", [""] + columns)
        code_col = st.selectbox("Colonne Code analytique / ISBN (optionnel)", [""] + columns)
        date_col = st.selectbox("Colonne Date", columns)
        libelle_col = st.selectbox("Colonne Libellé (optionnel)", [""] + columns)

        st.subheader("Paramétrage des comptes clés")
        ventes_comptes = st.text_input("Numéros de comptes ventes (séparés par virgule)", value="701")
        retours_comptes = st.text_input("Numéros de comptes retours", value="709")
        remises_comptes = st.text_input("Numéros de comptes remises", value="7091")
        charges_comptes = st.text_input("Numéros de comptes charges fixes", value="6")

        st.subheader("Charges fixes imputées")
        charges_imputees = st.radio("Les charges fixes ont-elles déjà été imputées par section ?", ["Oui", "Non"])

        if st.button("Générer le SOCLE"):
            # Mapping des colonnes
            mapping = {compte_col: "Compte", debit_col: "Débit", credit_col: "Crédit"}
            if famille_col != "": mapping[famille_col] = "Famille_Analytique"
            if code_col != "": mapping[code_col] = "Code_Analytique"
            if libelle_col != "": mapping[libelle_col] = "Libellé"
            mapping[date_col] = "Date"

            df.rename(columns=mapping, inplace=True)

            for col in ["Famille_Analytique", "Code_Analytique", "Libellé"]:
                if col not in df.columns:
                    df[col] = ""
                else:
                    df[col] = df[col].fillna("")

            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

            # Génération du pivot
            group_cols = ["Compte", "Famille_Analytique", "Code_Analytique", "Date"]
            if "Libellé" in df.columns:
                group_cols.append("Libellé")

            pivot = df.groupby(group_cols, as_index=False).agg({"Débit": "sum", "Crédit": "sum"})

            # Stockage dans session
            st.session_state["df_pivot"] = pivot
            st.session_state["param_comptes"] = {
                "ventes": [c.strip() for c in ventes_comptes.split(",")],
                "retours": [c.strip() for c in retours_comptes.split(",")],
                "remises": [c.strip() for c in remises_comptes.split(",")],
                "charges": [c.strip() for c in charges_comptes.split(",")],
                "charges_imputees": charges_imputees
            }

            st.success("✅ SOCLE EDITION généré et paramétré.")
            st.dataframe(pivot.head(20))
            st.info("ℹ️ Note : assurez-vous que les colonnes, libellés et comptes sont correctement renseignés pour votre logiciel.")

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
    st.header("📚 ROYALTIES EDITION - Droits d’auteurs détaillés et prévision")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        params = st.session_state["param_comptes"]
        taux_fixe = st.number_input("Taux fixe de droits (%)", value=10.0)
        df_ventes = df[df["Compte"].astype(str).str.startswith(tuple(params["ventes"]))]
        df_ventes["Droits"] = df_ventes["Crédit"] * taux_fixe/100
        droits_totaux = df_ventes.groupby("Code_Analytique", as_index=False)["Droits"].sum().sort_values("Droits", ascending=False)
        st.dataframe(droits_totaux)
        st.info(f"Total droits calculé : {droits_totaux['Droits'].sum():,.0f} €")
        # Prévision simple
        horizon = st.slider("Horizon prévision droits (mois)", 3, 24, 12)
        prevision = droits_totaux.copy()
        prevision["Droits prévus"] = prevision["Droits"].apply(lambda x: x*(1+0.02)**horizon)
        st.subheader("Prévision des droits sur horizon choisi")
        st.dataframe(prevision)

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

        st.info("⚠️ Assurez-vous que vos comptes ou libellés retours, ventes et remises sont correctement paramétrés.")

        # Paramètres
        comptes_ventes = param.get("ventes", [])
        comptes_retours = param.get("retours", [])
        comptes_remises = param.get("remises", [])
        col_libelle = st.text_input("Colonne Libellé (optionnel pour distinguer Retours/Remises)", value="Libellé")

        use_libelle = col_libelle in df.columns

        # --- FILTRAGE ET CALCUL NET ---
        def filtre_compte(df_compte, prefix_list, libelle_filtre=None):
            if not prefix_list:
                return pd.DataFrame()
            df_filt = df_compte[df_compte["Compte"].astype(str).str.startswith(tuple(prefix_list))]
            if use_libelle and libelle_filtre:
                df_filt = df_filt[df_filt[col_libelle].str.contains(libelle_filtre, case=False, na=False)]
            if not df_filt.empty:
                df_filt["Montant_net"] = df_filt["Débit"] - df_filt["Crédit"]
                df_filt["Mois"] = df_filt["Date"].dt.strftime("%Y-%m")
            return df_filt

        # Filtrage
        df_ret = filtre_compte(df, comptes_retours, "Retour")
        df_remises = filtre_compte(df, comptes_remises, "Remise")
        df_ventes = filtre_compte(df, comptes_ventes)

        # Totaux
        total_retours = df_ret["Montant_net"].sum() if not df_ret.empty else 0
        total_remises = df_remises["Montant_net"].sum() if not df_remises.empty else 0
        total_ventes = df_ventes["Montant_net"].sum() if not df_ventes.empty else 0

        # Provision retours
        df_prov = df[df["Compte"].astype(str).str.startswith("681")]
        if not df_prov.empty:
            df_prov["Montant_net"] = df_prov["Débit"] - df_prov["Crédit"]
            provision_retours = df_prov["Montant_net"].sum()
        else:
            provision_retours = 0

        # --- TAUX ---
        taux_retour = abs(total_retours) / abs(total_ventes) * 100 if total_ventes != 0 else 0
        taux_remise = abs(total_remises) / abs(total_ventes) * 100 if total_ventes != 0 else 0

        st.subheader("📊 Taux par rapport aux ventes")
        col1, col2 = st.columns(2)
        col1.metric("Taux de retour (%)", f"{taux_retour:.2f} %")
        col2.metric("Taux de remise (%)", f"{taux_remise:.2f} %")

        # --- INDICATEURS ---
        st.subheader("📊 Montants Retours / Remises")
        st.metric("Total ventes (brut)", f"{abs(total_ventes):,.0f} €")
        st.metric("Total retours", f"{abs(total_retours):,.0f} €")
        st.metric("Total remises", f"{abs(total_remises):,.0f} €")
        st.metric("Provision retours (681)", f"{abs(provision_retours):,.0f} €")

        # --- Détail par ISBN ---
        if not df_ret.empty:
            st.subheader("Retours par ISBN")
            ret_isbn = df_ret.groupby("Code_Analytique", as_index=False).agg({"Montant_net":"sum"})
            ret_isbn["Montant_net"] = ret_isbn["Montant_net"].abs()
            st.dataframe(ret_isbn)

        if not df_remises.empty:
            st.subheader("Remises par ISBN")
            rem_isbn = df_remises.groupby("Code_Analytique", as_index=False).agg({"Montant_net":"sum"})
            rem_isbn["Montant_net"] = rem_isbn["Montant_net"].abs()
            st.dataframe(rem_isbn)

        # --- Tendance mensuelle ---
        if not df_ret.empty:
            st.subheader("Tendance mensuelle des retours")
            trend_ret = df_ret.groupby("Mois", as_index=False)["Montant_net"].sum()
            trend_ret["Montant_net"] = trend_ret["Montant_net"].abs()
            fig_trend = px.bar(trend_ret, x="Mois", y="Montant_net", text="Montant_net",
                               title="Montant des retours par mois", labels={"Montant_net":"Montant (€)"})
            fig_trend.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig_trend, use_container_width=True)

        if not df_remises.empty:
            st.subheader("Tendance mensuelle des remises")
            trend_rem = df_remises.groupby("Mois", as_index=False)["Montant_net"].sum()
            trend_rem["Montant_net"] = trend_rem["Montant_net"].abs()
            fig_trend_rem = px.bar(trend_rem, x="Mois", y="Montant_net", text="Montant_net",
                                   title="Montant des remises par mois", labels={"Montant_net":"Montant (€)"})
            fig_trend_rem.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig_trend_rem, use_container_width=True)
# =====================
# CASH EDITION - Trésorerie prévisionnelle (intégrée)
# =====================
elif page == "CASH EDITION":
    st.header("💰 CASH EDITION - Trésorerie prévisionnelle")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df_pivot = st.session_state["df_pivot"].copy()

        st.info("Module de prévision de trésorerie basé sur le SOCLE analytique.")

        # Date de départ
        date_debut = st.date_input("Date de départ de la trésorerie", pd.to_datetime("2025-04-01"))

        # Nettoyage et conversions
        df_pivot["Compte"] = df_pivot["Compte"].astype(str).str.strip()
        df_pivot["Date"] = pd.to_datetime(df_pivot["Date"], errors="coerce")
        df_pivot["Débit"] = pd.to_numeric(df_pivot["Débit"], errors="coerce").fillna(0)
        df_pivot["Crédit"] = pd.to_numeric(df_pivot["Crédit"], errors="coerce").fillna(0)

        # Calcul du solde de départ : comptes bancaires commençant par '5'
        comptes_bancaires = df_pivot[df_pivot["Compte"].str.startswith("5")]
        solde_depart_df = comptes_bancaires[comptes_bancaires["Date"] <= pd.to_datetime(date_debut)]
        solde_depart_total = solde_depart_df["Crédit"].sum() - solde_depart_df["Débit"].sum()
        st.info(f"Solde de départ (comptes '5' jusqu'à {date_debut}): {solde_depart_total:,.2f} €")

        # Paramètres pour la prévision
        horizon = st.slider("Horizon de projection (en mois)", 3, 36, 12)
        croissance_ca = st.number_input("Croissance mensuelle du CA (%)", value=2.0, step=0.1) / 100
        evolution_charges = st.number_input("Évolution mensuelle des charges (%)", value=1.0, step=0.1) / 100

        # Préparation des flux : exclure les comptes bancaires (on projette les flux non bancaires)
        df_flux = df_pivot[~df_pivot["Compte"].str.startswith("5")].copy()
        df_flux = df_flux.dropna(subset=["Date"])
        df_flux = df_flux[df_flux["Date"] >= pd.to_datetime(date_debut)]  # uniquement après la date de départ

        if df_flux.empty:
            st.warning("Aucun flux non bancaire détecté après la date de départ. Vérifiez votre socle ou la date de départ.")
        else:
            # Agrégation mensuelle
            df_flux["Mois"] = df_flux["Date"].dt.to_period("M").astype(str)
            flux_mensuel = df_flux.groupby("Mois").agg({"Débit": "sum", "Crédit": "sum"}).reset_index()
            flux_mensuel["Solde_mensuel"] = flux_mensuel["Crédit"] - flux_mensuel["Débit"]
            flux_mensuel = flux_mensuel.sort_values("Mois").reset_index(drop=True)

            # Prévisions futures
            dernier_mois = pd.Period(flux_mensuel["Mois"].max(), freq="M") if not flux_mensuel.empty else pd.Period(date_debut, freq="M")
            previsions = []
            # Valeurs de départ : on prend le dernier mois existant s'il y en a
            ca_actuel = flux_mensuel["Crédit"].iloc[-1] if not flux_mensuel.empty else 0
            charges_actuelles = flux_mensuel["Débit"].iloc[-1] if not flux_mensuel.empty else 0

            for i in range(1, horizon + 1):
                prochain_mois = (dernier_mois + i).strftime("%Y-%m")
                ca_actuel = ca_actuel * (1 + croissance_ca)
                charges_actuelles = charges_actuelles * (1 + evolution_charges)
                solde_prevu = ca_actuel - charges_actuelles
                previsions.append({
                    "Mois": prochain_mois,
                    "Débit": charges_actuelles,
                    "Crédit": ca_actuel,
                    "Solde_mensuel": solde_prevu
                })

            df_prev = pd.DataFrame(previsions)

            # Concaténation historique + prévisions
            df_tresorerie = pd.concat([flux_mensuel, df_prev], ignore_index=True, sort=False)
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

            # Détail mensuel formaté
            st.subheader("📋 Détail mensuel (historique + prévisions)")
            # Formatage colonne numérique avant affichage
            df_display = df_tresorerie.copy()
            for col in ["Débit", "Crédit", "Solde_mensuel", "Trésorerie_cumulée"]:
                if col in df_display.columns:
                    df_display[col] = pd.to_numeric(df_display[col], errors="coerce")
            st.dataframe(df_display.style.format({
                "Débit": "{:,.0f}",
                "Crédit": "{:,.0f}",
                "Solde_mensuel": "{:,.0f}",
                "Trésorerie_cumulée": "{:,.0f}"
            }))

            # Téléchargement Excel
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_display.to_excel(writer, index=False, sheet_name="Tresorerie_Previsions")
            buffer.seek(0)
            st.download_button(
                label="📥 Télécharger prévisions trésorerie (Excel)",
                data=buffer,
                file_name="Previsions_Tresorerie.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# =====================
# SYNTHESE GLOBALE
# =====================
elif page == "SYNTHESE GLOBALE":
    st.header("📊 SYNTHESE GLOBALE")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        params = st.session_state["param_comptes"]
        ventes, retours, remises = params["ventes"], params["retours"], params["remises"]

        ca_brut = df[df["Compte"].astype(str).str.startswith(tuple(ventes))]["Crédit"].sum()
        total_retours = df[df["Compte"].astype(str).str.startswith(tuple(retours))]["Crédit"].sum()
        total_remises = df[df["Compte"].astype(str).str.startswith(tuple(remises))]["Crédit"].sum()
        ca_net = ca_brut - total_retours - total_remises

        df_summary = pd.DataFrame({
            "Indicateur":["CA brut","Total retours","Total remises","CA net"],
            "Montant":[ca_brut,total_retours,total_remises,ca_net]
        })

        st.subheader("Tableau récapitulatif")
        st.dataframe(df_summary.style.format({"Montant":"{:,.0f} €"}))

        fig_summary = px.bar(df_summary, x="Indicateur", y="Montant", text="Montant", title="📊 Synthèse financière globale")
        fig_summary.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig_summary, use_container_width=True)

# =====================
# FOOTER / COPYRIGHT
# =====================
st.markdown("---")
st.markdown("© 2025 Nicolas CUISSET - Créateur de l'application")
