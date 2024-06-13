from flask import Flask, jsonify, render_template, request
import requests
import threading
from queue import Queue

# Inicialização da aplicação Flask
app = Flask(__name__)

# Simulação de uma única conta
conta = {
    'nome': '',
    'tipo': '',
    'valor': 500
}

# Semáforo para controlar o acesso à região crítica
transfer_semaphore = threading.Semaphore(1)

# Fila para gerenciar as requisições de transferência
transfer_queue = Queue()

# Rota para retornar a conta
@app.route('/conta', methods=['GET'])
def get_conta():
    return jsonify(conta)

# Rota para definir a conta
@app.route('/submit', methods=['POST'])
def submit():
    conta['nome'] = request.form["name"]
    conta['tipo'] = request.form["tipo_de_conta"]
    conta['valor'] = 1000  # Valor inicial da conta

    return jsonify(conta)

# Função auxiliar para processar transferências complexas
def process_transfer_complex(transfer_data):
    ip_intermediario = transfer_data["ip_intermediario"]
    ip_final = transfer_data["ip_final"]
    to_conta_id = transfer_data['to_conta_id']
    valor_origem = transfer_data['valor_origem']
    valor_intermediario = transfer_data['valor_intermediario']

    # Verificar se a conta tem fundos suficientes para a parte do valor de origem
    if conta['valor'] < valor_origem:
        return {"error": "Fundos insuficientes na conta de origem."}, 400

    # Enviar solicitação ao servidor intermediário para realizar a transferência
    transfer_request_data_intermediario = {
        'valor': valor_intermediario,
        'ip_final': ip_final,
        'to_conta_id': to_conta_id
    }
    try:
        response_intermediario = requests.post(f'http://{ip_intermediario}/executar_transferencia', json=transfer_request_data_intermediario)
        response_data_intermediario = response_intermediario.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Erro na comunicação com o servidor intermediário: {str(e)}"}, 500

    # Verificar a resposta do servidor intermediário
    if response_intermediario.status_code != 200 or response_data_intermediario.get('status') != 'ACK':
        return {"error": "A transferência não foi validada pelo servidor intermediário."}, 400

    # Enviar solicitação ao servidor final para a parte do valor de origem
    transfer_request_data_final = {'valor': valor_origem}
    try:
        response_final = requests.post(f'http://{ip_final}/receber_transferencia', json=transfer_request_data_final)
        response_data_final = response_final.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Erro na comunicação com o servidor de destino final: {str(e)}"}, 500

    # Verificar a resposta do servidor final
    if response_final.status_code != 200 or response_data_final.get('status') != 'ACK':
        return {"error": "A transferência não foi validada pelo servidor de destino final."}, 400

    # Realizar a transferência
    conta['valor'] -= valor_origem
    print(f"Transferência enviada: {valor_origem} para {ip_final}")

    return {
        "to_conta_id": to_conta_id,
        "valor_transferencia": valor_origem + valor_intermediario,
        "novo_saldo": conta['valor']
    }

# Rota para fazer transferências complexas
@app.route('/fazer_transferencia_complexa', methods=['POST'])
def fazer_transferencia_complexa():
    transfer_data = {
        "ip_intermediario": request.form["ip_intermediario"],
        "ip_final": request.form["ip_final"],
        "to_conta_id": int(request.form['to_conta_id']),
        "valor_origem": float(request.form['valor_origem']),
        "valor_intermediario": float(request.form['valor_intermediario'])
    }

    # Adicionar a transferência na fila
    transfer_queue.put(transfer_data)

    # Processar a transferência em uma thread separada para não bloquear o servidor
    threading.Thread(target=process_queue_complex).start()

    return jsonify({"message": "Transferência complexa recebida e será processada em breve."})

# Função para processar a fila de transferências complexas
def process_queue_complex():
    while not transfer_queue.empty():
        transfer_data = transfer_queue.get()
        with transfer_semaphore:
            with app.app_context():
                result = process_transfer_complex(transfer_data)
                # Aqui, você pode enviar uma notificação de resultado se necessário
                print(f"Transferência complexa processada: {result}")

# Rota para receber transferência
@app.route('/receber_transferencia', methods=['POST'])
def receber_transferencia():
    valor_transferencia = float(request.json['valor'])

    # Acknowledgment da transferência
    conta['valor'] += valor_transferencia
    print(f"Transferência recebida: {valor_transferencia}")
    return jsonify({"status": "ACK", "novo_saldo": conta['valor']})

# Rota para executar transferência intermediária
@app.route('/executar_transferencia', methods=['POST'])
def executar_transferencia():
    valor_transferencia = float(request.json['valor'])
    ip_final = request.json['ip_final']
    to_conta_id = int(request.json['to_conta_id'])

    # Verificar se a conta tem fundos suficientes
    if conta['valor'] < valor_transferencia:
        return jsonify({"error": "Fundos insuficientes na conta intermediária."}), 400

    # Enviar solicitação ao servidor de destino final para validar a transferência
    transfer_request_data = {'valor': valor_transferencia}
    try:
        response = requests.post(f'http://{ip_final}/receber_transferencia', json=transfer_request_data)
        response_data = response.json()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Erro na comunicação com o servidor de destino final: {str(e)}"}), 500

    # Verificar a resposta do servidor de destino final
    if response.status_code != 200 or response_data.get('status') != 'ACK':
        return jsonify({"error": "A transferência não foi validada pelo servidor de destino final."}), 400

    # Realizar a transferência
    conta['valor'] -= valor_transferencia
    print(f"Transferência enviada: {valor_transferencia} para {ip_final}")

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
    app.run(host='0.0.0.0', port=5002)
