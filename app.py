import os

from flask import Flask, render_template, request, redirect, url_for
from database import init_database, get_connection

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")

init_database()


@app.route("/")
def accueil():
    connection = get_connection()
    terrain = connection.execute("SELECT * FROM terrain ORDER BY id LIMIT 1").fetchone()
    joueurs_total = connection.execute("SELECT COUNT(*) AS total FROM joueurs").fetchone()["total"]
    equipes_total = connection.execute("SELECT COUNT(*) AS total FROM equipes").fetchone()["total"]
    matchs_total = connection.execute("SELECT COUNT(*) AS total FROM matchs").fetchone()["total"]
    connection.close()

    return render_template(
        "index.html",
        terrain=terrain,
        joueurs_total=joueurs_total,
        equipes_total=equipes_total,
        matchs_total=matchs_total,
    )


@app.route("/joueurs", methods=["GET", "POST"])
def joueurs():
    if request.method == "POST":
        nom = (request.form.get("nom") or "").strip()
        prenom = (request.form.get("prenom") or "").strip()
        age = request.form.get("age") or None
        poste = (request.form.get("poste") or "").strip()
        numero = request.form.get("numero") or None
        equipe = (request.form.get("equipe") or "").strip()

        if nom and prenom:
            connection = get_connection()
            connection.execute(
                "INSERT INTO joueurs (nom, prenom, age, poste, numero, equipe) VALUES (?, ?, ?, ?, ?, ?)",
                (nom, prenom, age, poste or None, numero, equipe or None),
            )
            connection.commit()
            connection.close()

        return redirect(url_for("joueurs"))

    connection = get_connection()
    joueurs = connection.execute("SELECT * FROM joueurs ORDER BY nom, prenom").fetchall()
    connection.close()
    return render_template("joueurs.html", joueurs=joueurs)


@app.route("/joueurs/modifier/<int:id>", methods=["GET", "POST"])
def modifier_joueur(id):
    connection = get_connection()
    joueur = connection.execute("SELECT * FROM joueurs WHERE id = ?", (id,)).fetchone()

    if request.method == "POST":
        nom = (request.form.get("nom") or "").strip()
        prenom = (request.form.get("prenom") or "").strip()
        age = request.form.get("age") or None
        poste = (request.form.get("poste") or "").strip()
        numero = request.form.get("numero") or None
        equipe = (request.form.get("equipe") or "").strip()

        if nom and prenom and joueur:
            connection.execute(
                "UPDATE joueurs SET nom = ?, prenom = ?, age = ?, poste = ?, numero = ?, equipe = ? WHERE id = ?",
                (nom, prenom, age, poste or None, numero, equipe or None, id),
            )
            connection.commit()
            connection.close()
            return redirect(url_for("joueurs"))

    if joueur is None:
        connection.close()
        return redirect(url_for("joueurs"))

    connection.close()
    return render_template("modifier_joueur.html", joueur=joueur)


@app.route("/joueurs/supprimer/<int:id>", methods=["POST"])
def supprimer_joueur(id):
    connection = get_connection()
    connection.execute("DELETE FROM joueurs WHERE id = ?", (id,))
    connection.commit()
    connection.close()
    return redirect(url_for("joueurs"))


@app.route("/equipes", methods=["GET", "POST"])
def equipes():
    if request.method == "POST":
        nom = (request.form.get("nom") or "").strip()
        categorie = (request.form.get("categorie") or "").strip()
        entraineur = (request.form.get("entraineur") or "").strip()

        if nom:
            connection = get_connection()
            connection.execute(
                "INSERT INTO equipes (nom, categorie, entraineur) VALUES (?, ?, ?)",
                (nom, categorie or None, entraineur or None),
            )
            connection.commit()
            connection.close()

        return redirect(url_for("equipes"))

    connection = get_connection()
    equipes = connection.execute("SELECT * FROM equipes ORDER BY nom").fetchall()
    connection.close()
    return render_template("equipes.html", equipes=equipes)


@app.route("/equipes/modifier/<int:id>", methods=["GET", "POST"])
def modifier_equipe(id):
    connection = get_connection()
    equipe = connection.execute("SELECT * FROM equipes WHERE id = ?", (id,)).fetchone()

    if request.method == "POST":
        nom = (request.form.get("nom") or "").strip()
        categorie = (request.form.get("categorie") or "").strip()
        entraineur = (request.form.get("entraineur") or "").strip()

        if nom and equipe:
            connection.execute(
                "UPDATE equipes SET nom = ?, categorie = ?, entraineur = ? WHERE id = ?",
                (nom, categorie or None, entraineur or None, id),
            )
            connection.commit()
            connection.close()
            return redirect(url_for("equipes"))

    if equipe is None:
        connection.close()
        return redirect(url_for("equipes"))

    connection.close()
    return render_template("modifier_equipe.html", equipe=equipe)


@app.route("/equipes/supprimer/<int:id>", methods=["POST"])
def supprimer_equipe(id):
    connection = get_connection()
    connection.execute("DELETE FROM equipes WHERE id = ?", (id,))
    connection.commit()
    connection.close()
    return redirect(url_for("equipes"))


@app.route("/matchs", methods=["GET", "POST"])
def matchs():
    if request.method == "POST":
        domicile = (request.form.get("equipe_domicile") or "").strip()
        exterieur = (request.form.get("equipe_exterieure") or "").strip()
        date_match = request.form.get("date_match") or None
        heure = request.form.get("heure") or None
        score_domicile = request.form.get("score_domicile") or 0
        score_exterieur = request.form.get("score_exterieur") or 0
        minuteurs_domicile = (request.form.get("minuteurs_domicile") or "").strip()
        minuteurs_exterieur = (request.form.get("minuteurs_exterieur") or "").strip()

        if domicile and exterieur:
            connection = get_connection()
            connection.execute(
                "INSERT INTO matchs (equipe_domicile, equipe_exterieure, date_match, heure, score_domicile, score_exterieur, minuteurs_domicile, minuteurs_exterieur) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (domicile, exterieur, date_match, heure, score_domicile, score_exterieur, minuteurs_domicile or None, minuteurs_exterieur or None),
            )
            connection.commit()
            connection.close()

        return redirect(url_for("matchs"))

    connection = get_connection()
    matchs = connection.execute("SELECT * FROM matchs ORDER BY date_match DESC, heure DESC").fetchall()
    connection.close()
    return render_template("matchs.html", matchs=matchs)


@app.route("/matchs/modifier/<int:id>", methods=["GET", "POST"])
def modifier_match(id):
    connection = get_connection()
    match = connection.execute("SELECT * FROM matchs WHERE id = ?", (id,)).fetchone()

    if request.method == "POST":
        domicile = (request.form.get("equipe_domicile") or "").strip()
        exterieur = (request.form.get("equipe_exterieure") or "").strip()
        date_match = request.form.get("date_match") or None
        heure = request.form.get("heure") or None
        score_domicile = request.form.get("score_domicile") or 0
        score_exterieur = request.form.get("score_exterieur") or 0
        minuteurs_domicile = (request.form.get("minuteurs_domicile") or "").strip()
        minuteurs_exterieur = (request.form.get("minuteurs_exterieur") or "").strip()

        if domicile and exterieur and match:
            connection.execute(
                "UPDATE matchs SET equipe_domicile = ?, equipe_exterieure = ?, date_match = ?, heure = ?, score_domicile = ?, score_exterieur = ?, minuteurs_domicile = ?, minuteurs_exterieur = ? WHERE id = ?",
                (domicile, exterieur, date_match, heure, score_domicile, score_exterieur, minuteurs_domicile or None, minuteurs_exterieur or None, id),
            )
            connection.commit()
            connection.close()
            return redirect(url_for("matchs"))

    if match is None:
        connection.close()
        return redirect(url_for("matchs"))

    connection.close()
    return render_template("modifier_match.html", match=match)


@app.route("/matchs/supprimer/<int:id>", methods=["POST"])
def supprimer_match(id):
    connection = get_connection()
    connection.execute("DELETE FROM matchs WHERE id = ?", (id,))
    connection.commit()
    connection.close()
    return redirect(url_for("matchs"))


@app.route("/tournois", methods=["GET", "POST"])
def tournois():
    if request.method == "POST":
        nom = (request.form.get("nom") or "").strip()
        lieu = (request.form.get("lieu") or "").strip()
        date_debut = request.form.get("date_debut") or None
        date_fin = request.form.get("date_fin") or None
        description = (request.form.get("description") or "").strip()

        if nom:
            connection = get_connection()
            cursor = connection.execute(
                "INSERT INTO tournois (nom, lieu, date_debut, date_fin, description) VALUES (?, ?, ?, ?, ?)",
                (nom, lieu or None, date_debut, date_fin, description or None),
            )
            connection.commit()
            tournoi_id = cursor.lastrowid
            connection.close()
            return redirect(url_for("detail_tournoi", id=tournoi_id))

        return redirect(url_for("tournois"))

    connection = get_connection()
    tournois = connection.execute(
        """
        SELECT tournois.*, COUNT(matchs.id) AS matchs_total
        FROM tournois
        LEFT JOIN matchs ON matchs.tournoi_id = tournois.id
        GROUP BY tournois.id
        ORDER BY tournois.date_debut DESC, tournois.id DESC
        """
    ).fetchall()
    connection.close()
    return render_template("tournois.html", tournois=tournois)


@app.route("/tournois/<int:id>", methods=["GET", "POST"])
def detail_tournoi(id):
    connection = get_connection()
    tournoi = connection.execute("SELECT * FROM tournois WHERE id = ?", (id,)).fetchone()

    if tournoi is None:
        connection.close()
        return redirect(url_for("tournois"))

    if request.method == "POST":
        domicile = (request.form.get("equipe_domicile") or "").strip()
        exterieur = (request.form.get("equipe_exterieure") or "").strip()
        date_match = request.form.get("date_match") or None
        heure = request.form.get("heure") or None

        if domicile and exterieur:
            connection.execute(
                "INSERT INTO matchs (equipe_domicile, equipe_exterieure, date_match, heure, tournoi_id) VALUES (?, ?, ?, ?, ?)",
                (domicile, exterieur, date_match, heure, id),
            )
            connection.commit()

    matchs = connection.execute(
        "SELECT * FROM matchs WHERE tournoi_id = ? ORDER BY date_match, heure, id",
        (id,),
    ).fetchall()
    connection.close()
    return render_template("tournoi_detail.html", tournoi=tournoi, matchs=matchs)


@app.route("/terrain", methods=["GET", "POST"])
def terrain():
    if request.method == "POST":
        nom = (request.form.get("nom") or "").strip()
        localisation = (request.form.get("localisation") or "").strip()
        description = (request.form.get("description") or "").strip()

        connection = get_connection()
        connection.execute(
            "UPDATE terrain SET nom = ?, localisation = ?, description = ? WHERE id = 1",
            (nom or "TBC", localisation or "Thiadiaye, Sénégal", description or "Terrain du club"),
        )
        connection.commit()
        connection.close()
        return redirect(url_for("terrain"))

    connection = get_connection()
    terrain = connection.execute("SELECT * FROM terrain ORDER BY id LIMIT 1").fetchone()
    connection.close()
    return render_template("terrain.html", terrain=terrain)


@app.route("/reservations", methods=["GET", "POST"])
def reservations():
    if request.method == "POST":
        nom = (request.form.get("nom") or "").strip()
        date_reservation = request.form.get("date_reservation") or None
        heure_debut = request.form.get("heure_debut") or None
        heure_fin = request.form.get("heure_fin") or None
        telephone = (request.form.get("telephone") or "").strip()

        if nom and date_reservation:
            connection = get_connection()
            connection.execute(
                "INSERT INTO reservations (nom, date_reservation, heure_debut, heure_fin, telephone) VALUES (?, ?, ?, ?, ?)",
                (nom, date_reservation, heure_debut, heure_fin, telephone or None),
            )
            connection.commit()
            connection.close()

        return redirect(url_for("reservations"))

    connection = get_connection()
    reservations = connection.execute("SELECT * FROM reservations ORDER BY date_reservation DESC, heure_debut DESC").fetchall()
    connection.close()
    return render_template("reservations.html", reservations=reservations)


@app.route("/reservations/modifier/<int:id>", methods=["GET", "POST"])
def modifier_reservation(id):
    connection = get_connection()
    reservation = connection.execute("SELECT * FROM reservations WHERE id = ?", (id,)).fetchone()

    if request.method == "POST":
        nom = (request.form.get("nom") or "").strip()
        date_reservation = request.form.get("date_reservation") or None
        heure_debut = request.form.get("heure_debut") or None
        heure_fin = request.form.get("heure_fin") or None
        telephone = (request.form.get("telephone") or "").strip()

        if nom and date_reservation and reservation:
            connection.execute(
                "UPDATE reservations SET nom = ?, date_reservation = ?, heure_debut = ?, heure_fin = ?, telephone = ? WHERE id = ?",
                (nom, date_reservation, heure_debut, heure_fin, telephone or None, id),
            )
            connection.commit()
            connection.close()
            return redirect(url_for("reservations"))

    if reservation is None:
        connection.close()
        return redirect(url_for("reservations"))

    connection.close()
    return render_template("modifier_reservation.html", reservation=reservation)


@app.route("/reservations/supprimer/<int:id>", methods=["POST"])
def supprimer_reservation(id):
    connection = get_connection()
    connection.execute("DELETE FROM reservations WHERE id = ?", (id,))
    connection.commit()
    connection.close()
    return redirect(url_for("reservations"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)