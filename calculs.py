def calculer_plein(km_avant, km_apres, quantite, prix_unitaire):
    km_parcouru = km_apres - km_avant
    montant = quantite * prix_unitaire
    conso_100 = (quantite * 100 / km_parcouru) if km_parcouru > 0 else 0
    return {
        "km_parcouru": km_parcouru,
        "montant": round(montant, 2),
        "conso_100": round(conso_100, 2)
    }

def calculer_solde(solde_precedent, montant):
    return round(solde_precedent - montant, 2)

def moyenne_conso(liste_conso):
    if not liste_conso:
        return 0
    return round(sum(liste_conso) / len(liste_conso), 2)