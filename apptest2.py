from flask import Flask, jsonify, render_template, request, session, redirect, url_for
import requests
import threading

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Chave secreta para as sessões

# Inicialização das contas como um dicionário de dicionários
contas = {}
contas_lock = threading.Lock()
contador_contas = 0

class TransactionLog:
    def __init__(self):
        self.logs = []

    def log(self, action, data):
        self.logs.append((action, data))

    def rollback(self):
        while self.logs:
            action, data = self.logs.pop()
            action(data)

class LockManager:
    def __init__(self):
        self.locks = {}
        self.lock = threading.Lock()

    def acquire(self, resource, mode):
        with self.lock:
            if resource not in self.locks:
                self.locks[resource] = {'read': 0, 'write': 0}
            if mode == 'read':
                while self.locks[resource]['write'] > 0:
                    self.lock.release()
                    threading.Event().wait(0.1)
                    self.lock.acquire()
                self.locks[resource]['read'] += 1
            elif mode == 'write':
                while self.locks[resource]['read'] > 0 or self.locks[resource]['write'] > 0:
                    self.lock.release()
                    threading.Event().wait(0.1)
                    self.lock.acquire()
                self.locks[resource]['write'] += 1

    def release(self, resource, mode):
        with self.lock:
            if resource in self.locks:
                if mode == 'read':
                    self.locks[resource]['read'] -= 1
                elif mode == 'write':
                    self.locks[resource]['write'] -= 1
                if self.locks[resource]['read'] == 0 and self.locks[resource]['write'] == 0:
                    del self.locks[resource]

lock_manager = LockManager()

# Rota para retornar uma conta específica
@app.route('/conta/<conta_id>', methods=['GET'])
def get_conta(conta_id):
    if 'user_id' not in session or session['user_id'] != conta_id:
        return {"error": "Acesso não autorizado."}, 403

    lock_manager.acquire(conta_id, 'read')
    try:
        if conta_id in contas:
            return jsonify(contas[conta_id])
        else:
            return {"error": "Conta não encontrada."}, 404
    finally:
        lock_manager.release(conta_id, 'read')

# Rota para definir uma nova conta
@app.route('/submit', methods=['POST'])
def submit():
    global contador_contas
    with contas_lock:
        contador_contas += 1
        conta_id = str(contador_contas)
    
    lock_manager.acquire(conta_id, 'write')
    try:
        contas[conta_id] = {
            'nome': request.form["name"],
            'tipo': request.form["tipo_de_conta"],
            'valor': 1000,  # Valor inicial da conta
            'senha': request.form["senha"]
        }
        return jsonify(contas[conta_id])
    finally:
        lock_manager.release(conta_id, 'write')

def undo_transfer(data):
    contas[data['conta_id']]['valor'] += data['valor']

def process_transfer_complex(transfer_data):
    transaction_log = TransactionLog()
    from_conta_id = transfer_data["from_conta_id"]
    ip_intermediario = transfer_data["ip_intermediario"]
    ip_final = transfer_data["ip_final"]
    to_conta_id = transfer_data['to_conta_id']
    valor_origem = transfer_data['valor_origem']
    valor_intermediario = transfer_data['valor_intermediario']

    lock_manager.acquire(from_conta_id, 'write')
    try:
        if contas[from_conta_id]['valor'] < valor_origem:
            return {"error": "Fundos insuficientes na conta de origem."}, 400

        transfer_request_data_intermediario = {
            'from_conta_id': from_conta_id,
            'valor': valor_intermediario,
            'ip_final': ip_final,
            'to_conta_id': to_conta_id
        }
        try:
            response_intermediario = requests.post(f'http://{ip_intermediario}/executar_transferencia', json=transfer_request_data_intermediario)
            response_data_intermediario = response_intermediario.json()
        except requests.exceptions.RequestException as e:
            transaction_log.rollback()
            return {"error": f"Erro na comunicação com o servidor intermediário: {str(e)}"}, 500

        if response_intermediario.status_code != 200 or response_data_intermediario.get('status') != 'ACK':
            transaction_log.rollback()
            return {"error": "A transferência não foi validada pelo servidor intermediário."}, 400

        transfer_request_data_final = {'valor': valor_origem}
        try:
            response_final = requests.post(f'http://{ip_final}/receber_transferencia', json=transfer_request_data_final)
            response_data_final = response_final.json()
        except requests.exceptions.RequestException as e:
            transaction_log.rollback()
            return {"error": f"Erro na comunicação com o servidor de destino final: {str(e)}"}, 500

        if response_final.status_code != 200 or response_data_final.get('status') != 'ACK':
            transaction_log.rollback()
            return {"error": "A transferência não foi validada pelo servidor de destino final."}, 400

        transaction_log.log(undo_transfer, {'conta_id': from_conta_id, 'valor': valor_origem})
        contas[from_conta_id]['valor'] -= valor_origem
        print(f"Transferência enviada: {valor_origem} para {ip_final}")

        return {
            "to_conta_id": to_conta_id,
            "valor_transferencia": valor_origem + valor_intermediario,
            "novo_saldo": contas[from_conta_id]['valor']
        }
    except Exception as e:
        transaction_log.rollback()
        raise e
    finally:
        lock_manager.release(from_conta_id, 'write')

@app.route('/fazer_transferencia_complexa', methods=['POST'])
def fazer_transferencia_complexa():
    from_conta_id = session['user_id']
    transfer_data = {
        "from_conta_id": from_conta_id,
        "ip_intermediario": request.form["ip_intermediario"],
        "ip_final": request.form["ip_final"],
        "to_conta_id": int(request.form['to_conta_id']),
        "valor_origem": float(request.form['valor_origem']),
        "valor_intermediario": float(request.form['valor_intermediario'])
    }

    result = process_transfer_complex(transfer_data)
    return jsonify(result)


@app.route('/receber_transferencia', methods=['POST'])
def receber_transferencia():
    conta_id = request.json['to_conta_id']
    valor_transferencia = float(request.json['valor'])

    lock_manager.acquire(conta_id, 'write')
    try:
        if conta_id in contas:
            contas[conta_id]['valor'] += valor_transferencia
            print(f"Transferência recebida: {valor_transferencia}")
            return jsonify({"status": "ACK", "novo_saldo": contas[conta_id]['valor']})
        else:
            return {"error": "Conta não encontrada."}, 404
    finally:
        lock_manager.release(conta_id, 'write')

def undo_intermediate_transfer(data):
    contas[data['conta_id']]['valor'] += data['valor']

@app.route('/executar_transferencia', methods=['POST'])
def executar_transferencia():
    from_conta_id = request.json['from_conta_id']
    valor_transferencia = float(request.json['valor'])
    ip_final = request.json['ip_final']
    to_conta_id = int(request.json['to_conta_id'])
    transaction_log = TransactionLog()

    lock_manager.acquire(from_conta_id, 'write')
    try:
        if from_conta_id not in contas:
            return {"error": "Conta intermediária não encontrada."}, 404

        if contas[from_conta_id]['valor'] < valor_transferencia:
            return {"error": "Fundos insuficientes na conta intermediária."}, 400

        transfer_request_data = {'valor': valor_transferencia, 'to_conta_id': to_conta_id}
        try:
            response = requests.post(f'http://{ip_final}/receber_transferencia', json=transfer_request_data)
            response_data = response.json()
        except requests.exceptions.RequestException as e:
            transaction_log.rollback()
            return {"error": f"Erro na comunicação com o servidor de destino final: {str(e)}"}, 500

        if response.status_code != 200 or response_data.get('status') != 'ACK':
            transaction_log.rollback()
            return {"error": "A transferência não foi validada pelo servidor de destino final."}, 400

        transaction_log.log(undo_intermediate_transfer, {'conta_id': from_conta_id, 'valor': valor_transferencia})
        contas[from_conta_id]['valor'] -= valor_transferencia
        print(f"Transferência enviada: {valor_transferencia} para {ip_final}")

        return jsonify({"status": "ACK", "novo_saldo": contas[from_conta_id]['valor']})
    except Exception as e:
        transaction_log.rollback()
        raise e
    finally:
        lock_manager.release(from_conta_id, 'write')

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conta_id = request.form['conta_id']
        senha = request.form['senha']
        
        lock_manager.acquire(conta_id, 'read')
        try:
            if conta_id in contas and contas[conta_id]['senha'] == senha:
                session['user_id'] = conta_id
                return redirect(url_for('dashboard'))
            else:
                return {"error": "Credenciais inválidas."}, 401
        finally:
            lock_manager.release(conta_id, 'read')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        global contador_contas
        with contas_lock:
            contador_contas += 1
            conta_id = str(contador_contas)

        lock_manager.acquire(conta_id, 'write')
        try:
            contas[conta_id] = {
                'nome': request.form["name"],
                'tipo': request.form["tipo_de_conta"],
                'valor': 1000,  # Valor inicial da conta
                'senha': request.form["senha"]
            }
            return redirect(url_for('login'))
        finally:
            lock_manager.release(conta_id, 'write')

    return render_template('cadastro.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conta_id = session['user_id']
    lock_manager.acquire(conta_id, 'read')
    try:
        if conta_id in contas:
            return render_template('dashboard.html', conta=contas[conta_id])
        else:
            session.pop('user_id')
            return {"error": "Conta não encontrada."}, 404
    finally:
        lock_manager.release(conta_id, 'read')
        
@app.route('/transferencia')
def transferencia():
    return render_template('transferencia.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
