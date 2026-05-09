// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControlEnumerable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./NoblePortRegistry.sol";
import "./NoblePortInstitutionalRWA.sol";

contract NoblePortSubscription is AccessControlEnumerable, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    bytes32 public constant OPERATOR_ROLE = keccak256("OPERATOR_ROLE");

    NoblePortRegistry public immutable registry;
    NoblePortInstitutionalRWA public immutable rwaToken;
    IERC20 public immutable usdc;

    uint256 public minimumSubscription;
    uint256 public maximumSubscription;

    struct Subscription {
        address investor;
        uint256 usdcAmount;
        uint256 tokenAmount;
        uint256 timestamp;
        bool fulfilled;
        bool cancelled;
    }

    Subscription[] public subscriptions;

    // Audit chain
    bytes32 public latestAuditHash;
    uint256 public auditNonce;

    event SubscriptionCreated(uint256 indexed subId, address indexed investor, uint256 usdcAmount);
    event SubscriptionFulfilled(uint256 indexed subId, uint256 tokenAmount);
    event SubscriptionCancelled(uint256 indexed subId);
    event AuditEntry(uint256 indexed nonce, bytes32 indexed hash, bytes32 prevHash, string action);

    constructor(
        address _registry,
        address _rwaToken,
        address _usdc,
        uint256 _min,
        uint256 _max
    ) {
        require(_registry != address(0) && _rwaToken != address(0) && _usdc != address(0), "Zero address");
        registry = NoblePortRegistry(_registry);
        rwaToken = NoblePortInstitutionalRWA(_rwaToken);
        usdc = IERC20(_usdc);
        minimumSubscription = _min;
        maximumSubscription = _max;
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(OPERATOR_ROLE, msg.sender);
    }

    function _appendAudit(string memory action, bytes memory payload) internal {
        bytes32 prev = latestAuditHash;
        latestAuditHash = keccak256(abi.encodePacked(prev, payload, block.timestamp, auditNonce));
        emit AuditEntry(auditNonce, latestAuditHash, prev, action);
        auditNonce++;
    }

    function subscribe(uint256 usdcAmount) external whenNotPaused nonReentrant returns (uint256) {
        require(registry.isEligible(msg.sender), "Not eligible");
        require(usdcAmount >= minimumSubscription, "Below minimum");
        require(usdcAmount <= maximumSubscription, "Above maximum");

        usdc.safeTransferFrom(msg.sender, address(this), usdcAmount);

        uint256 subId = subscriptions.length;
        subscriptions.push(Subscription({
            investor: msg.sender,
            usdcAmount: usdcAmount,
            tokenAmount: 0,
            timestamp: block.timestamp,
            fulfilled: false,
            cancelled: false
        }));

        _appendAudit("SUBSCRIBE", abi.encodePacked(subId, msg.sender, usdcAmount));
        emit SubscriptionCreated(subId, msg.sender, usdcAmount);
        return subId;
    }

    function fulfillSubscription(uint256 subId, uint256 tokenAmount) external onlyRole(OPERATOR_ROLE) whenNotPaused nonReentrant {
        Subscription storage sub = subscriptions[subId];
        require(!sub.fulfilled && !sub.cancelled, "Invalid state");
        require(tokenAmount > 0, "Zero tokens");

        sub.tokenAmount = tokenAmount;
        sub.fulfilled = true;

        usdc.safeTransfer(address(rwaToken), sub.usdcAmount);

        _appendAudit("FULFILL", abi.encodePacked(subId, tokenAmount));
        emit SubscriptionFulfilled(subId, tokenAmount);
    }

    function cancelSubscription(uint256 subId) external whenNotPaused nonReentrant {
        Subscription storage sub = subscriptions[subId];
        require(!sub.fulfilled && !sub.cancelled, "Invalid state");
        require(msg.sender == sub.investor || hasRole(OPERATOR_ROLE, msg.sender), "Not authorized");

        sub.cancelled = true;
        usdc.safeTransfer(sub.investor, sub.usdcAmount);

        _appendAudit("CANCEL_SUB", abi.encodePacked(subId));
        emit SubscriptionCancelled(subId);
    }

    function setLimits(uint256 _min, uint256 _max) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_min <= _max, "Invalid range");
        minimumSubscription = _min;
        maximumSubscription = _max;
    }

    function getSubscriptionCount() external view returns (uint256) { return subscriptions.length; }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
