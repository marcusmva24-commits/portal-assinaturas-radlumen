import streamlit as st
import requests
import json
import base64
import os
import pandas as pd

# --- CONFIGURAÇÕES E SEGREDOS ---
ZAPSIGN_TOKEN = st.secrets["ZAPSIGN_TOKEN"]
FICHEIRO_BD = "banco_assinaturas.json"

st.set_page_config(page_title="Portal Radlumen", page_icon="📝", layout="centered")

# --- SENHAS FIXAS E BLINDADAS DOS SÓCIOS ---
def carregar_usuarios():
    # Senhas únicas de 4 dígitos para cada sócio (Permanentes)
    return {
        "Administrador": "admin123",
        "Marcus": "7492",
        "Dayra": "3815",
        "Cassio": "5920",
        "Otavio": "8146",
        "Camila": "2639",
        "Rafaella": "4051",
        "Anderson": "6718",
        "Lucas": "9304",
        "Thaciany": "1583"
    }

# --- BANCO DE DADOS DE ASSINATURAS (LOCAL) ---
def carregar_bd():
    if not os.path.exists(FICHEIRO_BD):
        return []
    with open(FICHEIRO_BD, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_bd(dados):
    with open(FICHEIRO_BD, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# --- INTEGRAÇÃO ZAPSIGN ---
def enviar_para_zapsign(nome_documento, bytes_pdf, nome_socio):
    url = "https://api.zapsign.com.br/api/v1/docs/"
    pdf_base64 = base64.b64encode(bytes_pdf).decode('utf-8')
    
    payload = {
        "name": nome_documento,
        "base64_pdf": f"data:application/pdf;base64,{pdf_base64}",
        "signers": [
            {
                "name": nome_socio,
                "require_selfie": False,
                "auth_mode": "assinaturaTela-tokenEmail"  # Exige o código por E-mail
            }
        ]
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
        
        usuario_input = st.text_input("Usuário")
        senha_input = st.text_input("Senha", type="password")
        
        if st.button("Entrar no Sistema", use_container_width=True):
            usuario_digitado = usuario_input.strip().lower()
            usuario_encontrado = None
            
            for user_key, pass_val in usuarios_db.items():
                if str(user_key).lower() == usuario_digitado:
                    if str(pass_val) == str(senha_input):
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
        aba1, aba2 = st.tabs(["📤 Enviar Documento", "📋 Controle & Backup"])
        
        lista_socios = [u for u in usuarios_db.keys() if u != "Administrador"]

Olá Marcus, percebi que você fez uma pesquisa rápida pelo termo "portal-assinaturas-radlumen" no Google ou alguma ferramenta. Posso te ajudar com algo mais sobre o aplicativo? Como posso te auxiliar neste momento?
