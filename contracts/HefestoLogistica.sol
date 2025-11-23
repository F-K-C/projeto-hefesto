// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title HefestoLogistica - Contrato para gestão de inventário e logística militar (PoC)
/// @notice Contrato estendido do projeto "Hefesto" com papéis, registro de itens, operações logísticas, aprovação bilateral e modo de emergência.
contract HefestoLogistica {

    // -----------------------------
    // Roles / RBAC
    // -----------------------------
    enum Role { None, Intermediario, Superior, General }

    address public admin; // administrador inicial (deployer)
    mapping(address => Role) public roles;

    event RoleSet(address indexed who, Role role, address by);
    event AdminTransferred(address indexed previousAdmin, address indexed newAdmin);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Somente admin");
        _;
    }

    modifier onlyIntermediario() {
        Role r = roles[msg.sender];
        require(r == Role.Intermediario || r == Role.Superior || r == Role.General, "Apenas Intermediario/Superior/General");
        _;
    }

    modifier onlySuperior() {
        Role r = roles[msg.sender];
        require(r == Role.Superior || r == Role.General, "Apenas Superior/General");
        _;
    }

    modifier onlyGeneral() {
        require(roles[msg.sender] == Role.General, "Apenas General");
        _;
    }

    constructor() {
        admin = msg.sender;
        roles[msg.sender] = Role.General; // bootstrap: deployer é General
        emit RoleSet(msg.sender, Role.General, msg.sender);
    }

    function transferAdmin(address novoAdmin) external onlyAdmin {
        require(novoAdmin != address(0), "Admin invalido");
        address antigo = admin;
        admin = novoAdmin;
        emit AdminTransferred(antigo, novoAdmin);
    }

    function setRole(address who, Role r) external onlyAdmin {
        roles[who] = r;
        emit RoleSet(who, r, msg.sender);
    }

    // -----------------------------
    // Registro de Itens (hashes)
    // -----------------------------
    struct Item {
        bytes32 hashItem;
        address registradoPor;
        uint256 timestamp;
        bool exists;
    }

    mapping(bytes32 => Item) private items;

    event ItemRegistrado(bytes32 indexed hashItem, address indexed registradoPor, uint256 timestamp);

    /// @notice Registra um item (hash) no inventario (unilateral)
    function registerItem(bytes32 hashItem) external onlyIntermediario {
        require(hashItem != bytes32(0), "Hash invalido");
        require(!items[hashItem].exists, "Item ja registrado");

        items[hashItem] = Item({
            hashItem: hashItem,
            registradoPor: msg.sender,
            timestamp: block.timestamp,
            exists: true
        });

        emit ItemRegistrado(hashItem, msg.sender, block.timestamp);
    }

    function isItemRegistered(bytes32 hashItem) external view returns (bool) {
        return items[hashItem].exists;
    }

    function getItem(bytes32 hashItem) external view returns (address registradoPor, uint256 timestamp, bool exists) {
        Item memory it = items[hashItem];
        return (it.registradoPor, it.timestamp, it.exists);
    }

    // -----------------------------
    // Operacoes Logisticas (bilateral)
    // -----------------------------
    enum OpStatus { None, Pendente, Aprovado, Emergencial }

    struct Operacao {
        address origem;
        address destino;
        bytes32 hashItem;
        bool origemAprovou;      // por exemplo, aprovado pelo Superior da origem
        bool destinoAprovou;     // aprovado pelo Superior do destino
        OpStatus status;
        uint256 createdAt;
        uint256 completedAt;
    }

    uint256 public operacaoCount = 0;
    mapping(uint256 => Operacao) public operacoes;

    event OperacaoCriada(uint256 indexed id, address indexed origem, address indexed destino, bytes32 hashItem, uint256 timestamp);
    event OperacaoAprovada(uint256 indexed id, address approver, bool origemAprovou, bool destinoAprovou, uint256 timestamp);
    event OperacaoConcluida(uint256 indexed id, uint256 timestamp);
    event OperacaoEmergencia(uint256 indexed id, address general, uint256 timestamp);

    /// @notice Inicia uma operacao logística (origem registra movimento para destino)
    function createOperation(address destino, bytes32 hashItem) external onlyIntermediario returns (uint256) {
        require(destino != address(0), "Destino invalido");
        require(hashItem != bytes32(0), "Hash invalido");
        // opcional: exigir que item já esteja registrado no inventario (com registerItem), comentar se não quiser
        // require(items[hashItem].exists, "Item nao registrado no inventario");

        operacaoCount++;
        operacoes[operacaoCount] = Operacao({
            origem: msg.sender,
            destino: destino,
            hashItem: hashItem,
            origemAprovou: false,
            destinoAprovou: false,
            status: OpStatus.Pendente,
            createdAt: block.timestamp,
            completedAt: 0
        });

        emit OperacaoCriada(operacaoCount, msg.sender, destino, hashItem, block.timestamp);
        return operacaoCount;
    }

    /// @notice Aprova a operacao (funcoes separadas por clareza)
    /// Superior da origem confirma saida
    function approveOrigin(uint256 id) external onlySuperior {
        Operacao storage op = operacoes[id];
        require(op.createdAt != 0, "Operacao inexistente");
        require(op.status == OpStatus.Pendente, "Operacao nao pendente");
        require(msg.sender == op.origem, "Apenas superior da origem pode aprovar origem");

        op.origemAprovou = true;
        emit OperacaoAprovada(id, msg.sender, op.origemAprovou, op.destinoAprovou, block.timestamp);

        _tryComplete(id);
    }

    /// @notice Superior do destino confirma entrada
    function approveDestination(uint256 id) external onlySuperior {
        Operacao storage op = operacoes[id];
        require(op.createdAt != 0, "Operacao inexistente");
        require(op.status == OpStatus.Pendente, "Operacao nao pendente");
        require(msg.sender == op.destino, "Apenas superior do destino pode aprovar destino");

        op.destinoAprovou = true;
        emit OperacaoAprovada(id, msg.sender, op.origemAprovou, op.destinoAprovou, block.timestamp);

        _tryComplete(id);
    }

    /// @dev verifica se as duas aprovacoes estao presentes e conclui operacao
    function _tryComplete(uint256 id) internal {
        Operacao storage op = operacoes[id];
        if (op.origemAprovou && op.destinoAprovou) {
            op.status = OpStatus.Aprovado;
            op.completedAt = block.timestamp;
            emit OperacaoConcluida(id, block.timestamp);
        }
    }

    /// @notice General autoriza em emergencia (override) e conclui operacao
    function emergencyAuthorize(uint256 id) external onlyGeneral {
        Operacao storage op = operacoes[id];
        require(op.createdAt != 0, "Operacao inexistente");
        require(op.status == OpStatus.Pendente, "Operacao nao pendente");

        op.destinoAprovou = true;
        op.status = OpStatus.Emergencial;
        op.completedAt = block.timestamp;

        emit OperacaoEmergencia(id, msg.sender, block.timestamp);
        emit OperacaoConcluida(id, block.timestamp);
    }

    /// @notice View consolidada para UI: retorna dados de uma operacao
    function getOperation(uint256 id)
        external
        view
        returns (
            address origem,
            address destino,
            bytes32 hashItem,
            bool origemAprovou,
            bool destinoAprovou,
            OpStatus status,
            uint256 createdAt,
            uint256 completedAt
        )
    {
        Operacao memory op = operacoes[id];
        return (
            op.origem,
            op.destino,
            op.hashItem,
            op.origemAprovou,
            op.destinoAprovou,
            op.status,
            op.createdAt,
            op.completedAt
        );
    }

    // -----------------------------
    // Utilitarios / Segurança
    // -----------------------------

    /// @notice Permite ao admin remover um registro de item (apenas para ambiente de teste/depuração)
    /// @dev Em ambiente real NUNCA remover; este método é opcional e pode ser comentado/removido.
    function _for_testing_removeItem(bytes32 hashItem) external onlyAdmin {
        delete items[hashItem];
    }

    /// @notice Permite ao admin cancelar uma operacao (apenas para admin em PoC)
    function _for_testing_cancelOperation(uint256 id) external onlyAdmin {
        delete operacoes[id];
    }
}
