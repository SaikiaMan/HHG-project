// SPDX-License-Identifier: MIT
pragma solidity ^0.8.34;

contract PostVerification {

    mapping(bytes32 => uint256) public records;

    function storeHash(bytes32 hash) public {
        records[hash] = block.timestamp;
    }

    function verifyHash(bytes32 hash) public view returns (bool) {
        return records[hash] != 0;
    }
}