// SPDX-License-Identifier: MIT
pragma solidity 0.8.37;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

contract LedgerAnchorRegistry is Ownable {
    struct Anchor {
        bytes32 referenceId;
        uint64 anchoredAt;
        address submitter;
    }

    mapping(bytes32 digest => Anchor anchor) private anchors;
    mapping(bytes32 referenceId => bytes32 digest) public digestByReference;
    mapping(address submitter => bool authorized) public authorizedSubmitters;

    string public constant CONTRACT_VERSION = "1.0.0";

    error UnauthorizedSubmitter();
    error ZeroAddress();
    error EmptyDigest();
    error EmptyReference();
    error AuthorizationUnchanged();
    error ReferenceAlreadyAnchored();

    event SubmitterAuthorizationUpdated(address indexed submitter, bool authorized);
    event RecordAnchored(
        bytes32 indexed digest,
        bytes32 indexed referenceId,
        uint64 timestamp,
        address indexed submitter
    );

    modifier onlyAuthorizedSubmitter() {
        if (!authorizedSubmitters[msg.sender]) revert UnauthorizedSubmitter();
        _;
    }

    constructor() Ownable(msg.sender) {
        authorizedSubmitters[msg.sender] = true;
        emit SubmitterAuthorizationUpdated(msg.sender, true);
    }

    function setAuthorizedSubmitter(address submitter, bool authorized) external onlyOwner {
        if (submitter == address(0)) revert ZeroAddress();
        if (authorizedSubmitters[submitter] == authorized) revert AuthorizationUnchanged();
        authorizedSubmitters[submitter] = authorized;
        emit SubmitterAuthorizationUpdated(submitter, authorized);
    }

    function anchorRecord(bytes32 digest, bytes32 referenceId)
        external
        onlyAuthorizedSubmitter
        returns (uint64 anchoredAt, bool created)
    {
        if (digest == bytes32(0)) revert EmptyDigest();
        if (referenceId == bytes32(0)) revert EmptyReference();

        Anchor storage existing = anchors[digest];
        if (existing.anchoredAt != 0) {
            if (existing.referenceId != referenceId) revert ReferenceAlreadyAnchored();
            return (existing.anchoredAt, false);
        }
        if (digestByReference[referenceId] != bytes32(0)) revert ReferenceAlreadyAnchored();

        anchoredAt = uint64(block.timestamp);
        anchors[digest] = Anchor({referenceId: referenceId, anchoredAt: anchoredAt, submitter: msg.sender});
        digestByReference[referenceId] = digest;
        emit RecordAnchored(digest, referenceId, anchoredAt, msg.sender);
        return (anchoredAt, true);
    }

    function verifyRecord(bytes32 digest, bytes32 referenceId) external view returns (bool) {
        Anchor storage anchor = anchors[digest];
        return digest != bytes32(0) && anchor.anchoredAt != 0 && anchor.referenceId == referenceId;
    }

    function getAnchor(bytes32 digest)
        external
        view
        returns (bool exists, bytes32 referenceId, uint64 timestamp, address submitter)
    {
        Anchor storage anchor = anchors[digest];
        exists = anchor.anchoredAt != 0;
        return (exists, anchor.referenceId, anchor.anchoredAt, anchor.submitter);
    }
}
