# app_hefesto.py (versão revisada — Aprovar usa emergencyAuthorize direto)
import streamlit as st
from web3 import Web3
import hashlib
import json
import os
from datetime import datetime

# ---------------------------
# CONFIGURAÇÕES
# ---------------------------

GANACHE_URL = "http://127.0.0.1:7545"

# Contrato Inventário (já existente)
CONTRACT_INVENTARIO_ADDRESS = "0x874fec5B9ec68D60DD4F749687b98bfA9a1a0f72"
ABI_INVENTARIO_PATH = "../python/abis/HefestoInventario.json"

# Contrato Logística (novo)
CONTRACT_LOGISTICA_ADDRESS = "0x0aB8478A571D6a81B4f5295EFa196Ac16b05541a"
ABI_LOGISTICA_PATH = "../python/abis/HefestoLogistica.json"

# Conta usada para assinar transações (ganache account) - para PoC local
PRIVATE_KEY = "0x847f133ca3db2c19254b4f9f244d7415fd30a1952f4cb4bd0b4bcefdfc16cdc2"
ACCOUNT_ADDRESS = "0x6Abc0B7A1360b6A4fC6c87D0e3a45F4DD9c6E17f"

# Senha simples para área de aprovação (PoC)
APPROVAL_PASSWORD = "1234"

# ---------------------------
# UTILITÁRIOS E HELPERS
# ---------------------------

def load_css(filename: str = "military_theme.css"):
    """Carrega CSS com encoding utf-8 (evita UnicodeDecodeError)."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass
    except Exception as e:
        st.warning(f"Erro ao carregar CSS: {e}")

def calc_hash(file_bytes: bytes) -> str:
    """Retorna hash SHA-256 em formato 0x... (64 hex)."""
    h = hashlib.sha256(file_bytes).hexdigest()
    return "0x" + h

def normalize_hash(h: str) -> str:
    """Aceita hash com ou sem 0x e devolve no formato 0x + 64 hex."""
    if not isinstance(h, str):
        raise ValueError("Hash deve ser texto (string).")
    h_clean = h.strip().lower().replace(" ", "")
    if h_clean.startswith("0x"):
        h_clean = h_clean[2:]
    if len(h_clean) != 64:
        raise ValueError("Hash deve ter 64 hex (SHA-256) — com ou sem 0x.")
    try:
        int(h_clean, 16)
    except Exception:
        raise ValueError("Hash contém caracteres não-hexadecimais.")
    return "0x" + h_clean

def format_timestamp(ts: int) -> str:
    if not ts:
        return "-"
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return str(ts)

# ---------------------------
# WEB3 / CONTRATOS
# ---------------------------

@st.cache_resource
def connect_web3():
    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    return w3

def load_inventario_contract(w3):
    if not os.path.exists(ABI_INVENTARIO_PATH):
        raise FileNotFoundError(f"ABI inventario não encontrada: {ABI_INVENTARIO_PATH}")
    with open(ABI_INVENTARIO_PATH, "r", encoding="utf-8") as f:
        abi = json.load(f)
    return w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_INVENTARIO_ADDRESS), abi=abi)

def load_logistica_contract(w3):
    if not os.path.exists(ABI_LOGISTICA_PATH):
        raise FileNotFoundError(f"ABI logistica não encontrada: {ABI_LOGISTICA_PATH}")
    with open(ABI_LOGISTICA_PATH, "r", encoding="utf-8") as f:
        abi = json.load(f)
    return w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_LOGISTICA_ADDRESS), abi=abi)

def _select_contract(w3, contract_type: str):
    if contract_type == "inventario":
        return load_inventario_contract(w3)
    elif contract_type == "logistica":
        return load_logistica_contract(w3)
    else:
        raise ValueError("Tipo de contrato inválido")

def send_transaction(contract_type: str, function_name: str, *args):
    """
    Constrói, assina e envia transação para o contrato selecionado.
    Retorna o receipt.
    """
    w3 = connect_web3()
    contract = _select_contract(w3, contract_type)

    # ajusta argumentos automáticos (converter hash hex -> bytes32 quando necessário)
    processed_args = []
    for a in args:
        if isinstance(a, str) and a.startswith("0x") and len(a) == 66:
            processed_args.append(bytes.fromhex(a[2:]))
        else:
            processed_args.append(a)

    # procura função no contrato
    try:
        fn = getattr(contract.functions, function_name)(*processed_args)
    except Exception as e:
        raise Exception(f"Função '{function_name}' não encontrada no contrato ABI. ({e})")

    nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)
    tx = fn.build_transaction({
        "from": ACCOUNT_ADDRESS,
        "nonce": nonce,
        "gas": 3000000,
        "gasPrice": w3.to_wei("1", "gwei"),
    })

    signed = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)

    # ATTENÇÃO: Web3.py SignedTransaction possui atributo raw_transaction
    try:
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    except AttributeError:
        try:
            tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        except Exception as e:
            raise Exception(f"Erro ao enviar transação (atributo raw): {e}")
    except Exception as e:
        raise Exception(f"Erro ao enviar transação: {e}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt

def call_contract(contract_type: str, function_name: str, *args):
    """Chamada de leitura (view)."""
    w3 = connect_web3()
    contract = _select_contract(w3, contract_type)
    try:
        fn = getattr(contract.functions, function_name)
    except Exception as e:
        raise Exception(f"Função '{function_name}' não encontrada no contrato ABI. ({e})")
    try:
        return fn(*args).call()
    except Exception as e:
        raise Exception(e)

# ---------------------------
# Helpers específicos para operações
# ---------------------------

def load_operations_pending():
    """
    Carrega operações pendentes do contrato de logística.
    Retorna lista de dicionários com campos prontos para exibição.
    """
    ops = []
    try:
        total_ops = call_contract("logistica", "operacaoCount")
    except Exception as e:
        raise Exception(f"Falha ao consultar operacaoCount: {e}")

    try:
        total_ops_int = int(total_ops)
    except Exception:
        total_ops_int = 0

    for op_id in range(1, total_ops_int + 1):
        try:
            op = call_contract("logistica", "getOperation", op_id)
            origem = op[0]
            destino = op[1]
            hash_item = op[2].hex() if hasattr(op[2], "hex") else str(op[2])
            origemAprovou = op[3]
            destinoAprovou = op[4]
            status_idx = int(op[5])
            createdAt = op[6]

            status_map = {
                0: "None",
                1: "Pendente",
                2: "Aprovado",
                3: "Emergencial"
            }
            status_text = status_map.get(status_idx, f"Desconhecido({status_idx})")

            if status_text == "Pendente":
                ops.append({
                    "ID": op_id,
                    "Origem": origem,
                    "Destino": destino,
                    "Hash": hash_item,
                    "OrigemAprovou": origemAprovou,
                    "DestinoAprovou": destinoAprovou,
                    "StatusIdx": status_idx,
                    "Status": status_text,
                    "CriadoEm": createdAt,
                    "CriadoEmFmt": format_timestamp(createdAt),
                })
        except Exception as e:
            ops.append({"ID": op_id, "Erro": str(e)})
    return ops

def refresh_ops_state():
    """Carrega operações e salva em st.session_state['ops_rows']"""
    try:
        ops = load_operations_pending()
        st.session_state['ops_rows'] = ops
        st.session_state['ops_error'] = None
    except Exception as e:
        st.session_state['ops_error'] = str(e)
        st.session_state['ops_rows'] = []

# ---------------------------
# UI: CARREGA CSS e SIDEBAR
# ---------------------------

load_css()

# inicializa session_state
if 'authorized' not in st.session_state:
    st.session_state['authorized'] = False
if 'ops_rows' not in st.session_state:
    st.session_state['ops_rows'] = []
if 'ops_error' not in st.session_state:
    st.session_state['ops_error'] = None

# Sidebar
st.sidebar.title("🪖 Projeto Hefesto")
st.sidebar.write("Navegue entre as áreas")
page = st.sidebar.radio("Menu", ["📦 Inventário", "🚚 Operações", "🔎 Consultas", "🛡️ Aprovação Militar"], label_visibility="collapsed")

# ---------------------------
# PÁGINA: INVENTÁRIO
# ---------------------------
if page == "📦 Inventário":
    st.title("📦 Inventário Militar")
    st.write("Registro e verificação de armamentos (PoC).")
    st.markdown("---")

    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader("Envie o arquivo do armamento (laudo, foto, ficha, etc.)", type=None)
    with col2:
        st.info("Hash gerado será baseado no conteúdo do arquivo (SHA-256).")

    numero_serie = st.text_input("Número de série / identificação do armamento")
    tipo = st.text_input("Tipo (ex.: Fuzil, Pistola, Munição)")
    modelo = st.text_input("Modelo (ex.: IA2, Glock 17)")
    estado = st.selectbox("Estado do material", ["Novo", "Em uso", "Manutenção", "Baixado"])

    hash_gerado = None
    if uploaded_file:
        try:
            file_bytes = uploaded_file.read()
            hash_gerado = calc_hash(file_bytes)
            st.success(f"Hash do arquivo (SHA-256): `{hash_gerado}`")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

    if st.button("Registrar item no inventário"):
        if not uploaded_file:
            st.error("Envie um arquivo antes de registrar.")
        elif not numero_serie.strip():
            st.error("Preencha o número de série.")
        else:
            try:
                receipt = send_transaction(
                    "inventario",
                    "registrarItem",
                    hash_gerado,
                    numero_serie,
                    tipo,
                    modelo,
                    estado
                )
                st.success("✅ Item registrado na blockchain!")
                st.json({
                    "blockNumber": receipt.blockNumber,
                    "transactionHash": receipt.transactionHash.hex(),
                    "gasUsed": receipt.gasUsed,
                })
            except Exception as e:
                msg = str(e)
                if "Item ja registrado" in msg or "Item ja cadastrado" in msg:
                    st.warning("⚠ Este hash já está cadastrado no inventário.")
                else:
                    st.error("❌ Erro ao registrar item.")
                    st.code(msg)

    st.markdown("---")

    # Listar inventário
    st.subheader("📋 Listar inventário (carregar)")
    if st.button("Carregar inventário"):
        try:
            total = call_contract("inventario", "totalItens")
            if total == 0:
                st.info("Ainda não há itens registrados.")
            else:
                rows = []
                for i in range(total):
                    try:
                        h = call_contract("inventario", "getHashAt", i)
                        item = call_contract("inventario", "getItem", h)
                        hash_item = item[0].hex() if hasattr(item[0], "hex") else str(item[0])
                        numero_serie = item[1]
                        tipo_item = item[2]
                        modelo_item = item[3]
                        estado_item = item[4]
                        timestamp_item = item[5]
                        registrado_por = item[6]

                        if isinstance(tipo_item, str) and tipo_item.strip().lower() == "operacao":
                            continue
                        if isinstance(modelo_item, str) and "origem:" in modelo_item.lower():
                            continue

                        rows.append({
                            "Hash": hash_item,
                            "Número de Série": numero_serie,
                            "Tipo": tipo_item,
                            "Modelo": modelo_item,
                            "Estado": estado_item,
                            "Registrado em": format_timestamp(timestamp_item),
                            "Registrado por": registrado_por,
                        })
                    except Exception as inner_e:
                        rows.append({"Hash": f"erro no índice {i}", "Erro": str(inner_e)})
                st.table(rows)
        except Exception as e:
            st.error("Erro ao carregar inventário.")
            st.code(str(e))

# ---------------------------
# PÁGINA: OPERAÇÕES
# ---------------------------
elif page == "🚚 Operações":
    st.title("🚚 Operações Logísticas")
    st.write("Registrar movimentações (origem → destino)")
    st.markdown("---")

    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file2 = st.file_uploader("Envie o arquivo do lote (ex.: lista, laudo, foto)", key="lote")
    with col2:
        st.info("O hash do lote será gerado a partir do conteúdo do arquivo (SHA-256).")

    origem = st.selectbox("Quartel de Origem", options=[
        "0x6Abc0B7A1360b6A4fC6c87D0e3a45F4DD9c6E17f",
        "0x5ba7828Bff6741cD9F2e3557Bf40d642440FE5C6",
        "0x99c38E10D0F050aF2D728594c4c5EF74d72E4D84"
    ])
    destino = st.selectbox("Quartel de Destino", options=[
        "0x5ba7828Bff6741cD9F2e3557Bf40d642440FE5C6",
        "0x99c38E10D0F050aF2D728594c4c5EF74d72E4D84",
        "0xBeF7c563b1E211EdADe2e465991447a6B9f14e6f"
    ])
    lote_id = st.text_input("Identificador do lote (número de série do lote)")
    modalidade = st.selectbox("Modalidade", ["Transferência", "Recebido", "Enviado"])

    hash_lote = None
    if uploaded_file2:
        try:
            fb = uploaded_file2.read()
            hash_lote = calc_hash(fb)
            st.success(f"Hash do lote: `{hash_lote}`")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

    if st.button("Registrar operação"):
        if not uploaded_file2:
            st.error("Envie o arquivo do lote antes de registrar.")
        elif not lote_id.strip():
            st.error("Preencha o identificador do lote.")
        else:
            # 1) tenta registrar como item — se duplicado, continua (PoC)
            modelo_field = f"Quartal de Origem:{origem} | Quartal de Destino:{destino}"
            try:
                receipt = send_transaction(
                    "inventario",
                    "registrarItem",
                    hash_lote,
                    lote_id,
                    "Operacao",
                    modelo_field,
                    modalidade
                )
                st.success("🚚 Operação registrada (armazenada como item).")
                st.json({
                    "blockNumber": receipt.blockNumber,
                    "transactionHash": receipt.transactionHash.hex()
                })
            except Exception as e:
                msg = str(e)
                if "Item ja registrado" in msg or "Item ja cadastrado" in msg or "Item ja" in msg:
                    st.warning("⚠ Item já registrado no inventário — continuando para criar operação no contrato de logística.")
                else:
                    st.error("Erro ao registrar item no inventário.")
                    st.code(msg)
                    st.stop()

            # 2) criar operação no contrato de logística (para aprovações)
            try:
                op_receipt = send_transaction(
                    "logistica",
                    "createOperation",
                    Web3.to_checksum_address(destino),
                    hash_lote
                )
                st.success("✅ Operação criada no contrato de logística para aprovação.")
                st.json({
                    "op_blockNumber": op_receipt.blockNumber,
                    "op_transactionHash": op_receipt.transactionHash.hex()
                })
            except Exception as e2:
                st.error("Falha ao criar operação no contrato de logística.")
                st.code(str(e2))

# ---------------------------
# PÁGINA: CONSULTAS
# ---------------------------
elif page == "🔎 Consultas":
    st.title("🔎 Consultas rápidas")
    st.write("Verifique hashes ou detalhes de itens.")
    st.markdown("---")

    hash_input = st.text_input("Verificar hash (aceita com ou sem 0x)")
    if st.button("Verificar hash"):
        try:
            normalized = normalize_hash(hash_input)
            exists = call_contract("inventario", "isRegistrado", normalized)
            if not exists:
                st.warning("❗ Hash NÃO encontrado.")
            else:
                data = call_contract("inventario", "getItem", normalized)
                st.success("✔ Item encontrado:")
                st.json({
                    "hash": data[0].hex() if hasattr(data[0], "hex") else str(data[0]),
                    "numeroSerie": data[1],
                    "tipo": data[2],
                    "modelo": data[3],
                    "estado": data[4],
                    "registradoEm": format_timestamp(data[5]),
                    "registradoPor": data[6],
                })
        except ValueError as ve:
            st.error(f"Erro de validação: {ve}")
        except Exception as e:
            st.error("Erro ao consultar o contrato.")
            st.code(str(e))

    st.markdown("---")
    st.write("Consulta por ID do lote / lista de inventário disponível em `Inventário -> Carregar inventário`.")

# ---------------------------
# PÁGINA: APROVAÇÃO MILITAR (OPÇÃO B — CARDS, ADMIN PODE APROVAR)
# ---------------------------
elif page == "🛡️ Aprovação Militar":
    st.title("🛡️ Aprovação Militar")
    st.write("Área restrita: aprovadores (oficiais). Digite a senha para acessar as operações pendentes.")
    st.markdown("---")

    # Login / autorização usando session_state
    if not st.session_state['authorized']:
        pwd = st.text_input("Senha de Oficial (PoC)", type="password", key="pwd_input")
        if st.button("Entrar", key="enter_pwd"):
            if pwd == APPROVAL_PASSWORD:
                st.session_state['authorized'] = True
                st.success("Acesso autorizado. Carregando operações...")
                refresh_ops_state()
                st.rerun()
            else:
                st.error("Senha incorreta.")
    else:
        # Top bar: info + logout + reload
        top1, top2, top3 = st.columns([4,1,1])
        with top1:
            st.info("Aprovador conectado (PoC). Ações gravadas no contrato HefestoLogistica.")
        with top2:
            if st.button("Recarregar", key="reload_ops"):
                refresh_ops_state()
                st.success("Operações recarregadas.")
        with top3:
            if st.button("Sair", key="logout"):
                st.session_state['authorized'] = False
                st.session_state['ops_rows'] = []
                st.session_state['ops_error'] = None
                st.rerun()

        st.markdown("---")

        # Exibe possíveis erros no carregamento
        if st.session_state.get('ops_error'):
            st.error(f"Erro ao carregar operações: {st.session_state['ops_error']}")

        ops_rows = st.session_state.get('ops_rows', [])
        if not ops_rows:
            st.info("Nenhuma operação pendente encontrada. Clique em 'Recarregar'.")
        else:
            st.write(f"Operações pendentes ({len(ops_rows)}):")
            # Renderiza cada operação como um card
            for row in ops_rows:
                if "Erro" in row:
                    st.warning(f"Erro ao carregar operação {row.get('ID')}: {row.get('Erro')}")
                    continue

                op_id = row.get("ID")
                origem = row.get("Origem")
                destino = row.get("Destino")
                hash_str = row.get("Hash")
                criado_fmt = row.get("CriadoEmFmt")
                origem_ap = row.get("OrigemAprovou")
                destino_ap = row.get("DestinoAprovou")

                # Card header (one row with columns)
                c0, c1, c2, c3, c4 = st.columns([0.6, 3, 3, 3, 1.2])
                c0.markdown(f"**{op_id}**")
                c1.markdown(f"**Origem**\n{origem}")
                c2.markdown(f"**Destino**\n{destino}")
                c3.markdown(f"**Hash**\n`{hash_str}`\n\n**Criado:** {criado_fmt}")

                # action buttons in c4
                approve_key = f"approve_{op_id}"
                reject_key = f"reject_{op_id}"
                details_key = f"details_{op_id}"

                # --- SIMPLIFICADO: Aprovar usa emergencyAuthorize direto (PoC admin) ---
                if c4.button("Aprovar", key=approve_key):
                    try:
                        receipt = send_transaction("logistica", "emergencyAuthorize", op_id)
                        st.success(f"Operação {op_id} aprovada (emergencial). Tx: {receipt.transactionHash.hex()}")
                        refresh_ops_state()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao aprovar operação {op_id}: {e}")

                if c4.button("Reprovar", key=reject_key):
                    try:
                        receipt = send_transaction("logistica", "_for_testing_cancelOperation", op_id)
                        st.warning(f"Operação {op_id} cancelada/reprovada. Tx: {receipt.transactionHash.hex()}")
                        refresh_ops_state()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao reprovar/cancelar operação {op_id}: {e}")

                # detalhes abaixo (expander full width) — evita espremimento
                with st.expander(f"Detalhes da operação {op_id}", expanded=False):
                    st.write("Informações completas (JSON):")
                    st.json(row)

                st.markdown("---")

# ---------------------------
# RODAPÉ
# ---------------------------
st.markdown("---")
st.caption("PoC — Hefesto. Rede de testes local (Ganache).")
