import streamlit as st
import pandas as pd
from datetime import date
from sqlalchemy import text
from database import init_db, get_conn
from calculs import calculer_plein, calculer_solde
from auth import check_password, logout

if not check_password():
    st.stop()

init_db()

st.set_page_config(page_title="GestiCarb ONG", layout="wide")
st.title("⛽ GestiCarb ONG - Suivi Carburant")

st.sidebar.write(f"👤 Connecté : {st.session_state.get('user','')}")
if st.sidebar.button("🚪 Se déconnecter"):
    logout()

menu = st.sidebar.selectbox(
    "Menu",
    ["Tableau de bord", "Saisie plein", "Historique",
     "Rapport mensuel", "Vehicules", "Tom Cards"]
)

if menu == "Tableau de bord":
    st.header("Tableau de bord")
    with get_conn() as conn:
        df_v = pd.read_sql("SELECT * FROM vehicules", conn)
        df_p = pd.read_sql("SELECT * FROM pleins", conn)
    col1, col2, col3 = st.columns(3)
    col1.metric("Vehicules", len(df_v))
    col2.metric("Pleins enregistres", len(df_p))
    if not df_p.empty and df_p["conso_100"].notna().any():
        col3.metric("Conso moyenne", f"{df_p['conso_100'].mean():.1f} L/100")
    else:
        col3.metric("Conso moyenne", "-")
    if not df_p.empty:
        st.subheader("Derniers pleins")
        st.dataframe(df_p.tail(10), use_container_width=True)

elif menu == "Saisie plein":
    st.header("Saisie d'un plein")
    with get_conn() as conn:
        df_v = pd.read_sql("SELECT id, immatriculation FROM vehicules", conn)
        df_tc = pd.read_sql("SELECT id, numero FROM tom_cards", conn)
    if df_v.empty:
        st.warning("Ajoutez d'abord des vehicules dans l'onglet 'Vehicules'.")
    else:
        with st.form("form_plein"):
            d = st.date_input("Date", date.today())
            veh = st.selectbox("Vehicule", df_v["immatriculation"])
            veh_id = int(df_v[df_v["immatriculation"] == veh]["id"].values[0])
            if not df_tc.empty:
                tc_label = st.selectbox("Tom Card", df_tc["numero"])
                tc_id = int(df_tc[df_tc["numero"] == tc_label]["id"].values[0])
            else:
                tc_id = None
                st.warning("Aucune Tom Card enregistree.")
            km_avant = st.number_input("Km avant", min_value=0, step=1)
            km_apres = st.number_input("Km apres", min_value=0, step=1)
            quantite = st.number_input("Quantite (L)", min_value=0.0, step=0.1)
            prix = st.number_input("Prix unitaire (FCFA/L)", min_value=0.0, value=668.0, step=1.0)
            agent = st.text_input("Agent")
            if st.form_submit_button("Enregistrer"):
                res = calculer_plein(km_avant, km_apres, quantite, prix)
                with get_conn() as conn:
                    row = conn.execute(text(
                        "SELECT solde_apres FROM pleins WHERE vehicule_id=:v ORDER BY date DESC LIMIT 1"),
                        {"v": veh_id}).fetchone()
                    solde_prec = row[0] if row else 0
                    nouveau_solde = calculer_solde(solde_prec, res["montant"])
                    conn.execute(text("""
                        INSERT INTO pleins (date, tom_card_id, vehicule_id, km_avant, km_apres,
                        km_parcouru, quantite, prix_unitaire, montant, conso_100, solde_apres, agent)
                        VALUES (:d,:tc,:v,:ka,:kap,:kp,:q,:pu,:m,:c,:s,:a)"""),
                        {"d": d, "tc": tc_id, "v": veh_id, "ka": km_avant, "kap": km_apres,
                         "kp": res["km_parcouru"], "q": quantite, "pu": prix, "m": res["montant"],
                         "c": res["conso_100"], "s": nouveau_solde, "a": agent})
                    conn.commit()
                st.success(f"Plein enregistre - Montant : {res['montant']:.0f} FCFA - "
                           f"Conso : {res['conso_100']} L/100 - Solde : {nouveau_solde:.0f} FCFA")

elif menu == "Historique":
    st.header("Historique des pleins")
    with get_conn() as conn:
        df = pd.read_sql("""
            SELECT p.id, p.date, v.immatriculation, p.km_parcouru, p.quantite,
                   p.montant, p.conso_100, p.solde_apres, p.agent
            FROM pleins p JOIN vehicules v ON v.id = p.vehicule_id
            ORDER BY p.date DESC
        """, conn)
    if df.empty:
        st.info("Aucun plein enregistre.")
    else:
        st.dataframe(df.drop(columns=["id"]), use_container_width=True)
        st.subheader("🗑️ Supprimer un plein")
        id_sup = st.selectbox("Choisir l'ID", df["id"].tolist(),
                              format_func=lambda x: f"ID {x} - {df[df['id']==x]['date'].values[0]} - {df[df['id']==x]['immatriculation'].values[0]}")
        if st.button("🗑️ Supprimer ce plein"):
            with get_conn() as conn:
                conn.execute(text("DELETE FROM pleins WHERE id=:id"), {"id": id_sup})
                conn.commit()
            st.success("Plein supprime ✅")
            st.rerun()

elif menu == "Rapport mensuel":
    st.header("Rapport mensuel")
    mois = st.text_input("Mois (format YYYY-MM)", "2026-09")
    if st.button("Generer le rapport"):
        with get_conn() as conn:
            df = pd.read_sql("""
                SELECT v.immatriculation, p.conso_100, p.solde_apres
                FROM pleins p JOIN vehicules v ON v.id = p.vehicule_id
                WHERE TO_CHAR(p.date, 'YYYY-MM') = :m
            """, conn, params={"m": mois})
        if df.empty:
            st.warning("Aucune donnee pour ce mois.")
        else:
            conso = df.groupby("immatriculation")["conso_100"].mean().round(0).reset_index()
            conso.columns = ["Immatriculation", "Conso moyenne (L/100km)"]
            soldes = df.groupby("immatriculation")["solde_apres"].last().reset_index()
            soldes.columns = ["Immatriculation", "Solde actuel"]
            soldes["Besoin"] = 400800
            soldes["A renflouer"] = soldes["Besoin"] - soldes["Solde actuel"]
            st.subheader("1. Consommation moyenne")
            st.dataframe(conso, use_container_width=True)
            st.info(f"Moyenne generale : {conso['Conso moyenne (L/100km)'].mean():.0f} L/100 km")
            st.subheader("2. Soldes et renflouement")
            st.dataframe(soldes, use_container_width=True)

elif menu == "Vehicules":
    st.header("Gestion des vehicules")
    st.subheader("➕ Ajouter un vehicule")
    with st.form("form_vehicule"):
        imm = st.text_input("Immatriculation")
        modele = st.text_input("Modele")
        type_v = st.selectbox("Type", ["vehicule", "groupe electrogene"])
        partenaire = st.text_input("Partenaire (ex: ONG ADKOUL)")
        if st.form_submit_button("Ajouter"):
            try:
                with get_conn() as conn:
                    conn.execute(text("INSERT INTO vehicules (immatriculation, modele, type, partenaire) VALUES (:i,:m,:t,:p)"),
                                 {"i": imm, "m": modele, "t": type_v, "p": partenaire})
                    conn.commit()
                st.success("Vehicule ajoute ✅")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")
    st.subheader("📋 Liste")
    with get_conn() as conn:
        df = pd.read_sql("SELECT * FROM vehicules ORDER BY immatriculation", conn)
    if df.empty:
        st.info("Aucun vehicule.")
    else:
        st.dataframe(df, use_container_width=True)
        st.subheader("✏️ Modifier")
        id_m = st.selectbox("Vehicule a modifier", df["id"].tolist(),
                            format_func=lambda x: f"ID {x} - {df[df['id']==x]['immatriculation'].values[0]}",
                            key="modif_v")
        ligne = df[df["id"] == id_m].iloc[0]
        with st.form("form_modif_v"):
            n_imm = st.text_input("Immatriculation", ligne["immatriculation"])
            n_mod = st.text_input("Modele", ligne["modele"] or "")
            n_type = st.selectbox("Type", ["vehicule", "groupe electrogene"],
                                  index=0 if ligne["type"]=="vehicule" else 1)
            n_part = st.text_input("Partenaire", ligne["partenaire"] or "")
            if st.form_submit_button("Enregistrer"):
                with get_conn() as conn:
                    conn.execute(text("UPDATE vehicules SET immatriculation=:i, modele=:m, type=:t, partenaire=:p WHERE id=:id"),
                                 {"i": n_imm, "m": n_mod, "t": n_type, "p": n_part, "id": id_m})
                    conn.commit()
                st.success("Modifie ✅")
                st.rerun()
        st.subheader("🗑️ Supprimer")
        id_s = st.selectbox("Vehicule a supprimer", df["id"].tolist(),
                            format_func=lambda x: f"ID {x} - {df[df['id']==x]['immatriculation'].values[0]}",
                            key="supp_v")
        if st.button("🗑️ Supprimer ce vehicule"):
            with get_conn() as conn:
                conn.execute(text("DELETE FROM vehicules WHERE id=:id"), {"id": id_s})
                conn.commit()
            st.success("Supprime ✅")
            st.rerun()

elif menu == "Tom Cards":
    st.header("Gestion des Tom Cards")
    with get_conn() as conn:
        df_v = pd.read_sql("SELECT id, immatriculation FROM vehicules", conn)
    if df_v.empty:
        st.warning("Ajoutez d'abord un vehicule.")
    else:
        st.subheader("➕ Ajouter")
        with st.form("form_tc"):
            numero = st.text_input("Numero Tom Card")
            barre = st.text_input("Code-barres")
            fournisseur = st.selectbox("Fournisseur", ["ORIBA", "BABATI PETROLIUM SERVICE"])
            veh = st.selectbox("Vehicule", df_v["immatriculation"])
            v_id = int(df_v[df_v["immatriculation"] == veh]["id"].values[0])
            if st.form_submit_button("Ajouter"):
                try:
                    with get_conn() as conn:
                        conn.execute(text("INSERT INTO tom_cards (numero, barre_code, fournisseur, vehicule_id) VALUES (:n,:b,:f,:v)"),
                                     {"n": numero, "b": barre, "f": fournisseur, "v": v_id})
                        conn.commit()
                    st.success("Tom Card ajoutee ✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")
    st.subheader("📋 Liste")
    with get_conn() as conn:
        df = pd.read_sql("""SELECT t.id, t.numero, t.barre_code, t.fournisseur, v.immatriculation
                            FROM tom_cards t LEFT JOIN vehicules v ON v.id = t.vehicule_id""", conn)
    if df.empty:
        st.info("Aucune Tom Card.")
    else:
        st.dataframe(df.drop(columns=["id"]), use_container_width=True)
        st.subheader("🗑️ Supprimer")
        id_tc = st.selectbox("Tom Card a supprimer", df["id"].tolist(),
                             format_func=lambda x: f"ID {x} - {df[df['id']==x]['numero'].values[0]}")
        if st.button("🗑️ Supprimer cette Tom Card"):
            with get_conn() as conn:
                conn.execute(text("DELETE FROM tom_cards WHERE id=:id"), {"id": id_tc})
                conn.commit()
            st.success("Supprimee ✅")
            st.rerun()