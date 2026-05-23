// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../interfaces/ICompliance.sol";
import "../interfaces/IIdentityRegistry.sol";

/**
 * Modular compliance engine for ERC-3643. Enforces:
 *   - Maximum holder count (Reg D 506(b): 35 non-accredited + unlimited accredited)
 *   - Country blocklist (OFAC jurisdictions)
 *   - Per-investor holding caps
 *   - Minimum holding period (Rule 144)
 *
 * Each rule can be toggled independently. The token contract calls
 * canTransfer() before every transfer, mint, and burn.
 *
 * Architecture layer: Layer 3 — Access Control
 */
contract ModularCompliance is ICompliance {
    address public owner;
    address public tokenAddress;
    IIdentityRegistry public identityRegistry;

    // ── Rule parameters ───────────────────────────────────────────

    uint256 public maxHolders;
    uint256 public currentHolders;
    uint256 public maxPerInvestor;
    uint256 public holdingPeriodSeconds;

    mapping(uint16 => bool) public blockedCountries;
    mapping(address => uint256) public firstReceived;
    mapping(address => uint256) public balanceOf;

    // ── Rule toggles ──────────────────────────────────────────────

    bool public enforceMaxHolders;
    bool public enforceCountryBlock;
    bool public enforceHoldingCap;
    bool public enforceHoldingPeriod;

    modifier onlyOwner() {
        require(msg.sender == owner, "only owner");
        _;
    }

    modifier onlyToken() {
        require(msg.sender == tokenAddress, "only token");
        _;
    }

    constructor(address identityRegistry_) {
        owner = msg.sender;
        identityRegistry = IIdentityRegistry(identityRegistry_);

        maxHolders = 2000;
        maxPerInvestor = type(uint256).max;
        holdingPeriodSeconds = 365 days;

        enforceMaxHolders = true;
        enforceCountryBlock = true;
        enforceHoldingCap = false;
        enforceHoldingPeriod = true;
    }

    // ── Core compliance check ─────────────────────────────────────

    function canTransfer(
        address from,
        address to,
        uint256 amount
    ) external view override returns (bool) {
        if (to == address(0)) return true; // burn always allowed

        if (enforceCountryBlock) {
            uint16 country = identityRegistry.investorCountry(to);
            if (blockedCountries[country]) return false;
        }

        if (enforceMaxHolders && balanceOf[to] == 0 && from != address(0)) {
            if (currentHolders >= maxHolders) return false;
        }

        if (enforceHoldingCap) {
            if (balanceOf[to] + amount > maxPerInvestor) return false;
        }

        if (enforceHoldingPeriod && from != address(0)) {
            uint256 first = firstReceived[from];
            if (first > 0 && block.timestamp < first + holdingPeriodSeconds) {
                return false;
            }
        }

        return true;
    }

    // ── State updates (called by token after transfer) ────────────

    function transferred(
        address from,
        address to,
        uint256 amount
    ) external override onlyToken {
        if (from != address(0)) {
            balanceOf[from] -= amount;
            if (balanceOf[from] == 0) {
                currentHolders--;
            }
        }

        if (to != address(0)) {
            if (balanceOf[to] == 0) {
                currentHolders++;
                firstReceived[to] = block.timestamp;
            }
            balanceOf[to] += amount;
        }

        emit ComplianceCheckPassed(from, to, amount);
    }

    function created(address to, uint256 amount) external override onlyToken {
        if (balanceOf[to] == 0) {
            currentHolders++;
            firstReceived[to] = block.timestamp;
        }
        balanceOf[to] += amount;
        emit ComplianceCheckPassed(address(0), to, amount);
    }

    function destroyed(address from, uint256 amount) external override onlyToken {
        balanceOf[from] -= amount;
        if (balanceOf[from] == 0) {
            currentHolders--;
        }
        emit ComplianceCheckPassed(from, address(0), amount);
    }

    // ── Rule configuration ────────────────────────────────────────

    function setMaxHolders(uint256 max) external onlyOwner {
        maxHolders = max;
    }

    function setMaxPerInvestor(uint256 max) external onlyOwner {
        maxPerInvestor = max;
    }

    function setHoldingPeriod(uint256 seconds_) external onlyOwner {
        holdingPeriodSeconds = seconds_;
    }

    function blockCountry(uint16 country) external onlyOwner {
        blockedCountries[country] = true;
    }

    function unblockCountry(uint16 country) external onlyOwner {
        blockedCountries[country] = false;
    }

    function batchBlockCountries(uint16[] calldata countries) external onlyOwner {
        for (uint256 i; i < countries.length; ++i) {
            blockedCountries[countries[i]] = true;
        }
    }

    function setEnforceMaxHolders(bool enforce) external onlyOwner {
        enforceMaxHolders = enforce;
    }

    function setEnforceCountryBlock(bool enforce) external onlyOwner {
        enforceCountryBlock = enforce;
    }

    function setEnforceHoldingCap(bool enforce) external onlyOwner {
        enforceHoldingCap = enforce;
    }

    function setEnforceHoldingPeriod(bool enforce) external onlyOwner {
        enforceHoldingPeriod = enforce;
    }

    // ── Admin ─────────────────────────────────────────────────────

    function setTokenAddress(address token) external onlyOwner {
        tokenAddress = token;
    }

    function setIdentityRegistry(address registry) external onlyOwner {
        identityRegistry = IIdentityRegistry(registry);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero address");
        owner = newOwner;
    }
}
