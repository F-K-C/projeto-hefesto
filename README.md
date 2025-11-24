# 📘 Projeto Hefesto — Blockchain Militar para Logística de Armamentos

O **Projeto Hefesto** é uma Prova de Conceito (PoC) baseada em **blockchain**, criada para demonstrar como forças militares podem utilizar tecnologias descentralizadas para garantir **rastreabilidade, integridade, controle hierárquico e auditabilidade completa** na gestão de armamentos e movimentações logísticas.

Ele integra:
- Smart Contracts (Solidity)
- Interface Web em Streamlit (Python)
- Conexão blockchain via Web3.py
- RBAC militar (Intermediário / Superior / General)
- Aprovação bilateral de operações (Potencial)
- Registro imutável via hashes SHA-256
- Execução em rede privada local (Ganache / PoA simulado)

---

# 🔰 1. Objetivo do Hefesto

O sistema foi idealizado para demonstrar:

- Registro imutável de inventário militar  
- Controle logístico descentralizado  
- Aprovação dupla entre unidades (origem → destino)  - (Potencial)
- Auditoria plena de operações  
- Garantia de integridade com SHA-256  
- Governança via RBAC militar  
- Interface simples e rápida via Streamlit  

---

# 📁 2. Estrutura do Projeto

```
PROJETO HEFESTO
│
├── contracts/
│   ├── HefestoLogistica.sol        ← Smart contract principal (logística + RBAC)
│   └── RegistroHash.sol            ← Contrato auxiliar (não usado no app)
│
├── interface/
│   ├── app_hefesto.py              ← Interface principal Streamlit
│   ├── military_theme.css          ← Tema militar personalizado
│
├── python/
│   └── abis/
│        ├── HefestoInventario.json ← ABI contrato inventário
│        ├── HefestoLogistica.json  ← ABI contrato logística

```

---

# 🧩 3. Explicação dos Componentes (Visão Macro)

## A) Smart Contracts (Solidity)

### 📌 HefestoLogistica.sol — Core do Sistema
Implementa toda a lógica militar, incluindo:

#### 🔹 RBAC hierárquico
Papéis disponíveis:
- Intermediario  
- Superior  
- General  

Modifiers controlam o acesso:
- `onlyIntermediario`  
- `onlySuperior`  
- `onlyGeneral`  

#### 🔹 Registro de itens
Estrutura utilizada:

```solidity
struct Item {
    bytes32 hashItem;
    address registradoPor;
    uint256 timestamp;
    bool exists;
}
```

Utilizado para registrar hashes de documentos/armamentos.

#### 🔹 Operações Logísticas + Aprovação Bilateral
Estrutura central:

```solidity
struct Operacao {
    address origem;
    address destino;
    bytes32 hashItem;
    bool origemAprovou;
    bool destinoAprovou;
    Status status;
    uint256 createdAt;
    uint256 completedAt;
}
```

Principais funções:
- `createOperation()`
- `approveOrigin()`
- `approveDestination()`
- `emergencyAuthorize()` (via autoridade superior)
- `getOperation()`

#### 🔹 Eventos
Todas as ações geram eventos para auditoria.

---

## B) Interface Python / Streamlit (Frontend)

### 📌 app_hefesto.py — UI principal
Responsável por toda a interface e comunicação com a blockchain.

#### 🔹 Utilitários
- `calc_hash()` → SHA-256  
- `normalize_hash()`  
- `format_timestamp()`  
- `load_css()`  

#### 🔹 Conexão Web3.py
- `connect_web3()`  
- `load_inventario_contract()`  
- `load_logistica_contract()`  
- `send_transaction()`  
- `call_contract()`  

#### 🔹 Páginas da UI
Organizada em 4 seções:

1. **Inventário**
   - Upload de arquivos  
   - Registro de hash  
   - Listagem  

2. **Operações**
   - Criação de operação  
   - Envio para o contrato  

3. **Consultas**
   - Consulta por hash  
   - Consulta de item (Potencial)  

4. **Aprovação Militar**
   - Login simples  
   - Lista de operações pendentes  
   - Aprovação / emergência  
   - Cartão de detalhe da operação  

---

## C) Estilo Visual

### 📌 military_theme.css
Define o tema estético militar:

- Paleta verde/oliva  
- Botões temáticos  
- Estilo de tabelas  
- Interface com visual “HUD tático”  

---

## D) ABIs — Application Binary Interface
Essenciais para que o Web3.py saiba como chamar funções dos contratos.

- **HefestoInventario.json**  
- **HefestoLogistica.json**  

Contêm:
- Funções disponíveis  
- Entradas e retornos  
- Eventos  
- Tipos de dados  

---

# 🔧 4. Tecnologias Utilizadas

| Camada | Tecnologia | Função |
|--------|------------|--------|
| Backend | **Solidity** | Lógica militar + blockchain |
| Rede | **Ganache** | Blockchain local (PoA simulado) |
| Middleware | **Web3.py** | Comunicação Python ↔ blockchain |
| Frontend | **Streamlit** | UI militar |
| Integridade | **SHA-256** | Hashing de arquivos |
| Estilo | **CSS** | Visual militar |

---

# ⚙️ 5. Como Executar o Projeto

### 1️⃣ Inicie a blockchain local
```bash
ganache
```

### 2️⃣ Instale as dependências
```bash
pip install streamlit web3
```

### 3️⃣ Execute a interface
```bash
streamlit run interface/app_hefesto.py
```

Acesse:
```
http://localhost:8501
```

---

# 📡 6. Arquitetura Resumida

```
┌─────────────────────┐
│     Streamlit       │  ← Interface militar
└───────────▲─────────┘
            │ Web3.py
┌───────────┴─────────┐
│   Smart Contracts    │  ← RBAC + logística + inventário
└───────────▲─────────┘
            │ RPC HTTP
┌───────────┴─────────┐
│       Ganache        │  ← Blockchain local (PoA simulado)
└──────────────────────┘
```

---

# 🛡️ 7. Funcionalidades do Hefesto

### Inventário Militar
- Registro de itens via SHA-256  
- Auditoria permanente  
- Consulta por hash  

### Operações Logísticas
- Criação de operação  
- Associação origem/destino  
- Aprovação bilateral (Potencial)  
- Finalização automática  

### Modo Emergência
- Aprovação unilateral por superiores  

### Consultas
- Histórico de itens  
- Histórico de operações  
- Status de aprovações  

---

# 📜 8. Screenshots
*(Adicione quando desejar.)*

---

# 📄 9. Licença
Projeto acadêmico — licença pendente de definição.

---

# 🎯 10. Conclusão

O Hefesto demonstra como ambientes militares podem adotar blockchain para criar um ecossistema com:

- Rastreabilidade total  
- Auditabilidade completa  
- Controle hierárquico  
- Imutabilidade  
- Descentralização controlada  

A combinação de:
- **Solidity** (backend imutável)  
- **Web3.py** (ponte segura)  
- **Streamlit** (UI militar)  

forma um sistema funcional, transparente e aplicável a cenários reais de logística militar.
