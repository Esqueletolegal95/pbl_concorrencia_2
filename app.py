from flask import Flask, jsonify, render_template, request
import requests


contas = {}
numero_de_contas = 0

app = Flask(__name__)

# Adicione esta rota em app.py
@app.route('/submit', methods=['POST'])
def submit():
    global numero_de_contas
    conta = {}
    conta['nome'] = request.form["name"]
    conta['senha'] = request.form["senha"]
    conta['tipo_de_conta'] = request.form["tipo_de_conta"]
    conta['valor'] = 1000
    contas[numero_de_contas] = conta
    numero_de_contas += 1
    return jsonify(conta)


@app.route('/fazer_transferencia', methods=['POST'])
def fazer_transferencia():
    from_conta_id = int(request.form['from_conta_id'])
    ip_destino = request.form["ip_destino"]
    to_conta_id = int(request.form['to_conta_id'])
    valor_transferencia = float(request.form['valor'])

    # Verificar se a conta de origem existe
    if from_conta_id not in contas:
        return jsonify({"error": "A conta de origem não existe."}), 400

    # Verificar se a conta de origem tem fundos suficientes
    if contas[from_conta_id]['valor'] < valor_transferencia:
        return jsonify({"error": "Fundos insuficientes na conta de origem."}), 400

    # Enviar solicitação ao servidor de destino para validar a transferência
    transfer_data = {
        'to_conta_id': to_conta_id,
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
    contas[from_conta_id]['valor'] -= valor_transferencia

    return jsonify({
        "from_conta_id": from_conta_id,
        "to_conta_id": to_conta_id,
        "valor_transferencia": valor_transferencia,
        "novo_saldo_from_conta": contas[from_conta_id]['valor']
    })


@app.route('/receber_transferencia', methods=['POST'])
def receber_transferencia():
    to_conta_id = int(request.json['to_conta_id'])
    valor_transferencia = float(request.json['valor'])

    # Verificar se a conta de destino existe
    if to_conta_id not in contas:
        return jsonify({"error": "A conta de destino não existe."}), 400

    # Acknowledgment da transferência
    contas[to_conta_id]['valor'] += valor_transferencia
    return jsonify({"status": "ACK"})
    
    
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
    app.run(host='0.0.0.0', port=5000)
