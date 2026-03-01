import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'atende50_projeto_2026_seguro'

# Ajuste para garantir que o SQLite funcione no Render
# Ele tentará criar o banco na pasta 'instance' se ela existir, ou na raiz.
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'atende50.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELOS DO BANCO DE DADOS ---
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    senha = db.Column(db.String(100), nullable=False)
    
class Profissional(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    apelido = db.Column(db.String(50))
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    whatsapp = db.Column(db.String(20), nullable=False)
    endereco = db.Column(db.String(200))
    cidade = db.Column(db.String(100))
    experiencia = db.Column(db.String(255))
    chamados = db.relationship('Chamado', backref='profissional', lazy=True)

class ClienteLead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), nullable=False)
    whatsapp = db.Column(db.String(20), nullable=False)
    endereco = db.Column(db.String(200))
    problema = db.Column(db.Text, nullable=False)
    chamados = db.relationship('Chamado', backref='cliente', lazy=True)
    
class Chamado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_abertura = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pendente')
    valor_total = db.Column(db.Float, default=0.0)
    profissional_id = db.Column(db.Integer, db.ForeignKey('profissional.id'), nullable=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente_lead.id'), nullable=False)

# --- ROTAS ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def exibir_login():
    if 'tentativas' not in session:
        session['tentativas'] = 0
    return render_template('login.html')

@app.route('/login-gestora', methods=['POST'])
def processar_login():
    if 'tentativas' not in session:
        session['tentativas'] = 0

    u = request.form.get('usuario')
    s = request.form.get('senha')
    
    admin = Admin.query.filter_by(usuario=u, senha=s).first()
    
    if admin:
        session['logado'] = True
        session['usuario_admin'] = u
        session['tentativas'] = 0
        return redirect(url_for('exibir_area_restrita'))
    else:
        session['tentativas'] += 1
        if session['tentativas'] >= 3:
            session['tentativas'] = 0
            flash('Muitas tentativas falhas. Retornando ao início.')
            return redirect(url_for('index'))
            
        flash(f'Credenciais inválidas. Tentativa {session["tentativas"]} de 3.')
        return redirect(url_for('exibir_login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/area-restrita')
def exibir_area_restrita():
    if not session.get('logado'):
        return redirect(url_for('exibir_login'))
    return render_template('area_restrita.html')

@app.route('/dashboard')
def ir_para_dashboard():
    if not session.get('logado'):
        return redirect(url_for('exibir_login'))
    
    contagem_profs = Profissional.query.count()
    contagem_leads = ClienteLead.query.count()
    contagem_chamados = Chamado.query.count()
    faturamento = db.session.query(func.sum(Chamado.valor_total)).scalar() or 0.0

    return render_template('dashboard.html', 
                           total_profs=contagem_profs, 
                           total_leads=contagem_leads, 
                           total_atendimentos=contagem_chamados,
                           faturamento_total=faturamento)

@app.route('/admin/clientes')
def admin_clientes():
    if not session.get('logado'):
        return redirect(url_for('exibir_login'))
    todos_clientes = ClienteLead.query.all() 
    return render_template('admin_clientes.html', clientes=todos_clientes)

@app.route('/admin/profissionais')
def admin_profissionais():
    if not session.get('logado'):
        return redirect(url_for('exibir_login'))
    todos_profs = Profissional.query.all()
    return render_template('admin_profissionais.html', profissionais=todos_profs)

@app.route('/chamados')
def listar_chamados():
    if not session.get('logado'):
        return redirect(url_for('exibir_login'))
    todos_chamados = Chamado.query.order_by(Chamado.data_abertura.desc()).all()
    todos_profs = Profissional.query.all() 
    return render_template('chamados.html', chamados=todos_chamados, profissionais=todos_profs)

# --- ROTAS DE SALVAMENTO ---

@app.route('/salvar-profissional', methods=['POST'])
def salvar_profissional():
    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    whatsapp = request.form.get('whatsapp')
    lista_experiencia = request.form.getlist('experiencia')
    experiencia_string = ", ".join(lista_experiencia)

    try:
        novo_prof = Profissional(
            nome=nome,
            apelido=request.form.get('apelido'),
            cpf=cpf,
            whatsapp=whatsapp,
            endereco=request.form.get('endereco'),
            cidade=request.form.get('cidade'),
            experiencia=experiencia_string
        )
        db.session.add(novo_prof)
        db.session.commit()
        flash('Profissional cadastrado com sucesso!')
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()
        flash('Erro ao salvar profissional.')
        return redirect(url_for('index'))

@app.route('/salvar-pedido', methods=['POST'])
def salvar_pedido():
    nome = request.form.get('nome_cliente')
    whatsapp = request.form.get('whatsapp_cliente')
    problema = request.form.get('problema')
    endereco = request.form.get('endereco_cliente') 

    try:
        novo_lead = ClienteLead(
            nome=nome,
            cpf=request.form.get('cpf_cliente'),
            whatsapp=whatsapp,
            endereco=endereco,
            problema=problema
        )
        db.session.add(novo_lead)
        db.session.flush() 

        novo_chamado = Chamado(
            cliente_id=novo_lead.id,
            status='Pendente',
            valor_total=0.0
        )
        db.session.add(novo_chamado)
        db.session.commit()
        flash('Solicitação enviada com sucesso!')
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()
        flash('Erro ao processar pedido.')
        return redirect(url_for('index'))

# --- NOVAS ROTAS PARA CORRIGIR O ERRO 500 ---

@app.route('/cadastro-profissional')
def ir_para_cadastro_prof():
    return render_template('cadastro_prof.html')

@app.route('/solicitar-servico')
def ir_para_cadastro_cliente():
    return render_template('cadastro_cliente.html')

@app.route('/contato')
def ir_para_contato():
    return render_template('contato.html')

@app.route('/debug-bd')
def debug_bd():
    if not session.get('logado'):
        return "Acesso negado. Faça login primeiro."
    
    # Busca dados de todas as tabelas
    profs = Profissional.query.all()
    clientes = ClienteLead.query.all()
    chamados = Chamado.query.all()
    
    # Cria uma visualização rápida em texto
    resumo = "<h1>Inspeção de Dados</h1>"
    
    resumo += "<h2>Profissionais</h2>"
    resumo += "<br>".join([f"ID: {p.id} | Nome: {p.nome} | CPF: {p.cpf}" for p in profs]) or "Nenhum"
    
    resumo += "<h2>Clientes (Leads)</h2>"
    resumo += "<br>".join([f"ID: {c.id} | Nome: {c.nome} | Problema: {c.problema}" for c in clientes]) or "Nenhum"
    
    resumo += "<h2>Chamados</h2>"
    resumo += "<br>".join([f"ID: {ch.id} | Status: {ch.status} | Cliente ID: {ch.cliente_id}" for ch in chamados]) or "Nenhum"
    
    return resumo

# --- INICIALIZAÇÃO DO BANCO ---
with app.app_context():
    try:
        db.create_all()
        admin_existe = Admin.query.filter_by(usuario='admin@atende50.com').first()
        if not admin_existe:
            novo_admin = Admin(usuario='admin@atende50.com', senha='123')
            db.session.add(novo_admin)
            db.session.commit()
    except Exception as e:
        pass

# AJUSTE PARA O RENDER: Definir host e porta dinâmicos
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)