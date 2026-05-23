// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface ICompliance {
    function canTransfer(address from, address to, uint256 amount) external view returns (bool);
    function transferred(address from, address to, uint256 amount) external;
    function created(address to, uint256 amount) external;
    function destroyed(address from, uint256 amount) external;

    event ComplianceCheckPassed(address indexed from, address indexed to, uint256 amount);
    event ComplianceCheckFailed(address indexed from, address indexed to, uint256 amount);
}
