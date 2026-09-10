from __future__ import annotations

import os
import sqlite3
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
    get_db().commit()


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


@app.route("/teams")
@login_required
def teams():
    rows = query("SELECT t.*, COUNT(p.id) AS player_count FROM teams t LEFT JOIN players p ON p.team_id=t.id GROUP BY t.id ORDER BY t.category, t.name")
    return render_template("teams.html", active="teams", teams=rows)


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


@app.route("/reservations")
@login_required
def reservations():
    return render_template("reservations.html", active="reservations", reservations=query("SELECT * FROM reservations ORDER BY reservation_date DESC, start_time DESC"))


@app.route("/venue")
@login_required
def venue():
    return render_template("venue.html", active="venue", venue=query("SELECT * FROM venue WHERE id=1", one=True))


@app.route("/statistics")
@login_required
def statistics():
    players_stats = query("SELECT p.first_name, p.last_name, t.name AS team_name, s.* FROM player_statistics s JOIN players p ON p.id=s.player_id LEFT JOIN teams t ON t.id=p.team_id ORDER BY s.points DESC")
    team_stats = query("SELECT t.name, t.category, s.*, (s.points_for-s.points_against) AS difference FROM team_statistics s JOIN teams t ON t.id=s.team_id ORDER BY s.wins DESC")
    return render_template("statistics.html", active="statistics", players_stats=players_stats, team_stats=team_stats)


@app.route("/scoreboard")
@login_required
def scoreboard():
    return render_template("scoreboard.html", active="scoreboard")


@app.route("/nba")
@login_required
def nba():
    games = query("SELECT * FROM nba_games ORDER BY CASE status WHEN 'LIVE' THEN 1 WHEN 'À VENIR' THEN 2 ELSE 3 END, start_time")
    return render_template("nba.html", active="nba", games=games, api_ready=bool(os.environ.get("NBA_API_KEY")))


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", active="settings")


@app.route("/api/scoreboard", methods=["POST"])
@login_required
def save_scoreboard():
    return {"ok": True, "message": "Score enregistré côté session"}


@app.cli.command("init-db")
def init_db_command():
    init_db()
    print("Base TBC initialisée.")


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
