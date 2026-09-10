from __future__ import annotations

import os
import sqlite3
import json
from datetime import date, datetime
from functools import wraps
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "database" / "tbc.db"

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "tbc-development-key-change-me"),
    DATABASE=str(DATABASE),
    CLUB_NAME="THIADIAYE BASKET CLUB",
    CLUB_SHORT="TBC",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'admin', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL,
    color TEXT DEFAULT '#e4572e', coach TEXT, description TEXT DEFAULT '', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
    birth_date TEXT, jersey_number INTEGER, position TEXT, team_id INTEGER, phone TEXT,
    address TEXT, height REAL, status TEXT DEFAULT 'Actif', registration_date TEXT,
    FOREIGN KEY(team_id) REFERENCES teams(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT, team_id INTEGER, opponent TEXT NOT NULL,
    match_date TEXT NOT NULL, match_time TEXT, venue TEXT, competition TEXT,
    status TEXT DEFAULT 'À venir', home_score INTEGER DEFAULT 0, away_score INTEGER DEFAULT 0,
    notes TEXT DEFAULT '', FOREIGN KEY(team_id) REFERENCES teams(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT, requester TEXT NOT NULL, phone TEXT, reservation_date TEXT NOT NULL,
    start_time TEXT NOT NULL, end_time TEXT NOT NULL, reason TEXT, status TEXT DEFAULT 'En attente'
);
CREATE TABLE IF NOT EXISTS venue (
    id INTEGER PRIMARY KEY CHECK (id = 1), name TEXT NOT NULL, location TEXT, description TEXT,
    capacity INTEGER, condition TEXT, opening_hours TEXT, equipment TEXT, contact TEXT
);
CREATE TABLE IF NOT EXISTS player_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT, player_id INTEGER UNIQUE NOT NULL, games INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0, rebounds INTEGER DEFAULT 0, assists INTEGER DEFAULT 0,
    steals INTEGER DEFAULT 0, blocks INTEGER DEFAULT 0, fouls INTEGER DEFAULT 0,
    FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS team_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT, team_id INTEGER UNIQUE NOT NULL, games INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, points_for INTEGER DEFAULT 0,
    points_against INTEGER DEFAULT 0, FOREIGN KEY(team_id) REFERENCES teams(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS nba_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT, external_id TEXT UNIQUE, home_team TEXT NOT NULL,
    away_team TEXT NOT NULL, home_score INTEGER, away_score INTEGER, status TEXT NOT NULL,
    start_time TEXT, period TEXT, source TEXT DEFAULT 'API à configurer'
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, age_range TEXT,
    gender TEXT DEFAULT 'Mixte', coach TEXT, description TEXT DEFAULT '',
    status TEXT DEFAULT 'active', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS category_players (
    category_id INTEGER NOT NULL, player_id INTEGER NOT NULL,
    PRIMARY KEY (category_id, player_id),
    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE,
    FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS systems (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, system_type TEXT NOT NULL,
    player_count INTEGER DEFAULT 5, description TEXT DEFAULT '', objective TEXT DEFAULT '',
    key_points TEXT DEFAULT '', instructions TEXT DEFAULT '', coach TEXT,
    status TEXT DEFAULT 'active', positions_json TEXT DEFAULT '[]', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS system_categories (
    system_id INTEGER NOT NULL, category_id INTEGER NOT NULL,
    PRIMARY KEY (system_id, category_id),
    FOREIGN KEY(system_id) REFERENCES systems(id) ON DELETE CASCADE,
    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS system_players (
    system_id INTEGER NOT NULL, player_id INTEGER NOT NULL, role TEXT,
    PRIMARY KEY (system_id, player_id),
    FOREIGN KEY(system_id) REFERENCES systems(id) ON DELETE CASCADE,
    FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE
);
"""


def get_db():
    if "db" not in g:
        Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db:
        db.close()


def query(sql, params=(), one=False):
    cursor = get_db().execute(sql, params)
    rows = cursor.fetchone() if one else cursor.fetchall()
    cursor.close()
    return rows


def execute(sql, params=()):
    db = get_db()
    cursor = db.execute(sql, params)
    db.commit()
    return cursor.lastrowid


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    required_columns = {
        "teams": {"id", "name", "category", "color"},
        "players": {"id", "first_name", "last_name", "team_id", "status"},
        "matches": {"id", "team_id", "opponent", "match_date", "status", "home_score", "away_score"},
        "reservations": {"id", "requester", "reservation_date", "start_time", "end_time", "status"},
    }
    schema_is_compatible = all(
        required.issubset({row["name"] for row in query(f"PRAGMA table_info({table})")})
        for table, required in required_columns.items()
    )
    if not schema_is_compatible:
        for table in ("player_statistics", "team_statistics", "players", "matches", "reservations", "teams", "venue", "nba_games", "settings", "users"):
            db.execute(f"DROP TABLE IF EXISTS {table}")
        db.executescript(SCHEMA)
    if not query("SELECT id FROM users LIMIT 1", one=True):
        execute("INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                ("admin", generate_password_hash("admin123"), datetime.now().isoformat()))
    if not query("SELECT id FROM venue WHERE id = 1", one=True):
        execute("INSERT INTO venue VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("Terrain TBC", "Thiadiaye, Sénégal", "Le terrain officiel du Thiadiaye Basket Club.",
                 500, "Bon état", "Lun-Dim · 08:00 - 22:00", "Paniers homologués, éclairage, vestiaires", "À renseigner"))
    if not query("SELECT id FROM teams LIMIT 1", one=True):
        senior = execute("INSERT INTO teams (name, category, color, coach, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                         ("TBC Seniors", "Seniors", "#e4572e", "Coach TBC", "Équipe fanion du club.", datetime.now().isoformat()))
        youth = execute("INSERT INTO teams (name, category, color, coach, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        ("TBC U18", "U18", "#1d3557", "À définir", "La relève du club.", datetime.now().isoformat()))
        players = [("Fallou", "Ndiaye", "1998-04-12", 7, "Meneur", senior, "77 000 00 00"),
                   ("Awa", "Diop", "2001-09-22", 11, "Ailier", senior, "76 000 00 00"),
                   ("Mamadou", "Sarr", "2008-01-05", 4, "Arrière", youth, "78 000 00 00")]
        for first, last, birth, jersey, position, team_id, phone in players:
            player_id = execute("INSERT INTO players (first_name,last_name,birth_date,jersey_number,position,team_id,phone,status,registration_date) VALUES (?,?,?,?,?,?,?,?,?)",
                                (first, last, birth, jersey, position, team_id, phone, "Actif", date.today().isoformat()))
            execute("INSERT INTO player_statistics (player_id, games, points, rebounds, assists, steals, blocks, fouls) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (player_id, 8, jersey * 2, jersey, 5, 3, 1, 4))
        for team_id, games, wins, losses, points_for, points_against in [(senior, 8, 6, 2, 524, 476), (youth, 5, 3, 2, 281, 264)]:
            execute("INSERT INTO team_statistics (team_id, games, wins, losses, points_for, points_against) VALUES (?, ?, ?, ?, ?, ?)", (team_id, games, wins, losses, points_for, points_against))
        execute("INSERT INTO matches (team_id, opponent, match_date, match_time, venue, competition, status, home_score, away_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (senior, "ASC Ville", date.today().isoformat(), "18:30", "Terrain TBC", "Championnat régional", "À venir", 0, 0))
        execute("INSERT INTO matches (team_id, opponent, match_date, match_time, venue, competition, status, home_score, away_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (senior, "BC Saloum", "2026-08-28", "17:00", "Thiès", "Coupe du Sénégal", "Terminé", 72, 64))
    seed_classes_and_systems()
    get_db().commit()


def seed_classes_and_systems():
    """Adds useful defaults once, without changing existing club records."""
    category_defaults = [
        ("U10", "6-9 ans", "Mixte"), ("U12", "10-11 ans", "Mixte"),
        ("U14", "12-13 ans", "Mixte"), ("U16", "14-15 ans", "Mixte"),
        ("U18", "16-17 ans", "Mixte"), ("U20", "18-19 ans", "Mixte"),
        ("Seniors", "20 ans et +", "Mixte"), ("Féminines", "Toutes catégories", "Féminines"),
        ("Loisirs", "Adultes", "Mixte"),
    ]
    for name, age_range, gender in category_defaults:
        execute("INSERT OR IGNORE INTO categories (name, age_range, gender, status, created_at) VALUES (?, ?, ?, 'active', ?)",
                (name, age_range, gender, datetime.now().isoformat()))
    execute("INSERT OR IGNORE INTO category_players (category_id, player_id) SELECT c.id, p.id FROM categories c JOIN teams t ON t.category = c.name JOIN players p ON p.team_id = t.id")
    system_defaults = [
        ("Pick and Roll", "attaque", 5, "Créer un avantage à deux joueurs.", "Mettre la défense en difficulté sur écran porteur."),
        ("Zone 2-3", "défense", 5, "Protéger la raquette et fermer les pénétrations.", "Contrôler le rebond et les lignes de passe."),
        ("Homme à homme", "défense", 5, "Responsabiliser chaque défenseur.", "Contenir, aider, reprendre son joueur."),
        ("Fast Break", "transition", 5, "Jouer vite après récupération.", "Écarter le terrain et courir les couloirs."),
        ("Motion Offense", "attaque", 5, "Créer du mouvement et des tirs ouverts.", "Passer, couper, poser des écrans."),
    ]
    for name, system_type, player_count, description, objective in system_defaults:
        if not query("SELECT id FROM systems WHERE name=? LIMIT 1", (name,), one=True):
            execute("INSERT INTO systems (name, system_type, player_count, description, objective, status, positions_json, created_at) VALUES (?, ?, ?, ?, ?, 'active', '[]', ?)",
                (name, system_type, player_count, description, objective, datetime.now().isoformat()))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Connectez-vous pour accéder à cet espace.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_globals():
    return {"club_name": app.config["CLUB_NAME"], "club_short": app.config["CLUB_SHORT"], "current_year": datetime.now().year}


@app.route("/", methods=["GET"])
@login_required
def dashboard():
    upcoming = query("SELECT m.*, t.name AS team_name FROM matches m LEFT JOIN teams t ON t.id=m.team_id WHERE m.status IN ('À venir','En cours') ORDER BY m.match_date, m.match_time LIMIT 4")
    recent = query("SELECT m.*, t.name AS team_name FROM matches m LEFT JOIN teams t ON t.id=m.team_id WHERE m.status='Terminé' ORDER BY m.match_date DESC LIMIT 4")
    stats = {"players": query("SELECT COUNT(*) c FROM players", one=True)["c"], "teams": query("SELECT COUNT(*) c FROM teams", one=True)["c"], "matches": query("SELECT COUNT(*) c FROM matches", one=True)["c"], "reservations": query("SELECT COUNT(*) c FROM reservations WHERE status='En attente'", one=True)["c"]}
    return render_template("dashboard.html", active="dashboard", upcoming=upcoming, recent=recent, stats=stats)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = query("SELECT * FROM users WHERE username = ?", (request.form.get("username", "").strip(),), one=True)
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Identifiants incorrects.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/players")
@login_required
def players():
    search = request.args.get("q", "").strip()
    team_id = request.args.get("team", "")
    position = request.args.get("position", "")
    sql = "SELECT p.*, t.name AS team_name FROM players p LEFT JOIN teams t ON t.id=p.team_id WHERE (p.first_name || ' ' || p.last_name) LIKE ?"
    params = [f"%{search}%"]
    if team_id:
        sql += " AND p.team_id = ?"; params.append(team_id)
    if position:
        sql += " AND p.position = ?"; params.append(position)
    sql += " ORDER BY p.last_name, p.first_name"
    return render_template("players.html", active="players", players=query(sql, params), teams=query("SELECT * FROM teams ORDER BY category, name"), search=search, position=position, team_id=team_id)


@app.route("/players/new", methods=["GET", "POST"])
@login_required
def player_new():
    teams_list = query("SELECT * FROM teams ORDER BY category, name")
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        if not first_name or not last_name:
            flash("Le prénom et le nom sont obligatoires.", "danger")
        else:
            player_id = execute("INSERT INTO players (first_name,last_name,birth_date,jersey_number,position,team_id,phone,address,height,status,registration_date) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                (first_name, last_name, request.form.get("birth_date") or None, request.form.get("jersey_number") or None,
                                 request.form.get("position") or None, request.form.get("team_id") or None, request.form.get("phone"),
                                 request.form.get("address"), request.form.get("height") or None, request.form.get("status") or "Actif", date.today().isoformat()))
            execute("INSERT INTO player_statistics (player_id) VALUES (?)", (player_id,))
            flash("Joueur ajouté avec succès.", "success")
            return redirect(url_for("players"))
    return render_template("player_form.html", active="players", player=None, teams=teams_list, form_title="Ajouter un joueur")


@app.post("/players/<int:player_id>/delete")
@login_required
def player_delete(player_id):
    execute("DELETE FROM players WHERE id = ?", (player_id,))
    flash("Joueur supprimé.", "success")
    return redirect(url_for("players"))


@app.route("/teams")
@login_required
def teams():
    rows = query("SELECT t.*, COUNT(p.id) AS player_count FROM teams t LEFT JOIN players p ON p.team_id=t.id GROUP BY t.id ORDER BY t.category, t.name")
    return render_template("teams.html", active="teams", teams=rows)


@app.route("/teams/new", methods=["GET", "POST"])
@login_required
def team_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        if not name or not category:
            flash("Le nom et la catégorie sont obligatoires.", "danger")
        else:
            team_id = execute("INSERT INTO teams (name,category,color,coach,description,created_at) VALUES (?,?,?,?,?,?)",
                              (name, category, request.form.get("color") or "#e4572e", request.form.get("coach"), request.form.get("description"), datetime.now().isoformat()))
            execute("INSERT INTO team_statistics (team_id) VALUES (?)", (team_id,))
            flash("Équipe créée avec succès.", "success")
            return redirect(url_for("teams"))
    return render_template("team_form.html", active="teams", form_title="Créer une équipe")


@app.post("/teams/<int:team_id>/delete")
@login_required
def team_delete(team_id):
    execute("DELETE FROM teams WHERE id = ?", (team_id,))
    flash("Équipe supprimée.", "success")
    return redirect(url_for("teams"))


@app.route("/matches")
@login_required
def matches():
    status = request.args.get("status", "")
    sql = "SELECT m.*, t.name AS team_name FROM matches m LEFT JOIN teams t ON t.id=m.team_id"
    params = []
    if status:
        sql += " WHERE m.status = ?"; params.append(status)
    sql += " ORDER BY m.match_date DESC, m.match_time DESC"
    return render_template("matches.html", active="matches", matches=query(sql, params), status=status)


@app.route("/matches/new", methods=["GET", "POST"])
@login_required
def match_new():
    teams_list = query("SELECT * FROM teams ORDER BY category, name")
    if request.method == "POST":
        opponent = request.form.get("opponent", "").strip()
        match_date = request.form.get("match_date", "").strip()
        if not opponent or not match_date:
            flash("L'adversaire et la date sont obligatoires.", "danger")
        else:
            execute("INSERT INTO matches (team_id,opponent,match_date,match_time,venue,competition,status,home_score,away_score) VALUES (?,?,?,?,?,?,?,?,?)",
                    (request.form.get("team_id") or None, opponent, match_date, request.form.get("match_time"), request.form.get("venue"), request.form.get("competition"), request.form.get("status") or "À venir", int(request.form.get("home_score") or 0), int(request.form.get("away_score") or 0)))
            flash("Match enregistré.", "success")
            return redirect(url_for("matches"))
    return render_template("match_form.html", active="matches", teams=teams_list, form_title="Programmer un match")


@app.post("/matches/<int:match_id>/delete")
@login_required
def match_delete(match_id):
    execute("DELETE FROM matches WHERE id = ?", (match_id,))
    flash("Match supprimé.", "success")
    return redirect(url_for("matches"))


@app.route("/reservations")
@login_required
def reservations():
    return render_template("reservations.html", active="reservations", reservations=query("SELECT * FROM reservations ORDER BY reservation_date DESC, start_time DESC"))


@app.route("/reservations/new", methods=["GET", "POST"])
@login_required
def reservation_new():
    if request.method == "POST":
        required = [request.form.get("requester", "").strip(), request.form.get("reservation_date", ""), request.form.get("start_time", ""), request.form.get("end_time", "")]
        if not all(required):
            flash("Demandeur, date et horaires sont obligatoires.", "danger")
        else:
            execute("INSERT INTO reservations (requester,phone,reservation_date,start_time,end_time,reason,status) VALUES (?,?,?,?,?,?,?)",
                    (required[0], request.form.get("phone"), required[1], required[2], required[3], request.form.get("reason"), request.form.get("status") or "En attente"))
            flash("Réservation créée.", "success")
            return redirect(url_for("reservations"))
    return render_template("reservation_form.html", active="reservations", form_title="Nouvelle réservation")


@app.post("/reservations/<int:reservation_id>/delete")
@login_required
def reservation_delete(reservation_id):
    execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))
    flash("Réservation supprimée.", "success")
    return redirect(url_for("reservations"))


@app.route("/venue")
@login_required
def venue():
    return render_template("venue.html", active="venue", venue=query("SELECT * FROM venue WHERE id=1", one=True))


@app.route("/classes-systems", methods=["GET", "POST"])
@login_required
def classes_systems():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "category":
            name = request.form.get("name", "").strip()
            if not name:
                flash("Le nom de la catégorie est obligatoire.", "danger")
            else:
                category_id = execute("INSERT INTO categories (name, age_range, gender, coach, description, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                      (name, request.form.get("age_range"), request.form.get("gender", "Mixte"), request.form.get("coach"), request.form.get("description"), request.form.get("status", "active"), datetime.now().isoformat()))
                for player_id in request.form.getlist("player_ids"):
                    execute("INSERT OR IGNORE INTO category_players (category_id, player_id) VALUES (?, ?)", (category_id, player_id))
                flash("Catégorie créée.", "success")
        elif action == "system":
            name = request.form.get("name", "").strip()
            if not name:
                flash("Le nom du système est obligatoire.", "danger")
            else:
                system_id = execute("INSERT INTO systems (name, system_type, player_count, description, objective, key_points, instructions, coach, status, positions_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                    (name, request.form.get("system_type", "attaque"), int(request.form.get("player_count") or 5), request.form.get("description"), request.form.get("objective"), request.form.get("key_points"), request.form.get("instructions"), request.form.get("coach"), request.form.get("status", "active"), "[]", datetime.now().isoformat()))
                for category_id in request.form.getlist("category_ids"):
                    execute("INSERT OR IGNORE INTO system_categories (system_id, category_id) VALUES (?, ?)", (system_id, category_id))
                flash("Système de jeu créé.", "success")
        return redirect(url_for("classes_systems"))
    categories = query("SELECT c.*, COUNT(cp.player_id) AS player_count FROM categories c LEFT JOIN category_players cp ON cp.category_id=c.id GROUP BY c.id ORDER BY c.name")
    systems = query("SELECT s.*, GROUP_CONCAT(c.name, ', ') AS category_names FROM systems s LEFT JOIN system_categories sc ON sc.system_id=s.id LEFT JOIN categories c ON c.id=sc.category_id GROUP BY s.id ORDER BY s.created_at DESC")
    players_list = query("SELECT id, first_name, last_name FROM players ORDER BY last_name, first_name")
    return render_template("classes_systems.html", active="classes", categories=categories, systems=systems, players=players_list)


@app.route("/classes-systems/categories/<int:category_id>")
@login_required
def category_detail(category_id):
    category = query("SELECT c.*, COUNT(cp.player_id) AS player_count FROM categories c LEFT JOIN category_players cp ON cp.category_id=c.id WHERE c.id=? GROUP BY c.id", (category_id,), one=True)
    if not category:
        return redirect(url_for("classes_systems"))
    players_list = query("SELECT p.* FROM players p JOIN category_players cp ON cp.player_id=p.id WHERE cp.category_id=? ORDER BY p.last_name", (category_id,))
    return render_template("category_detail.html", active="classes", category=category, players=players_list)


@app.route("/classes-systems/categories/<int:category_id>/edit", methods=["GET", "POST"])
@login_required
def category_edit(category_id):
    category = query("SELECT * FROM categories WHERE id=?", (category_id,), one=True)
    if not category:
        return redirect(url_for("classes_systems"))
    players_list = query("SELECT id, first_name, last_name FROM players ORDER BY last_name, first_name")
    if request.method == "POST":
        execute("UPDATE categories SET name=?, age_range=?, gender=?, coach=?, description=?, status=? WHERE id=?",
                (request.form.get("name", "").strip(), request.form.get("age_range"), request.form.get("gender"), request.form.get("coach"), request.form.get("description"), request.form.get("status"), category_id))
        execute("DELETE FROM category_players WHERE category_id=?", (category_id,))
        for player_id in request.form.getlist("player_ids"):
            execute("INSERT OR IGNORE INTO category_players (category_id, player_id) VALUES (?,?)", (category_id, player_id))
        flash("Catégorie modifiée.", "success")
        return redirect(url_for("category_detail", category_id=category_id))
    selected = {row["player_id"] for row in query("SELECT player_id FROM category_players WHERE category_id=?", (category_id,))}
    return render_template("category_form.html", active="classes", category=category, players=players_list, selected=selected, form_title="Modifier la catégorie")


@app.post("/classes-systems/categories/<int:category_id>/delete")
@login_required
def category_delete(category_id):
    execute("DELETE FROM categories WHERE id=?", (category_id,))
    flash("Catégorie supprimée.", "success")
    return redirect(url_for("classes_systems"))


@app.route("/classes-systems/systems/<int:system_id>")
@login_required
def system_detail(system_id):
    system = query("SELECT s.*, GROUP_CONCAT(c.name, ', ') AS category_names FROM systems s LEFT JOIN system_categories sc ON sc.system_id=s.id LEFT JOIN categories c ON c.id=sc.category_id WHERE s.id=? GROUP BY s.id", (system_id,), one=True)
    if not system:
        return redirect(url_for("classes_systems"))
    categories = query("SELECT c.* FROM categories c JOIN system_categories sc ON sc.category_id=c.id WHERE sc.system_id=?", (system_id,))
    players_list = query("SELECT p.*, sp.role FROM players p JOIN system_players sp ON sp.player_id=p.id WHERE sp.system_id=? ORDER BY p.last_name", (system_id,))
    return render_template("system_detail.html", active="classes", system=system, categories=categories, players=players_list,
                           positions=json.loads(system["positions_json"] or "[]"))


@app.route("/classes-systems/systems/<int:system_id>/edit", methods=["GET", "POST"])
@login_required
def system_edit(system_id):
    system = query("SELECT * FROM systems WHERE id=?", (system_id,), one=True)
    if not system:
        return redirect(url_for("classes_systems"))
    categories = query("SELECT * FROM categories ORDER BY name")
    if request.method == "POST":
        execute("UPDATE systems SET name=?, system_type=?, player_count=?, description=?, objective=?, key_points=?, instructions=?, coach=?, status=? WHERE id=?",
                (request.form.get("name", "").strip(), request.form.get("system_type"), int(request.form.get("player_count") or 5), request.form.get("description"), request.form.get("objective"), request.form.get("key_points"), request.form.get("instructions"), request.form.get("coach"), request.form.get("status"), system_id))
        execute("DELETE FROM system_categories WHERE system_id=?", (system_id,))
        for category_id in request.form.getlist("category_ids"):
            execute("INSERT OR IGNORE INTO system_categories (system_id, category_id) VALUES (?,?)", (system_id, category_id))
        flash("Système modifié.", "success")
        return redirect(url_for("system_detail", system_id=system_id))
    selected = {row["category_id"] for row in query("SELECT category_id FROM system_categories WHERE system_id=?", (system_id,))}
    return render_template("system_form.html", active="classes", system=system, categories=categories, selected=selected, form_title="Modifier le système")


@app.post("/classes-systems/systems/<int:system_id>/delete")
@login_required
def system_delete(system_id):
    execute("DELETE FROM systems WHERE id=?", (system_id,))
    flash("Système supprimé.", "success")
    return redirect(url_for("classes_systems"))


@app.post("/classes-systems/systems/<int:system_id>/duplicate")
@login_required
def system_duplicate(system_id):
    system = query("SELECT * FROM systems WHERE id=?", (system_id,), one=True)
    if system:
        new_id = execute("INSERT INTO systems (name, system_type, player_count, description, objective, key_points, instructions, coach, status, positions_json, created_at) SELECT name || ' (copie)', system_type, player_count, description, objective, key_points, instructions, coach, 'active', positions_json, ? FROM systems WHERE id=?", (datetime.now().isoformat(), system_id))
        execute("INSERT INTO system_categories SELECT ?, category_id FROM system_categories WHERE system_id=?", (new_id, system_id))
        flash("Système dupliqué.", "success")
    return redirect(url_for("classes_systems"))


@app.post("/classes-systems/systems/<int:system_id>/training")
@login_required
def system_training(system_id):
    system = query("SELECT name FROM systems WHERE id=?", (system_id,), one=True)
    if system:
        flash(f"{system['name']} est prêt pour l'entraînement.", "success")
    return redirect(url_for("system_detail", system_id=system_id))


@app.post("/classes-systems/systems/<int:system_id>/positions")
@login_required
def system_positions(system_id):
    data = request.get_json(silent=True) or {}
    positions = data.get("positions", [])
    if not isinstance(positions, list):
        return {"ok": False, "message": "Positions invalides."}, 400
    execute("UPDATE systems SET positions_json=? WHERE id=?", (json.dumps(positions), system_id))
    return {"ok": True, "message": "Tableau tactique enregistré."}


@app.route("/statistics")
@login_required
def statistics():
    players_stats = query("SELECT p.first_name, p.last_name, t.name AS team_name, s.* FROM player_statistics s JOIN players p ON p.id=s.player_id LEFT JOIN teams t ON t.id=p.team_id ORDER BY s.points DESC")
    team_stats = query("SELECT t.name, t.category, s.*, (s.points_for-s.points_against) AS difference FROM team_statistics s JOIN teams t ON t.id=s.team_id ORDER BY s.wins DESC")
    totals = {
        "points_for": sum(row["points_for"] or 0 for row in team_stats),
        "wins": sum(row["wins"] or 0 for row in team_stats),
        "top_points": players_stats[0]["points"] if players_stats else 0,
    }
    return render_template("statistics.html", active="statistics", players_stats=players_stats, team_stats=team_stats, totals=totals)


@app.route("/scoreboard")
@login_required
def scoreboard():
    match_id = request.args.get("match_id", type=int)
    matches_list = query("SELECT m.*, t.name AS team_name FROM matches m LEFT JOIN teams t ON t.id=m.team_id ORDER BY m.match_date DESC, m.match_time DESC")
    selected_match = query("SELECT m.*, t.name AS team_name FROM matches m LEFT JOIN teams t ON t.id=m.team_id WHERE m.id = ?", (match_id,), one=True) if match_id else (matches_list[0] if matches_list else None)
    return render_template("scoreboard.html", active="scoreboard", matches=matches_list, selected_match=selected_match)


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", active="settings")


@app.route("/api/scoreboard", methods=["POST"])
@login_required
def save_scoreboard():
    data = request.get_json(silent=True) or {}
    match_id = data.get("match_id")
    if not match_id:
        return {"ok": False, "message": "Sélectionnez un match TBC."}, 400
    execute("UPDATE matches SET home_score = ?, away_score = ?, status = ? WHERE id = ?",
            (max(0, int(data.get("home", 0))), max(0, int(data.get("away", 0))), data.get("status", "En cours"), match_id))
    return {"ok": True, "message": "Score du match TBC enregistré"}


@app.cli.command("init-db")
def init_db_command():
    init_db()
    print("Base TBC initialisée.")


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
