# Facilitator guide

## Before the day

1. Run `python tests/test_wonders.py`. It should end with "All tests passed."
2. Decide how participants will run notebooks (see README: local, Colab, or JupyterLite) and try it on one participant-type laptop.
3. Print `incident_cards.md` and cut it into eight cards.
4. Open the slides and, if you want the optional demo, `extras/GrantGovernance.sol` in Remix (remix.ethereum.org).

## Running order (3 hours)

| Clock | Part | Material |
|---|---|---|
| 0:00 to 1:00 | Interactive introduction | Slides |
| 1:00 to 1:30 | Activity 1: Build a Blockchain | `01_build_a_blockchain.ipynb` |
| 1:30 to 2:00 | Activity 2: Deterministic AI Agents | `02_deterministic_ai_agents.ipynb` |
| 2:00 to 2:30 | Activity 3: Smart Governance Rules | `03_smart_governance_rules.ipynb` |
| 2:30 to 3:00 | Activity 4: Governance Crisis Challenge | `04_governance_crisis_challenge.ipynb` + cards |

Each notebook ends with three discussion questions. Three minutes of pair discussion is enough; take one or two answers from the room.

## What each activity should leave behind

**Activity 1.** A hash is a fingerprint. Each block carries the previous block's fingerprint, so changing one record breaks every later block. Signatures say who wrote a record. Proof of work makes rewriting expensive. Many copies mean no single party owns the truth.

Common stumble: in step 3 participants expect the "clever cheat" to work. Let them be surprised, then ask what the cheat would have to do next.

**Activity 2.** Determinism makes a decision checkable by re-running it. The explanation says why the model decided; the ledger says what, who, which model, when, and whether it changed. Explanation is not the same as fairness: raise this in the discussion.

Demo moment: section 3, the "moody agent". Run it twice on the projector.

**Activity 3.** A ledger records; a contract decides what is allowed. Quorum and threshold are different things. Some decisions should go to a person. The rules themselves are recorded on the ledger at deployment.

**Activity 4.** Teams of three to five. Give each team one card to investigate, but every team must pass the full scorecard. Push the "too safe" lesson (section 4): rules that block honest applicants are also a failure.

## Answer key for Activity 4

| Incident | Rule that stops it | Stopped by |
|---|---|---|
| 1. The uninvited agent | `require_registration = True` | governance (identity) |
| 2. The silent model swap | `check_model_hash = True` | provenance on the ledger |
| 3. The edited decision | `replay_check = True` | deterministic AI |
| 4. The disagreement | `on_conflict = "escalate"` | human |
| 5. The typo | `validate_inputs = True` | governance (input rules) |
| 6. The big cheque | `human_review_above` below 400 | human |
| 7. The eager validator | `one_vote_each = True` **and** `quorum` above 0.2 | governance (voting) |
| 8. The rewritten past | `audit_before_finalize = True` | blockchain |
| 9. Honest application | needs `quorum` at most 0.8, `approval_threshold` at most 0.75, `min_agents` at most 3, `human_review_above` at least 25 (or None) | |

A rules dictionary that scores 9 out of 9:

```python
{
    "require_registration": True, "check_model_hash": True, "replay_check": True,
    "validate_inputs": True, "min_agents": 2, "on_conflict": "escalate",
    "quorum": 0.6, "approval_threshold": 0.6, "one_vote_each": True,
    "human_review_above": 200, "audit_before_finalize": True,
}
```

Notes for the debrief:

- Incident 3 can also be stopped by nothing else: the hash is correct and the agent is registered. Only replay catches it. This is the strongest argument in the workshop for deterministic AI.
- Incident 8: the weak system had a tamper-evident ledger the whole time. Nobody looked. Tamper evidence needs an auditor.
- What the system still cannot stop: a majority of validators colluding; a biased training set (every agent would be reproducibly unfair); the administrator abusing the human sign-off. Good closing discussion.

## Optional Remix demonstration (5 minutes)

Paste `extras/GrantGovernance.sol` into Remix, compile with Solidity 0.8.20 or newer, deploy to the built-in Remix VM, and show: `registerAgent`, `submitDecision` from an unregistered account (reverts with "unregistered agent"), `vote` twice from the same validator (reverts with "already voted"). The point is that the Python rules map one to one onto a real smart contract. The contract compiles cleanly; the click-through in Remix has not been rehearsed by the author of this package.

## If something breaks

| Symptom | Fix |
|---|---|
| "Cannot find the 'wonders' folder" | The notebook must sit next to the `wonders` folder |
| scikit-learn missing | Carry on: agents use the built-in rule tree. Model hashes will be the same for all agents, so skip Activity 2 section 4 and run Activity 4 from the projector |
| A participant's notebook is in a muddle | Kernel, Restart and run all; or switch to `solutions/` |
| Mining is slow on an old laptop | Use `Blockchain(difficulty=2)` |
