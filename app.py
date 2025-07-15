from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from datetime import datetime
import os
import json
import random
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'adminbankkey'
UPLOAD_FOLDER = 'static/uploads'
DATA_FILE = 'database.json'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({}, f)

def load_db():
    with open(DATA_FILE) as f:
        return json.load(f)

def save_db(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def generate_unique_account(db):
    while True:
        acc = str(random.randint(10000000, 99999999))
        if acc not in db:
            return acc

@app.route('/', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == 'sura' and request.form['password'] == '12345678':
            session['admin'] = True
            return redirect('/dashboard')
    return render_template('admin_login.html')

@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect('/')
    db = load_db()
    q = request.args.get('q', '').lower()
    accounts = {k: v for k, v in db.items() if q in v['name'].lower() or q in k}
    return render_template('admin_dashboard.html', accounts=accounts, query=q)

@app.route('/create', methods=['GET', 'POST'])
def create_account():
    if 'admin' not in session:
        return redirect('/')
    if request.method == 'POST':
        db = load_db()
        acc = generate_unique_account(db)
        name = request.form['name']
        age = request.form['age']
        address = request.form['address']
        idnumber = request.form['idnumber']

        profile = secure_filename(request.files['profile'].filename)
        id_front = secure_filename(request.files['id_front'].filename)
        id_back = secure_filename(request.files['id_back'].filename)

        request.files['profile'].save(os.path.join(UPLOAD_FOLDER, profile))
        request.files['id_front'].save(os.path.join(UPLOAD_FOLDER, id_front))
        request.files['id_back'].save(os.path.join(UPLOAD_FOLDER, id_back))

        db[acc] = {
            'name': name,
            'age': age,
            'address': address,
            'idnumber': idnumber,
            'profile': profile,
            'id_front': id_front,
            'id_back': id_back,
            'balance': 0,
            'transactions': []
        }
        save_db(db)
        return redirect(f'/account/{acc}')
    return render_template('create_account.html')

@app.route('/account/<acc>', methods=['GET', 'POST'])
def account_detail(acc):
    if 'admin' not in session:
        return redirect('/')
    db = load_db()
    if acc not in db:
        return "Account not found", 404
    user = db[acc]
    if request.method == 'POST':
        action = request.form['action']
        amount = float(request.form['amount'])
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if action == 'deposit':
            user['balance'] += amount
            desc = f"Deposited {amount} Birr"
        elif action == 'withdraw':
            fee = amount * 0.02
            total = amount + fee
            if user['balance'] >= total:
                user['balance'] -= total
                desc = f"Withdrew {amount} Birr (Fee: {fee:.2f})"
            else:
                desc = f"Failed withdrawal of {amount} Birr"
        elif action == 'send':
            target = request.form['target_acc']
            fee = amount * 0.02
            total = amount + fee
            if target in db and target != acc and user['balance'] >= total:
                user['balance'] -= total
                db[target]['balance'] += amount
                user['transactions'].insert(0, {'desc': f"Sent {amount} to {target} (Fee: {fee:.2f})", 'date': now, 'balance': user['balance']})
                db[target]['transactions'].insert(0, {'desc': f"Received {amount} from {acc}", 'date': now, 'balance': db[target]['balance']})
                save_db(db)
                session['last_tx'] = {'desc': f"Sent {amount} to {target}", 'date': now, 'amount': amount}
                return redirect('/receipt')
            else:
                desc = "Transfer failed"

        user['transactions'].insert(0, {'desc': desc, 'date': now, 'balance': user['balance']})
        save_db(db)
        session['last_tx'] = {'desc': desc, 'date': now, 'amount': amount}
        return redirect('/receipt')
    return render_template('customer_detail.html', acc=acc, user=user)

@app.route('/receipt')
def receipt():
    if 'admin' not in session:
        return redirect('/')
    tx = session.get('last_tx')
    return render_template('receipt.html', tx=tx)

if __name__ == '__main__':
    app.run(debug=True)
