// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// Optional Remix demonstration for the Blockchain Wonders workshop.
/// The same ideas as wonders/governance.py, as a real Solidity smart contract:
/// registered agents record decisions with a model fingerprint,
/// registered validators vote once each, and the contract finalises by quorum.
/// Teaching example only. Not audited. Do not deploy with real funds.
contract GrantGovernance {
    address public admin;
    uint256 public validatorCount;
    uint256 public quorumPercent = 60;      // share of validators who must vote
    uint256 public approvalPercent = 60;    // share of votes that must be YES

    mapping(address => bytes32) public agentModel;   // agent -> registered model hash
    mapping(address => bool) public isValidator;

    struct Case {
        address agent;
        bytes32 modelHash;
        bytes32 inputHash;
        bool approve;        // the agent's recommendation
        uint256 yes;
        uint256 no;
        bool finalised;
        bool confirmed;
    }

    mapping(bytes32 => Case) public cases;
    mapping(bytes32 => mapping(address => bool)) public hasVoted;

    event DecisionRecorded(bytes32 indexed caseId, address indexed agent, bytes32 modelHash, bool approve);
    event Voted(bytes32 indexed caseId, address indexed validator, bool approve);
    event Finalised(bytes32 indexed caseId, bool confirmed);

    modifier onlyAdmin() {
        require(msg.sender == admin, "not admin");
        _;
    }

    constructor() {
        admin = msg.sender;
    }

    function registerAgent(address agent, bytes32 modelHash) external onlyAdmin {
        require(modelHash != bytes32(0), "model hash required");
        agentModel[agent] = modelHash;
    }

    function registerValidator(address validator) external onlyAdmin {
        require(!isValidator[validator], "already registered");
        isValidator[validator] = true;
        validatorCount += 1;
    }

    function submitDecision(bytes32 caseId, bytes32 modelHash, bytes32 inputHash, bool approve) external {
        require(agentModel[msg.sender] != bytes32(0), "unregistered agent");
        require(agentModel[msg.sender] == modelHash, "model mismatch");
        require(cases[caseId].agent == address(0), "case exists");
        cases[caseId] = Case(msg.sender, modelHash, inputHash, approve, 0, 0, false, false);
        emit DecisionRecorded(caseId, msg.sender, modelHash, approve);
    }

    function vote(bytes32 caseId, bool approve) external {
        require(isValidator[msg.sender], "unregistered validator");
        Case storage c = cases[caseId];
        require(c.agent != address(0), "no such case");
        require(!c.finalised, "case closed");
        require(!hasVoted[caseId][msg.sender], "already voted");
        hasVoted[caseId][msg.sender] = true;
        if (approve) {
            c.yes += 1;
        } else {
            c.no += 1;
        }
        emit Voted(caseId, msg.sender, approve);
    }

    function finalise(bytes32 caseId) external {
        Case storage c = cases[caseId];
        require(c.agent != address(0), "no such case");
        require(!c.finalised, "case closed");
        uint256 total = c.yes + c.no;
        require(total * 100 >= validatorCount * quorumPercent, "no quorum");
        c.finalised = true;
        c.confirmed = c.yes * 100 >= total * approvalPercent;
        emit Finalised(caseId, c.confirmed);
    }
}
