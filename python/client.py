from web3 import Web3
import json
import os

# -----------------------------
# CONFIGURAÇÕES
# -----------------------------
GANACHE_URL = "http://127.0.0.1:7545"  # RPC do Ganache

# Caminho do ABI do RegistroHash
ABI_PATH = os.path.join("abis", "RegistroHash.json")

# ENDEREÇO DO CONTRATO — PEGADO DO REMIX
CONTRACT_ADDRESS = "0x6b91b79Cf5d3e754674c0DC0961D8C0EFdee0118"

# Conta e chave privada do Ganache (correspondentes)
PRIVATE_KEY = "0x847f133ca3db2c19254b4f9f244d7415fd30a1952f4cb4bd0b4bcefdfc16cdc2"
ACCOUNT_ADDRESS = "0x6Abc0B7A1360b6A4fC6c87D0e3a45F4DD9c6E17f"


# -----------------------------
# CONEXÃO WEB3
# -----------------------------
def connect_ganache():
    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    if w3.is_connected():
        print("✔ Conectado ao Ganache")
    else:
        raise Exception("❌ Não foi possível conectar ao Ganache")
    return w3


# -----------------------------
# CARREGAR ABI + CONTRATO
# -----------------------------
def load_contract(w3):
    with open(ABI_PATH) as f:
        abi = json.load(f)

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(CONTRACT_ADDRESS),
        abi=abi
    )
    return contract


# -----------------------------
# FUNÇÃO: leitura (view)
# -----------------------------
def call_contract_function(function_name, *args):
    w3 = connect_ganache()
    contract = load_contract(w3)

    fn = getattr(contract.functions, function_name)
    result = fn(*args).call()
    return result


# -----------------------------
# FUNÇÃO: transação (escrita)
# -----------------------------
def send_transaction(function_name, *args):
    w3 = connect_ganache()
    contract = load_contract(w3)

    fn = getattr(contract.functions, function_name)(*args)

    nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)

    tx = fn.build_transaction({
        "from": ACCOUNT_ADDRESS,
        "nonce": nonce,
        "gas": 3000000,
        "gasPrice": w3.to_wei("1", "gwei")
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print("✔ Transação executada com sucesso!")
    return receipt


# -----------------------------
# TESTE INICIAL
# -----------------------------
if __name__ == "__main__":
    print("\n=== TESTE DE CONEXÃO ===")
    connect_ganache()
    print("\nPronto para registrar hashes.\n")
