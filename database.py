import streamlit as st
from sqlalchemy import create_engine, text

def get_engine():
    url = st.secrets["supabase"]["url"]
    # Forcer psycopg v3 (compatible Python 3.14)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(url, pool_pre_ping=True)

def init_db():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vehicules (
                id SERIAL PRIMARY KEY,
                immatriculation VARCHAR(50) UNIQUE,
                modele VARCHAR(100),
                type VARCHAR(30),
                partenaire VARCHAR(100),
                statut VARCHAR(20) DEFAULT 'actif'
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tom_cards (
                id SERIAL PRIMARY KEY,
                numero VARCHAR(50) UNIQUE,
                barre_code VARCHAR(50),
                fournisseur VARCHAR(100),
                vehicule_id INTEGER REFERENCES vehicules(id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pleins (
                id SERIAL PRIMARY KEY,
                date DATE,
                tom_card_id INTEGER REFERENCES tom_cards(id),
                vehicule_id INTEGER REFERENCES vehicules(id),
                km_avant INTEGER,
                km_apres INTEGER,
                km_parcouru INTEGER,
                quantite REAL,
                prix_unitaire REAL,
                montant REAL,
                conso_100 REAL,
                solde_apres REAL,
                agent VARCHAR(100)
            )
        """))

def get_conn():
    return get_engine().connect()