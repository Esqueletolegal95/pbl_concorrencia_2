from flask import Flask, jsonify, render_template, request
import requests

# Inicialização da aplicação Flask
app = Flask(__name__)

# Simulação de uma única conta
conta = {
    'nome': '',
    'tipo': '',
    'valor': 0
}

# Rota para definir a conta
@app.route('/submit', methods=['POST'])
def submit():
    conta['nome'] = request.form["name"]
    conta['tipo'] = request.form["tipo_de_conta"]
    conta['valor'] = 1000  # Valor inicial da conta

    return jsonify(conta)

# Rota para fazer transferência
@app.route('/fazer_transferencia', methods=['POST'])
def fazer_transferencia():
    ip_destino = request.form["ip_destino"]
    to_conta_id = int(request.form['to_conta_id'])
    valor_transferencia = float(request.form['valor'])

    # Verificar se a conta tem fundos suficientes
    if conta['valor'] < valor_transferencia:
        return jsonify({"error": "Fundos insuficientes na conta de origem."}), 400

    # Enviar solicitação ao servidor de destino para validar a transferência
    transfer_data = {
        'valor': valor_transferencia
    }
    try:
        response = requests.post(f'http://{ip_destino}:5000/receber_transferencia', json=transfer_data)
        response_data = response.json()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Erro na comunicação com o servidor de destino: {str(e)}"}), 500

    # Verificar a resposta do servidor de destino
    if response.status_code != 200 or response_data.get('status') != 'ACK':
        return jsonify({"error": "A transferência não foi validada pelo servidor de destino."}), 400

    # Realizar a transferência
    conta['valor'] -= valor_transferencia

    return jsonify({
        "to_conta_id": to_conta_id,
        "valor_transferencia": valor_transferencia,
        "novo_saldo": conta['valor']
    })

# Rota para receber transferência
@app.route('/receber_transferencia', methods=['POST'])
def receber_transferencia():
    valor_transferencia = float(request.json['valor'])

    # Acknowledgment da transferência
    conta['valor'] += valor_transferencia
    return jsonify({"status": "ACK", "novo_saldo": conta['valor']})

# Rota para renderizar a página inicial
@app.route('/')
def home():
    return render_template('index.html')

# Rota para renderizar a página de login
@app.route('/login')
def login():
    return render_template('login.html')

# Rota para renderizar a página de cadastro
@app.route('/cadastro')
def cadastro():
    return render_template('cadastro.html')

# Inicialização do servidor
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
