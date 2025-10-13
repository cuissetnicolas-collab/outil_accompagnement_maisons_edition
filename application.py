# SYNTHÈSE GLOBALE
# =====================
elif page == "SYNTHÈSE GLOBALE":
    st.header("📊 Synthèse Globale Edition")

    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        param = st.session_state.get("param_comptes", {})

        st.info("Cette synthèse reprend les indicateurs des différents modules (Vision Edition, Cash Edition, Returns Edition...).")

        # Paramètres
        comptes_ventes = param.get("ventes", [])
        comptes_retours = param.get("retours", [])
        comptes_remises = param.get("remises", [])
        col_libelle = "Libellé"

        use_libelle = col_libelle in df.columns

        # --- FILTRAGE ET CALCUL NET (comme Returns Edition)
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

        # CA net et brut
        ca_brut = total_ventes
        ca_net = total_ventes - total_retours - total_remises

        # Provision retours (681)
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

        st.subheader("📊 Montants clés")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 CA Brut", f"{abs(ca_brut):,.0f} €")
        col2.metric("💰 CA Net", f"{abs(ca_net):,.0f} €")
        col3.metric("Total Retours", f"{abs(total_retours):,.0f} €")
        col4.metric("Total Remises", f"{abs(total_remises):,.0f} €")

        st.metric("Provision retours (681)", f"{abs(provision_retours):,.0f} €")

        # --- Optionnel : détail retours/remises par ISBN
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
