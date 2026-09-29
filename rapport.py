import pandas as pd
from database import get_conn

def generer_rapport_mensuel(mois):
    conn = get_conn()
    query = f"""
        SELECT v.immatriculation, p.date, p.km_parcouru, p.quantite,
               p.montant, p.conso_100, p.solde_apres
        FROM pleins p
        JOIN vehicules v ON v.id = p.vehicule_id
        WHERE strftime('%Y-%m', p.date) = '{mois}'
        ORDER BY v.immatriculation, p.date
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return None, None, None

    conso = df.groupby("immatriculation")["conso_100"].mean().round(0).reset_index()
    conso.columns = ["Immatriculation", "Conso moyenne (L/100km)"]
    moyenne_generale = round(conso["Conso moyenne (L/100km)"].mean(), 0)

    soldes = df.groupby("immatriculation")["solde_apres"].last().reset_index()
    soldes.columns = ["Immatriculation", "Solde actuel"]
    soldes["Besoin"] = 400800
    soldes["À renflouer"] = soldes["Besoin"] - soldes["Solde actuel"]

    return conso, soldes, moyenne_generale

def exporter_excel(mois, chemin="exports/rapport.xlsx"):
    import os
    os.makedirs("exports", exist_ok=True)
    conso, soldes, moyenne = generer_rapport_mensuel(mois)
    if conso is None:
        return None
    with pd.ExcelWriter(chemin) as writer:
        conso.to_excel(writer, sheet_name="Consommation", index=False)
        soldes.to_excel(writer, sheet_name="Soldes", index=False)
    return chemin