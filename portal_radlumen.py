import streamlit as st
import pandas as pd
import base64
import json
import os
import io
import zipfile
from fpdf import FPDF
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Configuração da Página
st.set_page_config(page_title="RADLUMEN - Gestão", page_icon="📊", layout="wide")

# ================= CONFIGURAÇÕES DE SEGURANÇA E TESTE =================
SENHA_ACESSO = "radlumen2026"

# CONFIGURAÇÃO DO REMETENTE
GMAIL_REMETENTE = "radlumen@gmail.com"
GMAIL_SENHA_APP = "pzeyzvhmkipunrtw"

# Helper para formatar moeda padrão Brasil no PDF
def fmt_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ================= TELA DE LOGIN =================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    col_vazia1, col_login, col_vazia2 = st.columns([1, 2, 1])
    with col_login:
        st.write(""); st.write("")
        try: st.image("logo.jpg", use_container_width=True)
        except: st.markdown("<h1 style='text-align: center;'>☢️ RADLUMEN</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>Acesso Restrito</h3>", unsafe_allow_html=True)
        senha_digitada = st.text_input("Digite a senha do sistema:", type="password")
        if st.button("Entrar no Sistema", use_container_width=True, type="primary"):
            if senha_digitada == SENHA_ACESSO:
                st.session_state["autenticado"] = True
                st.rerun()
            else: st.error("Senha incorreta.")
    st.stop()

# ================= BANCO DE DADOS NUVEM =================
ARQUIVO_CREDENCIAIS = "credenciais.json"

def conectar_planilha():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(ARQUIVO_CREDENCIAIS, scopes=scopes)
    client = gspread.authorize(creds)
    planilha = client.open("Banco_Radlumen_Nuvem")
    return planilha.sheet1

def carregar_banco():
    try:
        aba = conectar_planilha()
        valor = aba.acell('A1').value
        if valor:
            dados = json.loads(valor)
            for k, v in dados.items():
                if isinstance(v, dict) and v.get("__type__") == "df":
                    df_temp = pd.DataFrame(v["data"])
                    if not df_temp.empty and "Sócio" in df_temp.columns:
                        df_temp = df_temp.dropna(subset=["Sócio"])
                    st.session_state[k] = df_temp
                else: st.session_state[k] = v
    except: pass

def salvar_banco():
    dados_para_salvar = {}
    for k, v in st.session_state.items():
        if k.startswith("_") or k.startswith("wid_") or k.startswith("ed_"): continue 
        if isinstance(v, pd.DataFrame):
            df_limpo = v.dropna(subset=["Sócio"]) if "Sócio" in v.columns else v
            df_limpo = df_limpo.fillna("")
            dados_para_salvar[k] = {"__type__": "df", "data": df_limpo.to_dict(orient="records")}
        elif isinstance(v, (int, float, str, bool)): dados_para_salvar[k] = v
    try:
        json_string = json.dumps(dados_para_salvar, ensure_ascii=False)
        aba = conectar_planilha()
        aba.update_acell('A1', json_string)
        st.toast("☁️ Dados guardados com sucesso no Google Sheets!")
    except Exception as e: st.error(f"Erro ao guardar: {e}")

if "banco_carregado" not in st.session_state:
    carregar_banco()
    st.session_state["banco_carregado"] = True

# ================= MOTOR DE ENVIO DE EMAIL =================
def enviar_email(destinatario, assunto, corpo_html, pdf_bytes=None, nome_arquivo=None):
    msg = MIMEMultipart()
    msg['From'] = GMAIL_REMETENTE
    msg['To'] = destinatario
    msg['Cc'] = GMAIL_REMETENTE
    msg['Subject'] = assunto
    
    msg.attach(MIMEText(corpo_html, 'html'))
    
    if pdf_bytes and nome_arquivo:
        anexo = MIMEApplication(pdf_bytes, _subtype="pdf")
        anexo.add_header('Content-Disposition', 'attachment', filename=nome_arquivo)
        msg.attach(anexo)
        
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_REMETENTE, GMAIL_SENHA_APP)
        destinatarios_totais = [destinatario, GMAIL_REMETENTE]
        server.send_message(msg, from_addr=GMAIL_REMETENTE, to_addrs=destinatarios_totais)
        server.quit()
        return True
    except Exception as e: return str(e)


# ================= INICIALIZAÇÃO DA ABA RH & COMPLIANCE =================
if "rh_dados" not in st.session_state or st.session_state["rh_dados"].empty:
    st.session_state["rh_dados"] = pd.DataFrame([
        {"Sócio": "Marcus Vinicius de Almeida", "E-mail": "marcus-mva@hotmail.com", "Último ASO": "15/05/2025", "Ano Último Aviso": 0},
        {"Sócio": "Cassio Campos Marcondes", "E-mail": "cassiomarcondes@yahoo.com", "Último ASO": "15/05/2025", "Ano Último Aviso": 0},
        {"Sócio": "Dayra de Almeida Noronha", "E-mail": "dayraalmeida26@gmail.com", "Último ASO": "15/05/2025", "Ano Último Aviso": 0},
        {"Sócio": "Rafaella Elias Veiga", "E-mail": "rafaellaelias21@gmail.com", "Último ASO": "15/05/2025", "Ano Último Aviso": 0},
        {"Sócio": "Anderson Ferreira de Araujo", "E-mail": "andersonaraujoth31@gmail.com", "Último ASO": "15/05/2025", "Ano Último Aviso": 0},
        {"Sócio": "Camila Ribeiro Elias", "E-mail": "camilaribeiroelias8@gmail.com", "Último ASO": "15/05/2025", "Ano Último Aviso": 0},
        {"Sócio": "Lucas Matheus Geovanini de Paiva", "E-mail": "lucas.paiva95@hotmail.com", "Último ASO": "15/05/2025", "Ano Último Aviso": 0},
        {"Sócio": "Thaciany Santos Franco", "E-mail": "thacianysantosfranco0309@hotmail.com", "Último ASO": "15/05/2025", "Ano Último Aviso": 0},
        {"Sócio": "Otavio Augusto dos Santos Assunção", "E-mail": "otavioaugustoassuncao@gmail.com", "Último ASO": "15/05/2025", "Ano Último Aviso": 0},
    ])

# ================= FUNÇÕES DE INPUT SEGURO =================
def safe_toggle(label, key, default_value):
    if key not in st.session_state: st.session_state[key] = default_value
    wid_key = f"_{key}_widget"
    st.session_state[wid_key] = st.session_state[key]
    def sync(): st.session_state[key] = st.session_state[wid_key]
    st.sidebar.toggle(label, key=wid_key, on_change=sync)
    return st.session_state[key]

def safe_number_input(label, key, default_value, min_value=None, step=None):
    if key not in st.session_state: st.session_state[key] = default_value
    wid_key = f"_{key}_widget"
    st.session_state[wid_key] = st.session_state[key]
    def sync(): st.session_state[key] = st.session_state[wid_key]
    st.sidebar.number_input(label, min_value=min_value, step=step, key=wid_key, on_change=sync)
    return st.session_state[key]

def safe_text_input(label, key, default_value):
    if key not in st.session_state: st.session_state[key] = default_value
    wid_key = f"_{key}_widget"
    st.session_state[wid_key] = st.session_state[key]
    def sync(): st.session_state[key] = st.session_state[wid_key]
    st.sidebar.text_input(label, key=wid_key, on_change=sync)
    return st.session_state[key]

# ================= ESTRUTURA MÊS/ANO =================
meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
hoje = datetime.now()
ano_atual_real = hoje.year
mes_atual_real = hoje.month

if mes_atual_real == 1:
    mes_anterior = 12
    ano_anterior = ano_atual_real - 1
else:
    mes_anterior = mes_atual_real - 1
    ano_anterior = ano_atual_real

# ================= BARRA LATERAL =================
try: st.sidebar.image("logo.jpg", use_container_width=True)
except: st.sidebar.markdown("### ☢️ RADLUMEN")

if st.sidebar.button("☁️ GUARDAR NA NUVEM", type="primary", use_container_width=True): salvar_banco()

st.sidebar.divider()
col_m, col_a = st.sidebar.columns(2)

mes_sel = col_m.selectbox("📅 Mês", meses, index=mes_anterior - 1)
idx_ano_atual = ano_anterior - 2026 if 2026 <= ano_anterior <= 2035 else 0
ano_sel = col_a.selectbox("Ano", range(2026, 2036), index=idx_ano_atual)

key_sufixo = f"{mes_sel}_{ano_sel}"

is_antes_maio_26 = (ano_sel == 2026 and meses.index(mes_sel) + 1 < 5)
is_past_sel = (ano_sel < ano_atual_real) or (ano_sel == ano_atual_real and (meses.index(mes_sel) + 1) <= mes_atual_real)

if is_antes_maio_26:
    mes_ativo = False
    st.sidebar.toggle("🟢 Mês Ativo / Fechado", value=False, disabled=True)
else:
    mes_ativo = safe_toggle("🟢 Mês Ativo / Fechado", f"ativo_{key_sufixo}", is_past_sel)

st.sidebar.divider()
unid = safe_number_input("Unidades de Cobertura", f"unid_{key_sufixo}", 0 if is_antes_maio_26 else 7, min_value=0)
valor_unid = safe_number_input("Valor por Unidade (R$)", f"valor_unid_{key_sufixo}", 5460.00, step=50.0)
fat_bruto = unid * valor_unid

taxa_imp = safe_number_input("Imposto Simples (%)", f"imposto_{key_sufixo}", 6.0, step=0.1) / 100
imp_simples = fat_bruto * taxa_imp
cnpj_rad = safe_text_input("CNPJ", f"cnpj_{key_sufixo}", "66.149.891/0001-50")

pl_unit = safe_number_input("Sugestão Base: Pró-labore", f"prolab_{key_sufixo}", 0.0 if is_antes_maio_26 else 1621.00, min_value=0.0)
contab = safe_number_input("Contabilidade", f"contab_{key_sufixo}", 0.0 if is_antes_maio_26 else 487.50)
feriados = safe_number_input("Feriados (Qtd. Técnicos)", f"feriados_{key_sufixo}", 0)

if f"custos_{key_sufixo}" not in st.session_state:
    st.session_state[f"custos_{key_sufixo}"] = pd.DataFrame({"Descrição": [""], "Valor (R$)": [0.0]})

df_custos = st.session_state[f"custos_{key_sufixo}"]
if "Descrição" not in df_custos.columns: df_custos["Descrição"] = ""
if "Valor (R$)" not in df_custos.columns: df_custos["Valor (R$)"] = 0.0

df_custos = st.sidebar.data_editor(df_custos, num_rows="dynamic", use_container_width=True, hide_index=True)
total_custos_var = pd.to_numeric(df_custos["Valor (R$)"], errors='coerce').fillna(0).sum()
st.session_state[f"custos_{key_sufixo}"] = df_custos

# ================= TABELA PADRÃO (BASE AGOSTO) =================
def get_tabela_padrao():
    return pd.DataFrame([
        {"Sócio": "Marcus Vinicius de Almeida", "CPF": "124.031.846-40", "E-mail": "marcus-mva@hotmail.com", "Papel": "Gestão", "Total Alvo": 7000.00, "Pró-Labore Bruto": 1621.00, "Distribuição de Lucro": 9800.00},
        {"Sócio": "Cassio Campos Marcondes", "CPF": "086.007.496-03", "E-mail": "cassiomarcondes@yahoo.com", "Papel": "Técnico", "Total Alvo": 3100.00, "Pró-Labore Bruto": 1621.00, "Distribuição de Lucro": 1660.00},
        {"Sócio": "Dayra de Almeida Noronha", "CPF": "020.992.596-58", "E-mail": "dayraalmeida26@gmail.com", "Papel": "Técnico", "Total Alvo": 3100.00, "Pró-Labore Bruto": 1621.00, "Distribuição de Lucro": 1660.00},
        {"Sócio": "Rafaella Elias Veiga", "CPF": "487.243.208-89", "E-mail": "rafaellaelias21@gmail.com", "Papel": "Técnico", "Total Alvo": 3000.00, "Pró-Labore Bruto": 1621.00, "Distribuição de Lucro": 1560.00},
        {"Sócio": "Anderson Ferreira de Araujo", "CPF": "119.135.077-00", "E-mail": "andersonaraujoth31@gmail.com", "Papel": "Técnico", "Total Alvo": 3000.00, "Pró-Labore Bruto": 1621.00, "Distribuição de Lucro": 1560.00},
        {"Sócio": "Camila Ribeiro Elias", "CPF": "072.094.706-54", "E-mail": "camilaribeiroelias8@gmail.com", "Papel": "Técnico", "Total Alvo": 3000.00, "Pró-Labore Bruto": 1621.00, "Distribuição de Lucro": 1560.00},
        {"Sócio": "Lucas Matheus Geovanini de Paiva", "CPF": "073.002.736-88", "E-mail": "lucas.paiva95@hotmail.com", "Papel": "Técnico", "Total Alvo": 3000.00, "Pró-Labore Bruto": 1621.00, "Distribuição de Lucro": 1560.00},
        {"Sócio": "Thaciany Santos Franco", "CPF": "135.590.246-09", "E-mail": "thacianysantosfranco0309@hotmail.com", "Papel": "Técnico", "Total Alvo": 3000.00, "Pró-Labore Bruto": 1621.00, "Distribuição de Lucro": 1660.00},
        {"Sócio": "Otavio Augusto dos Santos Assunção", "CPF": "072.121.646-31", "E-mail": "otavioaugustoassuncao@gmail.com", "Papel": "Técnico", "Total Alvo": 3800.00, "Pró-Labore Bruto": 1621.00, "Distribuição de Lucro": 2360.00},
    ])

# ================= INICIALIZAÇÃO DA TABELA DE SÓCIOS =================
if f"alvos_{key_sufixo}" not in st.session_state or st.session_state[f"alvos_{key_sufixo}"].empty:
    st.session_state[f"alvos_{key_sufixo}"] = get_tabela_padrao()

df_temp = st.session_state[f"alvos_{key_sufixo}"].copy()

df_temp["Pró-Labore Bruto"] = pd.to_numeric(df_temp["Pró-Labore Bruto"], errors='coerce').fillna(0.0)
df_temp["Distribuição de Lucro"] = pd.to_numeric(df_temp["Distribuição de Lucro"], errors='coerce').fillna(0.0)

num_socios = len(df_temp)
df_temp["Pró-Labore Líq."] = df_temp["Pró-Labore Bruto"] * 0.89
df_temp["Total Recebido"] = df_temp["Pró-Labore Líq."] + df_temp["Distribuição de Lucro"]

# ================= FUNÇÃO DE CÁLCULO HISTÓRICO =================
def obter_metricas_historicas():
    dados_historico = []; dados_socios = []; caixa_acumulado = 0.0; meses_operacao = 0
    for ano_iter in range(2026, ano_sel + 1):
        for mes_idx_iter in range(1, 13):
            if ano_iter == 2026 and mes_idx_iter < 5: continue
            if ano_iter == ano_sel and mes_idx_iter > meses.index(mes_sel) + 1: break
            
            mes_nome_iter = meses[mes_idx_iter - 1]
            key_iter = f"{mes_nome_iter}_{ano_iter}"
            
            if ano_iter == ano_sel and mes_idx_iter == meses.index(mes_sel) + 1:
                is_ativo = mes_ativo
            else:
                is_past = (ano_iter < ano_atual_real) or (ano_iter == ano_atual_real and mes_idx_iter <= mes_atual_real)
                is_ativo = st.session_state.get(f"ativo_{key_iter}", is_past)

            if is_ativo:
                u_m = st.session_state.get(f"unid_{key_iter}", 7)
                v_u_m = st.session_state.get(f"valor_unid_{key_iter}", 5460.00)
                fat_m = u_m * v_u_m
                
                taxa_m = st.session_state.get(f"imposto_{key_iter}", 6.0) / 100
                contab_m = st.session_state.get(f"contab_{key_iter}", 487.50)
                fer_m = st.session_state.get(f"feriados_{key_iter}", 0)
                pl_base_hist = st.session_state.get(f"prolab_{key_iter}", 1621.00)
                
                df_cv = st.session_state.get(f"custos_{key_iter}", pd.DataFrame({"Valor (R$)": [0.0]}))
                if "Valor (R$)" not in df_cv.columns: df_cv["Valor (R$)"] = 0.0
                custos_var_m = pd.to_numeric(df_cv["Valor (R$)"], errors='coerce').fillna(0).sum()
                
                df_soc_m = st.session_state.get(f"alvos_{key_iter}", pd.DataFrame())
                if df_soc_m.empty: df_soc_m = get_tabela_padrao()
                df_soc_m = df_soc_m.dropna(subset=["Sócio"])
                
                if "Pró-Labore Bruto" not in df_soc_m.columns: df_soc_m["Pró-Labore Bruto"] = pl_base_hist
                if "Distribuição de Lucro" not in df_soc_m.columns: df_soc_m["Distribuição de Lucro"] = (pd.to_numeric(df_soc_m["Total Alvo"], errors='coerce').fillna(0) - (df_soc_m["Pró-Labore Bruto"]*0.89)).clip(lower=0)
                
                pl_bruto_total_m = pd.to_numeric(df_soc_m["Pró-Labore Bruto"], errors='coerce').fillna(0.0).sum()
                custos_tot_m = (fat_m * taxa_m) + contab_m + (fer_m * 100) + custos_var_m + pl_bruto_total_m
                
                lucro_liq_m = fat_m - custos_tot_m
                dist_tot_m = pd.to_numeric(df_soc_m["Distribuição de Lucro"], errors='coerce').fillna(0.0).sum()
                
                for _, row in df_soc_m.iterrows():
                    dados_socios.append({
                        "Período": f"{mes_nome_iter[:3]}/{ano_iter}",
                        "Sócio": row["Sócio"],
                        "Distribuição de Lucro (R$)": row["Distribuição de Lucro"]
                    })
                
                sobra_m = lucro_liq_m - dist_tot_m
                caixa_acumulado += sobra_m
                meses_operacao += 1
                
                dados_historico.append({
                    "Período": f"{mes_nome_iter[:3]}/{ano_iter}",
                    "Faturamento": fat_m,
                    "Despesas Totais": custos_tot_m,
                    "Sobra do Mês": sobra_m,
                    "Caixa Acumulado": caixa_acumulado
                })
                
    return pd.DataFrame(dados_historico), pd.DataFrame(dados_socios), caixa_acumulado, meses_operacao

df_hist, df_socios_hist, caixa_total_acumulado, meses_operacao_ativos = obter_metricas_historicas()

# ================= MOTOR DE PDF =================
def add_watermark(pdf, y_pos=70):
    if os.path.exists("LogoSimbolo.jpg"):
        try:
            with pdf.local_context(fill_opacity=0.06):
                pdf.image("LogoSimbolo.jpg", x=55, y=y_pos, w=100)
        except: pass

def gerar_pdf_recibos(df, mes, ano, cnpj):
    pdf = FPDF(); pdf.set_auto_page_break(auto=False)
    data_e = datetime.now().strftime("%d/%m/%Y")
    mes_ref_completo = f"{mes}/{ano}"
    df_pdf = df.dropna(subset=["Sócio"])
    for _, row in df_pdf.iterrows():
        if row['Pró-Labore Bruto'] == 0 and row['Distribuição de Lucro'] == 0: continue
        pdf.add_page(); add_watermark(pdf, 35) 
        
        pl_b = row['Pró-Labore Bruto']; inss = pl_b * 0.11
        pdf.set_y(15); pdf.set_font("helvetica", "B", 12); pdf.cell(0, 8, "RECIBO DE PRÓ-LABORE", align="C", ln=True); pdf.ln(8)
        pdf.set_font("helvetica", "", 9); pdf.cell(0, 5, f"Fonte Pagadora: RADLUMEN LTDA - CNPJ: {cnpj}", ln=True)
        pdf.cell(0, 5, f"Beneficiário(a): {row['Sócio']} - CPF: {row['CPF']}", ln=True); pdf.cell(0, 5, f"Mês de Referência: {mes_ref_completo}", ln=True); pdf.ln(5)
        pdf.multi_cell(0, 5, f"Recebi da empresa RADLUMEN LTDA a importância líquida de {fmt_br(row['Pró-Labore Líq.'])}, referente ao Pró-labore do mês de referência."); pdf.ln(5)
        pdf.set_font("helvetica", "B", 9); pdf.cell(80, 6, "Descrição", border=1); pdf.cell(50, 6, "Valor", border=1, ln=True, align="R")
        pdf.set_font("helvetica", "", 9); pdf.cell(80, 6, "Valor Bruto do Pró-Labore:", border=1); pdf.cell(50, 6, fmt_br(pl_b), border=1, ln=True, align="R")
        pdf.cell(80, 6, "(-) Retenção INSS (11%):", border=1); pdf.cell(50, 6, f"- {fmt_br(inss)}", border=1, ln=True, align="R")
        pdf.set_font("helvetica", "B", 9); pdf.cell(80, 6, "VALOR LÍQUIDO RECEBIDO:", border=1); pdf.cell(50, 6, fmt_br(row['Pró-Labore Líq.']), border=1, ln=True, align="R")
        pdf.set_y(110); pdf.cell(0, 4, "____________________________________________________________", align="C", ln=True)
        pdf.cell(0, 4, row['Sócio'], align="C", ln=True); pdf.set_font("helvetica", "", 9); pdf.cell(0, 4, "Assinatura do Sócio", align="C", ln=True); pdf.ln(3); pdf.cell(0, 4, f"Data: {data_e}", align="L")
        
        pdf.set_line_width(0.3); pdf.dashed_line(10, 148.5, 200, 148.5, dash_length=2, space_length=2)
        add_watermark(pdf, 185) 
        pdf.set_y(160); pdf.set_font("helvetica", "B", 12); pdf.cell(0, 8, "RECIBO DE ANTECIPAÇÃO DE LUCROS", align="C", ln=True); pdf.ln(8)
        pdf.set_font("helvetica", "", 9); pdf.cell(0, 5, f"Fonte Pagadora: RADLUMEN LTDA - CNPJ: {cnpj}", ln=True)
        pdf.cell(0, 5, f"Beneficiário(a): {row['Sócio']} - CPF: {row['CPF']}", ln=True); pdf.cell(0, 5, f"Mês de Referência: {mes_ref_completo}", ln=True); pdf.ln(5)
        pdf.multi_cell(0, 5, f"Recebi da empresa RADLUMEN LTDA a importância líquida de {fmt_br(row['Distribuição de Lucro'])}, referente à Antecipação de Lucros do mês de referência, distribuída de forma desproporcional às quotas de capital, em comum acordo e estrita observância ao estipulado em Ata de Reunião de Sócios e na legislação vigente."); pdf.ln(5)
        pdf.set_font("helvetica", "B", 9); pdf.cell(80, 6, "VALOR LÍQUIDO RECEBIDO:", border=1); pdf.cell(50, 6, fmt_br(row['Distribuição de Lucro']), border=1, ln=True, align="R")
        pdf.set_y(255); pdf.cell(0, 4, "____________________________________________________________", align="C", ln=True)
        pdf.cell(0, 4, row['Sócio'], align="C", ln=True); pdf.set_font("helvetica", "", 9); pdf.cell(0, 4, "Assinatura do Sócio", align="C", ln=True); pdf.ln(3); pdf.cell(0, 4, f"Data: {data_e}", align="L")
    return pdf.output()

def gerar_pdf_contabilidade(df, mes, ano, cnpj):
    pdf = FPDF(); pdf.add_page(); add_watermark(pdf, 70)
    df_pdf = df.dropna(subset=["Sócio"])
    pdf.set_font("helvetica", "B", 14); pdf.cell(0, 10, "RELATÓRIO DE DISTRIBUIÇÃO DE LUCROS", ln=True, align="C")
    pdf.set_font("helvetica", "", 10); pdf.cell(0, 5, f"Empresa: RADLUMEN LTDA - CNPJ: {cnpj}", ln=True); pdf.cell(0, 5, f"Referência: {mes}/{ano}", ln=True); pdf.ln(10)
    pdf.set_fill_color(26, 54, 93); pdf.set_text_color(255); pdf.set_font("helvetica", "B", 10)
    pdf.cell(80, 8, "Nome do Sócio", 1, 0, "L", True); pdf.cell(50, 8, "CPF", 1, 0, "C", True); pdf.cell(50, 8, "Distribuição (R$)", 1, 1, "R", True)
    pdf.set_text_color(0); pdf.set_font("helvetica", "", 10)
    total_d = 0
    for _, row in df_pdf.iterrows():
        if row['Distribuição de Lucro'] == 0: continue
        pdf.cell(80, 8, str(row['Sócio']), 1); pdf.cell(50, 8, str(row['CPF']), 1, 0, "C"); pdf.cell(50, 8, fmt_br(row['Distribuição de Lucro']), 1, 1, "R")
        total_d += row['Distribuição de Lucro']
    pdf.set_font("helvetica", "B", 10); pdf.cell(130, 8, "TOTAL:", 1, 0, "R"); pdf.cell(50, 8, fmt_br(total_d), 1, 1, "R")
    return pdf.output()

def gerar_pdf_relatorio_geral(df_socios, df_custos, mes, ano, cnpj, f_bruto, i_simples, v_contab, v_feriados, tot_prolab_bruto, lucro_liq, dist_tot, sobra):
    pdf = FPDF(); pdf.add_page(); add_watermark(pdf, 70)
    
    # Cabeçalho
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 8, "RELATÓRIO FINANCEIRO GERENCIAL", ln=True, align="C")
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 5, f"Empresa: RADLUMEN LTDA - CNPJ: {cnpj}", ln=True, align="C")
    pdf.cell(0, 5, f"Período de Apuração: {mes}/{ano}", ln=True, align="C")
    pdf.ln(8)
    
    # 1. RECEITAS
    pdf.set_fill_color(230, 230, 230); pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 8, " 1. RECEITAS DO MÊS", border=1, ln=True, fill=True)
    pdf.set_font("helvetica", "", 10); pdf.cell(130, 6, " Faturamento Bruto Total:", border=1)
    pdf.set_font("helvetica", "B", 10); pdf.cell(60, 6, fmt_br(f_bruto), border=1, ln=True, align="R"); pdf.ln(4)
    
    # 2. DESPESAS E CUSTOS
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 8, " 2. DESPESAS E CUSTOS OPERACIONAIS", border=1, ln=True, fill=True)
    pdf.set_font("helvetica", "", 10)
    pdf.cell(130, 6, " Imposto (Simples Nacional):", border=1); pdf.cell(60, 6, fmt_br(i_simples), border=1, ln=True, align="R")
    pdf.cell(130, 6, " Honorários Contábeis:", border=1); pdf.cell(60, 6, fmt_br(v_contab), border=1, ln=True, align="R")
    pdf.cell(130, 6, " Fundo de Feriados:", border=1); pdf.cell(60, 6, fmt_br(v_feriados), border=1, ln=True, align="R")
    
    tot_inss = tot_prolab_bruto * 0.11
    tot_pl_liq = tot_prolab_bruto - tot_inss
    pdf.cell(130, 6, " Folha de Pró-Labore (Líquido Pago aos Sócios):", border=1); pdf.cell(60, 6, fmt_br(tot_pl_liq), border=1, ln=True, align="R")
    pdf.cell(130, 6, " Guia de INSS (11% Retido do Pró-Labore):", border=1); pdf.cell(60, 6, fmt_br(tot_inss), border=1, ln=True, align="R")
    
    tot_custo_var = 0
    if "Valor (R$)" in df_custos.columns:
        for _, c_row in df_custos.iterrows():
            c_val = pd.to_numeric(c_row['Valor (R$)'], errors='coerce')
            if pd.notna(c_val) and c_val > 0:
                desc = str(c_row.get('Descrição', "Custo Variável Extra")).strip() or "Custo Variável Extra"
                pdf.cell(130, 6, f" Extra: {desc[:50]}:", border=1); pdf.cell(60, 6, fmt_br(c_val), border=1, ln=True, align="R")
                tot_custo_var += c_val
            
    tot_despesas = i_simples + v_contab + v_feriados + tot_prolab_bruto + tot_custo_var
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(130, 6, " TOTAL DE DESPESAS:", border=1); pdf.cell(60, 6, fmt_br(tot_despesas), border=1, ln=True, align="R"); pdf.ln(4)
    
    # 3. RESULTADO LÍQUIDO
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 8, " 3. RESULTADO LÍQUIDO APURADO", border=1, ln=True, fill=True)
    pdf.set_font("helvetica", "", 10)
    pdf.cell(130, 6, " Lucro Líquido (Receitas - Despesas):", border=1)
    pdf.set_font("helvetica", "B", 10); pdf.cell(60, 6, fmt_br(lucro_liq), border=1, ln=True, align="R"); pdf.ln(4)
    
    # 4. DISTRIBUIÇÃO E REPASSE
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 8, " 4. DISTRIBUIÇÃO AOS SÓCIOS", border=1, ln=True, fill=True)
    pdf.set_fill_color(26, 54, 93); pdf.set_text_color(255); pdf.set_font("helvetica", "B", 9)
    pdf.cell(70, 7, "Sócio", border=1, fill=True); pdf.cell(35, 7, "Pró-Labore Líq.", border=1, align="C", fill=True)
    pdf.cell(35, 7, "Lucro Distribuído", border=1, align="C", fill=True); pdf.cell(50, 7, "Total Repassado", border=1, align="C", ln=True, fill=True)
    
    pdf.set_text_color(0); pdf.set_font("helvetica", "", 9)
    df_validos = df_socios.dropna(subset=["Sócio"])
    tot_repassado_global = 0
    for _, s_row in df_validos.iterrows():
        if s_row['Pró-Labore Bruto'] > 0 or s_row['Distribuição de Lucro'] > 0:
            pl_l = pd.to_numeric(s_row['Pró-Labore Líq.'], errors='coerce')
            d_l = pd.to_numeric(s_row['Distribuição de Lucro'], errors='coerce')
            tot_r = pd.to_numeric(s_row['Total Recebido'], errors='coerce')
            tot_repassado_global += tot_r
            pdf.cell(70, 6, str(s_row['Sócio'])[:30], border=1)
            pdf.cell(35, 6, fmt_br(pl_l), border=1, align="R"); pdf.cell(35, 6, fmt_br(d_l), border=1, align="R"); pdf.cell(50, 6, fmt_br(tot_r), border=1, align="R", ln=True)

    pdf.set_font("helvetica", "B", 9)
    pdf.cell(140, 6, "TOTAL GERAL REPASSADO AOS SÓCIOS:", border=1, align="R")
    pdf.cell(50, 6, fmt_br(tot_repassado_global), border=1, align="R", ln=True); pdf.ln(4)
    
    # 5. FECHAMENTO DE CAIXA
    pdf.set_font("helvetica", "B", 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 8, " 5. FECHAMENTO DE CAIXA DA EMPRESA", border=1, ln=True, fill=True)
    pdf.set_font("helvetica", "", 10)
    pdf.cell(130, 6, " Sobra do Mês Retida na Conta da Empresa:", border=1)
    pdf.set_font("helvetica", "B", 10); pdf.cell(60, 6, fmt_br(sobra), border=1, ln=True, align="R")
    
    pdf.ln(10)
    pdf.set_font("helvetica", "I", 8)
    pdf.cell(0, 4, f"Relatório emitido pelo Sistema de Gestão Interna da Radlumen em {datetime.now().strftime('%d/%m/%Y %H:%M')}.", ln=True, align="C")
    return pdf.output()

def gerar_zip_recibos_individuais(df, mes, ano, cnpj):
    buffer_zip = io.BytesIO()
    with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zip_file:
        df_pdf = df.dropna(subset=["Sócio"])
        for _, row in df_pdf.iterrows():
            if row['Pró-Labore Bruto'] == 0 and row['Distribuição de Lucro'] == 0: continue
            df_ind = pd.DataFrame([row])
            pdf_bytes = gerar_pdf_recibos(df_ind, mes, ano, cnpj)
            nome_socio_limpo = str(row['Sócio']).replace(" ", "_")
            nome_arquivo = f"Recibo_{nome_socio_limpo}_{mes}_{ano}.pdf"
            zip_file.writestr(nome_arquivo, pdf_bytes)
    buffer_zip.seek(0)
    return buffer_zip.getvalue()

# ================= TELA PRINCIPAL (ABAS) =================
st.title("Gestão Integrada RADLUMEN")
tab_g, tab_d, tab_rh = st.tabs(["📋 Gestão Mensal e Documentos", "📈 Dashboard e Gráficos", "🩺 RH & Compliance"])

with tab_g:
    st.subheader(f"Repasse: {mes_sel}/{ano_sel}")
    
    edited_df = st.data_editor(
        df_temp[["Sócio", "CPF", "E-mail", "Papel", "Total Alvo", "Pró-Labore Bruto", "Pró-Labore Líq.", "Distribuição de Lucro", "Total Recebido"]],
        hide_index=True, num_rows="dynamic", use_container_width=True,
        disabled=["Pró-Labore Líq.", "Total Recebido"],
        key=f"ed_alvos_{key_sufixo}"
    )
    
    st.session_state[f"alvos_{key_sufixo}"] = edited_df.dropna(subset=["Sócio"])[["Sócio", "CPF", "E-mail", "Papel", "Total Alvo", "Pró-Labore Bruto", "Distribuição de Lucro"]].copy()

    col_btn_reset, col_espaco = st.columns([1, 2])
    with col_btn_reset:
        if st.button("🔄 Recalcular Padrão"):
            st.session_state[f"alvos_{key_sufixo}"] = get_tabela_padrao()
            tabela_key = f"ed_alvos_{key_sufixo}"
            if tabela_key in st.session_state:
                del st.session_state[tabela_key]
            st.rerun()

    total_prolabore_bruto_tabela = edited_df["Pró-Labore Bruto"].sum()
    total_inss_mes_tabela = total_prolabore_bruto_tabela * 0.11
    dist_total_mes = edited_df["Distribuição de Lucro"].sum()

    custos_fixos_mes = imp_simples + contab + (feriados * 100) + total_prolabore_bruto_tabela
    lucro_liq_mes = fat_bruto - (custos_fixos_mes + total_custos_var)
    sobra_mes = lucro_liq_mes - dist_total_mes

    st.divider()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Faturamento", f"R$ {fat_bruto:,.2f}")
    c2.metric("Simples Nacional", f"R$ {imp_simples:,.2f}")
    c3.metric("INSS Retido", f"R$ {total_inss_mes_tabela:,.2f}")
    c4.metric("Custos Operacionais", f"R$ {total_custos_var + (feriados * 100):,.2f}")
    c5.metric("Sobra do Mês", f"R$ {sobra_mes:,.2f}")
    
    st.divider()
    st.subheader("🏦 Patrimônio da Empresa (Caixa Acumulado Geral)")
    col_a, col_b = st.columns(2)
    col_a.metric(f"Saldo Total em Conta", f"R$ {caixa_total_acumulado:,.2f}")
    meta_acumulada = meses_operacao_ativos * 1500.0
    diferenca_meta = caixa_total_acumulado - meta_acumulada
    if meses_operacao_ativos == 0: col_b.info("Nenhum mês de operação registado.")
    elif diferenca_meta >= 0: col_b.success(f"✔️ Caixa Saudável (+ R$ {diferenca_meta:,.2f} acima da meta)")
    else: col_b.error(f"⚠️ Alerta: Faltam R$ {abs(diferenca_meta):,.2f} para compor a reserva mínima.")

    st.divider()
    st.subheader("🖨️ Exportação de Documentos e Comunicação")
    col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns(5)
    
    with col_btn1:
        if st.button("👤 Recibos (Lote Único)", use_container_width=True):
            pdf_b = gerar_pdf_recibos(edited_df, mes_sel, ano_sel, cnpj_rad)
            st.markdown(f'<a href="data:application/pdf;base64,{base64.b64encode(pdf_b).decode()}" download="Recibos_Todos_{key_sufixo}.pdf" style="display:block; text-align:center; padding:8px; background:#1a365d; color:white; text-decoration:none; border-radius:5px; font-weight:bold;">⬇️ Baixar PDF Único</a>', unsafe_allow_html=True)
    with col_btn2:
        if st.button("📦 Recibos Separados (.ZIP)", use_container_width=True):
            zip_bytes = gerar_zip_recibos_individuais(edited_df, mes_sel, ano_sel, cnpj_rad)
            st.markdown(f'<a href="data:application/zip;base64,{base64.b64encode(zip_bytes).decode()}" download="Recibos_Individuais_{key_sufixo}.zip" style="display:block; text-align:center; padding:8px; background:#2b6cb0; color:white; text-decoration:none; border-radius:5px; font-weight:bold;">⬇️ Baixar Pasta ZIP</a>', unsafe_allow_html=True)
    with col_btn3:
        if st.button("📊 Relatório Contador", use_container_width=True):
            pdf_c = gerar_pdf_contabilidade(edited_df, mes_sel, ano_sel, cnpj_rad)
            st.markdown(f'<a href="data:application/pdf;base64,{base64.b64encode(pdf_c).decode()}" download="Contabilidade_{key_sufixo}.pdf" style="display:block; text-align:center; padding:8px; background:#2f855a; color:white; text-decoration:none; border-radius:5px; font-weight:bold;">⬇️ Baixar Relatório</a>', unsafe_allow_html=True)
    with col_btn4:
        if st.button("🗄️ Backup Mensal", use_container_width=True):
            pdf_geral = gerar_pdf_relatorio_geral(edited_df, df_custos, mes_sel, ano_sel, cnpj_rad, fat_bruto, imp_simples, contab, feriados * 100, total_prolabore_bruto_tabela, lucro_liq_mes, dist_total_mes, sobra_mes)
            st.markdown(f'<a href="data:application/pdf;base64,{base64.b64encode(pdf_geral).decode()}" download="Relatorio_Gerencial_{key_sufixo}.pdf" style="display:block; text-align:center; padding:8px; background:#d97706; color:white; text-decoration:none; border-radius:5px; font-weight:bold;">⬇️ Baixar PDF Geral</a>', unsafe_allow_html=True)
    with col_btn5:
        if st.button("🚀 Disparar E-mails", use_container_width=True, type="primary"):
            with st.spinner("A gerar PDFs e a enviar e-mails..."):
                df_envio = edited_df.dropna(subset=["Sócio"])
                sucessos = 0; erros = []
                for _, row in df_envio.iterrows():
                    email_destinatario = str(row["E-mail"]).strip()
                    if "@" not in email_destinatario: continue
                    if row["Pró-Labore Bruto"] == 0 and row["Distribuição de Lucro"] == 0: continue
                    
                    df_individual = pd.DataFrame([row])
                    pdf_b = gerar_pdf_recibos(df_individual, mes_sel, ano_sel, cnpj_rad)
                    primeiro_nome = row['Sócio'].split()[0]
                    nome_pdf = f"Recibos_{primeiro_nome}_{mes_sel}_{ano_sel}.pdf"
                    
                    assunto = f"Repasse RADLUMEN - {mes_sel}/{ano_sel}"
                    pl_bruto_ind = row["Pró-Labore Bruto"]
                    inss_ind = pl_bruto_ind * 0.11
                    
                    corpo = f"""
                    <div style="font-family: Arial, sans-serif; color: #333; font-size: 14px;">
                        <p>Olá, {primeiro_nome},</p>
                        <p>Segue o detalhamento do seu repasse referente ao mês de <b>{mes_sel}/{ano_sel}</b>.</p>
                        
                        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #1a365d; max-width: 450px;">
                            <p style="margin-top: 0; color: #1a365d; font-weight: bold;">🔹 Resumo Financeiro</p>
                            <p style="margin: 5px 0;">Pró-Labore Bruto: R$ {pl_bruto_ind:,.2f}</p>
                            <p style="margin: 5px 0;">(-) Retenção INSS (11%): R$ {inss_ind:,.2f}</p>
                            <p style="margin: 5px 0;">(+) Distribuição de Lucros: R$ {row['Distribuição de Lucro']:,.2f}</p>
                            <hr style="border: 0; border-top: 1px solid #ddd; margin: 15px 0;">
                            <p style="margin-bottom: 0; font-weight: bold;">VALOR LÍQUIDO RECEBIDO: R$ {row['Total Recebido']:,.2f}</p>
                        </div>
                        
                        <p>📄 <i>Em anexo, encontram-se os seus recibos oficiais (Pró-labore e Antecipação de Lucros) para o seu controlo. A sua via já se encontra arquivada e registada digitalmente.</i></p>
                        
                        <p>Qualquer dúvida, estou à disposição.</p>
                        <p>Um abraço,<br><b>Marcus Almeida</b><br>Gestão Radlumen</p>
                    </div>
                    """
                    status = enviar_email(email_destinatario, assunto, corpo, pdf_b, nome_pdf)
                    if status is True: sucessos += 1
                    else: erros.append(f"{primeiro_nome}: {status}")
                if erros: st.error(f"Erros encontrados: {erros}")
                else: st.success(f"✅ Sucesso! {sucessos} e-mails foram enviados diretamente para os sócios da tabela.")

    # ================= MÓDULO ATA TRIMESTRAL =================
    st.divider()
    st.subheader("📝 Gerar Ata de Reunião de Sócios (Por Período)")
    col_ata_num, col_empty = st.columns([1, 3])
    ata_numero = col_ata_num.text_input("Número da Ata", value="", key="ata_num")
    col_ata1, col_ata2, col_ata3, col_ata4 = st.columns(4)
    ata_mes_in = col_ata1.selectbox("Mês Inicial", meses, index=4, key="ata_mi") 
    ata_ano_in = col_ata2.selectbox("Ano Inicial", range(2026, 2036), index=0, key="ata_ai")
    ata_mes_fim = col_ata3.selectbox("Mês Final", meses, index=6, key="ata_mf")  
    ata_ano_fim = col_ata4.selectbox("Ano Final", range(2026, 2036), index=0, key="ata_af")

    idx_inicio_abs = meses.index(ata_mes_in) + 1 + (ata_ano_in * 12)
    idx_fim_abs = meses.index(ata_mes_fim) + 1 + (ata_ano_fim * 12)
    total_distribuido_ata = 0.0

    if idx_inicio_abs <= idx_fim_abs:
        for ano_iter in range(ata_ano_in, ata_ano_fim + 1):
            for mes_idx_iter in range(1, 13):
                current_abs_idx = mes_idx_iter + (ano_iter * 12)
                if idx_inicio_abs <= current_abs_idx <= idx_fim_abs:
                    if ano_iter == 2026 and mes_idx_iter < 5: continue
                    mes_nome_iter = meses[mes_idx_iter - 1]
                    key_sufixo_iter = f"{mes_nome_iter}_{ano_iter}"
                    is_past_iter = (ano_iter < ano_atual_real) or (ano_iter == ano_atual_real and mes_idx_iter <= mes_atual_real)
                    ativo_iter = st.session_state.get(f"ativo_{key_sufixo_iter}", is_past_iter)
                    if ativo_iter:
                        df_soc_m = st.session_state.get(f"alvos_{key_sufixo_iter}", pd.DataFrame())
                        if not df_soc_m.empty:
                            if "Distribuição de Lucro" not in df_soc_m.columns:
                                pl_base_antigo = st.session_state.get(f"prolab_{key_sufixo_iter}", 1621.00)
                                df_soc_m["Distribuição de Lucro"] = (pd.to_numeric(df_soc_m["Total Alvo"], errors='coerce').fillna(0) - (pl_base_antigo*0.89)).clip(lower=0)
                            total_distribuido_ata += pd.to_numeric(df_soc_m["Distribuição de Lucro"], errors='coerce').fillna(0.0).sum()
                        
        st.info(f"💰 Lucro Total Distribuído no período selecionado: **R$ {total_distribuido_ata:,.2f}**")
        
        def gerar_pdf_ata(total, mes_in, ano_in, mes_f, ano_f, df_socios, cnpj, numero_ata):
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.set_margins(20, 20, 20); pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
            add_watermark(pdf, 70)
            pdf.set_font("helvetica", "B", 14); pdf.cell(0, 5, "RADLUMEN LTDA", align="C", ln=True)
            pdf.set_font("helvetica", "", 10); pdf.cell(0, 5, f"CNPJ: {cnpj}", align="C", ln=True); pdf.ln(6)
            titulo_ata = f"ATA DE REUNIÃO DE SÓCIOS Nº {numero_ata}" if numero_ata else "ATA DE REUNIÃO DE SÓCIOS"
            pdf.set_font("helvetica", "B", 12); pdf.cell(0, 5, titulo_ata, align="C", ln=True)
            pdf.set_font("helvetica", "B", 10); pdf.cell(0, 5, f"Ref: Aprovação de Antecipação de Lucros (Período: {mes_in}/{ano_in} a {mes_f}/{ano_f})", align="C", ln=True); pdf.ln(6)
            pdf.set_font("helvetica", "", 10.5)
            hoje = datetime.now()
            meses_extenso = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
            data_texto = f"Aos {hoje.strftime('%d')} dias do mês de {meses_extenso[hoje.month-1]} do ano de {hoje.year}"
            
            p1 = f"{data_texto}, às 09:00 horas, reuniram-se os sócios da empresa RADLUMEN LTDA, inscrita no CNPJ sob o nº {cnpj}, para deliberar sobre a antecipação e distribuição dos lucros apurados no período de {mes_in}/{ano_in} a {mes_f}/{ano_f}."
            p2 = f"A presidência da reunião foi assumida pelo sócio-administrador Marcus Vinicius de Almeida, que apresentou os demonstrativos financeiros do referido período. Verificou-se que a empresa obteve um montante total de R$ {total:,.2f} destinado e já transferido a título de antecipação de lucros entre os sócios."
            p3 = "Por deliberação unânime, os sócios ratificam e aprovam que o valor total supracitado foi distribuído de forma desproporcional à participação de cada sócio no capital social da empresa, em estrita observância ao que faculta o Artigo 1.007 da Lei nº 10.406/2002 (Código Civil Brasileiro) e o regimento interno acordado entre as partes."
            p4 = "Os sócios declaram ter pleno conhecimento e estar de inteiro acordo com os critérios de dedicação, desempenho e responsabilidades operacionais utilizados para a referida distribuição desproporcional. Declaram, ainda, que os repasses individuais referentes a este período foram devidamente recebidos e quitados, mantendo-se a privacidade dos valores em conformidade com as boas práticas de governança corporativa, não restando qualquer pendência ou reclamação a este título contra a sociedade ou seus administradores."
            p5 = "Ademais, visando garantir a máxima transparência deste processo, fica registado que qualquer sócio possui livre acesso e direito para consultar a contabilidade responsável pela empresa caso haja quaisquer dúvidas sobre os demonstrativos financeiros aqui apresentados."
            
            df_pdf = df_socios.dropna(subset=["Sócio"])
            df_pdf = df_pdf[(df_pdf['Pró-Labore Bruto'] > 0) | (df_pdf['Distribuição de Lucro'] > 0)]
            p6 = f"Nada mais havendo a tratar, a reunião foi encerrada e lavrou-se a presente Ata, que segue assinada por todos os {len(df_pdf)} sócios presentes."
            
            for p in [p1, p2, p3, p4, p5, p6]: pdf.multi_cell(0, 5.5, "        " + p, align="J"); pdf.ln(2.5)
            pdf.ln(5)
            nomes = df_pdf['Sócio'].tolist(); x_start = 20; col_w = 56.6; y_start = pdf.get_y()
            if y_start > 250: pdf.add_page(); y_start = 20
            for i, nome in enumerate(nomes):
                col = i % 3; row = i // 3; x = x_start + col * col_w; y = y_start + row * 18
                line_width = 46; x_line = x + (col_w - line_width) / 2
                pdf.set_line_width(0.3); pdf.line(x_line, y, x_line + line_width, y)
                pdf.set_xy(x, y + 1.5); pdf.set_font("helvetica", "B", 7.5); pdf.multi_cell(col_w, 3.5, nome, align="C")
            return pdf.output()

        if st.button("📝 Gerar Ata em PDF", type="primary"):
            if not ata_numero: st.warning("Por favor, preencha o 'Número da Ata'.")
            else:
                try:
                    pdf_bytes_ata = gerar_pdf_ata(total_distribuido_ata, ata_mes_in, ata_ano_in, ata_mes_fim, ata_ano_fim, edited_df, cnpj_rad, ata_numero)
                    st.markdown(f'<a href="data:application/pdf;base64,{base64.b64encode(pdf_bytes_ata).decode()}" download="Ata_{ata_numero.replace("/","-")}_Radlumen.pdf" style="display:inline-block; padding:10px 20px; background-color:#d97706; color:white; text-decoration:none; border-radius:5px; font-weight:bold;">⬇️ Baixar Ata Oficial</a>', unsafe_allow_html=True)
                except Exception as e: st.error(f"Erro ao gerar Ata: {e}")

# ================= ABA DASHBOARD =================
with tab_d:
    st.header("📈 Dashboard Analítico da Radlumen")
    if df_hist.empty:
        st.info("Nenhum dado operacional guardado. Insira os valores, ative os meses na aba lateral e guarde na nuvem para gerar os gráficos.")
    else:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("Crescimento do Caixa da Empresa")
            fig_caixa = px.area(df_hist, x="Período", y="Caixa Acumulado", markers=True, color_discrete_sequence=['#2f855a'])
            fig_caixa.update_layout(xaxis_title="", yaxis_title="R$")
            st.plotly_chart(fig_caixa, use_container_width=True)

        with col_g2:
            st.subheader("Faturamento vs Despesas")
            df_bar = pd.melt(df_hist, id_vars=['Período'], value_vars=['Faturamento', 'Despesas Totais'], var_name='Categoria', value_name='Valor')
            fig_fat = px.bar(df_bar, x="Período", y="Valor", color="Categoria", barmode='group', color_discrete_map={"Faturamento": "#1a365d", "Despesas Totais": "#e53e3e"})
            fig_fat.update_layout(xaxis_title="", yaxis_title="R$")
            st.plotly_chart(fig_fat, use_container_width=True)

        st.divider()
        st.subheader("Histórico de Distribuição de Lucros por Sócio")
        if not df_socios_hist.empty:
            fig_soc = px.line(df_socios_hist, x="Período", y="Distribuição de Lucro (R$)", color="Sócio", markers=True, color_discrete_sequence=px.colors.qualitative.Set2)
            fig_soc.update_layout(xaxis_title="Mês/Ano", yaxis_title="R$ Distribuídos")
            st.plotly_chart(fig_soc, use_container_width=True)

# ================= ABA RH & COMPLIANCE =================
with tab_rh:
    st.header("🩺 Gestão de Saúde Ocupacional (ASO)")
    st.write("Atualize a data do último exame de cada técnico. O sistema verifica as datas e você pode disparar os avisos com um clique.")
    
    df_rh_view = st.session_state["rh_dados"].copy()
    status_list = []
    venc_list = []
    
    for aso_str in df_rh_view["Último ASO"]:
        if pd.isna(aso_str) or str(aso_str).strip() == "":
            status_list.append("⚪ Pendente")
            venc_list.append("-")
            continue
        try:
            data_aso_calc = pd.to_datetime(aso_str, format="%d/%m/%Y")
            venc = data_aso_calc + pd.DateOffset(years=1)
            venc_list.append(venc.strftime("%d/%m/%Y"))
            dias_para_vencer = (venc - hoje).days
            
            if dias_para_vencer < 0: status_list.append("🔴 Vencido")
            elif dias_para_vencer <= 30: status_list.append(f"🟡 Vence em {dias_para_vencer} dias")
            else: status_list.append("🟢 Em dia")
        except:
            status_list.append("⚪ Formato Inválido")
            venc_list.append("-")
            
    df_rh_view["Data de Vencimento"] = venc_list
    df_rh_view["Status"] = status_list
    
    edited_rh = st.data_editor(
        df_rh_view[["Sócio", "E-mail", "Último ASO", "Data de Vencimento", "Status", "Ano Último Aviso"]],
        hide_index=True, use_container_width=True,
        disabled=["Sócio", "Data de Vencimento", "Status", "Ano Último Aviso"],
        column_config={
            "Último ASO": st.column_config.TextColumn("Último ASO (DD/MM/AAAA)"),
            "Ano Último Aviso": st.column_config.NumberColumn("Último Aviso (Ano)", format="%d")
        }
    )
    
    df_raw_new = st.session_state["rh_dados"].copy()
    df_raw_new["Último ASO"] = edited_rh["Último ASO"]
    df_raw_new["E-mail"] = edited_rh["E-mail"]
    st.session_state["rh_dados"] = df_raw_new

    st.divider()
    st.subheader("📩 Disparo de Avisos Automáticos")
    st.write("Clique no botão abaixo para verificar quem está com o ASO vencido (ou a vencer em 30 dias) e enviar um e-mail de cobrança.")

    if st.button("🚀 Verificar e Enviar Avisos ASO", type="primary"):
        with st.spinner("Verificando datas e enviando e-mails..."):
            df_rh_gatilho = st.session_state["rh_dados"].copy()
            houve_envio = False
            erros_envio = []
            sucessos_envio = 0
            ano_atual = datetime.now().year
            hoje = datetime.now()

            for idx, row in df_rh_gatilho.iterrows():
                data_str = str(row.get("Último ASO", "")).strip()
                if data_str == "" or data_str.lower() == "nan": continue
                
                try:
                    data_aso = pd.to_datetime(data_str, format="%d/%m/%Y")
                    data_venc = data_aso + pd.DateOffset(years=1)
                    dias_restantes = (data_venc - hoje).days
                    ano_aviso = int(row.get("Ano Último Aviso", 0))
                    
                    if dias_restantes <= 30 and ano_aviso != ano_atual:
                        primeiro_nome = str(row['Sócio']).split()[0]
                        assunto = f"Aviso Importante: Vencimento de ASO - {primeiro_nome}"
                        corpo = f"""
                        <div style="font-family: Arial, sans-serif; color: #333; font-size: 14px;">
                            <h2 style="color: #e53e3e;">Atenção, {primeiro_nome}</h2>
                            <p>Informamos que o seu Atestado de Saúde Ocupacional (ASO) está a aproximar-se do vencimento ou já se encontra vencido.</p>
                            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #e53e3e; max-width: 450px;">
                                <p style="margin: 5px 0;"><b>Data do Último ASO:</b> {data_aso.strftime('%d/%m/%Y')}</p>
                                <p style="margin: 5px 0;"><b>Data Limite (Vencimento):</b> {data_venc.strftime('%d/%m/%Y')}</p>
                            </div>
                            <p>Por motivos de compliance e exigência legal, solicitamos que providencie a renovação do exame o mais brevemente possível e envie o novo documento para o registo da empresa.</p>
                            <p>Qualquer dúvida, estou à disposição.</p>
                            <p>Um abraço,<br><b>Marcus Almeida</b><br>Gestão Radlumen</p>
                        </div>
                        """
                        email_dest = row.get("E-mail", "")
                        if "@" in str(email_dest):
                            status = enviar_email(email_dest, assunto, corpo)
                            if status is True:
                                df_rh_gatilho.at[idx, "Ano Último Aviso"] = ano_atual
                                houve_envio = True
                                sucessos_envio += 1
                            else:
                                erros_envio.append(f"{primeiro_nome}: {status}")
                except: pass

            if houve_envio:
                st.session_state["rh_dados"] = df_rh_gatilho
                salvar_banco()
                st.success(f"✅ Concluído! {sucessos_envio} avisos enviados com sucesso.")
            elif erros_envio:
                st.error(f"Erros encontrados: {erros_envio}")
            else:
                st.info("Nenhum aviso precisou ser enviado (todos em dia ou já avisados este ano).")
