// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title NoblePort ENS Resolver
 * @notice Custom resolver for nobleport.eth with subdomain support
 * @dev Implements ENS resolver interface with extended TXT record support
 *
 * DEPLOYMENT:
 *   1. Deploy to Ethereum mainnet
 *   2. Set as resolver for nobleport.eth via ENS Manager
 *   3. Call initializeRecords() to set default TXT records
 *   4. Register subdomains via registerSubdomain()
 */

interface IENS {
    function setSubnodeOwner(bytes32 node, bytes32 label, address owner) external;
    function setResolver(bytes32 node, address resolver) external;
    function owner(bytes32 node) external view returns (address);
}

contract NoblePortENSResolver {

    // ── State ───────────────────────────────────────────────
    address public owner;
    address public pendingOwner;
    IENS public immutable ens;

    // ENS namehash for nobleport.eth
    bytes32 public constant NOBLEPORT_NODE = keccak256(abi.encodePacked(
        keccak256(abi.encodePacked(bytes32(0), keccak256("eth"))),
        keccak256("nobleport")
    ));

    // Storage: node => key => value
    mapping(bytes32 => mapping(string => string)) private _texts;
    // Storage: node => address record
    mapping(bytes32 => address) private _addresses;
    // Storage: node => contenthash
    mapping(bytes32 => bytes) private _contenthashes;
    // Subdomain authorization
    mapping(bytes32 => address) private _subdomainOwners;

    // ── Events ──────────────────────────────────────────────
    event TextChanged(bytes32 indexed node, string key, string value);
    event AddressChanged(bytes32 indexed node, address addr);
    event ContenthashChanged(bytes32 indexed node, bytes hash);
    event SubdomainRegistered(bytes32 indexed node, string label, address owner);
    event OwnershipTransferStarted(address indexed currentOwner, address indexed pendingOwner);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    // ── Modifiers ───────────────────────────────────────────
    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    modifier onlyNodeOwner(bytes32 node) {
        require(
            msg.sender == owner || msg.sender == _subdomainOwners[node],
            "Not authorized for node"
        );
        _;
    }

    // ── Constructor ─────────────────────────────────────────
    constructor(address _ens) {
        owner = msg.sender;
        ens = IENS(_ens);
    }

    // ── Ownership (2-step) ──────────────────────────────────
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Zero address");
        pendingOwner = newOwner;
        emit OwnershipTransferStarted(owner, newOwner);
    }

    function acceptOwnership() external {
        require(msg.sender == pendingOwner, "Not pending owner");
        emit OwnershipTransferred(owner, pendingOwner);
        owner = pendingOwner;
        pendingOwner = address(0);
    }

    // ── TXT Records ─────────────────────────────────────────
    function setText(bytes32 node, string calldata key, string calldata value)
        external onlyNodeOwner(node)
    {
        _texts[node][key] = value;
        emit TextChanged(node, key, value);
    }

    function text(bytes32 node, string calldata key)
        external view returns (string memory)
    {
        return _texts[node][key];
    }

    // ── Address Records ─────────────────────────────────────
    function setAddr(bytes32 node, address addr)
        external onlyNodeOwner(node)
    {
        _addresses[node] = addr;
        emit AddressChanged(node, addr);
    }

    function addr(bytes32 node) external view returns (address) {
        return _addresses[node];
    }

    // ── Contenthash ─────────────────────────────────────────
    function setContenthash(bytes32 node, bytes calldata hash)
        external onlyNodeOwner(node)
    {
        _contenthashes[node] = hash;
        emit ContenthashChanged(node, hash);
    }

    function contenthash(bytes32 node) external view returns (bytes memory) {
        return _contenthashes[node];
    }

    // ── Subdomain Management ────────────────────────────────
    function registerSubdomain(string calldata label, address subOwner)
        external onlyOwner
    {
        bytes32 labelHash = keccak256(bytes(label));
        bytes32 subnode = keccak256(abi.encodePacked(NOBLEPORT_NODE, labelHash));

        // Register in ENS registry
        ens.setSubnodeOwner(NOBLEPORT_NODE, labelHash, address(this));
        ens.setResolver(subnode, address(this));

        // Track subdomain owner
        _subdomainOwners[subnode] = subOwner;

        emit SubdomainRegistered(subnode, label, subOwner);
    }

    // ── Batch Initialization ────────────────────────────────
    /**
     * @notice Initialize all default ENS TXT records for nobleport.eth
     * @dev Call once after deployment to set the on-chain identity profile
     */
    function initializeRecords() external onlyOwner {
        bytes32 node = NOBLEPORT_NODE;

        // Identity
        _texts[node]["name"] = "NoblePort Systems";
        _texts[node]["description"] = "AI-governed real estate empire. Stephanie.ai CEO.";
        _texts[node]["url"] = "https://nobleport.com";
        _texts[node]["avatar"] = "https://app.nobleport.com/assets/logo.png";

        // Contact
        _texts[node]["email"] = "info@nobleport.com";
        _texts[node]["com.twitter"] = "NoblePortHQ";
        _texts[node]["com.github"] = "nobleport";
        _texts[node]["com.discord"] = "nobleport";

        // Governance
        _texts[node]["dao"] = "https://snapshot.org/#/nobleport.eth";
        _texts[node]["governance.type"] = "zkSBT-gated-DAO";
        _texts[node]["governance.contract"] = "0x0000000000000000000000000000000000000000";

        // Compliance
        _texts[node]["compliance"] = "ipfs://QmCOMPLIANCE_CID_HERE";
        _texts[node]["jurisdictions"] = "61";
        _texts[node]["license"] = "MIT";

        // Technical
        _texts[node]["api"] = "https://api.nobleport.com";
        _texts[node]["ws"] = "wss://ws.nobleport.com";
        _texts[node]["ipfs.gateway"] = "https://ipfs.nobleport.com";

        // Token
        _texts[node]["token.symbol"] = "NBPT";
        _texts[node]["token.supply"] = "100000000";
        _texts[node]["token.chain"] = "ethereum";
    }

    // ── EIP-165 Interface Support ───────────────────────────
    function supportsInterface(bytes4 interfaceId) external pure returns (bool) {
        return
            interfaceId == 0x01ffc9a7 || // EIP-165
            interfaceId == 0x59d1d43c || // text()
            interfaceId == 0x3b3b57de || // addr()
            interfaceId == 0xbc1c58d1;   // contenthash()
    }
}
