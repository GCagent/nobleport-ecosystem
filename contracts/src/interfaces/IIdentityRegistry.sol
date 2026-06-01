// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IIdentityRegistry {
    function isVerified(address wallet) external view returns (bool);
    function identity(address wallet) external view returns (address);
    function investorCountry(address wallet) external view returns (uint16);
    function registerIdentity(address wallet, address id_, uint16 country) external;
    function deleteIdentity(address wallet) external;
    function updateCountry(address wallet, uint16 country) external;

    event IdentityRegistered(address indexed wallet, address indexed identity);
    event IdentityRemoved(address indexed wallet, address indexed identity);
    event CountryUpdated(address indexed wallet, uint16 indexed country);
}
