// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControlEnumerable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./NoblePortRegistry.sol";
import "./NoblePortInstitutionalRWA.sol";

contract NoblePortRedemption is AccessControlEnumerable, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    bytes32 public constant OPERATOR_ROLE = keccak256("OPERATOR_ROLE");

    NoblePortRegistry public immutable registry;
    NoblePortInstitutionalRWA public immutable rwaToken;
    IERC20 public immutable usdc;

    uint256 public redemptionDelay;
    uint256 public minimumRedemption;

    enum RedemptionStatus { Pending, Approved, Executed, Cancelled }

    struct RedemptionRequest {
        address investor;
        uint256 tokenAmount;
        uint256 usdcAmount;
        uint256 requestedAt;
        RedemptionStatus status;
    }

    RedemptionRequest[] public redemptions;

    // Audit chain
    bytes32 public latestAuditHash;
    uint256 public auditNonce;

    event RedemptionRequested(uint256 indexed reqId, address indexed investor, uint256 tokenAmount);
    event RedemptionApproved(uint256 indexed reqId, uint256 usdcAmount);
    event RedemptionExecuted(uint256 indexed reqId, address indexed investor, uint256 usdcAmount);
    event RedemptionCancelled(uint256 indexed reqId);
    event AuditEntry(uint256 indexed nonce, bytes32 indexed hash, bytes32 prevHash, string action);

    constructor(
        address _registry,
        address _rwaToken,
        address _usdc,
        uint256 _delay,
        uint256 _minRedemption
    ) {
        require(_registry != address(0) && _rwaToken != address(0) && _usdc != address(0), "Zero address");
        registry = NoblePortRegistry(_registry);
        rwaToken = NoblePortInstitutionalRWA(_rwaToken);
        usdc = IERC20(_usdc);
        redemptionDelay = _delay;
        minimumRedemption = _minRedemption;
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(OPERATOR_ROLE, msg.sender);
    }

    function _appendAudit(string memory action, bytes memory payload) internal {
        bytes32 prev = latestAuditHash;
        latestAuditHash = keccak256(abi.encodePacked(prev, payload, block.timestamp, auditNonce));
        emit AuditEntry(auditNonce, latestAuditHash, prev, action);
        auditNonce++;
    }

    function requestRedemption(uint256 tokenAmount) external whenNotPaused nonReentrant returns (uint256) {
        require(tokenAmount >= minimumRedemption, "Below minimum");
        require(rwaToken.balanceOf(msg.sender) >= tokenAmount, "Insufficient balance");

        uint256 reqId = redemptions.length;
        redemptions.push(RedemptionRequest({
            investor: msg.sender,
            tokenAmount: tokenAmount,
            usdcAmount: 0,
            requestedAt: block.timestamp,
            status: RedemptionStatus.Pending
        }));

        _appendAudit("REDEEM_REQUEST", abi.encodePacked(reqId, msg.sender, tokenAmount));
        emit RedemptionRequested(reqId, msg.sender, tokenAmount);
        return reqId;
    }

    function approveRedemption(uint256 reqId, uint256 usdcAmount) external onlyRole(OPERATOR_ROLE) whenNotPaused {
        RedemptionRequest storage req = redemptions[reqId];
        require(req.status == RedemptionStatus.Pending, "Not pending");
        require(usdcAmount > 0, "Zero USDC");

        req.usdcAmount = usdcAmount;
        req.status = RedemptionStatus.Approved;

        _appendAudit("REDEEM_APPROVED", abi.encodePacked(reqId, usdcAmount));
        emit RedemptionApproved(reqId, usdcAmount);
    }

    function executeRedemption(uint256 reqId) external onlyRole(OPERATOR_ROLE) whenNotPaused nonReentrant {
        RedemptionRequest storage req = redemptions[reqId];
        require(req.status == RedemptionStatus.Approved, "Not approved");
        require(block.timestamp >= req.requestedAt + redemptionDelay, "Delay not met");

        req.status = RedemptionStatus.Executed;
        usdc.safeTransfer(req.investor, req.usdcAmount);

        _appendAudit("REDEEM_EXECUTED", abi.encodePacked(reqId, req.investor, req.usdcAmount));
        emit RedemptionExecuted(reqId, req.investor, req.usdcAmount);
    }

    function cancelRedemption(uint256 reqId) external whenNotPaused {
        RedemptionRequest storage req = redemptions[reqId];
        require(req.status == RedemptionStatus.Pending, "Not pending");
        require(msg.sender == req.investor || hasRole(OPERATOR_ROLE, msg.sender), "Not authorized");

        req.status = RedemptionStatus.Cancelled;
        _appendAudit("REDEEM_CANCELLED", abi.encodePacked(reqId));
        emit RedemptionCancelled(reqId);
    }

    function setRedemptionDelay(uint256 _delay) external onlyRole(DEFAULT_ADMIN_ROLE) {
        redemptionDelay = _delay;
    }

    function setMinimumRedemption(uint256 _min) external onlyRole(DEFAULT_ADMIN_ROLE) {
        minimumRedemption = _min;
    }

    function getRedemptionCount() external view returns (uint256) { return redemptions.length; }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
