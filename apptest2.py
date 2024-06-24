from flask import Flask, jsonify, render_template, request, session, redirect, url_for
import requests
import threading

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Chave secreta para as sessões

# Inicialização da conta única
conta = {}
conta_lock = threading.Lock()

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

# Rota para retornar a conta
@app.route('/conta', methods=['GET'])
def get_conta():
    if 'user_id' not in session:
        return {"error": "Acesso não autorizado."}, 403

    lock_manager.acquire('conta', 'read')
    try:
        if conta:
            return jsonify(conta)
        else:
            return {"error": "Conta não encontrada."}, 404
    finally:
        lock_manager.release('conta', 'read')

# Rota para definir a conta
@app.route('/submit', methods=['POST'])
def submit():
    lock_manager.acquire('conta', 'write')
    try:
        conta.update({
            'nome': request.form["name"],
            'tipo': request.form["tipo_de_conta"],
            'valor': 1000,  # Valor inicial da conta
            'senha': request.form["senha"]
        })
        return jsonify(conta)
    finally:
        lock_manager.release('conta', 'write')

def undo_transfer(data):
    conta['valor'] += data['valor']

def process_transfer_complex(transfer_data):
    transaction_log = TransactionLog()
    ip_intermediario = transfer_data["ip_intermediario"]
    ip_final = transfer_data["ip_final"]
    to_conta_id = transfer_data['to_conta_id']
    valor_origem = transfer_data['valor_origem']
    valor_intermediario = transfer_data['valor_intermediario']

    lock_manager.acquire('conta', 'write')
    try:
        if conta['valor'] < valor_origem:
            return {"error": "Fundos insuficientes na conta de origem."}, 400

        transfer_request_data_intermediario = {
            'from_conta_id': 'conta',
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

        transaction_log.log(undo_transfer, {'valor': valor_origem})
        conta['valor'] -= valor_origem
        print(f"Transferência enviada: {valor_origem} para {ip_final}")

        return {
            "to_conta_id": to_conta_id,
            "valor_transferencia": valor_origem + valor_intermediario,
            "novo_saldo": conta['valor']
        }
    except Exception as e:
        transaction_log.rollback()
        raise e
    finally:
        lock_manager.release('conta', 'write')

@app.route('/fazer_transferencia_complexa', methods=['POST'])
def fazer_transferencia_complexa():
    if 'user_id' not in session:
        return {"error": "Acesso não autorizado."}, 403

    transfer_data = {
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
    valor_transferencia = float(request.json['valor'])

    lock_manager.acquire('conta', 'write')
    try:
        if conta:
            conta['valor'] += valor_transferencia
            print(f"Transferência recebida: {valor_transferencia}")
            return jsonify({"status": "ACK", "novo_saldo": conta['valor']})
        else:
            return {"error": "Conta não encontrada."}, 404
    finally:
        lock_manager.release('conta', 'write')

def undo_intermediate_transfer(data):
    conta['valor'] += data['valor']

@app.route('/executar_transferencia', methods=['POST'])
def executar_transferencia():
    valor_transferencia = float(request.json['valor'])
    ip_final = request.json['ip_final']
    to_conta_id = int(request.json['to_conta_id'])
    transaction_log = TransactionLog()

    lock_manager.acquire('conta', 'write')
    try:
        if not conta:
            return {"error": "Conta intermediária não encontrada."}, 404

        if conta['valor'] < valor_transferencia:
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

        transaction_log.log(undo_intermediate_transfer, {'valor': valor_transferencia})
        conta['valor'] -= valor_transferencia
        print(f"Transferência enviada: {valor_transferencia} para {ip_final}")

        return jsonify({"status": "ACK", "novo_saldo": conta['valor']})
    except Exception as e:
        transaction_log.rollback()
        raise e
    finally:
        lock_manager.release('conta', 'write')

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        senha = request.form['senha']
        
        lock_manager.acquire('conta', 'read')
        try:
            if conta and conta['senha'] == senha:
                session['user_id'] = 'conta'
                return redirect(url_for('dashboard'))
            else:
                return {"error": "Credenciais inválidas."}, 401
        finally:
            lock_manager.release('conta', 'read')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        lock_manager.acquire('conta', 'write')
        try:
            conta.update({
                'nome': request.form["name"],
                'tipo': request.form["tipo_de_conta"],
                'valor': 1000,  # Valor inicial da conta
                'senha': request.form["senha"]
            })
            return redirect(url_for('login'))
        finally:
            lock_manager.release('conta', 'write')

    return render_template('cadastro.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    lock_manager.acquire('conta', 'read')
    try:
        if conta:
            return render_template('dashboard.html', conta=conta)
        else:
            session.pop('user_id')
            return {"error": "Conta não encontrada."}, 404
    finally:
        lock_manager.release('conta', 'read')
        
@app.route('/transferencia')
def transferencia():
    return render_template('transferencia.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
