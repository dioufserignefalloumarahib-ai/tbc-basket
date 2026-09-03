import sqlite3
import os

PROJECT_FOLDER = os.path.dirname(os.path.abspath(__file__))
DATABASE_FOLDER = os.path.join(PROJECT_FOLDER, "database")
DATABASE_FILE = os.path.join(DATABASE_FOLDER, "tbc.db")


def get_connection():
    os.makedirs(DATABASE_FOLDER, exist_ok=True)
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS terrain (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            localisation TEXT,
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS joueurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            age INTEGER,
            poste TEXT,
            numero INTEGER,
            equipe TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            categorie TEXT,
            entraineur TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matchs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipe_domicile TEXT NOT NULL,
            equipe_exterieure TEXT NOT NULL,
            date_match TEXT,
            heure TEXT,
            score_domicile INTEGER DEFAULT 0,
            score_exterieur INTEGER DEFAULT 0,
            minuteurs_domicile TEXT,
            minuteurs_exterieur TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournois (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            lieu TEXT,
            date_debut TEXT,
            date_fin TEXT,
            description TEXT
        )
    """)

    match_columns = [column[1] for column in cursor.execute("PRAGMA table_info(matchs)").fetchall()]
    if "tournoi_id" not in match_columns:
        cursor.execute("ALTER TABLE matchs ADD COLUMN tournoi_id INTEGER")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            date_reservation TEXT NOT NULL,
            heure_debut TEXT,
            heure_fin TEXT,
            telephone TEXT
        )
    """)

    terrain_count = cursor.execute("SELECT COUNT(*) AS total FROM terrain").fetchone()["total"]
    if terrain_count == 0:
        cursor.execute(
            "INSERT INTO terrain (nom, localisation, description) VALUES (?, ?, ?)",
            (
                "TBC - THIADIAYE BASKET CLUB",
                "Thiadiaye, Sénégal",
                "Terrain de basketball du THIADIAYE BASKET CLUB.",
            ),
        )

    equipes_count = cursor.execute("SELECT COUNT(*) AS total FROM equipes").fetchone()["total"]
    if equipes_count == 0:
        cursor.executemany(
            "INSERT INTO equipes (nom, categorie, entraineur) VALUES (?, ?, ?)",
            [
                ("TBC Senior", "Senior", "Moussa Diop"),
                ("TBC U18", "U18", "Ali Ndiaye"),
            ],
        )

    joueurs_count = cursor.execute("SELECT COUNT(*) AS total FROM joueurs").fetchone()["total"]
    if joueurs_count == 0:
        cursor.executemany(
            "INSERT INTO joueurs (nom, prenom, age, poste, numero, equipe) VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("Diop", "Moussa", 25, "Meneur", 10, "TBC Senior"),
                ("Ndiaye", "Ali", 22, "Ailier", 7, "TBC Senior"),
                ("Sarr", "Ibrahima", 19, "Arrière", 15, "TBC U18"),
            ],
        )

    matchs_count = cursor.execute("SELECT COUNT(*) AS total FROM matchs").fetchone()["total"]
    if matchs_count == 0:
        cursor.execute(
            "INSERT INTO matchs (equipe_domicile, equipe_exterieure, date_match, heure, score_domicile, score_exterieur, minuteurs_domicile, minuteurs_exterieur) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("TBC Senior", "Dakar Basket", "2026-09-02", "18:30", 78, 72, "12, 24, 36", "9, 17, 41"),
        )

    connection.commit()
    connection.close()


if __name__ == "__main__":
    init_database()
    print("Base de données TBC créée avec succès !")