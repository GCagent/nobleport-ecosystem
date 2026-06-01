// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../interfaces/IIdentityRegistry.sol";
import "../interfaces/IZkSBTVerifier.sol";

/**
 * Maps wallet addresses to verified on-chain identities. Integrates
 * with the zkSBT verifier so accreditation can be proven without
 * exposing PII on-chain.
 *
 * Architecture layer: Layer 3 — zkSBT ERC-5114/5484 + DID/VC
 */
contract IdentityRegistry is IIdentityRegistry {
    address public owner;
    IZkSBTVerifier public zkVerifier;

    mapping(address => bool) public agents;
    mapping(address => address) private _identities;
    mapping(address => uint16) private _countries;
    mapping(address => bool) private _verified;

    // Trusted claim issuers — mapped by claim topic
    mapping(uint256 => address[]) public trustedIssuers;
    uint256[] public claimTopics;

    modifier onlyOwner() {
        require(msg.sender == owner, "only owner");
        _;
    }

    modifier onlyAgent() {
        require(agents[msg.sender] || msg.sender == owner, "only agent");
        _;
    }

    constructor(address zkVerifier_) {
        owner = msg.sender;
        agents[msg.sender] = true;
        zkVerifier = IZkSBTVerifier(zkVerifier_);
    }

    // ── Identity management ───────────────────────────────────────

    function registerIdentity(
        address wallet,
        address id_,
        uint16 country
    ) external override onlyAgent {
        require(wallet != address(0), "zero wallet");
        require(_identities[wallet] == address(0), "already registered");

        _identities[wallet] = id_;
        _countries[wallet] = country;
        _verified[wallet] = true;

        emit IdentityRegistered(wallet, id_);
        emit CountryUpdated(wallet, country);
    }

    function deleteIdentity(address wallet) external override onlyAgent {
        require(_identities[wallet] != address(0), "not registered");

        address id_ = _identities[wallet];
        delete _identities[wallet];
        delete _countries[wallet];
        _verified[wallet] = false;

        emit IdentityRemoved(wallet, id_);
    }

    function updateCountry(address wallet, uint16 country) external override onlyAgent {
        require(_identities[wallet] != address(0), "not registered");
        _countries[wallet] = country;
        emit CountryUpdated(wallet, country);
    }

    // ── Verification queries ──────────────────────────────────────

    function isVerified(address wallet) external view override returns (bool) {
        if (!_verified[wallet]) return false;
        if (address(zkVerifier) != address(0)) {
            return zkVerifier.isAccredited(wallet);
        }
        return true;
    }

    function identity(address wallet) external view override returns (address) {
        return _identities[wallet];
    }

    function investorCountry(address wallet) external view override returns (uint16) {
        return _countries[wallet];
    }

    // ── Trusted issuers ───────────────────────────────────────────

    function addClaimTopic(uint256 topic) external onlyOwner {
        claimTopics.push(topic);
    }

    function addTrustedIssuer(uint256 topic, address issuer) external onlyOwner {
        trustedIssuers[topic].push(issuer);
    }

    function removeTrustedIssuer(uint256 topic, uint256 index) external onlyOwner {
        address[] storage issuers = trustedIssuers[topic];
        require(index < issuers.length, "out of bounds");
        issuers[index] = issuers[issuers.length - 1];
        issuers.pop();
    }

    function getClaimTopics() external view returns (uint256[] memory) {
        return claimTopics;
    }

    function getTrustedIssuers(uint256 topic) external view returns (address[] memory) {
        return trustedIssuers[topic];
    }

    // ── Admin ─────────────────────────────────────────────────────

    function addAgent(address agent) external onlyOwner {
        agents[agent] = true;
    }

    function removeAgent(address agent) external onlyOwner {
        agents[agent] = false;
    }

    function setZkVerifier(address verifier) external onlyOwner {
        zkVerifier = IZkSBTVerifier(verifier);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero address");
        owner = newOwner;
    }
}
