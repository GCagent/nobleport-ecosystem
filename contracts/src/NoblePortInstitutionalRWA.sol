// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/AccessControlEnumerable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "./NoblePortRegistry.sol";

contract NoblePortInstitutionalRWA is ERC20, AccessControlEnumerable, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    bytes32 public constant ISSUER_ROLE = keccak256("ISSUER_ROLE");
    bytes32 public constant COMPLIANCE_ROLE = keccak256("COMPLIANCE_ROLE");
    bytes32 public constant NAV_UPDATER_ROLE = keccak256("NAV_UPDATER_ROLE");

    NoblePortRegistry public immutable registry;
    IERC20 public immutable usdc;

    // NAV oracle
    struct NavUpdate {
        uint256 value;
        uint256 timestamp;
        bytes32 appraisalHash;
        address signer;
    }

    NavUpdate public currentNav;
    uint256 public navStalenessThreshold;
    uint256 public totalSupplyCap;

    // Concentration controls
    uint256 public defaultMaxOwnershipBps;

    // Audit chain
    bytes32 public latestAuditHash;
    uint256 public auditNonce;

    event NavUpdated(uint256 value, bytes32 appraisalHash, address signer);
    event ForcedTransfer(address indexed from, address indexed to, uint256 amount, string reason);
    event AuditEntry(uint256 indexed nonce, bytes32 indexed hash, bytes32 prevHash, string action);

    constructor(
        string memory name,
        string memory symbol,
        address _registry,
        address _usdc,
        uint256 _supplyCap,
        uint256 _navStaleness,
        uint256 _defaultMaxBps
    ) ERC20(name, symbol) {
        require(_registry != address(0) && _usdc != address(0), "Zero address");
        registry = NoblePortRegistry(_registry);
        usdc = IERC20(_usdc);
        totalSupplyCap = _supplyCap;
        navStalenessThreshold = _navStaleness;
        defaultMaxOwnershipBps = _defaultMaxBps;

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(ISSUER_ROLE, msg.sender);
        _grantRole(COMPLIANCE_ROLE, msg.sender);
        _grantRole(NAV_UPDATER_ROLE, msg.sender);
    }

    function _appendAudit(string memory action, bytes memory payload) internal {
        bytes32 prev = latestAuditHash;
        latestAuditHash = keccak256(abi.encodePacked(prev, payload, block.timestamp, auditNonce));
        emit AuditEntry(auditNonce, latestAuditHash, prev, action);
        auditNonce++;
    }

    modifier onlyEligible(address account) {
        require(registry.isEligible(account), "Not eligible");
        _;
    }

    modifier navFresh() {
        require(currentNav.timestamp > 0, "NAV not set");
        require(block.timestamp - currentNav.timestamp <= navStalenessThreshold, "NAV stale");
        _;
    }

    function updateNav(uint256 value, bytes32 appraisalHash) external onlyRole(NAV_UPDATER_ROLE) whenNotPaused {
        require(value > 0, "Zero NAV");
        currentNav = NavUpdate({
            value: value,
            timestamp: block.timestamp,
            appraisalHash: appraisalHash,
            signer: msg.sender
        });
        _appendAudit("NAV_UPDATE", abi.encodePacked(value, appraisalHash, msg.sender));
        emit NavUpdated(value, appraisalHash, msg.sender);
    }

    function issue(address to, uint256 tokenAmount, uint256 usdcAmount)
        external onlyRole(ISSUER_ROLE) whenNotPaused nonReentrant onlyEligible(to) navFresh
    {
        require(totalSupply() + tokenAmount <= totalSupplyCap, "Supply cap exceeded");
        _checkConcentration(to, tokenAmount);

        usdc.safeTransferFrom(msg.sender, address(this), usdcAmount);
        _mint(to, tokenAmount);
        _appendAudit("ISSUE", abi.encodePacked(to, tokenAmount, usdcAmount));
    }

    function redeem(address from, uint256 tokenAmount, uint256 usdcAmount)
        external onlyRole(ISSUER_ROLE) whenNotPaused nonReentrant navFresh
    {
        require(balanceOf(from) >= tokenAmount, "Insufficient balance");
        _burn(from, tokenAmount);
        usdc.safeTransfer(from, usdcAmount);
        _appendAudit("REDEEM", abi.encodePacked(from, tokenAmount, usdcAmount));
    }

    function forcedTransfer(address from, address to, uint256 amount, string calldata reason)
        external onlyRole(COMPLIANCE_ROLE)
    {
        _transfer(from, to, amount);
        _appendAudit("FORCED_TRANSFER", abi.encodePacked(from, to, amount));
        emit ForcedTransfer(from, to, amount, reason);
    }

    function _update(address from, address to, uint256 value) internal override {
        if (from != address(0) && to != address(0)) {
            require(!paused(), "Transfers paused");
            if (to != address(this)) {
                require(registry.isEligible(to), "Recipient not eligible");
                _checkConcentration(to, value);
            }
        }
        super._update(from, to, value);
    }

    function _checkConcentration(address account, uint256 additionalAmount) internal view {
        if (totalSupply() == 0) return;
        (, , , uint256 maxBps, ) = registry.investors(account);
        uint256 cap = maxBps > 0 ? maxBps : defaultMaxOwnershipBps;
        uint256 futureBalance = balanceOf(account) + additionalAmount;
        uint256 futureBps = (futureBalance * 10000) / (totalSupply() + additionalAmount);
        require(futureBps <= cap, "Concentration limit exceeded");
    }

    function setNavStalenessThreshold(uint256 _threshold) external onlyRole(DEFAULT_ADMIN_ROLE) {
        navStalenessThreshold = _threshold;
    }

    function setDefaultMaxOwnershipBps(uint256 _bps) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_bps > 0 && _bps <= 10000, "Invalid bps");
        defaultMaxOwnershipBps = _bps;
    }

    function withdrawUsdc(address to, uint256 amount) external onlyRole(DEFAULT_ADMIN_ROLE) nonReentrant {
        usdc.safeTransfer(to, amount);
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
