// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title FundShare - permissioned shares of the Meridian Treasury Fund (MTF)
contract FundShare is ERC20 {
    address public issuer;
    bool public frozen;
    mapping(address => bool) public whitelisted;

    event Subscribed(address indexed investor, uint256 shares);
    event Redeemed(address indexed investor, uint256 shares);
    event WhitelistUpdated(address indexed account, bool status);
    event FreezeToggled(bool frozen);

    error NotIssuer();
    error NotWhitelisted(address account);
    error TransfersFrozen();

    modifier onlyIssuer() {
        if (msg.sender != issuer) revert NotIssuer();
        _;
    }

    constructor() ERC20("Meridian Treasury Fund", "MTF") {
        issuer = msg.sender;
    }

    function addToWhitelist(address account) external onlyIssuer {
        whitelisted[account] = true;
        emit WhitelistUpdated(account, true);
    }

    function removeFromWhitelist(address account) external onlyIssuer {
        whitelisted[account] = false;
        emit WhitelistUpdated(account, false);
    }

    function subscribe(address investor, uint256 shares) external onlyIssuer {
        if (!whitelisted[investor]) revert NotWhitelisted(investor);
        _mint(investor, shares);
        emit Subscribed(investor, shares);
    }

    function redeem(address investor, uint256 shares) external onlyIssuer {
        _burn(investor, shares);
        emit Redeemed(investor, shares);
    }

    function freeze() external onlyIssuer {
        frozen = true;
        emit FreezeToggled(true);
    }

    function unfreeze() external onlyIssuer {
        frozen = false;
        emit FreezeToggled(false);
    }

    // Every balance change (transfer, mint, burn) funnels through _update in
    // v5, so enforcing the freeze/whitelist gates here covers all of them
    // without duplicating checks across transfer/mint/burn call sites.
    function _update(address from, address to, uint256 value) internal override {
        if (frozen) revert TransfersFrozen();
        // from/to are address(0) for mint/burn respectively; skip the
        // whitelist check there so the issuer can subscribe/redeem shares
        // without whitelisting the zero address.
        if (from != address(0) && !whitelisted[from]) revert NotWhitelisted(from);
        if (to != address(0) && !whitelisted[to]) revert NotWhitelisted(to);
        super._update(from, to, value);
    }
}
