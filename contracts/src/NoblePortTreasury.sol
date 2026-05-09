// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControlEnumerable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./NoblePortRegistry.sol";

contract NoblePortTreasury is AccessControlEnumerable, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    bytes32 public constant TREASURER_ROLE = keccak256("TREASURER_ROLE");
    bytes32 public constant APPROVER_ROLE = keccak256("APPROVER_ROLE");

    NoblePortRegistry public immutable registry;

    struct WithdrawalRequest {
        address to;
        address token;
        uint256 amount;
        uint256 createdAt;
        address requestedBy;
        address approvedBy;
        bool executed;
        bool cancelled;
        string reason;
    }

    WithdrawalRequest[] public requests;
    uint256 public withdrawalDelay;
    uint256 public maxSingleWithdrawal;

    // Audit chain
    bytes32 public latestAuditHash;
    uint256 public auditNonce;

    event WithdrawalRequested(uint256 indexed reqId, address indexed to, address token, uint256 amount);
    event WithdrawalApproved(uint256 indexed reqId, address indexed approver);
    event WithdrawalExecuted(uint256 indexed reqId, address indexed to, uint256 amount);
    event WithdrawalCancelled(uint256 indexed reqId);
    event DelayUpdated(uint256 newDelay);
    event AuditEntry(uint256 indexed nonce, bytes32 indexed hash, bytes32 prevHash, string action);

    constructor(address _registry, uint256 _delay, uint256 _maxSingle) {
        require(_registry != address(0), "Zero registry");
        registry = NoblePortRegistry(_registry);
        withdrawalDelay = _delay;
        maxSingleWithdrawal = _maxSingle;
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(TREASURER_ROLE, msg.sender);
        _grantRole(APPROVER_ROLE, msg.sender);
    }

    function _appendAudit(string memory action, bytes memory payload) internal {
        bytes32 prev = latestAuditHash;
        latestAuditHash = keccak256(abi.encodePacked(prev, payload, block.timestamp, auditNonce));
        emit AuditEntry(auditNonce, latestAuditHash, prev, action);
        auditNonce++;
    }

    function requestWithdrawal(
        address to,
        address token,
        uint256 amount,
        string calldata reason
    ) external onlyRole(TREASURER_ROLE) whenNotPaused returns (uint256) {
        require(to != address(0), "Zero address");
        require(registry.approvedStablecoins(token), "Token not approved");
        require(amount > 0 && amount <= maxSingleWithdrawal, "Amount out of range");

        uint256 reqId = requests.length;
        requests.push(WithdrawalRequest({
            to: to,
            token: token,
            amount: amount,
            createdAt: block.timestamp,
            requestedBy: msg.sender,
            approvedBy: address(0),
            executed: false,
            cancelled: false,
            reason: reason
        }));

        _appendAudit("WITHDRAWAL_REQUESTED", abi.encodePacked(reqId, to, token, amount));
        emit WithdrawalRequested(reqId, to, token, amount);
        return reqId;
    }

    function approveWithdrawal(uint256 reqId) external onlyRole(APPROVER_ROLE) whenNotPaused {
        WithdrawalRequest storage req = requests[reqId];
        require(!req.executed && !req.cancelled, "Invalid state");
        require(req.approvedBy == address(0), "Already approved");
        require(msg.sender != req.requestedBy, "Cannot self-approve");

        req.approvedBy = msg.sender;
        _appendAudit("WITHDRAWAL_APPROVED", abi.encodePacked(reqId, msg.sender));
        emit WithdrawalApproved(reqId, msg.sender);
    }

    function executeWithdrawal(uint256 reqId) external onlyRole(TREASURER_ROLE) whenNotPaused nonReentrant {
        WithdrawalRequest storage req = requests[reqId];
        require(!req.executed && !req.cancelled, "Invalid state");
        require(req.approvedBy != address(0), "Not approved");
        require(block.timestamp >= req.createdAt + withdrawalDelay, "Timelock active");

        req.executed = true;
        IERC20(req.token).safeTransfer(req.to, req.amount);

        _appendAudit("WITHDRAWAL_EXECUTED", abi.encodePacked(reqId, req.to, req.amount));
        emit WithdrawalExecuted(reqId, req.to, req.amount);
    }

    function cancelWithdrawal(uint256 reqId) external onlyRole(TREASURER_ROLE) {
        WithdrawalRequest storage req = requests[reqId];
        require(!req.executed && !req.cancelled, "Invalid state");
        req.cancelled = true;
        _appendAudit("WITHDRAWAL_CANCELLED", abi.encodePacked(reqId));
        emit WithdrawalCancelled(reqId);
    }

    function setWithdrawalDelay(uint256 _delay) external onlyRole(DEFAULT_ADMIN_ROLE) {
        withdrawalDelay = _delay;
        emit DelayUpdated(_delay);
    }

    function setMaxSingleWithdrawal(uint256 _max) external onlyRole(DEFAULT_ADMIN_ROLE) {
        maxSingleWithdrawal = _max;
    }

    function getRequestCount() external view returns (uint256) { return requests.length; }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
