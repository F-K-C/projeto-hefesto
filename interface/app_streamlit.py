import streamlit as st
from web3 import Web3
import hashlib
import json
import os

# =============================
# CONFIGURAÇÕES
# =============================

GANACHE_URL = "http://127.0.0.1:7545"

# ⚠️ COLOQUE AQUI O ENDEREÇO DO SEU CONTRATO RegistroHash
CONTRACT_ADDRESS = "0x6b91b79Cf5d3e754674c0DC0961D8C0EFdee0118"
ABI_PATH = "../python/abis/RegistroHash.json"

ABI_PATH = "../python/abis/RegistroHash.json"

PRIVATE_KEY = "0x847f133ca3db2c19254b4f9f244d7415fd30a1952f4cb4bd0b4bcefdfc16cdc2"
ACCOUNT_ADDRESS = "0x6Abc0B7A1360b6A4fC6c87D0e3a45F4DD9c6E17f"


# =============================
# TEMA MILITAR
# =============================

def load_css():
    with open("military_theme.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()


# HUD LATERAL
st.markdown('<div class="hud-left"></div>', unsafe_allow_html=True)
st.markdown('<div class="hud-right"></div>', unsafe_allow_html=True)


# =============================
# CONEXÃO WEB3
# =============================

@st.cache_resource
def connect_web3():
    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    if not w3.is_connected():
        st.error("❌ Não conectado ao Ganache")
    return w3


def load_contract(w3):
    with open(ABI_PATH) as f:
        abi = json.load(f)

    return w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=abi
    )


# =============================
# FUNÇÕES DE CONTRATO
# =============================

def send_transaction(function_name, *args):
    w3 = connect_web3()
    contract = load_contract(w3)

    fn = getattr(contract.functions, function_name)(*args)
    nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)

    tx = fn.build_transaction({
        "from": ACCOUNT_ADDRESS,
        "nonce": nonce,
        "gas": 3000000,
        "gasPrice": w3.to_wei("1", "gwei")
    })

    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt


def call_contract(function_name, *args):
    w3 = connect_web3()
    contract = load_contract(w3)
    fn = getattr(contract.functions, function_name)
    return fn(*args).call()


# =============================
# INTERFACE
# =============================

st.title("🔥 Projeto Hefesto — Registro de Hash na Blockchain")
st.write("Sistema militar para registrar e verificar autenticidade de arquivos via blockchain")
st.markdown("---")

# ================================================
# 1) GERAR HASH E REGISTRAR
# ================================================

st.header("📁 Registrar arquivo no Blockchain")

uploaded_file = st.file_uploader("Envie um arquivo", type=None)

if uploaded_file:
    file_bytes = uploaded_file.read()
    hash_hex = hashlib.sha256(file_bytes).hexdigest()
    hash_bytes32 = "0x" + hash_hex

    st.success(f"Hash gerado:\n`{hash_bytes32}`")

    if st.button("Registrar no Blockchain"):
        try:
            receipt = send_transaction("registrar", hash_bytes32)

            st.success("✔ Hash registrado!")
            st.json({
                "blockNumber": receipt.blockNumber,
                "transactionHash": receipt.transactionHash.hex(),
                "gasUsed": receipt.gasUsed
            })

        except Exception as e:
            if "Hash ja registrado" in str(e):
                st.error("⚠ Hash já registrado anteriormente!")
            else:
                st.error("Erro ao registrar hash:")
                st.code(str(e))


st.markdown("---")

# ================================================
# 2) VERIFICAR HASH
# ================================================

st.header("🔍 Verificar hash existente")

hash_input = st.text_input("Cole o hash (0x...)", "")

if st.button("Verificar"):
    if len(hash_input) != 66:
        st.error("Hash inválido! Deve ter 66 caracteres.")
    else:
        exists = call_contract("verificar", hash_input)
        if exists:
            st.success("✔ Hash encontrado no contrato!")
        else:
            st.warning("❗ Hash NÃO registrado.")


