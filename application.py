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
        
        # --- Message d'introduction ---
        st.info("""
        💡 Bienvenue dans le module SOCLE EDITION !  
        Ici, vous allez pouvoir générer votre pivot analytique à partir des données importées.  
        Veuillez renseigner soigneusement :
        - Les **colonnes correspondant à vos données** (comptes, débit, crédit, libellés, dates…)  
        - Les **paramètres de comptes comptables** correspondant à votre logiciel pour les ventes, retours, remises et charges  
        ⚠️ Ces informations permettront de générer correctement le socle analytique et vos outils d'analyse ultérieurs.
        """)
        
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
            st.info("""
            🎯 Le socle pivot est prêt !  
            Vous pouvez maintenant générer et analyser vos données dans les modules suivants :
            - **VISION EDITION** : analyse des ventes par ISBN et indicateurs analytiques  
            - **ISBN VIEW** : mini compte de résultat par ISBN  
            - **CASH EDITION** : trésorerie prévisionnelle  
            - **ROYALTIES EDITION** : suivi des droits d’auteurs  
            - **RETURNS EDITION** : gestion des retours et remises  

            📌 Une synthèse globale sera disponible à la fin dans **SYNTHESE GLOBALE**.
            """)

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
    st.header("📚 ROYALTIES EDITION — Droits d'auteurs & URSSAF")
 
    # ──────────────────────────────────────────────
    # TAUX URSSAF (précompte diffuseur — en vigueur 2024)
    # Le diffuseur/éditeur prélève ces cotisations sur les droits bruts avant
    # de les verser à l'auteur, puis les reverse à l'URSSAF.
    # ──────────────────────────────────────────────
    TAUX_CSG_CRDS        = 0.097   # CSG (9,2%) + CRDS (0,5%) = 9,7%
    TAUX_FORMATION_PROF  = 0.01    # Contribution formation professionnelle = 1,0%
    # Cotisation retraite complémentaire RAAP (variable selon revenus) : on laisse paramétrable
    # Attention : ces taux s'appliquent sur 98,25% des droits bruts (abattement de 1,75%)
    ASSIETTE_COEFF       = 0.9825  # Abattement forfaitaire frais professionnels
 
    st.info("""
    **Comment fonctionne ce module ?**
    
    1. **Onglet Référentiel** : saisissez vos contrats (auteur, ISBN, taux, paliers, répartition co-auteurs)
    2. **Onglet Calcul** : les droits sont calculés automatiquement depuis le SOCLE EDITION  
    3. **Onglet URSSAF** : calcul du précompte (CSG/CRDS + formation pro) à reverser à l'URSSAF  
    4. **Onglet Relevés** : relevé de compte par auteur, exportable en Excel
    """)
 
    # ──────────────────────────────────────────────
    # INITIALISATION DU RÉFÉRENTIEL EN SESSION
    # Structure : liste de dicts {auteur, isbn, titre, taux_base, paliers, part_auteur}
    # paliers : liste de {seuil, taux} — ex. [{seuil:0, taux:10}, {seuil:10000, taux:12}]
    # ──────────────────────────────────────────────
    if "royalties_referentiel" not in st.session_state:
        st.session_state["royalties_referentiel"] = []
 
    onglet1, onglet2, onglet3, onglet4 = st.tabs([
        "📋 Référentiel contrats",
        "🧮 Calcul des droits",
        "🏛️ URSSAF / Précompte",
        "📄 Relevés par auteur"
    ])
 
    # ══════════════════════════════════════════════
    # ONGLET 1 — RÉFÉRENTIEL CONTRATS
    # ══════════════════════════════════════════════
    with onglet1:
        st.subheader("Saisie des contrats auteurs")
 
        st.markdown("**Ajouter un contrat**")
        col_a, col_b = st.columns(2)
        with col_a:
            inp_auteur  = st.text_input("Nom de l'auteur")
            inp_isbn    = st.text_input("ISBN (code analytique exact du SOCLE)")
            inp_titre   = st.text_input("Titre du livre (pour l'affichage)")
        with col_b:
            inp_assiette = st.selectbox(
                "Assiette de calcul",
                ["CA net HT (après retours et remises)", "CA brut HT", "Prix public HT"]
            )
            inp_part = st.number_input(
                "Part de cet auteur (%)", min_value=0.0, max_value=100.0, value=100.0, step=1.0,
                help="Si plusieurs auteurs partagent les droits, indiquez la part de chacun. La somme doit faire 100%."
            )
 
        st.markdown("**Paliers de droits**")
        st.caption("Saisissez les paliers de CA à partir desquels le taux change. "
                   "Si pas de paliers, laissez un seul palier avec seuil = 0.")
 
        nb_paliers = st.number_input("Nombre de paliers", min_value=1, max_value=5, value=1, step=1)
        paliers = []
        for i in range(int(nb_paliers)):
            pc1, pc2 = st.columns(2)
            with pc1:
                seuil = st.number_input(
                    f"Palier {i+1} — CA à partir de (€)", value=0 if i == 0 else i * 5000,
                    key=f"seuil_{i}"
                )
            with pc2:
                taux = st.number_input(
                    f"Palier {i+1} — Taux (%)", value=10.0 if i == 0 else 12.0,
                    key=f"taux_{i}"
                )
            paliers.append({"seuil": seuil, "taux": taux})
 
        if st.button("➕ Ajouter ce contrat"):
            if inp_auteur and inp_isbn:
                st.session_state["royalties_referentiel"].append({
                    "auteur":    inp_auteur,
                    "isbn":      inp_isbn.strip(),
                    "titre":     inp_titre or inp_isbn,
                    "assiette":  inp_assiette,
                    "part":      inp_part,
                    "paliers":   paliers
                })
                st.success(f"✅ Contrat ajouté : {inp_auteur} / {inp_titre or inp_isbn}")
            else:
                st.warning("Veuillez renseigner au minimum l'auteur et l'ISBN.")
 
        # ── Import CSV du référentiel ──
        st.markdown("---")
        st.markdown("**Import du référentiel depuis un fichier CSV**")
        st.caption("Le fichier doit avoir les colonnes : auteur, isbn, titre, assiette, part, seuil_1, taux_1, seuil_2, taux_2, ...")
        fichier_ref = st.file_uploader("Importer le référentiel (CSV)", type=["csv"], key="ref_csv")
        if fichier_ref:
            try:
                df_ref_import = pd.read_csv(fichier_ref)
                df_ref_import.columns = df_ref_import.columns.str.strip().str.lower()
                for _, row in df_ref_import.iterrows():
                    paliers_import = []
                    i = 1
                    while f"seuil_{i}" in row and f"taux_{i}" in row:
                        if pd.notna(row[f"seuil_{i}"]) and pd.notna(row[f"taux_{i}"]):
                            paliers_import.append({"seuil": float(row[f"seuil_{i}"]), "taux": float(row[f"taux_{i}"])})
                        i += 1
                    if not paliers_import:
                        paliers_import = [{"seuil": 0, "taux": 10.0}]
                    st.session_state["royalties_referentiel"].append({
                        "auteur":   str(row.get("auteur", "")),
                        "isbn":     str(row.get("isbn", "")).strip(),
                        "titre":    str(row.get("titre", row.get("isbn", ""))),
                        "assiette": str(row.get("assiette", "CA net HT (après retours et remises)")),
                        "part":     float(row.get("part", 100)),
                        "paliers":  paliers_import
                    })
                st.success(f"✅ {len(df_ref_import)} contrats importés.")
            except Exception as e:
                st.error(f"Erreur lors de l'import : {e}")
 
        # ── Affichage et gestion du référentiel ──
        st.markdown("---")
        st.subheader("Contrats enregistrés")
        ref = st.session_state["royalties_referentiel"]
        if ref:
            rows_display = []
            for idx, c in enumerate(ref):
                paliers_str = " | ".join(
                    f">{p['seuil']:,.0f}€ → {p['taux']}%" for p in c["paliers"]
                )
                rows_display.append({
                    "#": idx,
                    "Auteur": c["auteur"],
                    "ISBN": c["isbn"],
                    "Titre": c["titre"],
                    "Part (%)": c["part"],
                    "Assiette": c["assiette"],
                    "Paliers": paliers_str
                })
            df_ref_display = pd.DataFrame(rows_display)
            st.dataframe(df_ref_display, use_container_width=True)
 
            # Suppression
            idx_suppr = st.number_input("Supprimer le contrat n°", min_value=0, max_value=len(ref)-1, step=1)
            if st.button("🗑️ Supprimer ce contrat"):
                st.session_state["royalties_referentiel"].pop(int(idx_suppr))
                st.rerun()
 
            # Export CSV du référentiel
            buffer_ref = BytesIO()
            df_ref_display.to_csv(buffer_ref, index=False)
            buffer_ref.seek(0)
            st.download_button(
                "📥 Exporter le référentiel (CSV)", buffer_ref,
                file_name="referentiel_contrats.csv", mime="text/csv"
            )
        else:
            st.info("Aucun contrat enregistré. Commencez par en ajouter un ci-dessus.")
 
    # ══════════════════════════════════════════════
    # ONGLET 2 — CALCUL DES DROITS
    # ══════════════════════════════════════════════
    with onglet2:
        st.subheader("Calcul des droits d'auteurs par titre")
 
        if "df_pivot" not in st.session_state:
            st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
        elif not st.session_state["royalties_referentiel"]:
            st.warning("⚠️ Saisir au moins un contrat dans l'onglet Référentiel.")
        else:
            df_pivot = st.session_state["df_pivot"].copy()
            params   = st.session_state["param_comptes"]
 
            # ── Calcul des CA par ISBN (brut, retours, remises, net) ──
            def ca_isbn(df, prefix_list):
                if not prefix_list:
                    return pd.Series(dtype=float)
                mask = df["Compte"].astype(str).str.startswith(tuple(prefix_list))
                return df[mask].groupby("Code_Analytique")["Crédit"].sum() \
                     - df[mask].groupby("Code_Analytique")["Débit"].sum()
 
            ca_brut    = ca_isbn(df_pivot, params["ventes"])
            ca_retours = ca_isbn(df_pivot, params["retours"])
            ca_remises = ca_isbn(df_pivot, params["remises"])
 
            # ── Fonction de calcul par paliers ──
            def calcul_droits_paliers(base, paliers):
                """
                Calcule les droits dus selon des paliers progressifs.
                paliers : liste triée de {seuil, taux}
                Exemple : [{seuil:0, taux:10}, {seuil:10000, taux:12}]
                → de 0 à 10 000€ : 10% ; au-delà : 12%
                """
                paliers_sorted = sorted(paliers, key=lambda p: p["seuil"])
                droits = 0.0
                for i, palier in enumerate(paliers_sorted):
                    seuil_bas = palier["seuil"]
                    seuil_haut = paliers_sorted[i+1]["seuil"] if i+1 < len(paliers_sorted) else float("inf")
                    if base <= seuil_bas:
                        break
                    tranche = min(base, seuil_haut) - seuil_bas
                    droits += tranche * palier["taux"] / 100
                return droits
 
            # ── Boucle sur chaque contrat ──
            resultats = []
            for contrat in st.session_state["royalties_referentiel"]:
                isbn = contrat["isbn"]
 
                ca_b  = float(ca_brut.get(isbn, 0))
                ca_r  = float(ca_retours.get(isbn, 0))
                ca_re = float(ca_remises.get(isbn, 0))
                ca_n  = ca_b - abs(ca_r) - abs(ca_re)
 
                # Choix de l'assiette
                if contrat["assiette"] == "CA brut HT":
                    base = ca_b
                else:
                    # "CA net HT (après retours et remises)" par défaut
                    base = max(ca_n, 0)
 
                droits_bruts_total = calcul_droits_paliers(base, contrat["paliers"])
                droits_bruts_part  = droits_bruts_total * contrat["part"] / 100
 
                resultats.append({
                    "Auteur":         contrat["auteur"],
                    "ISBN":           isbn,
                    "Titre":          contrat["titre"],
                    "Part auteur (%)": contrat["part"],
                    "Assiette":       contrat["assiette"],
                    "CA brut (€)":    round(ca_b, 2),
                    "Retours (€)":    round(abs(ca_r), 2),
                    "Remises (€)":    round(abs(ca_re), 2),
                    "Base calcul (€)": round(base, 2),
                    "Droits bruts (€)": round(droits_bruts_part, 2),
                })
 
            df_resultats = pd.DataFrame(resultats)
            st.session_state["df_royalties_resultats"] = df_resultats
 
            if df_resultats.empty:
                st.info("Aucune correspondance trouvée entre les ISBN du référentiel et ceux du SOCLE.")
            else:
                st.dataframe(
                    df_resultats.style.format({
                        "CA brut (€)": "{:,.2f}",
                        "Retours (€)": "{:,.2f}",
                        "Remises (€)": "{:,.2f}",
                        "Base calcul (€)": "{:,.2f}",
                        "Droits bruts (€)": "{:,.2f}",
                    }),
                    use_container_width=True
                )
 
                total_droits = df_resultats["Droits bruts (€)"].sum()
                st.metric("💰 Total droits d'auteurs bruts dus", f"{total_droits:,.2f} €")
 
                # Graphique droits par titre
                fig_droits = px.bar(
                    df_resultats.sort_values("Droits bruts (€)", ascending=False),
                    x="Titre", y="Droits bruts (€)", color="Auteur",
                    title="Droits d'auteurs par titre",
                    labels={"Droits bruts (€)": "Droits (€)", "Titre": ""},
                    text_auto=".0f"
                )
                fig_droits.update_traces(textposition="outside")
                fig_droits.update_layout(xaxis_tickangle=-30)
                st.plotly_chart(fig_droits, use_container_width=True)
 
    # ══════════════════════════════════════════════
    # ONGLET 3 — URSSAF / PRÉCOMPTE
    # ══════════════════════════════════════════════
    with onglet3:
        st.subheader("Calcul URSSAF — Précompte diffuseur")
 
        st.markdown("""
        En tant qu'éditeur/diffuseur, vous êtes **précompteur** : vous prélevez les cotisations
        sociales sur les droits bruts avant de les verser à l'auteur, puis vous les reversez à l'URSSAF.
 
        **Assiette** = droits bruts × 98,25% (abattement forfaitaire de 1,75%)
        """)
 
        col_u1, col_u2, col_u3 = st.columns(3)
        taux_csg_crds = col_u1.number_input(
            "CSG + CRDS (%)", value=9.70, step=0.01,
            help="CSG 9,2% + CRDS 0,5% = 9,7% par défaut"
        )
        taux_fp = col_u2.number_input(
            "Formation professionnelle (%)", value=1.00, step=0.01,
            help="1% des droits bruts"
        )
        taux_raap = col_u3.number_input(
            "Retraite complémentaire RAAP (%)", value=0.0, step=0.01,
            help="Variable selon revenus annuels de l'auteur. Laisser à 0 si géré séparément."
        )
 
        if "df_royalties_resultats" not in st.session_state:
            st.warning("⚠️ Effectuez d'abord le calcul dans l'onglet 'Calcul des droits'.")
        else:
            df_r = st.session_state["df_royalties_resultats"].copy()
 
            df_r["Assiette URSSAF (€)"]     = df_r["Droits bruts (€)"] * ASSIETTE_COEFF
            df_r["CSG + CRDS (€)"]           = df_r["Assiette URSSAF (€)"] * taux_csg_crds / 100
            df_r["Formation pro (€)"]        = df_r["Droits bruts (€)"] * taux_fp / 100
            df_r["Retraite RAAP (€)"]        = df_r["Assiette URSSAF (€)"] * taux_raap / 100
            df_r["Total cotisations (€)"]    = (
                df_r["CSG + CRDS (€)"]
                + df_r["Formation pro (€)"]
                + df_r["Retraite RAAP (€)"]
            )
            df_r["Net à payer auteur (€)"]   = df_r["Droits bruts (€)"] - df_r["Total cotisations (€)"]
 
            st.session_state["df_royalties_urssaf"] = df_r
 
            cols_urssaf = [
                "Auteur", "Titre",
                "Droits bruts (€)",
                "Assiette URSSAF (€)",
                "CSG + CRDS (€)",
                "Formation pro (€)",
                "Retraite RAAP (€)",
                "Total cotisations (€)",
                "Net à payer auteur (€)"
            ]
            st.dataframe(
                df_r[cols_urssaf].style.format({
                    c: "{:,.2f}" for c in cols_urssaf if "(€)" in c
                }),
                use_container_width=True
            )
 
            # Totaux
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Droits bruts totaux",       f"{df_r['Droits bruts (€)'].sum():,.2f} €")
            col_m2.metric("Total cotisations URSSAF",  f"{df_r['Total cotisations (€)'].sum():,.2f} €")
            col_m3.metric("Net versé aux auteurs",      f"{df_r['Net à payer auteur (€)'].sum():,.2f} €")
 
            # Graphique cotisations vs net
            df_urssaf_chart = df_r.groupby("Auteur", as_index=False).agg({
                "Total cotisations (€)": "sum",
                "Net à payer auteur (€)": "sum"
            })
            df_urssaf_melt = df_urssaf_chart.melt(
                id_vars="Auteur",
                value_vars=["Total cotisations (€)", "Net à payer auteur (€)"],
                var_name="Composante", value_name="Montant (€)"
            )
            fig_urssaf = px.bar(
                df_urssaf_melt, x="Auteur", y="Montant (€)", color="Composante",
                title="Répartition cotisations URSSAF vs net auteur",
                barmode="stack", text_auto=".0f"
            )
            fig_urssaf.update_traces(textposition="inside")
            st.plotly_chart(fig_urssaf, use_container_width=True)
 
    # ══════════════════════════════════════════════
    # ONGLET 4 — RELEVÉS PAR AUTEUR
    # ══════════════════════════════════════════════
    with onglet4:
        st.subheader("Relevés de droits par auteur")
 
        source_df_key = "df_royalties_urssaf" if "df_royalties_urssaf" in st.session_state \
                        else "df_royalties_resultats"
 
        if source_df_key not in st.session_state:
            st.warning("⚠️ Effectuez d'abord le calcul des droits (onglet 'Calcul des droits').")
        else:
            df_releves = st.session_state[source_df_key].copy()
            auteurs    = sorted(df_releves["Auteur"].unique().tolist())
 
            auteur_sel = st.selectbox("Sélectionnez un auteur", ["Tous"] + auteurs)
 
            if auteur_sel != "Tous":
                df_auteur = df_releves[df_releves["Auteur"] == auteur_sel]
            else:
                df_auteur = df_releves
 
            # Colonnes à afficher selon ce qui est disponible
            cols_releve_base = [
                "Auteur", "Titre", "ISBN",
                "CA brut (€)", "Retours (€)", "Remises (€)",
                "Base calcul (€)", "Droits bruts (€)"
            ]
            cols_releve_urssaf = [
                "CSG + CRDS (€)", "Formation pro (€)",
                "Retraite RAAP (€)", "Total cotisations (€)", "Net à payer auteur (€)"
            ]
            cols_dispo = [c for c in cols_releve_base + cols_releve_urssaf if c in df_auteur.columns]
 
            st.dataframe(
                df_auteur[cols_dispo].style.format({
                    c: "{:,.2f}" for c in cols_dispo if "(€)" in c
                }),
                use_container_width=True
            )
 
            # Résumé par auteur (si "Tous")
            if auteur_sel == "Tous":
                st.subheader("Synthèse par auteur")
                cols_sum = {c: "sum" for c in cols_dispo if "(€)" in c}
                df_synth = df_releves.groupby("Auteur", as_index=False).agg(cols_sum)
                st.dataframe(
                    df_synth.style.format({c: "{:,.2f}" for c in cols_sum}),
                    use_container_width=True
                )
 
            # ── Export Excel multi-feuilles ──
            buffer_xl = BytesIO()
            with pd.ExcelWriter(buffer_xl, engine="openpyxl") as writer:
                # Feuille 1 : détail complet
                df_auteur[cols_dispo].to_excel(
                    writer, index=False,
                    sheet_name=f"Détail_{auteur_sel[:20]}"
                )
                # Feuille 2 : synthèse par auteur
                if auteur_sel == "Tous" and "df_synth" in dir():
                    df_synth.to_excel(writer, index=False, sheet_name="Synthèse auteurs")
                # Feuille 3 : référentiel contrats
                if st.session_state["royalties_referentiel"]:
                    rows_ref = []
                    for c in st.session_state["royalties_referentiel"]:
                        row = {
                            "auteur": c["auteur"], "isbn": c["isbn"],
                            "titre": c["titre"], "part": c["part"],
                            "assiette": c["assiette"]
                        }
                        for i, p in enumerate(c["paliers"], 1):
                            row[f"seuil_{i}"] = p["seuil"]
                            row[f"taux_{i}"]  = p["taux"]
                        rows_ref.append(row)
                    pd.DataFrame(rows_ref).to_excel(writer, index=False, sheet_name="Référentiel contrats")
 
            buffer_xl.seek(0)
            st.download_button(
                label=f"📥 Télécharger le relevé — {auteur_sel}",
                data=buffer_xl,
                file_name=f"Royalties_{auteur_sel.replace(' ','_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

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
        col_libelle = "Libellé"
        use_libelle = col_libelle in df.columns

        # --- FILTRAGE NET comme Returns Edition ---
        def filtre_compte(df_compte, prefix_list, libelle_filtre=None):
            if not prefix_list:
                return pd.DataFrame()
            df_filt = df_compte[df_compte["Compte"].astype(str).str.startswith(tuple(prefix_list))]
            if use_libelle and libelle_filtre:
                df_filt = df_filt[df_filt[col_libelle].str.contains(libelle_filtre, case=False, na=False)]
            if not df_filt.empty:
                df_filt["Montant_net"] = df_filt["Débit"] - df_filt["Crédit"]
            return df_filt

        # Filtrage
        df_ret = filtre_compte(df, retours, "Retour")
        df_rem = filtre_compte(df, remises, "Remise")
        df_ventes = filtre_compte(df, ventes)

        # Totaux avec valeur absolue pour éviter les négatifs
        ca_brut = abs(df_ventes["Montant_net"].sum()) if not df_ventes.empty else 0
        total_retours = abs(df_ret["Montant_net"].sum()) if not df_ret.empty else 0
        total_remises = abs(df_rem["Montant_net"].sum()) if not df_rem.empty else 0
        ca_net = ca_brut - total_retours - total_remises

        # Affichage tableau
        df_summary = pd.DataFrame({
            "Indicateur": ["CA brut", "Total retours", "Total remises", "CA net"],
            "Montant": [ca_brut, total_retours, total_remises, ca_net]
        })

        st.subheader("Tableau récapitulatif")
        st.dataframe(df_summary.style.format({"Montant":"{:,.0f} €"}))

        # Graphique
        fig_summary = px.bar(df_summary, x="Indicateur", y="Montant", text="Montant",
                             title="📊 Synthèse financière globale")
        fig_summary.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig_summary, use_container_width=True)

# =====================
# FOOTER / COPYRIGHT
# =====================
st.markdown("---")
st.markdown("© 2025 Nicolas CUISSET - Créateur de l'application")
