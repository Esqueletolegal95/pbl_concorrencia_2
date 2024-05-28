from flask import Flask, render_template, request
name =""
sigla =""

app = Flask(__name__)

# Adicione esta rota em app.py
@app.route('/submit', methods=['POST'])
def submit():
    global name
    global sigla
    name = request.form['name']
    senha = request.form['senha']
    return f'Olá, {name},{senha}!'


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/cadastro')
def cadastro():
    return render_template('cadastro.html')

if __name__ == '__main__':
    app.run(debug=True)
