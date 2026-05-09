// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControlEnumerable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

contract NoblePortRegistry is AccessControlEnumerable, Pausable {
    bytes32 public constant COMPLIANCE_ROLE = keccak256("COMPLIANCE_ROLE");

    struct Investor {
        bool whitelisted;
        uint256 accreditedUntil;
        bytes2 countryCode;
        uint256 maxOwnershipBps;
        bool sanctioned;
    }

    mapping(address => Investor) public investors;
    mapping(bytes2 => bool) public restrictedCountries;
    mapping(address => bool) public approvedStablecoins;

    uint256 public investorCount;
    uint256 public maxInvestors;

    // Audit chain
    bytes32 public latestAuditHash;
    uint256 public auditNonce;

    event InvestorWhitelisted(address indexed investor, uint256 accreditedUntil, bytes2 countryCode);
    event InvestorRemoved(address indexed investor);
    event InvestorSanctioned(address indexed investor, bool sanctioned);
    event CountryRestricted(bytes2 indexed countryCode, bool restricted);
    event StablecoinApproved(address indexed token, bool approved);
    event AuditEntry(uint256 indexed nonce, bytes32 indexed hash, bytes32 prevHash, string action);

    constructor(uint256 _maxInvestors) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(COMPLIANCE_ROLE, msg.sender);
        maxInvestors = _maxInvestors;
    }

    function _appendAudit(string memory action, bytes memory payload) internal {
        bytes32 prev = latestAuditHash;
        latestAuditHash = keccak256(abi.encodePacked(prev, payload, block.timestamp, auditNonce));
        emit AuditEntry(auditNonce, latestAuditHash, prev, action);
        auditNonce++;
    }

    function whitelistInvestor(
        address investor,
        uint256 accreditedUntil,
        bytes2 countryCode,
        uint256 maxBps
    ) external onlyRole(COMPLIANCE_ROLE) whenNotPaused {
        require(investor != address(0), "Zero address");
        require(accreditedUntil > block.timestamp, "Accreditation expired");
        require(!restrictedCountries[countryCode], "Restricted country");
        require(maxBps > 0 && maxBps <= 10000, "Invalid bps");

        if (!investors[investor].whitelisted) {
            require(investorCount < maxInvestors, "Max investors reached");
            investorCount++;
        }

        investors[investor] = Investor({
            whitelisted: true,
            accreditedUntil: accreditedUntil,
            countryCode: countryCode,
            maxOwnershipBps: maxBps,
            sanctioned: false
        });

        _appendAudit("WHITELIST", abi.encodePacked(investor, accreditedUntil, countryCode));
        emit InvestorWhitelisted(investor, accreditedUntil, countryCode);
    }

    function removeInvestor(address investor) external onlyRole(COMPLIANCE_ROLE) {
        require(investors[investor].whitelisted, "Not whitelisted");
        investors[investor].whitelisted = false;
        investorCount--;
        _appendAudit("REMOVE", abi.encodePacked(investor));
        emit InvestorRemoved(investor);
    }

    function setSanctioned(address investor, bool sanctioned) external onlyRole(COMPLIANCE_ROLE) {
        investors[investor].sanctioned = sanctioned;
        _appendAudit("SANCTION", abi.encodePacked(investor, sanctioned));
        emit InvestorSanctioned(investor, sanctioned);
    }

    function setCountryRestriction(bytes2 countryCode, bool restricted) external onlyRole(COMPLIANCE_ROLE) {
        restrictedCountries[countryCode] = restricted;
        emit CountryRestricted(countryCode, restricted);
    }

    function setApprovedStablecoin(address token, bool approved) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(token != address(0), "Zero address");
        approvedStablecoins[token] = approved;
        emit StablecoinApproved(token, approved);
    }

    function isEligible(address investor) public view returns (bool) {
        Investor memory inv = investors[investor];
        return inv.whitelisted
            && !inv.sanctioned
            && inv.accreditedUntil > block.timestamp
            && !restrictedCountries[inv.countryCode];
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
