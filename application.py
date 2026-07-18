import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
import qrcode
from PIL import Image
import anthropic
import json

# =====================
# CONFIGURATION PAGE
# =====================
st.set_page_config(
    page_title="Outil éditorial - Maisons d'édition indépendantes",
    page_icon="📚",
    layout="wide"
)

APP_URL = "https://outilaccompagnementmaisonsedition-lyvgltfbwtqo4m9tdmzofu.streamlit.app/"

# =====================
# AUTHENTIFICATION
# =====================
if "login" not in st.session_state:
    st.session_state["login"] = False
if "page" not in st.session_state:
    st.session_state["page"] = "🏠 Accueil"
if "messages_agent" not in st.session_state:
    st.session_state["messages_agent"] = []

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
        st.session_state["page"] = "🏠 Accueil"
        st.rerun()
    else:
        st.error("❌ Identifiants incorrects")

if not st.session_state["login"]:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("## 📚 Outil d'accompagnement éditorial")
        st.markdown("*Maisons d'édition indépendantes*")
        st.divider()
        username_input = st.text_input("Identifiant", placeholder="Votre identifiant")
        password_input = st.text_input("Mot de passe", type="password", placeholder="Votre mot de passe")
        if st.button("🔑 Connexion", use_container_width=True, type="primary"):
            login(username_input, password_input)
        st.divider()
        # QR code sur la page de login aussi
        st.markdown("**Accès mobile — scannez pour ouvrir l'app**")
        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        qr.add_data(APP_URL)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img_qr.save(buf, format="PNG")
        st.image(buf.getvalue(), width=140)
    st.stop()

# =====================
# SIDEBAR
# =====================
with st.sidebar:
    st.markdown(f"👤 **{st.session_state['name']}**")
    st.divider()
    pages = [
        "🏠 Accueil",
        "📂 Import des données",
        "⚙️ Paramétrage analytique",
        "📈 Tableau de bord éditorial",
        "📖 Analyse par titre",
        "💰 Trésorerie prévisionnelle",
        "✍️ Droits d'auteurs",
        "📦 Retours & Remises",
        "📊 Synthèse financière",
        "🤖 Assistant IA"
    ]
    page = st.selectbox("Navigation", pages)
    st.divider()
    if st.button("🚪 Déconnexion", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# =====================
# HELPERS
# =====================
def get_client():
    """Retourne le client Anthropic — la clé est injectée par Streamlit Cloud via secrets."""
    try:
        return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    except Exception:
        return None

def filtrer_isbn_reels(df):
    """Ne garde que les lignes réellement rattachées à un titre (un vrai ISBN).

    Sans ce filtre, deux types de lignes viennent polluer les classements/aggrégations
    par Code_Analytique :
    - les lignes hors comptes de charges/produits (tiers, banque, TVA...) qui n'ont jamais
      reçu de code analytique et remontent avec un Code_Analytique vide ;
    - les lignes "CHARGES INDIRECTES" / "PRODUITS INDIRECTS" (libellés globaux, pas des ISBN),
      tant qu'elles n'ont pas été réparties sur les titres actifs.

    Si le jeu de données utilise plusieurs familles analytiques en parallèle (cas du grand
    livre réel : EDITION / COMMUNICATION / Types de dépenses), on restreint en plus à la
    famille EDITION pour ignorer les lignes des autres familles qui pourraient elles aussi
    porter un code non vide. Si aucune ligne ne porte littéralement "EDITION" (cas des jeux
    de données de démonstration, qui ne suivent pas cette convention), cette restriction
    supplémentaire est ignorée pour rester compatible.
    """
    if "Code_Analytique" not in df.columns:
        return df.iloc[0:0]
    label_ci = st.session_state.get("labels_indirect", {}).get("charges", "CHARGES INDIRECTES")
    label_pi = st.session_state.get("labels_indirect", {}).get("produits", "PRODUITS INDIRECTS")
    labels_exclus = {label_ci.upper(), label_pi.upper(), ""}
    code = df["Code_Analytique"].astype(str)
    mask = (~code.str.upper().isin(labels_exclus)) & (code.str.strip() != "")
    if "Famille_Analytique" in df.columns and df["Famille_Analytique"].astype(str).str.upper().eq("EDITION").any():
        mask = mask & (df["Famille_Analytique"].astype(str).str.upper() == "EDITION")
    return df[mask]

def _dialog_decorator(title, width="large"):
    """Retourne le décorateur st.dialog si disponible (Streamlit ≥ 1.31), sinon un
    expander déplié en repli pour rester compatible avec une version plus ancienne."""
    if hasattr(st, "dialog"):
        return st.dialog(title, width=width)
    def _wrap(func):
        def _inner(*args, **kwargs):
            with st.expander(f"🪟 {title}", expanded=True):
                return func(*args, **kwargs)
        return _inner
    return _wrap

@_dialog_decorator("📖 Fiche titre", width="large")
def afficher_fiche_titre(isbn_sel, df, params):
    """Fiche détaillée d'un titre (mini SIG) affichée dans une fenêtre modale dédiée."""
    df_t = df[df["Code_Analytique"] == isbn_sel]
    df_v   = df_t[df_t["Compte"].astype(str).str.startswith(tuple(params["ventes"]))]
    df_r   = df_t[df_t["Compte"].astype(str).str.startswith(tuple(params["retours"]))]
    df_rem = df_t[df_t["Compte"].astype(str).str.startswith(tuple(params["remises"]))]
    df_c   = df_t[df_t["Compte"].astype(str).str.startswith(tuple(params["charges"]))]

    # Charges fixes imputées = quote-part de la répartition des charges indirectes sur ce
    # titre précis (compte "CHARGES INDIRECTES REPARTIES", généré si la répartition au nombre
    # de titres actifs a été activée dans ⚙️ Paramétrage analytique). Vaut 0 sinon.
    df_cfi = df_t[df_t["Compte"].astype(str) == "CHARGES INDIRECTES REPARTIES"]

    ventes_ht     = df_v["Crédit"].sum()
    retours_m     = df_r["Débit"].sum()
    remises_m     = df_rem["Débit"].sum()
    ca_net        = ventes_ht - retours_m - remises_m
    charges_v     = df_c["Débit"].sum()
    marge_brute   = ca_net - charges_v
    charges_fixes = df_cfi["Débit"].sum()
    resultat_net  = marge_brute - charges_fixes
    taux_ret      = (retours_m / ventes_ht * 100) if ventes_ht else 0
    taux_rem      = (remises_m / ventes_ht * 100) if ventes_ht else 0

    if resultat_net > 0 and taux_ret < 20:
        signal, bg, fg = "🟢 Titre rentable", "#d1fae5", "#065f46"
    elif resultat_net > 0 and taux_ret < 35:
        signal, bg, fg = "🟡 Rentabilité à surveiller", "#fef3c7", "#92400e"
    else:
        signal, bg, fg = "🔴 Titre en difficulté", "#fee2e2", "#991b1b"

    st.markdown(f"""
    <div style='padding:14px 18px; border-radius:12px; background:{bg}; color:{fg};
                font-weight:600; font-size:16px; margin-bottom:14px'>
        {isbn_sel} — {signal}
    </div>
    """, unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Taux de retour", f"{taux_ret:.1f} %")
    k2.metric("Taux de remise", f"{taux_rem:.1f} %")
    k3.metric("Marge brute", f"{marge_brute:,.0f} €")
    k4.metric("Résultat net (charges fixes incl.)", f"{resultat_net:,.0f} €")
    if charges_fixes == 0 and not st.session_state.get("repartition_active"):
        st.caption("ℹ️ Aucune charge fixe imputée : la répartition des charges indirectes sur les "
                   "titres actifs n'a pas été activée dans ⚙️ Paramétrage analytique.")

    st.markdown("#### Mini SIG — Soldes intermédiaires de gestion")
    rows_sig = [
        ("Ventes HT",                  ventes_ht,      "base"),
        ("− Retours",                  -retours_m,     "deduction"),
        ("− Remises",                  -remises_m,     "deduction"),
        ("= CA net",                   ca_net,         "subtotal"),
        ("− Charges variables",        -charges_v,     "deduction"),
        ("= Marge brute",              marge_brute,    "subtotal"),
        ("− Charges fixes imputées",   -charges_fixes, "deduction"),
        ("= Résultat net du titre",    resultat_net,   "total"),
    ]
    html_rows = ""
    for libelle, montant, style in rows_sig:
        if style == "subtotal":
            row_style = "background:#eef2ff; font-weight:600;"
        elif style == "total":
            color = "#065f46" if montant >= 0 else "#991b1b"
            fill = "#d1fae5" if montant >= 0 else "#fee2e2"
            row_style = f"background:{fill}; font-weight:700; color:{color};"
        elif style == "deduction":
            row_style = "color:#b91c1c;"
        else:
            row_style = "font-weight:500;"
        html_rows += (f"<tr style='{row_style}'>"
                      f"<td style='padding:7px 12px; border-bottom:1px solid #eee'>{libelle}</td>"
                      f"<td style='padding:7px 12px; border-bottom:1px solid #eee; text-align:right'>{montant:,.0f} €</td>"
                      f"</tr>")
    st.markdown(f"""
    <table style='width:100%; border-collapse:collapse; font-size:14px; border-radius:8px; overflow:hidden'>
        {html_rows}
    </table>
    """, unsafe_allow_html=True)

    fig_sig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "total", "relative", "total", "relative", "total"],
        x=[r[0] for r in rows_sig], y=[r[1] for r in rows_sig],
        connector={"line": {"color": "gray", "width": 0.5}},
        decreasing={"marker": {"color": "#EF4444"}},
        increasing={"marker": {"color": "#10B981"}},
        totals={"marker": {"color": "#3B82F6"}}
    ))
    fig_sig.update_layout(height=300, margin=dict(t=10), yaxis_title="€")
    st.plotly_chart(fig_sig, use_container_width=True)

    df_t_evol = df_t.copy()
    df_t_evol["Mois"] = pd.to_datetime(df_t_evol["Date"], errors="coerce").dt.to_period("M").astype(str)
    evol_v = df_t_evol[df_t_evol["Compte"].astype(str).str.startswith(tuple(params["ventes"]))].groupby("Mois")["Crédit"].sum().reset_index()
    evol_r = df_t_evol[df_t_evol["Compte"].astype(str).str.startswith(tuple(params["retours"]))].groupby("Mois")["Débit"].sum().reset_index()
    evol = evol_v.merge(evol_r, on="Mois", how="left").fillna(0)
    evol.columns = ["Mois", "Ventes", "Retours"]
    if not evol.empty:
        st.markdown("#### Évolution mensuelle")
        fig = px.line(evol, x="Mois", y=["Ventes", "Retours"], markers=True, height=260)
        fig.update_layout(margin=dict(t=10), legend_title="")
        st.plotly_chart(fig, use_container_width=True)

    cr_data = {
        "Poste": [r[0] for r in rows_sig],
        "Montant (€)": [r[1] for r in rows_sig]
    }
    df_cr = pd.DataFrame(cr_data)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_cr.to_excel(writer, index=False, sheet_name="Compte_Resultat")
        evol.to_excel(writer, index=False, sheet_name="Evolution_mensuelle")
    buffer.seek(0)
    st.download_button("📥 Exporter la fiche titre (Excel)", buffer,
                        file_name=f"Fiche_titre_{isbn_sel.replace('/', '-')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"export_fiche_{isbn_sel}")

def resoudre_mapping_auteurs(df):
    """Si une famille analytique nommée "AUTEUR" a été mappée dans ⚙️ Paramétrage analytique
    (en plus d'EDITION/COMMUNICATION/Types de dépenses), on en déduit directement la
    correspondance ISBN → auteur depuis la comptabilité elle-même, sans référentiel séparé.
    Retourne un dict {isbn: auteur} (vide si aucune famille de ce type n'est configurée)."""
    noms = st.session_state.get("noms_familles_actives", [])
    codes_cols = st.session_state.get("codes_cols", [])
    if not noms or not codes_cols or df is None or "Code_Analytique" not in df.columns:
        return {}
    idx_auteur = next((i for i, n in enumerate(noms) if "auteur" in n.lower()), None)
    if idx_auteur is None or idx_auteur >= len(codes_cols):
        return {}
    col_auteur = codes_cols[idx_auteur]
    if col_auteur not in df.columns or col_auteur == "Code_Analytique":
        return {}
    sous = df[(df["Code_Analytique"].astype(str).str.strip() != "") & (df[col_auteur].astype(str).str.strip() != "")]
    if sous.empty:
        return {}
    # Auteur le plus fréquent par ISBN, au cas où une incohérence ponctuelle existerait.
    mapping = sous.groupby("Code_Analytique")[col_auteur].agg(lambda s: s.mode().iloc[0] if not s.mode().empty else s.iloc[0])
    return mapping.to_dict()

def calculer_indicateurs_titres(df, params, titres):
    """Calcule, pour chaque titre actif, CA brut/net, charges variables, charges fixes
    imputées (quote-part de répartition des charges indirectes sur ce titre, si activée)
    et résultat net — utilisé pour les repères rapides (titres significatifs / rentables /
    compliqués) de la page Analyse par titre."""
    df_i = df[df["Code_Analytique"].isin(titres)]

    def par_compte(prefix_list, col):
        if not prefix_list:
            return pd.Series(0.0, index=titres)
        mask = df_i["Compte"].astype(str).str.startswith(tuple(prefix_list))
        return df_i[mask].groupby("Code_Analytique")[col].sum().reindex(titres, fill_value=0.0)

    ventes  = par_compte(params["ventes"], "Crédit")
    retours = par_compte(params["retours"], "Débit")
    remises = par_compte(params["remises"], "Débit")
    charges = par_compte(params["charges"], "Débit")
    # Charges fixes imputées = quote-part de la répartition des charges indirectes sur ce
    # titre (compte "CHARGES INDIRECTES REPARTIES", cf. module Paramétrage analytique).
    # Reste à 0 si la répartition n'a pas été activée.
    mask_cfi = df_i["Compte"].astype(str) == "CHARGES INDIRECTES REPARTIES"
    charges_fixes = df_i[mask_cfi].groupby("Code_Analytique")["Débit"].sum().reindex(titres, fill_value=0.0)

    res = pd.DataFrame({"Code_Analytique": titres})
    res["Ventes HT"]  = ventes.values
    res["Retours"]    = retours.values
    res["Remises"]    = remises.values
    res["CA net"]      = res["Ventes HT"] - res["Retours"] - res["Remises"]
    res["Charges variables"] = charges.values
    res["Marge brute"] = res["CA net"] - res["Charges variables"]
    res["Charges fixes imputées"] = charges_fixes.values
    res["Résultat net"] = res["Marge brute"] - res["Charges fixes imputées"]
    res["Taux retour (%)"] = np.where(res["Ventes HT"] != 0, res["Retours"] / res["Ventes HT"] * 100, 0)

    def _signal(row):
        if row["Résultat net"] > 0 and row["Taux retour (%)"] < 20:
            return "🟢"
        elif row["Résultat net"] > 0 and row["Taux retour (%)"] < 35:
            return "🟡"
        return "🔴"
    res["Signal"] = res.apply(_signal, axis=1)
    return res

def build_data_summary():
    """Construit un résumé textuel du pivot pour l'envoyer à Claude."""
    if "df_pivot" not in st.session_state:
        return None
    df = st.session_state["df_pivot"].copy()
    params = st.session_state.get("param_comptes", {})
    ventes = params.get("ventes", ["701"])
    retours = params.get("retours", ["709"])
    df_v = df[df["Compte"].astype(str).str.startswith(tuple(ventes))]
    df_r = df[df["Compte"].astype(str).str.startswith(tuple(retours))]
    ca_brut = df_v["Crédit"].sum()
    total_retours = df_r["Débit"].sum()
    ca_net = ca_brut - total_retours
    taux_retour = (total_retours / ca_brut * 100) if ca_brut else 0
    df_isbn = filtrer_isbn_reels(df)
    top = df_isbn.groupby("Code_Analytique", as_index=False).agg({"Crédit": "sum", "Débit": "sum"})
    top["Résultat"] = top["Crédit"] - top["Débit"]
    top5 = top.nlargest(5, "Résultat")[["Code_Analytique", "Résultat"]].to_dict(orient="records")
    bot5 = top.nsmallest(5, "Résultat")[["Code_Analytique", "Résultat"]].to_dict(orient="records")
    summary = f"""
DONNÉES ANALYTIQUES — MAISON D'ÉDITION INDÉPENDANTE
====================================================
CA brut : {ca_brut:,.0f} €
Total retours : {total_retours:,.0f} €
CA net : {ca_net:,.0f} €
Taux de retour : {taux_retour:.1f} %
Nombre de titres (ISBN) : {top['Code_Analytique'].nunique()}

Top 5 titres les plus rentables :
{json.dumps(top5, ensure_ascii=False, indent=2)}

Top 5 titres les moins rentables :
{json.dumps(bot5, ensure_ascii=False, indent=2)}
"""
    return summary

SYSTEM_PROMPT = """Tu es un expert-comptable spécialisé dans l'accompagnement des maisons d'édition indépendantes françaises.

Tu connais parfaitement :
- Les normes comptables françaises (PCG) appliquées à l'édition
- Les spécificités du secteur : droits d'auteurs, retours éditeurs, provisions, distributeurs
- Les ratios clés : taux de retour, taux de remise, marge brute éditeur, couverture des droits
- Les logiciels comptables utilisés en édition (CEGID, Sage, EBP)

Tu assistes l'utilisateur dans l'analyse de ses données comptables analytiques via cet outil Streamlit dédié aux éditeurs indépendants.

L'outil comporte les modules suivants : Import des données, Paramétrage analytique, Tableau de bord éditorial, Analyse par titre, Trésorerie prévisionnelle, Droits d'auteurs, Retours & Remises, Synthèse financière.

Réponds toujours en français, de façon concise et orientée action. Si tu détectes une anomalie dans les données, signale-la clairement."""

def generate_qr():
    qr = qrcode.QRCode(version=1, box_size=6, border=3)
    qr.add_data(APP_URL)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a1a2e", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def load_demo_data():
    """Génère un jeu de données de démonstration réaliste pour une maison d'édition."""
    np.random.seed(42)
    isbns = [f"978-2-{i:04d}-{j:04d}-{k}" for i, j, k in [
        (1234, 1001, 1), (1234, 1002, 8), (1234, 1003, 5), (1234, 1004, 2),
        (1234, 1005, 9), (1234, 1006, 6), (1234, 1007, 3), (1234, 1008, 0)
    ]]
    titres = ["Le Dernier Manuscrit", "Mémoires du Vent", "Sous les Toits de Paris",
              "L'Héritage Silencieux", "Chroniques du Nord", "La Lumière d'Août",
              "Terres Inconnues", "Les Mots du Soir"]
    familles = ["Roman", "Roman", "Essai", "Roman", "Polar", "Essai", "Jeunesse", "Poésie"]
    rows = []
    dates = pd.date_range("2024-01-01", "2024-12-31", freq="MS")
    for date in dates:
        for isbn, titre, famille in zip(isbns, titres, familles):
            ventes = np.random.randint(500, 8000)
            rows.append({"Compte": "701100", "Débit": 0, "Crédit": round(ventes, 2),
                         "Code_Analytique": isbn, "Famille_Analytique": famille,
                         "Libellé": f"Ventes {titre}", "Date": date})
            if np.random.random() < 0.6:
                retours = round(ventes * np.random.uniform(0.05, 0.30), 2)
                rows.append({"Compte": "709100", "Débit": retours, "Crédit": 0,
                             "Code_Analytique": isbn, "Famille_Analytique": famille,
                             "Libellé": f"Retours {titre}", "Date": date})
            charges = round(ventes * np.random.uniform(0.15, 0.40), 2)
            rows.append({"Compte": "607100", "Débit": charges, "Crédit": 0,
                         "Code_Analytique": isbn, "Famille_Analytique": famille,
                         "Libellé": f"Charges {titre}", "Date": date})
        # Charges fixes mensuelles
        for compte, libelle, montant in [
            ("615000", "Loyer", 1200), ("641000", "Salaires", 4500),
            ("512000", "Banque", 0), ("512000", "Recettes banque", 0)
        ]:
            if compte == "512000":
                rows.append({"Compte": compte, "Débit": 0, "Crédit": np.random.randint(8000, 15000),
                             "Code_Analytique": "", "Famille_Analytique": "",
                             "Libellé": "Recettes banque", "Date": date})
            else:
                rows.append({"Compte": compte, "Débit": montant, "Crédit": 0,
                             "Code_Analytique": "", "Famille_Analytique": "",
                             "Libellé": libelle, "Date": date})
    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    return df

# =====================
# ACCUEIL
# =====================
if page == "🏠 Accueil":
    col_main, col_qr = st.columns([3, 1])
    with col_main:
        st.title("📚 Outil d'accompagnement éditorial")
        st.markdown(f"*Bienvenue, **{st.session_state['name']}** — Maisons d'édition indépendantes*")
        st.divider()

        # Stepper visuel
        st.markdown("### Comment démarrer ?")
        col1, col2, col3, col4 = st.columns(4)
        for col, num, icon, titre, desc in [
            (col1, "1", "📂", "Importer", "Chargez votre export comptable Excel"),
            (col2, "2", "⚙️", "Paramétrer", "Mappez vos colonnes et comptes"),
            (col3, "3", "📈", "Analyser", "Explorez vos tableaux de bord"),
            (col4, "4", "🤖", "Interroger", "Posez vos questions à l'IA"),
        ]:
            with col:
                st.markdown(f"""
                <div style='text-align:center; padding:16px; background:#f8f9fa; border-radius:12px; border:1px solid #e0e0e0'>
                    <div style='font-size:28px'>{icon}</div>
                    <div style='font-size:11px; color:#888; margin:4px 0'>Étape {num}</div>
                    <div style='font-weight:600; font-size:14px'>{titre}</div>
                    <div style='font-size:12px; color:#666; margin-top:4px'>{desc}</div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()
        st.markdown("### Fonctionnalités disponibles")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""
- 📂 **Import des données** — fichier Excel comptable analytique
- ⚙️ **Paramétrage analytique** — mapping colonnes, contrôles et répartition
- 📈 **Tableau de bord éditorial** — KPIs, tendances, répartitions
- 📖 **Analyse par titre** — compte de résultat par ISBN
            """)
        with c2:
            st.markdown("""
- 💰 **Trésorerie prévisionnelle** — projection multi-scénarios
- ✍️ **Droits d'auteurs** — calcul par paliers, suivi avances
- 📦 **Retours & Remises** — taux, tendances, alertes
- 🤖 **Assistant IA** — analyse et conseils en langage naturel
            """)
    with col_qr:
        st.markdown("### Accès mobile")
        st.image(generate_qr(), width=180)
        st.caption("Scannez pour ouvrir l'app sur votre téléphone")
        st.markdown(f"[🔗 Lien direct]({APP_URL})")
    st.stop()

# =====================
# IMPORT DES DONNÉES
# =====================
elif page == "📂 Import des données":
    st.header("📂 Import des données analytiques")
    tab1, tab2 = st.tabs(["📁 Importer mon fichier", "🎭 Données de démonstration"])

    with tab1:
        st.info("Importez votre export comptable analytique au format Excel (.xlsx).")
        fichier = st.file_uploader("Sélectionnez votre fichier Excel", type=["xlsx"])
        if fichier:
            try:
                df = pd.read_excel(fichier, header=0)
                df.columns = df.columns.str.strip()
                st.session_state["df_comptables"] = df
                st.success(f"✅ Fichier chargé — {df.shape[0]} lignes, {df.shape[1]} colonnes")
                st.write("**Colonnes détectées :**", list(df.columns))
                # Validation rapide — on ne signale que les colonnes structurelles évidentes
                # (numéro de compte, débit, crédit, date). Les colonnes analytiques par famille
                # (Famille/Catégorie/Code analytique : EDITION, COMMUNICATION, Types de dépenses...)
                # sont normalement vides sur la majorité des lignes : chaque écriture n'appartient
                # qu'à UNE seule famille à la fois, donc les colonnes des 2 autres familles sont
                # vides pour cette ligne. Les remonter ici comme "valeurs manquantes" est un faux
                # positif systématique — le vrai contrôle de cohérence analytique se fait plus loin,
                # dans ⚙️ Paramétrage analytique, où le mapping multi-familles est connu.
                colonnes_structurelles = [c for c in df.columns if any(
                    mot in c.lower() for mot in ["compte", "débit", "debit", "crédit", "credit", "date"]
                ) and "analytique" not in c.lower() and "catégorie" not in c.lower() and "categorie" not in c.lower()]
                if colonnes_structurelles:
                    missing = df[colonnes_structurelles].isnull().sum()
                    missing = missing[missing > 0]
                    if not missing.empty:
                        st.warning(f"⚠️ Valeurs manquantes sur des colonnes structurelles : {missing.to_dict()}")
                st.caption("ℹ️ Les colonnes analytiques par famille (EDITION, COMMUNICATION, Types de dépenses...) "
                           "sont normalement vides sur une bonne partie des lignes — chaque écriture n'appartient "
                           "qu'à une seule famille à la fois. Ce n'est pas signalé ici ; la cohérence analytique "
                           "réelle est vérifiée dans **⚙️ Paramétrage analytique**.")
                st.dataframe(df.head(10))
                st.info("➡️ Passez maintenant dans **⚙️ Paramétrage analytique** pour configurer les colonnes.")
            except Exception as e:
                st.error(f"❌ Erreur : {e}")
        else:
            st.warning("Aucun fichier sélectionné.")

    with tab2:
        st.info("Chargez un jeu de données fictif réaliste pour explorer tous les modules sans fichier réel.")
        if st.button("🎭 Charger les données de démonstration", type="primary"):
            df_demo = load_demo_data()
            st.session_state["df_comptables"] = df_demo
            st.session_state["df_source_mappe"] = df_demo
            # Générer automatiquement le pivot avec paramètres par défaut
            pivot = df_demo.groupby(
                ["Compte", "Famille_Analytique", "Code_Analytique", "Date", "Libellé"],
                as_index=False
            ).agg({"Débit": "sum", "Crédit": "sum"})
            st.session_state["df_pivot"] = pivot
            st.session_state["df_pivot_brut"] = pivot.copy()
            st.session_state["param_comptes"] = {
                "ventes": ["701"], "retours": ["709"],
                "remises": ["7091"], "charges": ["6"],
                "charges_imputees": "Oui"
            }
            # Clés nécessaires au module Paramétrage (contrôles + répartition) pour rester
            # cohérent même quand on saute directement le mapping via les données de démo.
            st.session_state["labels_indirect"] = {"charges": "CHARGES INDIRECTES", "produits": "PRODUITS INDIRECTS"}
            st.session_state["familles_cols"] = ["Famille_Analytique"]
            st.session_state["codes_cols"] = ["Code_Analytique"]
            st.session_state["noms_familles_actives"] = ["EDITION"]
            st.session_state["repartition_active"] = False
            st.success("✅ Données de démonstration chargées — pivot analytique généré automatiquement !")
            st.dataframe(df_demo.head(15))
            st.info("➡️ Tous les modules sont maintenant accessibles. Commencez par **📈 Tableau de bord éditorial** !")

# =====================
# PARAMÉTRAGE ANALYTIQUE
# =====================
elif page == "⚙️ Paramétrage analytique":
    st.header("⚙️ Paramétrage analytique")
    if "df_comptables" not in st.session_state:
        st.warning("⚠️ Importez d'abord vos données via **📂 Import des données**.")
        st.stop()

    df = st.session_state["df_comptables"].copy()
    st.info("Associez les colonnes de votre fichier aux champs attendus, puis configurez vos comptes comptables.")

    columns = list(df.columns)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Mapping des colonnes de base")
        compte_col  = st.selectbox("Colonne Compte", columns)
        debit_col   = st.selectbox("Colonne Débit", columns)
        credit_col  = st.selectbox("Colonne Crédit", columns)
        date_col    = st.selectbox("Colonne Date", columns)
        libelle_col = st.selectbox("Libellé (optionnel)", [""] + columns)
        journal_col = st.selectbox(
            "Code journal (optionnel)", [""] + columns,
            help="Recommandé pour le module Trésorerie : permet d'exclure les écritures de report "
                 "à nouveau (reprise des soldes d'ouverture, souvent codées « AN ») des flux de "
                 "trésorerie reconstitués, afin de ne pas les compter comme des mouvements de la période."
        )
    with col2:
        st.subheader("Comptes comptables")
        ventes_comptes  = st.text_input("Comptes ventes", value="701")
        retours_comptes = st.text_input("Comptes retours", value="709")
        remises_comptes = st.text_input("Comptes remises", value="7091")
        charges_comptes = st.text_input("Comptes charges", value="6")
        charges_imputees = st.radio("Charges déjà imputées par section ?", ["Oui", "Non"])

    st.subheader("Familles analytiques")
    st.caption("Votre export peut contenir plusieurs familles analytiques en parallèle "
               "(ex. EDITION pour les ISBN, COMMUNICATION pour la création graphique, "
               "la famille native « Types de dépenses / revenus » de votre logiciel, et une "
               "éventuelle famille AUTEUR). "
               "Mappez ici chaque paire de colonnes Famille / Valeur analytique. La 1ère famille "
               "mappée sert de référence pour le pivot ISBN (EDITION) ; les suivantes ne servent "
               "qu'aux contrôles de cohérence, pour qu'une ligne déjà affectée dans une autre "
               "famille (ex. COMMUNICATION) ne soit pas signalée à tort comme non affectée.")
    st.info("""
    ✍️ **Famille AUTEUR (recommandé) :** si votre logiciel comptable le permet, créez une 4e famille
    analytique nommée **AUTEUR**, taguée sur les mêmes lignes que la famille EDITION (chaque écriture
    de droits d'auteur porte alors à la fois son ISBN et son auteur). Une fois mappée ici, le module
    **✍️ Droits d'auteurs → 📒 Réel (comptabilisé)** détecte automatiquement la correspondance ISBN → auteur
    directement depuis la comptabilité, sans référentiel à ressaisir séparément.
    """)
    st.warning("""
    ⚠️ **Attention à ne pas confondre deux colonnes qui se ressemblent, pour chaque famille :**
    - **« Catégorie : \\<famille\\> »** → contient la vraie valeur affectée (ex. l'ISBN, "CHARGES INDIRECTES"…).
      **C'est celle-ci qu'il faut choisir.**
    - **« Code analytique : \\<famille\\> »** → identifiant technique interne de votre logiciel,
      généralement **vide sur toutes les lignes**. La sélectionner par erreur fait remonter énormément
      de faux positifs au contrôle de cohérence.
    """)

    nb_familles = st.number_input("Nombre de familles analytiques à mapper", min_value=1, max_value=4, value=1, step=1)
    familles_mapping = []
    noms_suggestion = ["EDITION", "COMMUNICATION", "Types de dépenses / revenus", "AUTEUR"]
    for i in range(int(nb_familles)):
        fc1, fc2, fc3 = st.columns([1, 1, 1])
        with fc1:
            nom_famille = st.text_input(
                f"Nom de la famille {i+1}",
                value=noms_suggestion[i] if i < len(noms_suggestion) else "",
                key=f"nom_famille_{i}"
            )
        with fc2:
            famille_col_i = st.selectbox(f"Colonne « Famille de catégories » {i+1} (optionnel)", [""] + columns, key=f"famille_col_{i}")
        with fc3:
            code_col_i = st.selectbox(
                f"Colonne « Catégorie » (valeur analytique) {i+1} (optionnel)", [""] + columns, key=f"code_col_{i}",
                help="Choisissez la colonne « Catégorie : <famille> », PAS « Code analytique : <famille> » (souvent vide)."
            )
        familles_mapping.append({"nom": nom_famille, "famille_col": famille_col_i, "code_col": code_col_i})

    st.subheader("Libellés des lignes indirectes")
    col_li1, col_li2 = st.columns(2)
    label_charges_indirectes = col_li1.text_input("Libellé des charges indirectes", value="CHARGES INDIRECTES")
    label_produits_indirects = col_li2.text_input("Libellé des produits indirects", value="PRODUITS INDIRECTS")

    # Aperçu avant validation
    st.subheader("Aperçu du mapping")
    apercu = df.head(5)[[compte_col, debit_col, credit_col, date_col]].copy()
    apercu.columns = ["Compte", "Débit", "Crédit", "Date"]
    st.dataframe(apercu)

    if st.button("⚙️ Générer le socle analytique", type="primary"):
        mapping = {compte_col: "Compte", debit_col: "Débit", credit_col: "Crédit", date_col: "Date"}
        if libelle_col:
            mapping[libelle_col] = "Libellé"
        if journal_col:
            mapping[journal_col] = "Journal"

        # Chaque famille mappée génère une paire de colonnes Famille_Analytique[_i] / Code_Analytique[_i].
        # La famille n°1 (sans suffixe) reste la référence utilisée par les modules ISBN (EDITION).
        familles_cols, codes_cols, noms_familles_actives = [], [], []
        for i, fam in enumerate(familles_mapping):
            suffix = "" if i == 0 else f"_{i+1}"
            col_famille_out = f"Famille_Analytique{suffix}"
            col_code_out = f"Code_Analytique{suffix}"
            if fam["famille_col"]:
                mapping[fam["famille_col"]] = col_famille_out
            if fam["code_col"]:
                mapping[fam["code_col"]] = col_code_out
            familles_cols.append(col_famille_out)
            codes_cols.append(col_code_out)
            noms_familles_actives.append(fam["nom"] or f"Famille {i+1}")

        df.rename(columns=mapping, inplace=True)
        for col in familles_cols + codes_cols + ["Libellé", "Journal"]:
            if col not in df.columns:
                df[col] = ""
            else:
                df[col] = df[col].fillna("")
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Débit"] = pd.to_numeric(df["Débit"], errors="coerce").fillna(0)
        df["Crédit"] = pd.to_numeric(df["Crédit"], errors="coerce").fillna(0)
        df["Compte"] = df["Compte"].astype(str).str.strip()

        st.session_state["df_source_mappe"] = df
        st.session_state["labels_indirect"] = {
            "charges": label_charges_indirectes.strip(),
            "produits": label_produits_indirects.strip(),
        }
        st.session_state["familles_cols"] = familles_cols
        st.session_state["codes_cols"] = codes_cols
        st.session_state["noms_familles_actives"] = noms_familles_actives

        # ================================================
        # CONTRÔLES 1 ET 2 (cf. mémoire — 3 contrôles ; le 3e est plus bas, hors du bouton)
        # ================================================
        st.subheader("🔎 Contrôles de cohérence")
        alerte_globale = False

        # --- Contrôle 1 : contrôle de l'import ---
        champs_attendus = ["Compte", "Débit", "Crédit", "Date"]
        champs_manquants = [c for c in champs_attendus if c not in df.columns]
        lignes_compte_vide = df["Compte"].isna().sum() + (df["Compte"] == "").sum()
        lignes_date_invalide = df["Date"].isna().sum()

        if champs_manquants or lignes_compte_vide > 0 or lignes_date_invalide > 0:
            alerte_globale = True
            st.error("❌ Contrôle de l'import : anomalies détectées")
            if champs_manquants:
                st.write(f"- Champs manquants dans l'export : {champs_manquants}")
            if lignes_compte_vide > 0:
                st.write(f"- {lignes_compte_vide} ligne(s) sans numéro de compte")
            if lignes_date_invalide > 0:
                st.write(f"- {lignes_date_invalide} ligne(s) avec une date invalide")
        else:
            st.success("✅ Contrôle de l'import : tous les champs attendus sont présents et renseignés.")

        # --- Contrôle 2 : cohérence charges générales / charges analytiques ---
        # Une ligne compte comme affectée dès qu'elle porte un code dans AU MOINS UNE des
        # familles mappées (EDITION, COMMUNICATION, Types de dépenses...).
        df_pl = df[df["Compte"].str.startswith(("6", "7"))].copy()
        has_any_code = pd.Series(False, index=df_pl.index)
        for c in codes_cols:
            has_any_code = has_any_code | (df_pl[c].astype(str).str.strip() != "")
        df_pl_non_code = df_pl[~has_any_code]
        total_general_pl = (df_pl["Crédit"] - df_pl["Débit"]).sum()
        total_analytique_pl = (df_pl[has_any_code]["Crédit"] - df_pl[has_any_code]["Débit"]).sum()
        ecart_pl = round(total_general_pl - total_analytique_pl, 2)

        if len(df_pl_non_code) > 0 or abs(ecart_pl) > 0.01:
            alerte_globale = True
            st.error("❌ Contrôle de cohérence charges/produits analytiques : anomalies détectées")
            st.write(f"- {len(df_pl_non_code)} ligne(s) de charge ou de produit sans code analytique dans "
                     f"aucune des familles mappées ({', '.join(noms_familles_actives)}) "
                     f"(montant net non affecté : {round((df_pl_non_code['Crédit'] - df_pl_non_code['Débit']).sum(), 2):,.2f} €)")
            st.write(f"- Écart total général / total analytique : {ecart_pl:,.2f} €")
            st.dataframe(df_pl_non_code[["Compte", "Libellé", "Date", "Débit", "Crédit"]].head(50))
        else:
            st.success(f"✅ Contrôle de cohérence charges/produits analytiques : toutes les lignes 6xx/7xx sont "
                       f"affectées (toutes familles confondues : {', '.join(noms_familles_actives)}), "
                       f"total général = total analytique.")

        if alerte_globale:
            st.warning("⚠️ Des anomalies ont été détectées ci-dessus (contrôles 1 et 2). Vous pouvez tout de "
                       "même générer le socle, mais il est recommandé de corriger l'affectation analytique "
                       "en amont avant de valider le rapport de pilotage.")
        else:
            st.success("✅ Contrôles 1 et 2 passés avec succès.")
        st.caption("Le contrôle 3 (cohérence des volumes BLDD) et la répartition des charges/produits "
                   "indirects sont disponibles juste en dessous, une fois le socle généré ci-dessous — "
                   "ils restent accessibles sans qu'il soit nécessaire de re-générer le socle.")

        # ================================================
        # GÉNÉRATION DU PIVOT
        # ================================================
        group_cols = ["Compte"] + familles_cols + codes_cols + ["Date"]
        if "Libellé" in df.columns:
            group_cols.append("Libellé")
        if "Journal" in df.columns:
            group_cols.append("Journal")
        pivot = df.groupby(group_cols, as_index=False).agg({"Débit": "sum", "Crédit": "sum"})

        st.session_state["df_pivot"] = pivot
        st.session_state["df_pivot_brut"] = pivot.copy()
        st.session_state["param_comptes"] = {
            "ventes":  [c.strip() for c in ventes_comptes.split(",")],
            "retours": [c.strip() for c in retours_comptes.split(",")],
            "remises": [c.strip() for c in remises_comptes.split(",")],
            "charges": [c.strip() for c in charges_comptes.split(",")],
            "charges_imputees": charges_imputees
        }

        # Export configuration JSON
        config = {
            "mapping": mapping,
            "param_comptes": st.session_state["param_comptes"],
            "familles_cols": familles_cols,
            "codes_cols": codes_cols,
            "noms_familles_actives": noms_familles_actives,
        }
        st.success("✅ Socle analytique généré avec succès !")
        st.download_button(
            "💾 Sauvegarder la configuration (JSON)",
            data=json.dumps(config, ensure_ascii=False, indent=2),
            file_name="config_edition.json", mime="application/json"
        )
        st.dataframe(pivot.head(15))

    # ================================================
    # CONTRÔLE 3 : cohérence des volumes BLDD
    # ================================================
    # Placé HORS du bloc "if st.button(...)" : dans Streamlit, tout widget interactif
    # (uploader, radio...) déclenche un nouveau passage du script où st.button() redevient
    # False. S'il était imbriqué dans le bouton, interagir avec lui faisait disparaître tout
    # le socle généré. Ce bloc lit donc les données depuis st.session_state et reste actif
    # tant que le socle a été généré au moins une fois.
    if "df_source_mappe" in st.session_state:
        st.subheader("🔎 Contrôle de cohérence des volumes BLDD")
        st.caption("Redéposez le relevé BLDD du mois pour vérifier que les écritures de CA, remises et commissions "
                   "générées dans l'export analytique correspondent bien au relevé du diffuseur.")
        fichier_bldd = st.file_uploader("Relevé BLDD (optionnel)", type=["xlsx", "csv"], key="controle_bldd")

        if fichier_bldd:
            try:
                df_source = st.session_state["df_source_mappe"]
                param_ctrl = st.session_state["param_comptes"]
                if fichier_bldd.name.endswith(".csv"):
                    df_bldd = pd.read_csv(fichier_bldd)
                else:
                    df_bldd = pd.read_excel(fichier_bldd)
                df_bldd.columns = df_bldd.columns.str.strip()
                total_bldd = 0
                if "Débit" in df_bldd.columns and "Crédit" in df_bldd.columns:
                    total_bldd = (df_bldd["Crédit"] - df_bldd["Débit"]).sum()
                comptes_ctrl = tuple(param_ctrl["ventes"] + param_ctrl["retours"] + param_ctrl["remises"])
                mask_ctrl = df_source["Compte"].astype(str).str.startswith(comptes_ctrl)
                total_export_bldd = (df_source[mask_ctrl]["Crédit"] - df_source[mask_ctrl]["Débit"]).sum()
                ecart_bldd = round(total_bldd - total_export_bldd, 2)
                if abs(ecart_bldd) > 0.01:
                    st.error(f"❌ Écart entre le relevé BLDD ({total_bldd:,.2f} €) et l'export analytique "
                             f"({total_export_bldd:,.2f} €) : {ecart_bldd:,.2f} €")
                else:
                    st.success(f"✅ Le relevé BLDD ({total_bldd:,.2f} €) correspond à l'export analytique.")
            except Exception as e:
                st.warning(f"Impossible de lire le relevé BLDD : {e}")
        else:
            st.info("Aucun relevé BLDD déposé — ce contrôle sera ignoré pour cette génération.")

    # ================================================
    # RÉPARTITION DES CHARGES ET PRODUITS INDIRECTS
    # ================================================
    # Également hors du bouton, pour la même raison : le radio ci-dessous doit rester
    # interactif sans faire disparaître le socle déjà généré.
    if "df_pivot_brut" in st.session_state:
        st.subheader("📐 Répartition des charges et produits indirects")
        st.markdown("""
        Les charges de structure et certains produits (subventions, prestations non identifiables)
        n'ont pas pu être affectés à un titre en particulier et ont été codés comme
        **charges/produits indirects**. Conformément à la méthodologie retenue, il est proposé
        de les répartir au **nombre de titres actifs** plutôt qu'au chiffre d'affaires, afin de ne pas
        masquer les titres non rentables derrière les titres porteurs.
        """)

        pivot_brut = st.session_state["df_pivot_brut"]
        label_ci = st.session_state["labels_indirect"]["charges"]
        label_pi = st.session_state["labels_indirect"]["produits"]

        masque_ci = pivot_brut["Code_Analytique"].astype(str).str.strip() == label_ci
        masque_pi = pivot_brut["Code_Analytique"].astype(str).str.strip() == label_pi
        total_charges_indirectes = (pivot_brut[masque_ci]["Débit"] - pivot_brut[masque_ci]["Crédit"]).sum()
        total_produits_indirects = (pivot_brut[masque_pi]["Crédit"] - pivot_brut[masque_pi]["Débit"]).sum()

        titres_actifs = sorted(filtrer_isbn_reels(pivot_brut)["Code_Analytique"].astype(str).unique().tolist())
        nb_titres_actifs = len(titres_actifs)

        col_r1, col_r2, col_r3 = st.columns(3)
        col_r1.metric("Charges indirectes détectées", f"{total_charges_indirectes:,.2f} €")
        col_r2.metric("Produits indirects détectés", f"{total_produits_indirects:,.2f} €")
        col_r3.metric("Nombre de titres actifs", nb_titres_actifs)

        repartir = st.radio(
            "Souhaitez-vous répartir les charges et produits indirects sur les titres actifs ?",
            ["Non, je garde une ligne 'indirecte' globale", "Oui, répartir sur les titres actifs"],
            index=0,
            key="repartir_radio"
        )

        st.selectbox(
            "Clé de répartition (inducteur)",
            ["Nombre de titres actifs"],
            help="Seul l'inducteur 'nombre de titres actifs' est disponible pour le moment, "
                 "conformément à la méthodologie retenue (le CA n'est volontairement pas proposé "
                 "car il compenserait les titres non rentables par les titres porteurs)."
        )

        if repartir.startswith("Oui"):
            if nb_titres_actifs == 0:
                st.error("❌ Aucun titre actif détecté — répartition impossible.")
            else:
                pivot_reparti = pivot_brut[~masque_ci & ~masque_pi].copy()
                nouvelles_lignes = []

                if total_charges_indirectes != 0:
                    part_charge = round(total_charges_indirectes / nb_titres_actifs, 2)
                    for isbn in titres_actifs:
                        nouvelles_lignes.append({
                            "Compte": "CHARGES INDIRECTES REPARTIES",
                            "Famille_Analytique": "EDITION",
                            "Code_Analytique": isbn,
                            "Date": pd.NaT,
                            "Libellé": f"Quote-part charges indirectes ({nb_titres_actifs} titres actifs)",
                            "Débit": part_charge,
                            "Crédit": 0,
                        })

                if total_produits_indirects != 0:
                    part_produit = round(total_produits_indirects / nb_titres_actifs, 2)
                    for isbn in titres_actifs:
                        nouvelles_lignes.append({
                            "Compte": "PRODUITS INDIRECTS REPARTIS",
                            "Famille_Analytique": "EDITION",
                            "Code_Analytique": isbn,
                            "Date": pd.NaT,
                            "Libellé": f"Quote-part produits indirects ({nb_titres_actifs} titres actifs)",
                            "Débit": 0,
                            "Crédit": part_produit,
                        })

                if nouvelles_lignes:
                    df_nouvelles = pd.DataFrame(nouvelles_lignes)
                    for c in pivot_reparti.columns:
                        if c not in df_nouvelles.columns:
                            df_nouvelles[c] = None
                    pivot_reparti = pd.concat([pivot_reparti, df_nouvelles[pivot_reparti.columns]], ignore_index=True)

                st.session_state["df_pivot"] = pivot_reparti
                st.session_state["repartition_active"] = True
                st.session_state["repartition_detail"] = {
                    "nb_titres_actifs": nb_titres_actifs,
                    "part_charge": round(total_charges_indirectes / nb_titres_actifs, 2) if nb_titres_actifs else 0,
                    "part_produit": round(total_produits_indirects / nb_titres_actifs, 2) if nb_titres_actifs else 0,
                }

                st.success(
                    f"✅ Répartition effectuée sur {nb_titres_actifs} titres actifs : "
                    f"{round(total_charges_indirectes / nb_titres_actifs, 2):,.2f} € de charges et "
                    f"{round(total_produits_indirects / nb_titres_actifs, 2):,.2f} € de produits par titre."
                )
                st.dataframe(pivot_reparti[
                    pivot_reparti["Compte"].isin(["CHARGES INDIRECTES REPARTIES", "PRODUITS INDIRECTS REPARTIS"])
                ].head(20))
        else:
            st.session_state["df_pivot"] = pivot_brut
            st.session_state["repartition_active"] = False
            st.info("Les charges et produits indirects restent regroupés sur une ligne globale "
                    "(non répartie sur les titres). Vous pourrez revenir sur ce choix à tout moment ci-dessus, "
                    "sans avoir besoin de régénérer le socle.")

# =====================
# TABLEAU DE BORD ÉDITORIAL
# =====================
elif page == "📈 Tableau de bord éditorial":
    st.header("📈 Tableau de bord éditorial")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générez d'abord le socle via **⚙️ Paramétrage analytique**.")
        st.stop()

    df = st.session_state["df_pivot"].copy()
    params = st.session_state["param_comptes"]
    if st.session_state.get("repartition_active"):
        st.caption("ℹ️ Les charges/produits indirects ont été répartis sur les titres actifs.")

    # Filtres temporels
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    df["Mois"] = df["Date"].dt.to_period("M").astype(str)
    years = sorted(df["Date"].dt.year.dropna().unique().tolist())
    col_f1, col_f2 = st.columns([1, 3])
    with col_f1:
        annee = st.selectbox("Année", ["Toutes"] + [str(y) for y in years])
    if annee != "Toutes":
        df = df[df["Date"].dt.year == int(annee)]

    df_v = df[df["Compte"].astype(str).str.startswith(tuple(params["ventes"]))]
    df_r = df[df["Compte"].astype(str).str.startswith(tuple(params["retours"]))]
    df_rem = df[df["Compte"].astype(str).str.startswith(tuple(params["remises"]))]
    df_c = df[df["Compte"].astype(str).str.startswith(tuple(params["charges"]))]

    ca_brut       = df_v["Crédit"].sum()
    total_retours = df_r["Débit"].sum()
    total_remises = df_rem["Débit"].sum()
    ca_net        = ca_brut - total_retours - total_remises
    charges_tot   = df_c["Débit"].sum()
    resultat      = ca_net - charges_tot
    taux_retour   = (total_retours / ca_brut * 100) if ca_brut else 0

    # KPIs
    st.subheader("Indicateurs clés")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("CA brut", f"{ca_brut:,.0f} €")
    k2.metric("CA net", f"{ca_net:,.0f} €", delta=f"-{total_retours+total_remises:,.0f} €")
    k3.metric("Taux de retour", f"{taux_retour:.1f} %",
              delta_color="inverse", delta="⚠️ Élevé" if taux_retour > 25 else "✅ Normal")
    k4.metric("Charges totales", f"{charges_tot:,.0f} €")
    k5.metric("Résultat net", f"{resultat:,.0f} €",
              delta_color="normal" if resultat >= 0 else "inverse")

    st.divider()
    col_g1, col_g2 = st.columns(2)

    # Évolution mensuelle CA
    with col_g1:
        st.subheader("Évolution mensuelle")
        trend_v = df_v.groupby("Mois")["Crédit"].sum().reset_index().rename(columns={"Crédit": "CA brut"})
        trend_r = df_r.groupby("Mois")["Débit"].sum().reset_index().rename(columns={"Débit": "Retours"})
        trend = trend_v.merge(trend_r, on="Mois", how="left").fillna(0)
        trend["CA net"] = trend["CA brut"] - trend["Retours"]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=trend["Mois"], y=trend["CA brut"], name="CA brut", marker_color="#3B82F6"))
        fig.add_trace(go.Bar(x=trend["Mois"], y=trend["Retours"], name="Retours", marker_color="#EF4444"))
        fig.add_trace(go.Scatter(x=trend["Mois"], y=trend["CA net"], name="CA net",
                                  mode="lines+markers", line=dict(color="#10B981", width=2)))
        fig.update_layout(barmode="overlay", legend=dict(orientation="h"), height=350,
                          xaxis_title="", yaxis_title="€", margin=dict(t=20))
        st.plotly_chart(fig, use_container_width=True)

    # Répartition par famille
    with col_g2:
        st.subheader("Répartition par famille")
        if df_v["Famille_Analytique"].str.strip().any():
            fam = df_v.groupby("Famille_Analytique")["Crédit"].sum().reset_index()
            fam = fam[fam["Famille_Analytique"].str.strip() != ""]
            if not fam.empty:
                fig2 = px.pie(fam, values="Crédit", names="Famille_Analytique",
                               hole=0.4, height=350)
                fig2.update_layout(margin=dict(t=20))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Aucune famille analytique renseignée.")
        else:
            st.info("Aucune famille analytique renseignée.")

    # Top 10 ISBN
    st.subheader("Top 10 titres par résultat net")
    # On ne classe que les vraies lignes ISBN (famille EDITION, hors code vide et hors
    # libellés indirects globaux) — sinon une ligne "CHARGES INDIRECTES" ou une ligne hors
    # comptes de charges/produits pouvait remonter en tête du classement.
    df_isbn_tb = filtrer_isbn_reels(df)
    top = df_isbn_tb.groupby("Code_Analytique", as_index=False).agg({"Crédit": "sum", "Débit": "sum"})
    top["Résultat"] = top["Crédit"] - top["Débit"]
    top10 = top.nlargest(10, "Résultat")
    fig3 = px.bar(top10, x="Code_Analytique", y="Résultat", text="Résultat",
                   color="Résultat", color_continuous_scale=["#EF4444", "#F59E0B", "#10B981"],
                   labels={"Code_Analytique": "ISBN / Titre", "Résultat": "Résultat net (€)"}, height=380)
    fig3.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig3.update_layout(showlegend=False, margin=dict(t=20))
    st.plotly_chart(fig3, use_container_width=True)

# =====================
# ANALYSE PAR TITRE
# =====================
elif page == "📖 Analyse par titre":
    st.header("📖 Analyse par titre (ISBN)")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générez d'abord le socle analytique.")
        st.stop()

    df = st.session_state["df_pivot"].copy()
    params = st.session_state["param_comptes"]
    if st.session_state.get("repartition_active"):
        st.caption("ℹ️ Les charges/produits indirects ont été répartis sur les titres actifs.")

    # Même filtre que le Tableau de bord : ne proposer que de vrais ISBN dans la liste.
    titres = sorted(filtrer_isbn_reels(df)["Code_Analytique"].astype(str).unique().tolist())
    if not titres:
        st.warning("Aucun ISBN/code analytique détecté dans les données.")
        st.stop()

    # ================================================
    # REPÈRES RAPIDES : significatifs / rentables / compliqués
    # ================================================
    st.subheader("🧭 Repères rapides")
    st.caption("Calculés sur l'ensemble des titres actifs, charges fixes imputées incluses "
               "si la répartition a été activée.")
    indicateurs = calculer_indicateurs_titres(df, params, titres)

    col_signif, col_top, col_bas = st.columns(3)

    def _liste_titres(container, sous_titre, df_tri, prefix_key, colonne_montant):
        container.markdown(f"**{sous_titre}**")
        if df_tri.empty:
            container.caption("Aucune donnée.")
            return
        for _, row in df_tri.iterrows():
            c1, c2 = container.columns([3, 1])
            c1.markdown(f"{row['Signal']} **{row['Code_Analytique']}** — {row[colonne_montant]:,.0f} €")
            if c2.button("Voir", key=f"{prefix_key}_{row['Code_Analytique']}", use_container_width=True):
                afficher_fiche_titre(row["Code_Analytique"], df, params)

    _liste_titres(col_signif, "📊 Les plus significatifs (CA brut)",
                  indicateurs.sort_values("Ventes HT", ascending=False).head(5),
                  "signif", "Ventes HT")
    _liste_titres(col_top, "🏆 Les plus rentables (résultat net)",
                  indicateurs.sort_values("Résultat net", ascending=False).head(5),
                  "rent", "Résultat net")
    _liste_titres(col_bas, "⚠️ Les plus compliqués (résultat net)",
                  indicateurs.sort_values("Résultat net", ascending=True).head(5),
                  "diff", "Résultat net")

    st.divider()

    st.markdown("Ou sélectionnez directement un titre puis ouvrez sa fiche détaillée — elle s'affiche "
                "dans une fenêtre dédiée avec un mini SIG (soldes intermédiaires de gestion, charges "
                "fixes imputées incluses) et son évolution mensuelle.")
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        isbn_sel = st.selectbox("Titre (ISBN)", titres, label_visibility="collapsed")
    with col_btn:
        ouvrir = st.button("📖 Ouvrir la fiche", type="primary", use_container_width=True)

    if ouvrir:
        afficher_fiche_titre(isbn_sel, df, params)

# =====================
# TRÉSORERIE PRÉVISIONNELLE
# =====================
elif page == "💰 Trésorerie prévisionnelle":
    st.header("💰 Trésorerie prévisionnelle")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générez d'abord le socle analytique.")
        st.stop()

    st.caption(
        "Tableau de flux de trésorerie (TFT) reconstitué à partir du grand livre — méthode directe, classement "
        "par nature de compte (encaissements clients, paiements fournisseurs, dettes sociales/fiscales, "
        "investissement, financement), sur le modèle du tableau de flux fourni. Les montants sont calculés à "
        "partir des dates d'enregistrement comptable et peuvent différer légèrement d'un relevé bancaire réel "
        "en cas de décalage d'encaissement/décaissement."
    )

    df_tr = st.session_state["df_pivot"].copy()
    df_tr["Compte"] = df_tr["Compte"].astype(str).str.strip()
    df_tr["Date"]   = pd.to_datetime(df_tr["Date"], errors="coerce")
    df_tr["Débit"]  = pd.to_numeric(df_tr["Débit"], errors="coerce").fillna(0)
    df_tr["Crédit"] = pd.to_numeric(df_tr["Crédit"], errors="coerce").fillna(0)
    if "Journal" in df_tr.columns:
        df_tr["Journal"] = df_tr["Journal"].astype(str).str.strip()
    else:
        df_tr["Journal"] = ""
    df_tr = df_tr.dropna(subset=["Date"])
    if df_tr.empty:
        st.warning("Aucune écriture datée dans le socle analytique.")
        st.stop()

    # ---- Mapping par défaut des lignes du TFT (plan comptable général) ----
    DEFAULT_MAPPING = [
        ("Exploitation",   "Encaissements clients",                                  "411",             "credit"),
        ("Exploitation",   "Paiements fournisseurs",                                 "401,408",         "debit_neg"),
        ("Exploitation",   "Paiements dettes sociales - Salariés",                   "421,428",         "debit_neg"),
        ("Exploitation",   "Paiements dettes sociales - Organismes",                 "431,437,438",     "debit_neg"),
        ("Exploitation",   "Paiements dettes fiscales - TVA",                        "445510000",       "debit_neg"),
        ("Exploitation",   "Paiements dettes fiscales - IS",                         "444",             "debit_neg"),
        ("Exploitation",   "Encaissements aides et subventions d'exploitation",      "740",             "credit"),
        ("Exploitation",   "Autres débiteurs et créditeurs",                         "419,446,448",     "net"),
        ("Investissement", "Acquisitions d'immobilisations incorp. et corp.",        "201,205,215,218", "debit_neg"),
        ("Investissement", "Acquisitions/Cessions d'immobilisations financières",    "271,275,277",     "net"),
        ("Investissement", "Produits de cession des immobilisations",               "675,775",         "credit"),
        ("Financement",    "Variation des comptes courants d'associés",             "455",             "net"),
        ("Financement",    "Augmentation/(Diminution) du capital social",           "101",             "net"),
        ("Financement",    "Subventions d'investissement",                          "13",              "net"),
        ("Financement",    "Billets de trésorerie",                                 "4673,4674",       "net"),
        ("Financement",    "Encaissement d'emprunt",                                "164,168",         "credit"),
        ("Financement",    "Décaissement d'emprunt",                                "164,168",         "debit_neg"),
    ]
    SECTION_ORDER = ["Exploitation", "Investissement", "Financement"]

    with st.expander("⚙️ Configuration des comptes du TFT (avancé)"):
        st.caption("Préfixes de comptes (séparés par des virgules) utilisés pour classer chaque ligne du tableau. "
                   "À adapter si votre plan comptable diffère. Note : les comptes 438/604300000 etc. liés aux "
                   "droits d'auteurs sont également suivis dans le module « Droits d'auteurs ».")
        mapping = []
        for section, label, prefixes_def, mode in DEFAULT_MAPPING:
            p = st.text_input(f"{section} — {label}", value=prefixes_def, key=f"tft_pfx_{label}")
            mapping.append((section, label, [x.strip() for x in p.split(",") if x.strip()], mode))
        comptes_banque = st.text_input("Comptes de trésorerie (banque/caisse)", value="512,530,580", key="tft_banque")
        comptes_banque = tuple(x.strip() for x in comptes_banque.split(",") if x.strip())
        journaux_exclus_txt = st.text_input(
            "Journaux exclus des flux (report à nouveau)", value="AN", key="tft_journaux_exclus",
            help="Les écritures de report à nouveau (reprise des soldes d'ouverture en début d'exercice, "
                 "souvent codées « AN ») ne sont pas de vrais flux de la période : elles sont exclues du "
                 "classement, mais utilisées pour suggérer la trésorerie à l'ouverture (solde bancaire repris)."
        )
        journaux_exclus = tuple(x.strip() for x in journaux_exclus_txt.split(",") if x.strip())

    def montants_par_mois(sub_df, mode):
        """Agrégation vectorisée par mois — gère proprement le cas d'un sous-ensemble vide."""
        if sub_df.empty:
            return {}
        deb = sub_df.groupby("Mois")["Débit"].sum()
        cre = sub_df.groupby("Mois")["Crédit"].sum()
        if mode == "credit":
            res = cre
        elif mode == "debit_neg":
            res = -deb
        elif mode == "net":
            res = cre.sub(deb, fill_value=0)
        else:
            res = cre * 0
        return res.to_dict()

    mask_an = df_tr["Journal"].isin(journaux_exclus) if journaux_exclus else pd.Series(False, index=df_tr.index)
    df_tr_flux = df_tr[~mask_an].copy()

    col1, col2 = st.columns(2)
    with col1:
        date_debut = st.date_input("Date de départ (réalisé)", df_tr["Date"].min())
        banque_an = df_tr[mask_an & df_tr["Compte"].str.startswith(comptes_banque)]
        if not banque_an.empty:
            solde_suggere = float(banque_an["Débit"].sum() - banque_an["Crédit"].sum())
        else:
            banque_avant = df_tr_flux[df_tr_flux["Compte"].str.startswith(comptes_banque) & (df_tr_flux["Date"] < pd.to_datetime(date_debut))]
            solde_suggere = float(banque_avant["Débit"].sum() - banque_avant["Crédit"].sum())
        tresorerie_ouverture = st.number_input(
            "Trésorerie à l'ouverture (€)", value=solde_suggere, step=100.0,
            help="Solde bancaire à la date de départ. Suggéré depuis les écritures de report à nouveau sur les "
                 "comptes de trésorerie si elles existent, sinon depuis les écritures antérieures à cette date "
                 "(0 si aucune des deux — à saisir manuellement dans ce cas)."
        )
    with col2:
        horizon = st.slider("Horizon de projection (mois)", 0, 24, 6)
        st.markdown("**Scénarios de projection (au-delà du réalisé)**")
        croissance_opt  = st.number_input("Croissance encaissements — optimiste (%/mois)", value=4.0, step=0.5) / 100
        croissance_cent = st.number_input("Croissance encaissements — central (%/mois)", value=2.0, step=0.5) / 100
        croissance_pess = st.number_input("Croissance encaissements — pessimiste (%/mois)", value=0.0, step=0.5) / 100
        evolution_charges = st.number_input("Évolution charges décaissées (%/mois)", value=1.0, step=0.5) / 100

    df_period = df_tr_flux[df_tr_flux["Date"] >= pd.to_datetime(date_debut)].copy()
    if df_period.empty:
        st.warning("Aucune écriture après la date de départ.")
        st.stop()
    df_period["Mois"] = df_period["Date"].dt.to_period("M")
    mois_realises = sorted(df_period["Mois"].unique())

    lignes = {}
    for section, label, prefixes, mode in mapping:
        if not prefixes:
            continue
        sub = df_period[df_period["Compte"].str.startswith(tuple(prefixes))]
        lignes[(section, label)] = montants_par_mois(sub, mode)

    table = pd.DataFrame(0.0, index=pd.MultiIndex.from_tuples(lignes.keys(), names=["Section", "Ligne"]), columns=mois_realises)
    for key, vals in lignes.items():
        for m, v in vals.items():
            table.loc[key, m] = v

    sous_totaux = table.groupby(level="Section", sort=False).sum()
    flux_net_total = table.sum()
    treso_real = tresorerie_ouverture + flux_net_total.cumsum()

    _MOIS_FR = ["", "Janv.", "Févr.", "Mars", "Avr.", "Mai", "Juin", "Juil.", "Août", "Sept.", "Oct.", "Nov.", "Déc."]
    def mois_label(p):
        return f"{_MOIS_FR[p.month]} {p.year}"

    # ---- Indicateurs ----
    m1, m2, m3 = st.columns(3)
    m1.metric("Trésorerie à l'ouverture", f"{tresorerie_ouverture:,.0f} €")
    m2.metric("Trésorerie à la clôture (réalisé)", f"{treso_real.iloc[-1]:,.0f} €",
              delta=f"{treso_real.iloc[-1] - tresorerie_ouverture:,.0f} €")
    m3.metric("Flux net généré (période réalisée)", f"{flux_net_total.sum():,.0f} €")

    # ---- Tableau détaillé (réalisé) ----
    display_rows, display_index = [], []
    for section in SECTION_ORDER:
        if section not in table.index.get_level_values("Section"):
            continue
        for key in table.index:
            if key[0] == section:
                display_rows.append(table.loc[key])
                display_index.append(key[1])
        display_rows.append(sous_totaux.loc[section])
        display_index.append(f"▶ Flux net — {section}")
    display_rows.append(treso_real)
    display_index.append("● Trésorerie à la clôture (cumulée)")

    df_affiche = pd.DataFrame(display_rows, index=display_index)
    df_affiche.columns = [mois_label(m) for m in df_affiche.columns]

    def style_lignes(row):
        if row.name.startswith("▶") or row.name.startswith("●"):
            return ["font-weight: bold; background-color: rgba(59,130,246,0.12)"] * len(row)
        return [""] * len(row)

    st.dataframe(df_affiche.style.apply(style_lignes, axis=1).format("{:,.0f} €"), use_container_width=True)

    # ---- Projection (scénarios) ----
    def base_ligne(key):
        vals = table.loc[key]
        return vals.iloc[-3:].mean() if len(vals) >= 3 else vals.mean()

    def construire_projection(taux_encaissement, taux_charges):
        futurs = [mois_realises[-1] + i for i in range(1, horizon + 1)]
        proj = pd.DataFrame(0.0, index=table.index, columns=futurs)
        for key in table.index:
            section, label = key
            if section == "Exploitation" and "encaissement" in label.lower():
                taux = taux_encaissement
            elif section == "Exploitation":
                taux = taux_charges
            else:
                # Pas de nouvelle opération d'investissement/financement supposée par défaut
                continue
            v = base_ligne(key)
            for m in futurs:
                v *= (1 + taux)
                proj.loc[key, m] = v
        return proj

    if horizon > 0:
        scenarios = {
            "Optimiste":  construire_projection(croissance_opt, evolution_charges),
            "Central":    construire_projection(croissance_cent, evolution_charges),
            "Pessimiste": construire_projection(croissance_pess, evolution_charges),
        }
        courbes = {}
        for nom, proj in scenarios.items():
            flux_proj = proj.sum()
            treso_proj = treso_real.iloc[-1] + flux_proj.cumsum()
            courbes[nom] = pd.concat([treso_real, treso_proj])

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[mois_label(m) for m in treso_real.index], y=treso_real.values,
                                  name="Réalisé", line=dict(color="#111827", width=2.5)))
        couleurs = {"Optimiste": "#10B981", "Central": "#3B82F6", "Pessimiste": "#EF4444"}
        for nom, serie in courbes.items():
            proj_part = serie.iloc[len(treso_real) - 1:]
            fig.add_trace(go.Scatter(x=[mois_label(m) for m in proj_part.index], y=proj_part.values,
                                      name=nom, line=dict(color=couleurs[nom], width=2, dash="dot")))
        fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Seuil zéro")
        fig.update_layout(title="Trésorerie — réalisé et projection à 3 scénarios",
                          xaxis_title="Mois", yaxis_title="Trésorerie cumulée (€)",
                          legend=dict(orientation="h"), height=420)
        st.plotly_chart(fig, use_container_width=True)

        treso_cent_complete = courbes["Central"]
        if treso_cent_complete.min() < 0:
            mois_neg = treso_cent_complete[treso_cent_complete < 0].index[0]
            st.error(f"⚠️ Alerte : la trésorerie passe en négatif en **{mois_label(mois_neg)}** dans le scénario central !")
    else:
        scenarios = {}
        st.info("Augmentez l'horizon de projection pour visualiser les scénarios optimiste / central / pessimiste.")

    # ---- Export Excel ----
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_affiche.to_excel(writer, sheet_name="Réalisé")
        for nom, proj in scenarios.items():
            rows, idx = [], []
            for section in SECTION_ORDER:
                for key in proj.index:
                    if key[0] == section:
                        rows.append(proj.loc[key]); idx.append(key[1])
                rows.append(proj[proj.index.get_level_values("Section") == section].sum()); idx.append(f"▶ Flux net — {section}")
            flux_proj = proj.sum()
            rows.append(tresorerie_ouverture + pd.concat([flux_net_total, flux_proj]).cumsum().iloc[len(flux_net_total):])
            idx.append("● Trésorerie à la clôture (cumulée)")
            df_export = pd.DataFrame(rows, index=idx)
            df_export.columns = [mois_label(m) for m in df_export.columns]
            df_export.to_excel(writer, sheet_name=f"Prévisionnel_{nom}"[:31])
        wb = writer.book
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                label_cell = row[0]
                if isinstance(label_cell.value, str) and (label_cell.value.startswith("▶") or label_cell.value.startswith("●")):
                    for cell in row:
                        cell.font = cell.font.copy(bold=True)
    buffer.seek(0)
    st.download_button("📥 Exporter le tableau de flux de trésorerie (Excel)", buffer,
                        file_name="Tableau_Flux_Tresorerie.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =====================
# DROITS D'AUTEURS
# =====================
elif page == "✍️ Droits d'auteurs":
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

    Les droits d'auteurs sont **déjà calculés et provisionnés dans votre comptabilité analytique**
    (droits bruts, précompte URSSAF, contribution diffuseur, net dû) — ce module ne fait pas de
    double calcul, il fait remonter titre par titre, puis auteur par auteur, ce qui est réellement
    comptabilisé. Un simulateur reste disponible pour estimer un montant *avant* la provision de clôture.

    1. **📋 Référentiel** : correspondance ISBN ↔ auteur (détectée automatiquement si vous utilisez une
       famille analytique AUTEUR ; à défaut, à compléter manuellement) + paramètres du simulateur
    2. **🧮 Simulateur** : estimation par paliers, à titre indicatif avant comptabilisation
    3. **🏛️ Simulateur URSSAF** : estimation du précompte, à titre indicatif
    4. **📒 Réel (comptabilisé)** : montants réellement provisionnés, lus directement dans le grand livre
    5. **📄 Relevés par auteur** : relevé de compte par auteur (priorité au réel), exportable en Excel
    """)

    # ──────────────────────────────────────────────
    # INITIALISATION DU RÉFÉRENTIEL EN SESSION
    # Structure : liste de dicts {auteur, isbn, titre, taux_base, paliers, part_auteur}
    # paliers : liste de {seuil, taux} — ex. [{seuil:0, taux:10}, {seuil:10000, taux:12}]
    # Ce référentiel sert (a) de repli si aucune famille analytique AUTEUR n'est mappée, et
    # (b) au simulateur par paliers (taux, assiette, répartition co-auteurs), qui ne peut de
    # toute façon pas être déduit de la seule comptabilité.
    # ──────────────────────────────────────────────
    if "royalties_referentiel" not in st.session_state:
        st.session_state["royalties_referentiel"] = []

    onglet1, onglet2, onglet3, onglet4, onglet5 = st.tabs([
        "📋 Référentiel",
        "🧮 Simulateur",
        "🏛️ Simulateur URSSAF",
        "📒 Réel (comptabilisé)",
        "📄 Relevés par auteur"
    ])

    # ══════════════════════════════════════════════
    # ONGLET 1 — RÉFÉRENTIEL
    # ══════════════════════════════════════════════
    with onglet1:
        mapping_auto_preview = resoudre_mapping_auteurs(st.session_state.get("df_pivot")) if "df_pivot" in st.session_state else {}
        if mapping_auto_preview:
            st.success(f"✅ {len(mapping_auto_preview)} correspondance(s) ISBN → auteur détectée(s) "
                       f"automatiquement depuis une famille analytique AUTEUR de votre export — pas besoin "
                       f"de les ressaisir ci-dessous pour l'onglet **📒 Réel (comptabilisé)**.")
            st.dataframe(
                pd.DataFrame([{"ISBN": k, "Auteur (détecté)": v} for k, v in mapping_auto_preview.items()]),
                use_container_width=True
            )
            st.caption("Le référentiel ci-dessous reste utile pour le **🧮 Simulateur** (taux, paliers, "
                       "répartition co-auteurs), qui ne peut pas être déduit de la comptabilité seule.")
        else:
            st.info("💡 Si votre logiciel comptable permet de tagger une famille analytique supplémentaire "
                    "nommée **AUTEUR** (en plus d'EDITION/COMMUNICATION/Types de dépenses) — mappable dans "
                    "⚙️ Paramétrage analytique — la correspondance ISBN → auteur sera détectée automatiquement "
                    "ici. En l'absence de cette famille, complétez le référentiel manuel ci-dessous.")

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
    # ONGLET 2 — SIMULATEUR (ESTIMATION PAR PALIERS)
    # ══════════════════════════════════════════════
    with onglet2:
        st.subheader("Simulateur — estimation par paliers")
        st.caption("⚠️ Ceci est une estimation indicative (taux/paliers saisis dans le référentiel), "
                   "utile avant la provision de clôture. Les montants réellement dus sont dans l'onglet "
                   "**📒 Réel (comptabilisé)**.")

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
    # ONGLET 3 — SIMULATEUR URSSAF
    # ══════════════════════════════════════════════
    with onglet3:
        st.subheader("Simulateur URSSAF — Précompte diffuseur")
        st.caption("⚠️ Estimation basée sur le simulateur de l'onglet précédent — à comparer avec les montants "
                   "réellement provisionnés dans l'onglet **📒 Réel (comptabilisé)**.")

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
    # ONGLET 4 — RÉEL (COMPTABILISÉ)
    # ══════════════════════════════════════════════
    with onglet4:
        st.subheader("Montants réellement comptabilisés — titre par titre, puis auteur par auteur")
        st.caption("Ce module ne recalcule rien : il lit directement, pour chaque ISBN, les écritures déjà "
                   "provisionnées dans votre grand livre analytique (droits bruts, contribution diffuseur, "
                   "précompte URSSAF, net dû à l'auteur), pour ne jamais diverger de la comptabilité réelle.")

        if "df_pivot" not in st.session_state:
            st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
        else:
            df_pivot_reel = st.session_state["df_pivot"].copy()
            df_pivot_reel["Date"] = pd.to_datetime(df_pivot_reel["Date"], errors="coerce")

            st.markdown("**Période de déclaration**")
            dates_valides = df_pivot_reel["Date"].dropna()
            date_min_defaut = dates_valides.min() if not dates_valides.empty else pd.Timestamp("2024-01-01")
            date_max_defaut = dates_valides.max() if not dates_valides.empty else pd.Timestamp.today()
            col_p1, col_p2 = st.columns(2)
            periode_debut = col_p1.date_input("Du", value=date_min_defaut.date(), key="reel_periode_debut")
            periode_fin   = col_p2.date_input("Au", value=date_max_defaut.date(), key="reel_periode_fin")
            st.caption("Les montants ci-dessous ne portent que sur les écritures dont la date est comprise "
                       "dans cette période (ex. un trimestre ou un mois de déclaration URSSAF).")

            mask_periode = (
                (df_pivot_reel["Date"] >= pd.to_datetime(periode_debut))
                & (df_pivot_reel["Date"] <= pd.to_datetime(periode_fin))
            )
            df_pivot_reel = df_pivot_reel[mask_periode]

            st.markdown("**Comptes à lire dans le grand livre** _(réutilisables d'un exercice à l'autre)_")
            col_c1, col_c2, col_c3, col_c4 = st.columns(4)
            compte_droits_bruts = col_c1.text_input("Droits bruts (charge)", value="604300000", key="cpt_droits_bruts")
            compte_diffuseur    = col_c2.text_input("Contribution diffuseur", value="645106", key="cpt_diffuseur")
            compte_urssaf       = col_c3.text_input("URSSAF à payer", value="438106", key="cpt_urssaf")
            compte_net_du       = col_c4.text_input("Droits d'auteurs à payer (net)", value="408106", key="cpt_net_du")
            st.caption("⚠️ Le compte de droits bruts peut aussi contenir d'autres prestations (achats non liés "
                       "aux droits d'auteurs) selon votre plan de comptes — vérifiez le détail en cas d'écart "
                       "inattendu avec vos attentes.")

            def _par_isbn(compte, col):
                m = df_pivot_reel["Compte"].astype(str).str.strip() == str(compte).strip()
                if not m.any():
                    return pd.Series(dtype=float)
                return df_pivot_reel[m].groupby("Code_Analytique")[col].sum()

            droits_bruts_s = _par_isbn(compte_droits_bruts, "Débit")
            diffuseur_s    = _par_isbn(compte_diffuseur, "Débit")
            urssaf_s       = _par_isbn(compte_urssaf, "Crédit")
            net_du_s       = _par_isbn(compte_net_du, "Crédit")

            isbns_reels = sorted(set(droits_bruts_s.index) | set(diffuseur_s.index)
                                | set(urssaf_s.index) | set(net_du_s.index))
            isbns_reels = [i for i in isbns_reels
                           if str(i).strip() not in ("", "CHARGES INDIRECTES", "PRODUITS INDIRECTS")]

            if not isbns_reels:
                st.info("Aucun montant trouvé sur ces comptes pour l'instant. Vérifiez les numéros de comptes "
                        "ci-dessus, ou provisionnez d'abord les droits d'auteurs dans votre grand livre.")
            else:
                mapping_auto = resoudre_mapping_auteurs(df_pivot_reel)
                referentiel_par_isbn = {}
                for c in st.session_state["royalties_referentiel"]:
                    referentiel_par_isbn.setdefault(c["isbn"], []).append((c["auteur"], c["part"], c["titre"]))

                source_mapping = ("détection automatique (famille analytique AUTEUR)" if mapping_auto
                                   else "référentiel manuel (onglet Référentiel)")
                st.caption(f"Correspondance ISBN → auteur utilisée : {source_mapping}.")

                lignes, isbn_sans_auteur = [], []
                for isbn in isbns_reels:
                    droits_bruts = float(droits_bruts_s.get(isbn, 0))
                    diffuseur    = float(diffuseur_s.get(isbn, 0))
                    urssaf_total = float(urssaf_s.get(isbn, 0))
                    net_du       = float(net_du_s.get(isbn, 0))

                    if isbn in referentiel_par_isbn:
                        parts = referentiel_par_isbn[isbn]
                    elif isbn in mapping_auto:
                        parts = [(mapping_auto[isbn], 100.0, isbn)]
                    else:
                        parts = [("(auteur non identifié)", 100.0, isbn)]
                        isbn_sans_auteur.append(isbn)

                    for auteur, part, titre in parts:
                        coeff = part / 100.0
                        lignes.append({
                            "ISBN": isbn,
                            "Titre": titre if titre and titre != isbn else isbn,
                            "Auteur": auteur,
                            "Part (%)": part,
                            "Droits bruts (€)": round(droits_bruts * coeff, 2),
                            "Contribution diffuseur (€)": round(diffuseur * coeff, 2),
                            "URSSAF precompte+diffuseur (€)": round(urssaf_total * coeff, 2),
                            "Net du a l'auteur (€)": round(net_du * coeff, 2),
                        })

                df_reel = pd.DataFrame(lignes)
                st.session_state["df_royalties_reel"] = df_reel

                if isbn_sans_auteur:
                    st.warning(f"⚠️ {len(isbn_sans_auteur)} ISBN avec des droits comptabilisés mais sans auteur "
                               f"identifié : {', '.join(isbn_sans_auteur)}. Ajoutez-les dans l'onglet "
                               f"Référentiel pour qu'ils apparaissent nommément dans les relevés.")

                cols_montant = ["Droits bruts (€)", "Contribution diffuseur (€)",
                                "URSSAF precompte+diffuseur (€)", "Net du a l'auteur (€)"]
                st.dataframe(
                    df_reel.style.format({c: "{:,.2f}" for c in cols_montant}),
                    use_container_width=True
                )

                total_droits_bruts = df_reel["Droits bruts (€)"].sum()
                total_urssaf       = df_reel["URSSAF precompte+diffuseur (€)"].sum()
                total_net_du       = df_reel["Net du a l'auteur (€)"].sum()
                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("Droits bruts comptabilisés", f"{total_droits_bruts:,.2f} €")
                col_m2.metric("URSSAF (précompte + diffuseur)", f"{total_urssaf:,.2f} €")
                col_m3.metric("Net dû aux auteurs", f"{total_net_du:,.2f} €")

                df_par_auteur_reel = df_reel.groupby("Auteur", as_index=False)[cols_montant].sum()
                fig_reel = px.bar(
                    df_par_auteur_reel.sort_values("Net du a l'auteur (€)", ascending=False),
                    x="Auteur", y="Net du a l'auteur (€)", text_auto=".0f",
                    title="Net dû par auteur (comptabilisé)"
                )
                fig_reel.update_traces(textposition="outside")
                st.plotly_chart(fig_reel, use_container_width=True)

                # ================================================
                # RÉCAPITULATIF — droits dus par auteur + déclaration URSSAF de la période
                # ================================================
                st.divider()
                st.subheader(f"📋 Récapitulatif de la période du {periode_debut.strftime('%d/%m/%Y')} "
                             f"au {periode_fin.strftime('%d/%m/%Y')}")

                st.markdown("**Droits dus par auteur** _(net après précompte, tel que comptabilisé)_")
                st.dataframe(
                    df_par_auteur_reel.sort_values("Net du a l'auteur (€)", ascending=False)
                                      .style.format({c: "{:,.2f}" for c in cols_montant}),
                    use_container_width=True
                )

                st.markdown(f"""
                <div style='padding:14px 18px; border-radius:12px; background:#eef2ff;
                            margin-top:8px; margin-bottom:8px'>
                    <div style='font-weight:600; font-size:15px; margin-bottom:6px'>
                        🏛️ Déclaration URSSAF à effectuer sur cette période
                    </div>
                    <div>Précompte + contribution diffuseur à reverser : <b>{total_urssaf:,.2f} €</b></div>
                    <div>Assis sur des droits bruts comptabilisés de : <b>{total_droits_bruts:,.2f} €</b></div>
                </div>
                """, unsafe_allow_html=True)

                buffer_reel = BytesIO()
                with pd.ExcelWriter(buffer_reel, engine="openpyxl") as writer:
                    df_reel.to_excel(writer, index=False, sheet_name="Detail_par_titre")
                    df_par_auteur_reel.to_excel(writer, index=False, sheet_name="Recap_par_auteur")
                    pd.DataFrame([{
                        "Période début": periode_debut, "Période fin": periode_fin,
                        "Droits bruts (€)": total_droits_bruts,
                        "URSSAF precompte+diffuseur à déclarer (€)": total_urssaf,
                        "Net dû aux auteurs (€)": total_net_du,
                    }]).to_excel(writer, index=False, sheet_name="Declaration_URSSAF")
                buffer_reel.seek(0)
                st.download_button(
                    "📥 Exporter le récapitulatif de la période (Excel)",
                    buffer_reel,
                    file_name=f"Droits_auteurs_{periode_debut}_{periode_fin}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="export_reel_periode"
                )

    # ══════════════════════════════════════════════
    # ONGLET 5 — RELEVÉS PAR AUTEUR
    # ══════════════════════════════════════════════
    with onglet5:
        st.subheader("Relevés de droits par auteur")

        if "df_royalties_reel" in st.session_state and not st.session_state["df_royalties_reel"].empty:
            source_df_key = "df_royalties_reel"
            st.caption("✅ Source : montants réellement comptabilisés (onglet 📒 Réel).")
        elif "df_royalties_urssaf" in st.session_state:
            source_df_key = "df_royalties_urssaf"
            st.caption("ℹ️ Source : simulateur (estimation), aucun montant réel comptabilisé trouvé pour l'instant.")
        else:
            source_df_key = "df_royalties_resultats"

        if source_df_key not in st.session_state:
            st.warning("⚠️ Effectuez d'abord le calcul dans l'onglet 'Simulateur' ou 'Réel (comptabilisé)'.")
        else:
            df_releves = st.session_state[source_df_key].copy()
            auteurs    = sorted(df_releves["Auteur"].unique().tolist())

            auteur_sel = st.selectbox("Sélectionnez un auteur", ["Tous"] + auteurs)

            if auteur_sel != "Tous":
                df_auteur = df_releves[df_releves["Auteur"] == auteur_sel]
            else:
                df_auteur = df_releves

            # Colonnes à afficher selon la source active (simulateur, simulateur+URSSAF, ou réel comptabilisé)
            cols_releve_base = [
                "Auteur", "Titre", "ISBN", "Part (%)",
                "CA brut (€)", "Retours (€)", "Remises (€)",
                "Base calcul (€)", "Droits bruts (€)",
                "Contribution diffuseur (€)", "URSSAF precompte+diffuseur (€)", "Net du a l'auteur (€)"
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
# RETOURS & REMISES
# =====================
elif page == "📦 Retours & Remises":
    st.header("📦 Retours & Remises")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générez d'abord le socle analytique.")
        st.stop()

    df = st.session_state["df_pivot"].copy()
    param = st.session_state.get("param_comptes", {})
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Mois"] = df["Date"].dt.strftime("%Y-%m")

    seuil_alerte = st.sidebar.number_input("Seuil alerte taux de retour (%)", value=25, step=5)

    def filtre(df_src, prefix_list):
        if not prefix_list: return pd.DataFrame()
        f = df_src[df_src["Compte"].astype(str).str.startswith(tuple(prefix_list))].copy()
        if not f.empty: f["Montant_net"] = f["Débit"] - f["Crédit"]
        return f

    df_ret = filtre(df, param.get("retours", []))
    df_rem = filtre(df, param.get("remises", []))
    df_v   = filtre(df, param.get("ventes", []))

    total_retours = abs(df_ret["Montant_net"].sum()) if not df_ret.empty else 0
    total_remises = abs(df_rem["Montant_net"].sum()) if not df_rem.empty else 0
    total_ventes  = df_v["Crédit"].sum() if not df_v.empty else 0
    taux_ret = (total_retours / total_ventes * 100) if total_ventes else 0
    taux_rem = (total_remises / total_ventes * 100) if total_ventes else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CA brut", f"{total_ventes:,.0f} €")
    c2.metric("Total retours", f"{total_retours:,.0f} €")
    c3.metric("Taux de retour", f"{taux_ret:.1f} %",
              delta="⚠️ Dépasse le seuil !" if taux_ret > seuil_alerte else "✅ Normal",
              delta_color="inverse" if taux_ret > seuil_alerte else "normal")
    c4.metric("Taux de remise", f"{taux_rem:.1f} %")

    if taux_ret > seuil_alerte:
        st.error(f"🚨 Alerte : le taux de retour ({taux_ret:.1f}%) dépasse votre seuil de {seuil_alerte}% !")

    # Comparaison retours réels vs provision 681
    df_prov = df[df["Compte"].astype(str).str.startswith("681")]
    provision = (df_prov["Débit"] - df_prov["Crédit"]).sum() if not df_prov.empty else 0
    ecart = total_retours - provision
    st.info(f"📋 Provision retours comptabilisée (681) : **{provision:,.0f} €** — "
            f"Écart avec retours réels : **{ecart:,.0f} €** "
            f"({'sous-provision' if ecart > 0 else 'sur-provision'})")

    col_g1, col_g2 = st.columns(2)
    if not df_ret.empty:
        with col_g1:
            trend_ret = df_ret.groupby("Mois")["Montant_net"].sum().abs().reset_index()
            fig1 = px.bar(trend_ret, x="Mois", y="Montant_net", title="Retours mensuels (€)",
                           text="Montant_net", labels={"Montant_net": "€"}, color_discrete_sequence=["#EF4444"])
            fig1.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig1.update_layout(height=320, margin=dict(t=40))
            st.plotly_chart(fig1, use_container_width=True)
    if not df_rem.empty:
        with col_g2:
            trend_rem = df_rem.groupby("Mois")["Montant_net"].sum().abs().reset_index()
            fig2 = px.bar(trend_rem, x="Mois", y="Montant_net", title="Remises mensuelles (€)",
                           text="Montant_net", labels={"Montant_net": "€"}, color_discrete_sequence=["#F59E0B"])
            fig2.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig2.update_layout(height=320, margin=dict(t=40))
            st.plotly_chart(fig2, use_container_width=True)

    if not df_ret.empty:
        # Même filtre "vraie ligne ISBN" que les autres modules, pour ne pas laisser une
        # ligne "CHARGES INDIRECTES" ou un code vide polluer le classement des retours par titre.
        df_ret_isbn = filtrer_isbn_reels(df_ret)
        if not df_ret_isbn.empty:
            ret_isbn = df_ret_isbn.groupby("Code_Analytique")["Montant_net"].sum().abs().reset_index()
            ret_isbn = ret_isbn.sort_values("Montant_net", ascending=False)
            st.subheader("Retours par titre")
            st.dataframe(ret_isbn.style.format({"Montant_net": "{:,.0f} €"}), hide_index=True)

# =====================
# SYNTHÈSE FINANCIÈRE
# =====================
elif page == "📊 Synthèse financière":
    st.header("📊 Synthèse financière globale")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générez d'abord le socle analytique.")
        st.stop()

    df = st.session_state["df_pivot"].copy()
    params = st.session_state["param_comptes"]

    def filtre_m(df_src, prefix_list):
        if not prefix_list: return pd.DataFrame()
        f = df_src[df_src["Compte"].astype(str).str.startswith(tuple(prefix_list))].copy()
        if not f.empty: f["Montant_net"] = f["Débit"] - f["Crédit"]
        return f

    df_v   = filtre_m(df, params["ventes"])
    df_r   = filtre_m(df, params["retours"])
    df_rem = filtre_m(df, params["remises"])
    df_c   = filtre_m(df, params["charges"])

    ca_brut       = df_v["Crédit"].sum() if not df_v.empty else 0
    total_retours = abs(df_r["Montant_net"].sum())  if not df_r.empty else 0
    total_remises = abs(df_rem["Montant_net"].sum()) if not df_rem.empty else 0
    ca_net        = ca_brut - total_retours - total_remises
    charges_tot   = df_c["Débit"].sum() if not df_c.empty else 0
    resultat_net  = ca_net - charges_tot
    marge_pct     = (resultat_net / ca_brut * 100) if ca_brut else 0

    soldes = [ca_brut, -total_retours, -total_remises, ca_net, -charges_tot, resultat_net]
    libelles = ["CA brut", "Retours", "Remises", "CA net", "Charges", "Résultat net"]
    df_summary = pd.DataFrame({"Poste": libelles, "Montant (€)": soldes})

    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.subheader("Compte de résultat synthétique")
        st.dataframe(df_summary.style.format({"Montant (€)": "{:,.0f}"}), hide_index=True, height=280)
        st.metric("Taux de marge nette", f"{marge_pct:.1f} %")
    with col2:
        st.subheader("Waterfall")
        colors = ["#3B82F6", "#EF4444", "#EF4444", "#10B981", "#EF4444",
                  "#10B981" if resultat_net >= 0 else "#EF4444"]
        fig = go.Figure(go.Waterfall(
            name="Résultat",
            orientation="v",
            measure=["absolute", "relative", "relative", "total", "relative", "total"],
            x=libelles, y=soldes,
            connector={"line": {"color": "gray", "width": 0.5}},
            decreasing={"marker": {"color": "#EF4444"}},
            increasing={"marker": {"color": "#10B981"}},
            totals={"marker": {"color": "#3B82F6"}}
        ))
        fig.update_layout(height=350, margin=dict(t=20), yaxis_title="€")
        st.plotly_chart(fig, use_container_width=True)

    # Export PDF synthèse (Excel ici, PDF nécessiterait reportlab)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_summary.to_excel(writer, index=False, sheet_name="Synthese")
    buffer.seek(0)
    st.download_button("📥 Exporter la synthèse (Excel)", buffer,
                        file_name="Synthese_Financiere.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =====================
# ASSISTANT IA — 3 NIVEAUX
# =====================
elif page == "🤖 Assistant IA":
    st.header("🤖 Assistant IA — Expert éditorial")
    client = get_client()
    if client is None:
        st.error("⚠️ Clé API Anthropic non configurée. Ajoutez `ANTHROPIC_API_KEY` dans vos secrets Streamlit Cloud.")
        st.code("""
# Dans Streamlit Cloud > Settings > Secrets :
ANTHROPIC_API_KEY = "sk-ant-..."
        """)
        st.stop()

    tab1, tab2, tab3 = st.tabs([
        "💬 Niveau 1 — Questions sur les modules",
        "🔍 Niveau 2 — Analyse de vos données",
        "🤖 Niveau 3 — Agent conversationnel"
    ])

    # ─── NIVEAU 1 : Assistant contextuel ───
    with tab1:
        st.markdown("**Posez une question sur l'utilisation de l'outil ou sur la comptabilité éditoriale.**")
        questions_types = [
            "Comment paramétrer mes comptes de retours ?",
            "Que signifie le taux de retour et quel seuil est normal en édition ?",
            "Comment fonctionne la provision pour retours (compte 681) ?",
            "Comment lire le tableau de bord éditorial ?",
            "Qu'est-ce qu'une reddition de comptes d'auteur ?",
            "Comment calculer la marge brute éditeur ?"
        ]
        st.markdown("**Questions fréquentes :**")
        cols = st.columns(3)
        for i, q in enumerate(questions_types):
            if cols[i % 3].button(q, key=f"q1_{i}", use_container_width=True):
                with st.spinner("Réflexion en cours..."):
                    resp = client.messages.create(
                        model="claude-opus-4-5",
                        max_tokens=600,
                        system=SYSTEM_PROMPT,
                        messages=[{"role": "user", "content": q}]
                    )
                    st.info(f"**Question :** {q}")
                    st.success(resp.content[0].text)
        st.divider()
        question_libre = st.text_input("Ou posez votre propre question :", placeholder="Ex: Comment traiter un avoir client en édition ?")
        if st.button("Envoyer", key="btn_n1") and question_libre:
            with st.spinner("Réflexion en cours..."):
                resp = client.messages.create(
                    model="claude-opus-4-5",
                    max_tokens=600,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": question_libre}]
                )
                st.success(resp.content[0].text)

    # ─── NIVEAU 2 : Analyste sur les données ───
    with tab2:
        if "df_pivot" not in st.session_state:
            st.warning("⚠️ Chargez d'abord des données pour activer l'analyse IA.")
        else:
            st.markdown("**L'IA analyse vos données et génère un commentaire de gestion personnalisé.**")
            if st.button("🔍 Analyser mes données maintenant", type="primary"):
                summary = build_data_summary()
                prompt = f"""Voici les données analytiques d'une maison d'édition indépendante :
{summary}

En tant qu'expert-comptable spécialisé en édition, fournis :
1. Un commentaire de gestion synthétique (3-4 phrases)
2. Les 2-3 points d'attention prioritaires avec leur niveau de risque
3. Des recommandations concrètes et actionnables pour améliorer la rentabilité
4. Une évaluation du taux de retour par rapport aux standards du secteur (entre 20% et 35% en édition française)

Sois précis, factuel et orienté action."""
                with st.spinner("Analyse en cours..."):
                    resp = client.messages.create(
                        model="claude-opus-4-5",
                        max_tokens=900,
                        system=SYSTEM_PROMPT,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.markdown("### Analyse IA de vos données")
                    st.markdown(resp.content[0].text)
            st.divider()
            st.markdown("**Demande d'analyse spécifique :**")
            analyse_custom = st.text_area("Que souhaitez-vous analyser en particulier ?",
                                           placeholder="Ex: Quels sont les signaux d'alerte sur ma trésorerie prévisionnelle ?")
            if st.button("Analyser", key="btn_n2") and analyse_custom:
                summary = build_data_summary()
                with st.spinner("Analyse en cours..."):
                    resp = client.messages.create(
                        model="claude-opus-4-5",
                        max_tokens=800,
                        system=SYSTEM_PROMPT,
                        messages=[{
                            "role": "user",
                            "content": f"Données de l'éditeur :\n{summary}\n\nQuestion : {analyse_custom}"
                        }]
                    )
                    st.markdown(resp.content[0].text)

    # ─── NIVEAU 3 : Agent conversationnel multi-tours ───
    with tab3:
        st.markdown("**Dialogue libre et multi-tours avec l'agent. Il mémorise le contexte de la conversation.**")
        # Contexte données injecté au départ
        data_context = ""
        if "df_pivot" in st.session_state:
            data_context = f"\n\nDONNÉES DISPONIBLES :\n{build_data_summary()}"
        system_with_data = SYSTEM_PROMPT + data_context

        # Affichage historique
        for msg in st.session_state["messages_agent"]:
            with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🤖"):
                st.markdown(msg["content"])

        # Input utilisateur
        if prompt_user := st.chat_input("Posez votre question à l'agent..."):
            st.session_state["messages_agent"].append({"role": "user", "content": prompt_user})
            with st.chat_message("user", avatar="🧑"):
                st.markdown(prompt_user)
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("L'agent réfléchit..."):
                    resp = client.messages.create(
                        model="claude-opus-4-5",
                        max_tokens=1000,
                        system=system_with_data,
                        messages=st.session_state["messages_agent"]
                    )
                    answer = resp.content[0].text
                    st.markdown(answer)
                    st.session_state["messages_agent"].append({"role": "assistant", "content": answer})

        if st.button("🗑️ Effacer la conversation", key="clear_chat"):
            st.session_state["messages_agent"] = []
            st.rerun()

# =====================
# FOOTER
# =====================
st.divider()
st.markdown(
    "<div style='text-align:center; color:#888; font-size:12px'>"
    "© 2025 Nicolas CUISSET — Mémoire d'expertise comptable — Maisons d'édition indépendantes"
    "</div>",
    unsafe_allow_html=True
)
