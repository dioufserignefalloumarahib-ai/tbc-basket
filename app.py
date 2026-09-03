from flask import Flask

app = Flask(__name__)


@app.route('/')
def home():
    return '''
    <h1>🏀 TBC THIADIAYE</h1>
    <p>Le site est en ligne !</p>
    '''


if __name__ == '__main__':
    app.run()