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
    st.info("Module inchangé par rapport à votre version BLDD précédente.")

# =====================
# MODULE 2 : IMPORT COMPTABLE
# =====================
elif menu == "Import données comptables":
    st.header("📂 Importation des données comptables")
    fichier_comptables = st.file_uploader("📂 Sélectionnez votre fichier Excel", type=["xlsx"])

    if fichier_comptables is not None:
        df = pd.read_excel(fichier_comptables, header=0)
        # Normalisation colonnes
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("\n","")
        st.session_state["df_comptables"] = df
        st.success(f"✅ Fichier chargé : {df.shape[0]} lignes")
        st.dataframe(df.head())

        if st.button("🛠️ Générer le socle pivot analytique"):
            try:
                df_pivot = pd.pivot_table(
                    df,
                    index=["compte", "famille_de_catégories", "catégories", "date"],
                    values=["débit", "crédit"],
                    aggfunc=np.sum,
                    fill_value=0
                ).reset_index()
                # Renommer pour cohérence
                df_pivot.rename(columns={
                    "famille_de_catégories": "famille_analytique",
                    "catégories": "code_analytique"
                }, inplace=True)
                st.session_state["df_pivot"] = df_pivot
                st.success("✅ Socle pivot analytique généré !")
                st.dataframe(df_pivot.head(20))
            except Exception as e:
                st.error(f"❌ Erreur lors de la génération du pivot : {e}")

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

    # Vérifier que le socle pivot est généré
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le socle pivot depuis le module Import données comptables.")
    else:
        df_pivot = st.session_state["df_pivot"].copy()

        # Normalisation des colonnes
        df_pivot.columns = df_pivot.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("é", "e").str.replace("è","e").str.replace("ê","e")

        # Choix de l'analyse
        sous_menu = st.selectbox("Choix de l'analyse", [
            "Dashboard analytique",
            "Mini compte de résultat par ISBN",
            "Trésorerie prévisionnelle"
        ])

        # ----------------------------
        # Dashboard analytique
        # ----------------------------
        if sous_menu == "Dashboard analytique":
            st.subheader("📈 Top 10 ISBN par résultat net")

            # Calcul du résultat net : Crédit - Débit
            df_pivot["resultat"] = df_pivot["credit"] - df_pivot["debit"]

            # Top 10 ISBN
            top_isbn = df_pivot.groupby("code_analytique", as_index=False)["resultat"].sum()
            top_isbn = top_isbn.sort_values(by="resultat", ascending=False).head(10)

            if top_isbn.empty:
                st.warning("⚠️ Aucun résultat disponible pour générer le dashboard.")
            else:
                st.dataframe(top_isbn)

                fig = px.bar(
                    top_isbn,
                    x="code_analytique",
                    y="resultat",
                    title="Top 10 ISBN par résultat net",
                    labels={"code_analytique": "ISBN", "resultat": "Résultat net"}
                )
                st.plotly_chart(fig, use_container_width=True)

        # ----------------------------
        # Mini compte de résultat par ISBN
        # ----------------------------
        elif sous_menu == "Mini compte de résultat par ISBN":
            st.subheader("💼 Mini compte de résultat par ISBN")

            # Somme des Débit / Crédit par ISBN
            df_cr = df_pivot.groupby("code_analytique", as_index=False).agg({
                "debit": "sum",
                "credit": "sum"
            })
            df_cr["resultat"] = df_cr["credit"] - df_cr["debit"]

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

        # ----------------------------
        # Trésorerie prévisionnelle
        # ----------------------------
        elif sous_menu == "Trésorerie prévisionnelle":
            st.subheader("💰 Trésorerie prévisionnelle")

            # Sélection de la date de début
            date_debut = st.date_input("📅 Date de début de la projection", pd.to_datetime("2025-04-01"))

            # Solde de départ automatique à partir des comptes bancaires
            comptes_bancaires = df_pivot[df_pivot["compte"].str.startswith("5")]
            solde_depart = comptes_bancaires[(comptes_bancaires["date"] <= pd.to_datetime(date_debut))].copy()

            if solde_depart.empty:
                tresorerie_initiale = st.number_input("Solde de départ (€)", value=0.0)
            else:
                tresorerie_initiale = solde_depart["credit"].sum() - solde_depart["debit"].sum()
                st.info(f"Solde de départ calculé automatiquement : {tresorerie_initiale:,.2f} €")

            # Paramètres de projection
            st.markdown("### 🔮 Paramètres de projection")
            horizon = st.slider("Horizon de projection (en mois)", 3, 24, 12)
            croissance_ca = st.number_input("Croissance mensuelle du CA (%)", value=2.0)
            evolution_charges = st.number_input("Évolution mensuelle des charges (%)", value=1.0)

            # Calculs prévisionnels
            if st.button("📊 Générer la prévision de trésorerie"):
                try:
                    df = df_pivot.copy()
                    df["date"] = pd.to_datetime(df["date"], errors="coerce")
                    df = df.dropna(subset=["date"])
                    df = df[df["date"] >= pd.to_datetime(date_debut)]
                    df["mois"] = df["date"].dt.to_period("M").astype(str)

                    # Flux mensuels
                    flux_mensuel = df.groupby("mois").agg({
                        "debit": "sum",
                        "credit": "sum"
                    }).reset_index()
                    flux_mensuel["solde_mensuel"] = flux_mensuel["credit"] - flux_mensuel["debit"]
                    flux_mensuel = flux_mensuel.sort_values("mois")

                    # Prévision pour les mois futurs
                    dernier_mois = pd.Period(flux_mensuel["mois"].max(), freq="M") if not flux_mensuel.empty else pd.Period(date_debut, freq="M")
                    previsions = []
                    ca_actuel = flux_mensuel["credit"].iloc[-1] if not flux_mensuel.empty else 0
                    charges_actuelles = flux_mensuel["debit"].iloc[-1] if not flux_mensuel.empty else 0

                    for i in range(1, horizon + 1):
                        prochain_mois = (dernier_mois + i).strftime("%Y-%m")
                        ca_actuel *= (1 + croissance_ca / 100)
                        charges_actuelles *= (1 + evolution_charges / 100)
                        solde_prevu = ca_actuel - charges_actuelles
                        previsions.append({
                            "mois": prochain_mois,
                            "debit": charges_actuelles,
                            "credit": ca_actuel,
                            "solde_mensuel": solde_prevu
                        })

                    df_prev = pd.DataFrame(previsions)
                    df_tresorerie = pd.concat([flux_mensuel, df_prev], ignore_index=True)

                    # Calcul du solde cumulé
                    df_tresorerie["tresorerie_cumulee"] = tresorerie_initiale + df_tresorerie["solde_mensuel"].cumsum()

                    # Résumé
                    solde_final = df_tresorerie["tresorerie_cumulee"].iloc[-1]
                    variation = solde_final - tresorerie_initiale
                    st.success(f"✅ Solde final prévisionnel : {solde_final:,.2f} € ({variation:+.2f} € vs départ)")

                    # Graphique
                    fig = px.line(
                        df_tresorerie,
                        x="mois",
                        y="tresorerie_cumulee",
                        title="📈 Évolution prévisionnelle de la trésorerie",
                        markers=True
                    )
                    fig.update_layout(xaxis_title="Mois", yaxis_title="Trésorerie (€)")
                    st.plotly_chart(fig, use_container_width=True)

                    # Tableau complet
                    st.subheader("📋 Détail de la prévision mensuelle")
                    st.dataframe(df_tresorerie.style.format({
                        "debit": "{:,.0f}",
                        "credit": "{:,.0f}",
                        "solde_mensuel": "{:,.0f}",
                        "tresorerie_cumulee": "{:,.0f}"
                    }))

                    # Export Excel
                    buffer_tres = BytesIO()
                    with pd.ExcelWriter(buffer_tres, engine="openpyxl") as writer:
                        df_tresorerie.to_excel(writer, index=False, sheet_name="Prevision_Tresorerie")
                    buffer_tres.seek(0)

                    st.download_button(
                        label="📥 Télécharger la prévision (Excel)",
                        data=buffer_tres,
                        file_name="Prevision_Tresorerie.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                except Exception as e:
                    st.error(f"❌ Erreur pendant la simulation : {e}")
