// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IZkSBTVerifier {
    function isAccredited(address wallet) external view returns (bool);
    function verifyProof(
        address wallet,
        uint256[2] calldata a,
        uint256[2][2] calldata b,
        uint256[2] calldata c,
        uint256[] calldata publicInputs
    ) external returns (bool);

    event AccreditationVerified(address indexed wallet, uint256 timestamp);
    event AccreditationRevoked(address indexed wallet);
}
