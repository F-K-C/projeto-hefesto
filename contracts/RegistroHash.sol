// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title RegistroHash - Contrato mínimo para registrar e verificar hashes
/// @notice Contrato para : registrar/verificar hashes.
contract RegistroHash {
    mapping(bytes32 => bool) public registrado;

    event HashRegistrado(bytes32 indexed hash, address indexed autor, uint256 timestamp);

    /// @notice Registra um hash (se ainda não registrado)
    /// @param hashArquivo Hash do arquivo/texto (bytes32)
    function registrar(bytes32 hashArquivo) external {
        require(!registrado[hashArquivo], "Hash ja registrado");
        registrado[hashArquivo] = true;
        emit HashRegistrado(hashArquivo, msg.sender, block.timestamp);
    }

    /// @notice Verifica se um hash esta registrado
    /// @param hashArquivo Hash do arquivo/texto (bytes32)
    /// @return bool true se registrado
    function verificar(bytes32 hashArquivo) external view returns (bool) {
        return registrado[hashArquivo];
    }
}
