from flask import Flask

app = Flask(__name__)


@app.route('/')
def home():
    return '''
    <html>
    <head>
        <title>TBC Thiadiaye</title>
        <style>
            body { font-family: Arial; background: #FF6B00; color: white; text-align: center; padding: 50px; }
            h1 { font-size: 50px; }
            .btn { background: white; color: #FF6B00; padding: 15px 30px; margin: 10px; text-decoration: none; border-radius: 10px; display: inline-block; }
        </style>
    </head>
    <body>
        <h1>🏀 TBC THIADIAYE</h1>
        <p>Thiadiaye Basket Club - La fierté de la commune</p>
        <br>
        <a href="/matchs" class="btn">Prochains Matchs</a>
        <a href="/joueurs" class="btn">Notre Effectif</a>
    </body>
    </html>
    '''


@app.route('/matchs')
def matchs():
    return '<h1>Prochains Matchs</h1><p>Dimanche 14h vs ASC Thiadiaye</p><a href="/">Retour</a>'


@app.route('/joueurs')
def joueurs():
    return '<h1>Notre Effectif</h1><p>Liste des joueurs à venir...</p><a href="/">Retour</a>'


if __name__ == '__main__':
    app.run()