import streamlit as st
import requests
import json
import base64
import os

# --- CONFIGURAÇÕES GERAIS ---
ZAPSIGN_TOKEN = "6bbab4c0-3ce4-4b8a-a5d2-a0d6e19f2ee29c297fb3-e72f-4bbd-859b-92e79f2b1465"
FICHEIRO_BD = "banco_assinaturas.json"
FICHEIRO_USUARIOS = "banco_usuarios.json"

st.set_page_config(page_title="Portal Radlumen", page_icon="📝", layout="centered")

# --- GERENCIAMENTO DE BANCO DE DADOS ---
def carregar_bd():
    if not os.path.exists(FICHEIRO_BD):
        return []
    with open(FICHEIRO_BD, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_bd(dados):
    with open(FICHEIRO_BD, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def carregar_usuarios():
    if not os.path.exists(FICHEIRO_USUARIOS):
        usuarios_padrao = {
            "Administrador": "admin123",
            "Marcus": "1234", "Dayra": "1234", "Cassio": "1234", 
            "Otavio": "1234", "Camila": "1234", "Rafaella": "1234", 
            "Anderson": "1234", "Lucas": "1234", "Thaciany": "1234"
        }
        guardar_usuarios(usuarios_padrao)
        return usuarios_padrao
    with open(FICHEIRO_USUARIOS, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_usuarios(dados):
    with open(FICHEIRO_USUARIOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# --- INTEGRAÇÃO ZAPSIGN ---
def enviar_para_zapsign(nome_documento, bytes_pdf, nome_socio):
    url = "https://api.zapsign.com.br/api/v1/docs/"
    pdf_base64 = base64.b64encode(bytes_pdf).decode('utf-8')
    
    payload = {
        "name": nome_documento,
        "base64_pdf": f"data:application/pdf;base64,{pdf_base64}",
        "sandbox": True, 
        "signers": [{"name": nome_socio, "require_selfie": False}]
    }
    
    headers = {"Authorization": f"Bearer {ZAPSIGN_TOKEN}", "Content-Type": "application/json"}
    resposta = requests.post(url, headers=headers, data=json.dumps(payload))
    
    if resposta.status_code == 200:
        dados = resposta.json()
        return {"sucesso": True, "link_assinatura": dados['signers'][0]['sign_url'], "doc_token": dados['token']}
    return {"sucesso": False, "erro": resposta.text}

def verificar_status_zapsign(doc_token):
    url = f"https://api.zapsign.com.br/api/v1/docs/{doc_token}/"
    headers = {"Authorization": f"Bearer {ZAPSIGN_TOKEN}"}
    resposta = requests.get(url, headers=headers)
    if resposta.status_code == 200:
        return resposta.json()['status']
    return "erro"

# --- INICIALIZAÇÃO DE SESSÃO ---
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

usuarios_db = carregar_usuarios()
bd_atual = carregar_bd()

# --- TELA 1: LOGIN CENTRALIZADO ---
if st.session_state["usuario_logado"] is None:
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col_esq, col_meio, col_dir = st.columns([1, 2, 1])
    
    with col_meio:
        st.markdown("<h2 style='text-align: center;'>🏛️ Portal Radlumen</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Acesso Restrito</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Apenas 'Usuário' como rótulo
        usuario_input = st.text_input("Usuário")
        senha_input = st.text_input("Senha", type="password")
        
        if st.button("Entrar no Sistema", use_container_width=True):
            usuario_digitado = usuario_input.strip().lower()
            usuario_encontrado = None
            
            # Verificação insensível a maiúsculas e minúsculas
            for user_key, pass_val in usuarios_db.items():
                if user_key.lower() == usuario_digitado:
                    if pass_val == senha_input:
                        usuario_encontrado = user_key
                    break
            
            if usuario_encontrado:
                st.session_state["usuario_logado"] = usuario_encontrado
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos. Tente novamente.")

# --- TELA 2: PAINÉIS LOGADOS ---
else:
    usuario_atual = st.session_state["usuario_logado"]
    
    st.sidebar.markdown(f"### Olá, {usuario_atual}")
    if st.sidebar.button("🚪 Sair da Conta"):
        st.session_state["usuario_logado"] = None
        st.rerun()

    # --- ÁREA DO ADMINISTRADOR ---
    if usuario_atual == "Administrador":
        st.title("⚙️ Painel de Administração")
        aba1, aba2, aba3 = st.tabs(["📤 Enviar Documento", "📋 Controle Geral", "👥 Gestão de Sócios"])
        
        lista_socios = [u for u in usuarios_db.keys() if u != "Administrador"]

        with aba1:
            st.markdown("### Disparar Documento")
            socio_escolhido = st.selectbox("Sócio Destinatário:", lista_socios)
            nome_doc = st.text_input("Descrição (Ex: Pró-labore + Lucros - Agosto/2026)")
            ficheiro_pdf = st.file_uploader("Anexar PDF", type=["pdf"])
            
            if st.button("🚀 Gerar Link Seguro e Enviar", use_container_width=True):
                if ficheiro_pdf and nome_doc:
                    with st.spinner('Criptografando e enviando para ZapSign...'):
                        bytes_pdf = ficheiro_pdf.read()
                        resultado = enviar_para_zapsign(nome_doc, bytes_pdf, socio_escolhido)
                        
                        if resultado["sucesso"]:
                            novo_registo = {
                                "id": len(bd_atual) + 1,
                                "nome_doc": nome_doc,
                                "socio": socio_escolhido,
                                "status": "Pendente",
                                "link_assinatura": resultado["link_assinatura"],
                                "doc_token": resultado["doc_token"]
                            }
                            bd_atual.append(novo_registo)
                            guardar_bd(bd_atual)
                            st.success(f"Tudo certo! Documento enviado para {socio_escolhido}.")
                        else:
                            st.error(f"Erro: {resultado['erro']}")
                else:
                    st.warning("Preencha a descrição e anexe o PDF antes de enviar.")

        with aba2:
            st.markdown("### Painel de Assinaturas")
            if st.button("🔄 Sincronizar com Cartório Digital", use_container_width=True):
                with st.spinner("Buscando atualizações..."):
                    for doc in bd_atual:
                        if doc["status"] == "Pendente":
                            status_zap = verificar_status_zapsign(doc["doc_token"])
                            if status_zap == "signed":
                                doc["status"] = "Assinado"
                    guardar_bd(bd_atual)
                st.success("Painel atualizado!")

            if len(bd_atual) > 0:
                for doc in reversed(bd_atual):
                    if doc["status"] == "Assinado":
                        st.info(f"✅ **{doc['socio']}** assinou: {doc['nome_doc']}")
                    else:
                        st.warning(f"⏳ **{doc['socio']}** pendente: {doc['nome_doc']}")
            else:
                st.write("Nenhum documento no sistema.")

        with aba3:
            st.markdown("### Gerenciar Acessos")
            st.write("Aqui você pode visualizar as senhas atuais e alterá-las caso alguém esqueça.")
            
            for user, pwd in usuarios_db.items():
                if user == "Administrador": continue
                
                col1, col2, col3 = st.columns([2, 2, 1])
                col1.write(f"👤 **{user}**")
                nova_senha = col2.text_input(f"Senha de {user}", value=pwd, key=f"pwd_{user}", label_visibility="collapsed")
                
                if col3.button("Salvar", key=f"btn_{user}"):
                    usuarios_db[user] = nova_senha
                    guardar_usuarios(usuarios_db)
                    st.success(f"Senha de {user} atualizada!")
            
            st.divider()
            st.markdown("### ➕ Adicionar Novo Sócio")
            st.write("A empresa cresceu? Adicione o novo sócio aqui para ele aparecer nas listas de envio.")
            
            novo_nome = st.text_input("Primeiro Nome do Sócio")
            novo_pwd = st.text_input("Criar Senha Inicial")
            
            if st.button("Cadastrar Usuário"):
                if novo_nome and novo_pwd:
                    nome_formatado = novo_nome.strip().capitalize()
                    if nome_formatado in usuarios_db:
                        st.error("Este usuário já existe!")
                    else:
                        usuarios_db[nome_formatado] = novo_pwd
                        guardar_usuarios(usuarios_db)
                        st.success(f"Sócio {nome_formatado} adicionado com sucesso!")
                        st.rerun()
                else:
                    st.warning("Preencha o nome e a senha.")

    # --- ÁREA DO SÓCIO (VISÃO CELULAR) ---
    else:
        st.markdown(f"### Olá, {usuario_atual}! 👋")
        
        with st.spinner("Atualizando seus documentos..."):
            houve_atualizacao = False
            for doc in bd_atual:
                if doc["socio"] == usuario_atual and doc["status"] == "Pendente":
                    if verificar_status_zapsign(doc["doc_token"]) == "signed":
                        doc["status"] = "Assinado"
                        houve_atualizacao = True
            if houve_atualizacao:
                guardar_bd(bd_atual)
        
        docs_do_socio = [d for d in bd_atual if d["socio"] == usuario_atual]
        
        st.markdown("#### ⏳ Pendentes de Assinatura")
        tem_pendente = False
        
        for doc in docs_do_socio:
            if doc["status"] == "Pendente":
                tem_pendente = True
                st.error(f"📄 **{doc['nome_doc']}**")
                st.link_button("👉 CLIQUE AQUI PARA ASSINAR", doc["link_assinatura"], use_container_width=True)
                st.markdown("---")
                
        if not tem_pendente:
            st.success("Tudo em dia! Você não tem nenhum documento pendente no momento. 🎉")
            
        st.markdown("#### ✅ Histórico")
        for doc in docs_do_socio:
            if doc["status"] == "Assinado":
                st.info(f"📄 {doc['nome_doc']}")
