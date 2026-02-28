from flask import Flask, render_template, request, redirect, url_for, flash, session # Adicione session aqui
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'atende50_projeto_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///atende50.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- MODELOS DO BANCO DE DADOS ---
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    senha = db.Column(db.String(100), nullable=False) # Em produção, usaríamos hash
    
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

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_cliente = db.Column(db.String(100), nullable=False)
    cpf_cliente = db.Column(db.String(20), nullable=False)
    whatsapp_cliente = db.Column(db.String(20), nullable=False)
    endereco_cliente = db.Column(db.String(255), nullable=False)
    problema = db.Column(db.Text, nullable=False)
    expectativa = db.Column(db.String(255))
    
class ClienteLead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), nullable=False)
    whatsapp = db.Column(db.String(20), nullable=False)
    endereco = db.Column(db.String(200)) # ADICIONE ESTA LINHA
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
# 1. Rota para mostrar a tela de login
@app.route('/login')
def exibir_login():
    return render_template('login.html')

# 2. Rota que processa o login e envia para a Área Restrita
@app.route('/login-gestora', methods=['POST'])
def processar_login():
    u = request.form.get('usuario')
    s = request.form.get('senha')
    admin = Admin.query.filter_by(usuario=u, senha=s).first()
    
    if admin:
        session['logado'] = True  # Cria o "carimbo" de acesso
        session['usuario_admin'] = u
        return redirect(url_for('exibir_area_restrita'))
    else:
        flash('Usuário ou senha incorretos.')
        return redirect(url_for('exibir_login'))

# Crie a rota de Logout (Sair)
@app.route('/logout')
def logout():
    session.clear() # Limpa o "carimbo"
    return redirect(url_for('exibir_login'))

# 3. Rota da Página Mestre - PROTEGIDA
@app.route('/area-restrita')
def exibir_area_restrita():
    if not session.get('logado'):
        return redirect(url_for('exibir_login'))
    # Remova o return extra e alinhe este:
    return render_template('area_restrita.html')

# Rota do Dashboard - PROTEGIDA
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
    
# Rota de Clientes - PROTEGIDA E CORRIGIDA
@app.route('/admin/clientes')
def admin_clientes():
    if not session.get('logado'):
        return redirect(url_for('exibir_login'))
    # IMPORTANTE: Mudei de Pedido para ClienteLead para os dados aparecerem
    todos_clientes = ClienteLead.query.all() 
    return render_template('admin_clientes.html', clientes=todos_clientes)

# Rota de Profissionais - PROTEGIDA
@app.route('/admin/profissionais')
def admin_profissionais():
    if not session.get('logado'):
        return redirect(url_for('exibir_login'))
    todos_profs = Profissional.query.all()
    return render_template('admin_profissionais.html', profissionais=todos_profs)

# Rota de Chamados - PROTEGIDA
@app.route('/chamados')
def listar_chamados():
    if not session.get('logado'):
        return redirect(url_for('exibir_login'))
    
    # Carrega todos os chamados e também todos os profissionais para o select de amarração
    todos_chamados = Chamado.query.order_by(Chamado.data_abertura.desc()).all()
    todos_profs = Profissional.query.all() 
    
    return render_template('chamados.html', chamados=todos_chamados, profissionais=todos_profs)

# 4. Rota da Página principal e outras
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cadastro-profissional')
def ir_para_cadastro_prof():
    return render_template('cadastro_prof.html')

@app.route('/solicitar-servico')
def ir_para_cadastro_cliente():
    return render_template('cadastro_cliente.html')

@app.route('/contato')
def ir_para_contato():
    return render_template('contato.html')

@app.route('/salvar-profissional', methods=['POST'])
def salvar_profissional():
    # 1. Coleta dos dados básicos
    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    whatsapp = request.form.get('whatsapp')
    
    # 2. Captura e formatação das experiências (Multiselect)
    # Pegamos a lista do formulário e unimos em uma única frase
    lista_experiencia = request.form.getlist('experiencia')
    experiencia_string = ", ".join(lista_experiencia)

    # 3. Validação de segurança
    if not nome or not cpf:
        flash('Erro: Nome e CPF são obrigatórios!')
        return redirect(url_for('ir_para_cadastro_prof'))

    try:
        # 4. Criação do objeto único com todos os campos, incluindo a nova coluna
        novo_prof = Profissional(
            nome=nome,
            apelido=request.form.get('apelido'),
            cpf=cpf,
            whatsapp=whatsapp,
            endereco=request.form.get('endereco'),
            cidade=request.form.get('cidade'),
            experiencia=experiencia_string  # Aqui salvamos as especialidades
        )
        
        db.session.add(novo_prof)
        db.session.commit()
        
        flash('Profissional cadastrado com sucesso!')
        return redirect(url_for('index'))

    except Exception as e:
        db.session.rollback()
        # O print abaixo ajuda você a ver o erro real no terminal do VS Code
        print(f"Erro detalhado: {e}") 
        flash('Erro ao salvar no banco: Verifique se o CPF já existe.')
        return redirect(url_for('ir_para_cadastro_prof'))
    
@app.route('/salvar-pedido', methods=['POST'])
def salvar_pedido():
    nome = request.form.get('nome_cliente')
    whatsapp = request.form.get('whatsapp_cliente')
    problema = request.form.get('problema')
    endereco = request.form.get('endereco_cliente') 

    if not nome or not problema or not whatsapp:
        flash('Por favor, preencha seu nome, WhatsApp e descreva o problema.')
        return redirect(url_for('ir_para_cadastro_cliente'))

    try:
        # 1. Cria o registro do Cliente (Lead)
        novo_lead = ClienteLead(
            nome=nome,
            cpf=request.form.get('cpf_cliente'),
            whatsapp=whatsapp,
            endereco=endereco, # Garanta que adicionou essa coluna no modelo ClienteLead
            problema=problema
        )
        db.session.add(novo_lead)
        
        # O flush serve para o banco gerar o ID do cliente antes do commit final, 
        # permitindo que o chamado já nasça com o ID correto do cliente.
        db.session.flush() 

        # 2. CRIA O CHAMADO AUTOMATICAMENTE (A Amarração Pendente)
        # O chamado nasce com profissional_id como None (vazio) e status 'Pendente'
        novo_chamado = Chamado(
            cliente_id=novo_lead.id,
            status='Pendente',
            valor_total=0.0
        )
        db.session.add(novo_chamado)
        
        db.session.commit()
        flash('Solicitação enviada com sucesso! Em breve um Prof50+ será designado.')
        return redirect(url_for('index'))

    except Exception as e:
        db.session.rollback()
        print(f"Erro ao salvar pedido e gerar chamado: {e}")
        flash('Ocorreu um erro técnico ao processar seu pedido.')
        return redirect(url_for('ir_para_cadastro_cliente'))
    
#vincular chamado com profissional e clieente
@app.route('/vincular_chamado/<int:chamado_id>', methods=['POST'])
def vincular_chamado(chamado_id):
    if not session.get('logado'):
        return redirect(url_for('exibir_login'))
        
    id_prof = request.form.get('profissional_selecionado')
    valor = request.form.get('valor_servico', 0.0)
    
    chamado = Chamado.query.get(chamado_id)
    if chamado and id_prof:
        chamado.profissional_id = id_prof
        chamado.status = 'Em Andamento'
        chamado.valor_total = valor
        db.session.commit()
        flash('Profissional vinculado com sucesso!')
    
    return redirect(url_for('listar_chamados'))

#Rota para atualizar o status do chamado
@app.route('/atualizar_status_chamado/<int:chamado_id>', methods=['POST'])
def atualizar_status_chamado(chamado_id):
    if not session.get('logado'):
        return redirect(url_for('exibir_login'))
    
    novo_status = request.form.get('status_selecionado')
    chamado = Chamado.query.get(chamado_id)
    
    if chamado:
        chamado.status = novo_status
        db.session.commit()
        flash(f'Status do chamado #{chamado_id} atualizado para {novo_status}!')
    
    return redirect(url_for('listar_chamados'))

# Cria o banco e as tabelas
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)