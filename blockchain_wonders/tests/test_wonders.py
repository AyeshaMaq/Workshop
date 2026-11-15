"""Run with:  python tests/test_wonders.py   (or pytest)"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wonders import (Blockchain, Wallet, Network, make_transaction, verify_transaction,
                     DeterministicAgent, sample_application, replay, same_decision,
                     World, WEAK_RULES, GovernanceError, scorecard)

STRONG = {"require_registration": True, "check_model_hash": True, "replay_check": True,
          "validate_inputs": True, "min_agents": 2, "on_conflict": "escalate", "quorum": 0.6,
          "approval_threshold": 0.6, "one_vote_each": True, "human_review_above": 200,
          "audit_before_finalize": True}


def test_chain_detects_tampering():
    c, ali = Blockchain(2), Wallet("ali")
    c.record(ali, "note", {"amount": 1})
    assert c.is_valid()
    c.chain[1].transactions[0]["payload"]["amount"] = 2
    assert not c.is_valid()


def test_signatures():
    tx = make_transaction(Wallet("ali"), "note", {"x": 1})
    assert verify_transaction(tx)
    tx["payload"]["x"] = 2
    assert not verify_transaction(tx)
    forged = make_transaction(Wallet("eve"), "note", {"x": 1})
    forged["sender"] = "ali"
    assert not verify_transaction(forged)


def test_network_repairs():
    c, ali = Blockchain(2), Wallet("ali")
    c.record(ali, "note", {"x": 1})
    net = Network(["a", "b", "c"], c)
    net.nodes["b"].chain[1].transactions[0]["payload"]["x"] = 9
    assert net.consensus()[2] == ["b"]
    assert net.repair() == ["b"] and net.consensus()[2] == []


def test_agent_is_deterministic():
    a = DeterministicAgent(Wallet("a"), seed=11)
    b = DeterministicAgent(Wallet("a"), seed=11)
    c = DeterministicAgent(Wallet("a"), seed=22)
    assert a.model_hash == b.model_hash != c.model_hash
    d = a.decide(sample_application())
    assert same_decision(d, b.decide(sample_application())) and replay(a, d)
    d["decision"] = "REJECT" if d["decision"] == "APPROVE" else "APPROVE"
    assert not replay(a, d)


def test_contract_flow():
    w = World(STRONG)
    w.submit(sample_application("T-1"))
    assert w.contract.finalize("T-1")["status"] == "no_quorum"
    w.votes("T-1", yes=4)
    assert w.contract.finalize("T-1")["status"] == "final"
    try:
        w.contract.vote(Wallet("nobody"), "T-1", True)
        assert False
    except GovernanceError as e:
        assert e.code == "UNREGISTERED_VALIDATOR"


def test_scorecards():
    assert sum(r["passed"] for r in scorecard(WEAK_RULES, verbose=False)) == 1
    assert all(r["passed"] for r in scorecard(STRONG, verbose=False))
    assert not scorecard({**STRONG, "approval_threshold": 1.0}, verbose=False)[-1]["passed"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
    print("All tests passed.")
