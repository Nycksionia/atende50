import requests
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
    bairro = db.Column(db.String(100))
    cep = db.Column(db.String(20))
    experiencia = db.Column(db.String(255))
    # O backref='profissional' cria o link automático
    chamados = db.relationship('Chamado', backref='profissional', lazy=True)

class ClienteLead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(14), nullable=False, unique=True) # CPF único
    whatsapp = db.Column(db.String(20), nullable=False)
    endereco = db.Column(db.String(200))
    # REMOVA o campo 'problema' daqui!
    chamados = db.relationship('Chamado', backref='cliente', lazy=True)

class Chamado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_abertura = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Pendente')
    valor_total = db.Column(db.Float, default=0.0)
    
    # ADICIONE o campo aqui:
    descricao_problema = db.Column(db.Text, nullable=False) 
    
    profissional_id = db.Column(db.Integer, db.ForeignKey('profissional.id'), nullable=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente_lead.id'), nullable=False)
    
def disparar_whatsapp_automatico(numero, mensagem):
    """
    Envia o comando para o servidor Node.js (porta 3000) 
    disparar a mensagem via WhatsApp.
    """
    # Remove parênteses, espaços e traços do número
    numero_limpo = "".join(filter(str.isdigit, str(numero)))
    
    # Adiciona o 55 se o usuário não tiver colocado (padrão Brasil)
    #if not numero_limpo.startswith("55"):
    #    numero_limpo = "55" + numero_limpo

    url = "http://127.0.0.1:3000/enviar"
    #localhost:3000/enviar"
    payload = {
        "numero": numero_limpo,
        "mensagem": mensagem
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Erro ao falar com o motor de mensagens: {e}")
        return False

def disparar_whatsapp(numero, texto):
    try:
        # O Python avisa o Node.js para enviar a mensagem
        requests.post('http://localhost:3000/enviar', 
                      json={'numero': numero, 'mensagem': texto})
    except Exception as e:
        print(f"Falha ao conectar no motor de mensagens: {e}")

# --- ROTAS ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def exibir_login():
    # Limpa mensagens flash residuais para não abrir o modal direto
    session.pop('_flashes', None) 
    
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

@app.route('/buscar_profissional/<cpf>')
def buscar_profissional(cpf):
    prof = Profissional.query.filter_by(cpf=cpf).first()
    if prof:
        return {
"encontrado": True,
            "nome": prof.nome, #
            "apelido": prof.apelido,
            "whatsapp": prof.whatsapp, #
            "fone_fixo": getattr(prof, 'fone_fixo', ''),
            "endereco": prof.endereco, #
            "bairro": getattr(prof, 'bairro', ''),
            "cidade": prof.cidade, #
            "uf": getattr(prof, 'uf', 'GO'),
            "cep": getattr(prof, 'cep', ''),
            "experiencia": prof.experiencia #
        }
    return {"encontrado": False}

@app.route('/chamados')
def listar_chamados():
    if not session.get('logado'):
        return redirect(url_for('exibir_login'))
    
    try:
        # Busca chamados ordenados por data
        todos_chamados = Chamado.query.order_by(Chamado.data_abertura.desc()).all()
        # Busca todos os profissionais para o formulário de vínculo
        todos_profs = Profissional.query.all() 
        
        return render_template('chamados.html', 
                               chamados=todos_chamados, 
                               profissionais=todos_profs,
                               pagina_ativa='chamados') # <--- Adicione isso aqui
    except Exception as e:
        print(f"Erro ao listar chamados: {e}")
        return f"Erro interno: {e}", 500
        
def disparar_whatsapp_motor(numero, mensagem):
    """
    Versão de teste: APENAS limpa caracteres especiais.
    NÃO adiciona 55, NÃO adiciona 9.
    """
    # Mantém apenas os dígitos que estão no banco de dados
    n = "".join(filter(str.isdigit, str(numero)))
    
    # Se o número começar com 0 (ex: 062...), remove apenas o zero
    if n.startswith("0"):
        n = n[1:]

    url = "http://localhost:3000/enviar"
    payload = {"numero": n, "mensagem": mensagem}

    try:
        requests.post(url, json=payload, timeout=5)
        print(f"🚀 Enviando para o Node exatamente como está no banco: {n}")
        return True
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return False
      
# Rota para atualizar apenas o status (Pendente, Concluído, etc)
@app.route('/atualizar_status_chamado/<int:chamado_id>', methods=['POST'])
def atualizar_status_chamado(chamado_id):
    if not session.get('logado'):
        return redirect(url_for('exibir_login'))
    
    novo_status = request.form.get('status_selecionado')
    chamado = Chamado.query.get(chamado_id)
    
    if chamado:
        chamado.status = novo_status
        db.session.commit()
        flash(f'Status do chamado #{chamado_id} atualizado!')
    
    return redirect(url_for('listar_chamados'))

@app.route('/admin/gestao-problemas')
def gestao_problemas():
    # Busca todos os chamados ordenados pelos mais recentes
    chamados = Chamado.query.order_by(Chamado.id.desc()).all()
    return render_template('area_restrita.html', chamados=chamados, pagina_ativa='problemas')

# --- ROTAS DE SALVAMENTO ---

@app.route('/salvar-profissional', methods=['POST'])
def salvar_profissional():
    cpf = request.form.get('cpf')
    nome = request.form.get('nome')
    
    # 1. Tenta buscar se o profissional já existe
    prof = Profissional.query.filter_by(cpf=cpf).first()

    try:
        if prof:
            # MODO ATUALIZAÇÃO: O CPF já existe, vamos atualizar os dados editáveis
            # O nome e CPF geralmente não mudam, mas atualizamos por segurança se necessário
            prof.nome = nome 
            status_msg = f'✅ Cadastro de {prof.nome} atualizado com sucesso!'
        else:
            # MODO NOVO CADASTRO: Cria um novo objeto
            prof = Profissional(cpf=cpf, nome=nome)
            db.session.add(prof)
            status_msg = '✅ Novo profissional cadastrado com sucesso!'

        # 2. Atualiza os campos que você liberou para edição no formulário
        prof.apelido = request.form.get('apelido')
        prof.whatsapp = request.form.get('whatsapp')
        prof.endereco = request.form.get('endereco')
        prof.cidade = request.form.get('cidade')
        
        # Se você tiver esses campos no seu modelo Profissional, descomente abaixo:
        # prof.bairro = request.form.get('bairro')
        # prof.cep = request.form.get('cep')
        # prof.uf = request.form.get('uf')

        # Trata as especialidades (lista para string)
        lista_experiencia = request.form.getlist('experiencia')
        prof.experiencia = ", ".join(lista_experiencia)

        db.session.commit()
        flash(status_msg)
        return redirect(url_for('index'))
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ ERRO NO SALVAMENTO/UPDATE: {e}")
        flash('Erro técnico ao processar os dados.')
        return redirect(url_for('ir_para_cadastro_prof'))
    
@app.route('/buscar_cliente/<cpf>')
def buscar_cliente(cpf):
    cliente = ClienteLead.query.filter_by(cpf=cpf).first()
    if cliente:
        return {
            "encontrado": True,
            "nome": cliente.nome,
            "whatsapp": cliente.whatsapp,
            "endereco": cliente.endereco
        }
    return {"encontrado": False}

@app.route('/salvar-pedido', methods=['POST'])
def salvar_pedido():
    nome = request.form.get('nome_cliente')
    cpf = request.form.get('cpf_cliente')
    whatsapp = request.form.get('whatsapp_cliente')
    problema_digitado = request.form.get('problema') # Captura o que foi escrito agora
    endereco = request.form.get('endereco_cliente') 

    cliente = ClienteLead.query.filter_by(cpf=cpf).first()

    try:
        if cliente:
            # Se já existe, apenas atualizamos os dados de contato se mudaram
            cliente.whatsapp = whatsapp
            cliente.endereco = endereco
            flash(f'Bem-vindo de volta, {cliente.nome}!')
        else:
            # Se é novo, cria o cadastro do cliente
            cliente = ClienteLead(
                nome=nome,
                cpf=cpf,
                whatsapp=whatsapp,
                endereco=endereco
            )
            db.session.add(cliente)
            db.session.flush()

        # O SEGREDO: Criamos o chamado com a descrição específica desta vez
        novo_chamado = Chamado(
            cliente_id=cliente.id,
            descricao_problema=problema_digitado, # Salva o problema aqui!
            status='Pendente',
            valor_total=0.0
        )
        db.session.add(novo_chamado)
        db.session.commit()
        
        flash('✅ Solicitação enviada com sucesso!')
        return redirect(url_for('index'))

    except Exception as e:
        db.session.rollback()
        print(f"❌ ERRO AO SALVAR PEDIDO: {e}")
        flash('Erro ao processar pedido.')
        return redirect(url_for('ir_para_cadastro_cliente'))
        
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

# Rota para vincular o profissional e disparar as mensagens automáticas
@app.route('/vincular_chamado/<int:chamado_id>', methods=['POST'])
def vincular_chamado(chamado_id):
    if not session.get('logado'):
        return "Não autorizado", 401
        
    id_prof = request.form.get('profissional_selecionado')
    
    # Busca o chamado e o profissional no banco de dados
    chamado = Chamado.query.get(chamado_id)
    profissional = Profissional.query.get(id_prof)
    
    if chamado and profissional:
        # 1. Atualiza o banco de dados
        chamado.profissional_id = id_prof
        chamado.status = 'Em Andamento'
        db.session.commit()

        # 2. Prepara as mensagens (Estilo Card de Confirmação)
        msg_cliente = (f"*PORTAL ATENDE50+ - CONFIRMAÇÃO*\n\n"
                       f"Conectando a experiência de quem viveu com as necessidades de quem precisa."
                       f"Olá, *{chamado.cliente.nome}*! O profissional *{profissional.nome}* "
                       f"já foi escalado para seu atendimento.\n\n"
                       f"Aguarde o contato para agendamento! ✅")

        msg_prof = (f"*ATENDE50+ - NOVO SERVIÇO*\n\n"
                    f"Conectando a experiência de quem viveu com as necessidades de quem precisa."
                    f"Você foi vinculado ao chamado de: *{chamado.cliente.nome}*\n"
                    f"📱 WhatsApp: {chamado.cliente.whatsapp}\n"
                    f"🛠️ Serviço: {chamado.descricao_problema}\n\n"
                    f"Entre em contato o mais breve possível! 🚀")
        
        # 3. CHAMA O MOTOR NODE.JS (O envio invisível)
        disparar_whatsapp_motor(chamado.cliente.whatsapp, msg_cliente)
        disparar_whatsapp_motor(profissional.whatsapp, msg_prof)
        
        return "Sucesso", 200
    
    return "Erro: Chamado ou Profissional não encontrado", 400

# AJUSTE PARA O RENDER: Definir host e porta dinâmicos
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)