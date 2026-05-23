// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../interfaces/IIdentityRegistry.sol";
import "../interfaces/ICompliance.sol";

/**
 * ERC-3643 (T-REX) compliant security token for NoblePort real estate
 * tokenization. Every transfer is gated by identity verification and
 * modular compliance rules. Only approved agents can mint/burn/freeze.
 *
 * Implements: ERC-20 + ERC-3643 transfer restrictions
 * Architecture layer: Layer 3 — RE Token ERC-3643
 */
contract NBPTSecurityToken {
    string public name;
    string public symbol;
    uint8 public constant decimals = 18;
    uint256 public totalSupply;

    address public owner;
    IIdentityRegistry public identityRegistry;
    ICompliance public compliance;

    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;
    mapping(address => bool) public frozen;
    mapping(address => bool) public agents;
    bool public paused;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event AddressFrozen(address indexed wallet, bool isFrozen, address indexed agent);
    event TokensPaused(address indexed agent);
    event TokensUnpaused(address indexed agent);
    event AgentAdded(address indexed agent);
    event AgentRemoved(address indexed agent);
    event IdentityRegistrySet(address indexed registry);
    event ComplianceSet(address indexed compliance);
    event RecoveryExecuted(address indexed lostWallet, address indexed newWallet, address indexed agent);

    modifier onlyOwner() {
        require(msg.sender == owner, "only owner");
        _;
    }

    modifier onlyAgent() {
        require(agents[msg.sender], "only agent");
        _;
    }

    modifier whenNotPaused() {
        require(!paused, "token paused");
        _;
    }

    constructor(
        string memory name_,
        string memory symbol_,
        address identityRegistry_,
        address compliance_
    ) {
        name = name_;
        symbol = symbol_;
        owner = msg.sender;
        agents[msg.sender] = true;
        identityRegistry = IIdentityRegistry(identityRegistry_);
        compliance = ICompliance(compliance_);
    }

    // ── ERC-20 reads ──────────────────────────────────────────────

    function balanceOf(address account) external view returns (uint256) {
        return _balances[account];
    }

    function allowance(address holder, address spender) external view returns (uint256) {
        return _allowances[holder][spender];
    }

    // ── ERC-20 writes ─────────────────────────────────────────────

    function approve(address spender, uint256 amount) external returns (bool) {
        _allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transfer(address to, uint256 amount) external whenNotPaused returns (bool) {
        _transferChecked(msg.sender, to, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external whenNotPaused returns (bool) {
        uint256 current = _allowances[from][msg.sender];
        require(current >= amount, "allowance exceeded");
        unchecked { _allowances[from][msg.sender] = current - amount; }
        _transferChecked(from, to, amount);
        return true;
    }

    // ── ERC-3643 transfer restriction ─────────────────────────────

    function _transferChecked(address from, address to, uint256 amount) internal {
        require(!frozen[from], "sender frozen");
        require(!frozen[to], "recipient frozen");
        require(identityRegistry.isVerified(to), "recipient not verified");
        require(compliance.canTransfer(from, to, amount), "compliance rejected");

        _balances[from] -= amount;
        _balances[to] += amount;

        compliance.transferred(from, to, amount);
        emit Transfer(from, to, amount);
    }

    // ── Agent operations (mint / burn / freeze) ───────────────────

    function mint(address to, uint256 amount) external onlyAgent whenNotPaused {
        require(identityRegistry.isVerified(to), "recipient not verified");
        require(compliance.canTransfer(address(0), to, amount), "compliance rejected mint");

        totalSupply += amount;
        _balances[to] += amount;

        compliance.created(to, amount);
        emit Transfer(address(0), to, amount);
    }

    function burn(address from, uint256 amount) external onlyAgent {
        require(_balances[from] >= amount, "burn exceeds balance");

        _balances[from] -= amount;
        totalSupply -= amount;

        compliance.destroyed(from, amount);
        emit Transfer(from, address(0), amount);
    }

    function setAddressFrozen(address wallet, bool freeze) external onlyAgent {
        frozen[wallet] = freeze;
        emit AddressFrozen(wallet, freeze, msg.sender);
    }

    function batchSetAddressFrozen(address[] calldata wallets, bool[] calldata freezeFlags) external onlyAgent {
        require(wallets.length == freezeFlags.length, "length mismatch");
        for (uint256 i; i < wallets.length; ++i) {
            frozen[wallets[i]] = freezeFlags[i];
            emit AddressFrozen(wallets[i], freezeFlags[i], msg.sender);
        }
    }

    function pause() external onlyAgent {
        paused = true;
        emit TokensPaused(msg.sender);
    }

    function unpause() external onlyAgent {
        paused = false;
        emit TokensUnpaused(msg.sender);
    }

    // ── Recovery (lost wallet → replacement) ──────────────────────

    function recoveryAddress(
        address lostWallet,
        address newWallet
    ) external onlyAgent {
        require(identityRegistry.isVerified(newWallet), "new wallet not verified");
        require(_balances[lostWallet] > 0, "nothing to recover");

        uint256 bal = _balances[lostWallet];
        _balances[lostWallet] = 0;
        _balances[newWallet] += bal;

        frozen[lostWallet] = true;

        emit Transfer(lostWallet, newWallet, bal);
        emit RecoveryExecuted(lostWallet, newWallet, msg.sender);
    }

    // ── Owner admin ───────────────────────────────────────────────

    function addAgent(address agent) external onlyOwner {
        agents[agent] = true;
        emit AgentAdded(agent);
    }

    function removeAgent(address agent) external onlyOwner {
        agents[agent] = false;
        emit AgentRemoved(agent);
    }

    function setIdentityRegistry(address registry) external onlyOwner {
        identityRegistry = IIdentityRegistry(registry);
        emit IdentityRegistrySet(registry);
    }

    function setCompliance(address compliance_) external onlyOwner {
        compliance = ICompliance(compliance_);
        emit ComplianceSet(compliance_);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero address");
        owner = newOwner;
    }
}
