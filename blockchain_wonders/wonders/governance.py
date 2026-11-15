"""
wonders.governance - a simplified smart contract, written in Python.

A smart contract is a set of rules that executes the same way for everybody
and writes what it did to the ledger. This one governs how AI agents'
grant recommendations become final decisions.

    agents submit decisions  ->  contract checks the rules
    validators vote          ->  contract counts the votes
    contract finalises       ->  outcome is written to the blockchain

The RULES dictionary is the 'constitution'. Change it and you change how
the whole system behaves. In Activity 4 you will find out which rules matter.
"""

import copy

from .agents import validate_application, same_decision
from .chain import Wallet, sha256_hex

# Deliberately weak. Good governance is your job.
WEAK_RULES = {
    "require_registration": False,   # must agents / validators be registered?
    "check_model_hash": False,       # must the model match the registered one?
    "replay_check": False,           # re-run the registered model and compare?
    "validate_inputs": False,        # reject out-of-range application data?
    "min_agents": 1,                 # how many agents must decide each case?
    "on_conflict": "first_wins",     # "first_wins" or "escalate" (to a human)
    "quorum": 0.2,                   # share of validators that must vote
    "approval_threshold": 0.5,       # share of votes that must be YES
    "one_vote_each": False,          # count only one vote per validator?
    "human_review_above": None,      # amount (thousand PKR) needing human sign-off
    "audit_before_finalize": False,  # audit the ledger before finalising?
}

RULE_HELP = {
    "require_registration": "Only registered agents may submit; only registered validators may vote.",
    "check_model_hash": "The decision's model fingerprint must equal the registered one.",
    "replay_check": "The contract re-runs the registered model; the result must match.",
    "validate_inputs": "Application values must be inside their allowed ranges.",
    "min_agents": "Number of independent agent decisions required per case.",
    "on_conflict": "What to do when agents disagree: 'first_wins' or 'escalate'.",
    "quorum": "Fraction of validators who must vote (0 to 1).",
    "approval_threshold": "Fraction of votes cast that must be YES (0 to 1).",
    "one_vote_each": "Count each validator once, however many times they vote.",
    "human_review_above": "Requests above this amount need a human sign-off (None = never).",
    "audit_before_finalize": "Verify the whole ledger before finalising any case.",
}


class GovernanceError(Exception):
    """Raised when the contract refuses an action."""

    def __init__(self, code, message):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


class GovernanceContract:
    def __init__(self, chain, admin, rules=None):
        self.chain = chain
        self.admin = admin
        self.rules = {**WEAK_RULES, **(rules or {})}
        unknown = set(self.rules) - set(WEAK_RULES)
        if unknown:
            raise ValueError(f"Unknown rule(s): {sorted(unknown)}")
        self.wallet = Wallet("governance-contract", role="contract")
        self.members = {}      # address -> {"name", "role"}
        self.models = {}       # agent name -> {"hash", "reference" (a frozen copy)}
        self.cases = {}        # case id -> case
        self.chain.record(self.wallet, "contract_deployed",
                          {"rules": self.rules, "rules_hash": sha256_hex(self.rules)})

    # -- internal helpers -------------------------------------------------
    def _log(self, wallet, kind, payload):
        return self.chain.record(wallet, kind, payload)

    def _refuse(self, code, message, actor):
        """Write the refusal to the ledger, then raise."""
        self._log(self.wallet, "violation", {"code": code, "message": message, "actor": actor})
        raise GovernanceError(code, message)

    def _role_of(self, wallet):
        return self.members.get(wallet.address, {}).get("role")

    def _validators(self):
        return [m["name"] for m in self.members.values() if m["role"] == "validator"]

    # -- membership -------------------------------------------------------
    def register(self, admin, wallet, role, agent=None):
        """Admin registers a participant. Agents also register their model."""
        if admin.address != self.admin.address:
            self._refuse("NOT_ADMIN", f"{admin.name} is not the administrator", admin.name)
        self.members[wallet.address] = {"name": wallet.name, "role": role}
        payload = {"member": wallet.name, "address": wallet.address, "role": role}
        if agent is not None:
            self.models[wallet.name] = {"hash": agent.model_hash,
                                        "reference": copy.deepcopy(agent)}
            payload["model_hash"] = agent.model_hash
        self._log(admin, "member_registered", payload)

    # -- step 1: agents submit decisions ----------------------------------
    def submit_decision(self, agent_wallet, decision):
        r, who = self.rules, agent_wallet.name
        if decision.get("agent_id") != who:
            self._refuse("IDENTITY_MISMATCH",
                         f"{who} submitted a decision claiming to be {decision.get('agent_id')}", who)
        if r["require_registration"] and self._role_of(agent_wallet) != "agent":
            self._refuse("UNREGISTERED_AGENT", f"{who} is not a registered agent", who)
        if r["validate_inputs"]:
            problems = validate_application(decision["input"])
            if problems:
                self._refuse("INVALID_INPUT", "; ".join(problems), who)
        registered = self.models.get(who)
        if r["check_model_hash"]:
            if registered is None or decision["model_hash"] != registered["hash"]:
                self._refuse("MODEL_MISMATCH",
                             f"{who} used a model that is not the registered version", who)
        if r["replay_check"]:
            if registered is None:
                self._refuse("NO_REFERENCE_MODEL", f"no registered model to replay for {who}", who)
            again = registered["reference"].decide(
                {"application_id": decision["application_id"], **decision["input"]})
            if not same_decision(again, decision):
                self._refuse("NOT_REPRODUCIBLE",
                             f"{who}'s decision cannot be reproduced from the registered model", who)

        case_id = decision["application_id"]
        case = self.cases.setdefault(case_id, {
            "case_id": case_id, "decisions": [], "votes": [], "human": None,
            "status": "open", "outcome": None})
        if case["status"] == "final":
            self._refuse("CASE_CLOSED", f"case {case_id} is already final", who)
        case["decisions"].append(decision)
        self._log(agent_wallet, "decision", decision)
        return case_id

    # -- step 2: validators vote ------------------------------------------
    def vote(self, validator_wallet, case_id, approve, reason=""):
        who = validator_wallet.name
        if case_id not in self.cases:
            self._refuse("NO_SUCH_CASE", f"case {case_id} does not exist", who)
        if self.rules["require_registration"] and self._role_of(validator_wallet) != "validator":
            self._refuse("UNREGISTERED_VALIDATOR", f"{who} is not a registered validator", who)
        vote = {"case_id": case_id, "validator": who, "approve": bool(approve), "reason": reason}
        self.cases[case_id]["votes"].append(vote)
        self._log(validator_wallet, "vote", vote)

    # -- optional: a human signs off --------------------------------------
    def human_signoff(self, admin, case_id, outcome, note=""):
        if admin.address != self.admin.address:
            self._refuse("NOT_ADMIN", f"{admin.name} cannot sign off cases", admin.name)
        if outcome not in ("APPROVE", "REJECT"):
            raise ValueError("outcome must be 'APPROVE' or 'REJECT'")
        record = {"case_id": case_id, "outcome": outcome, "note": note, "by": admin.name}
        self.cases[case_id]["human"] = record
        self._log(admin, "human_signoff", record)

    # -- step 3: the contract finalises -----------------------------------
    def finalize(self, case_id):
        """Apply the rules and return the case with its status.

        Possible statuses
            final               outcome confirmed and written to the ledger
            waiting_for_agents  not enough agent decisions yet
            escalated           agents disagree: needs a human
            needs_human         amount is above the human-review limit
            no_quorum           too few validators voted
            not_confirmed       validators did not approve the outcome
            halted              the ledger failed its audit
        """
        r, case = self.rules, self.cases[case_id]

        def result(status, outcome=None, why=""):
            case.update(status=status, outcome=outcome, why=why)
            if status == "final":
                self._log(self.wallet, "outcome", {
                    "case_id": case_id, "outcome": outcome, "why": why,
                    "agents": [d["agent_id"] for d in case["decisions"]],
                    "rules_hash": sha256_hex(r)})
            return dict(case)

        if r["audit_before_finalize"]:
            problems = self.chain.audit()
            if problems:
                return result("halted", why="ledger failed audit: " + problems[0])

        if case["human"]:
            return result("final", case["human"]["outcome"], "decided by human sign-off")

        decisions = case["decisions"]
        if len(decisions) < r["min_agents"]:
            return result("waiting_for_agents",
                          why=f"{len(decisions)} of {r['min_agents']} agent decisions received")

        outcomes = {d["decision"] for d in decisions}
        if len(outcomes) > 1 and r["on_conflict"] == "escalate":
            return result("escalated", why="agents disagree; a human must decide")
        proposed = decisions[0]["decision"]

        limit = r["human_review_above"]
        amount = decisions[0]["input"]["amount_requested"]
        if limit is not None and amount > limit:
            return result("needs_human", why=f"amount {amount} is above the review limit {limit}")

        votes = case["votes"]
        if r["one_vote_each"]:
            latest = {}
            for v in votes:
                latest[v["validator"]] = v
            votes = list(latest.values())
        n_validators = max(len(self._validators()), 1)
        turnout = len(votes) / n_validators
        if not votes or turnout < r["quorum"]:
            return result("no_quorum", why=f"turnout {turnout:.0%} is below quorum {r['quorum']:.0%}")
        yes_share = sum(v["approve"] for v in votes) / len(votes)
        if yes_share < r["approval_threshold"]:
            return result("not_confirmed",
                          why=f"only {yes_share:.0%} of votes were YES "
                              f"(need {r['approval_threshold']:.0%})")
        return result("final", proposed,
                      f"{yes_share:.0%} YES on {turnout:.0%} turnout")

    # -- reading ----------------------------------------------------------
    def violations(self):
        return [tx["payload"] for tx in self.chain.transactions("violation")]

    def history(self, case_id):
        """Everything the ledger knows about one case, in order."""
        out = []
        for tx in self.chain.transactions():
            p = tx["payload"]
            if isinstance(p, dict) and (p.get("case_id") == case_id
                                        or p.get("application_id") == case_id):
                out.append({"block": tx["block"], "kind": tx["kind"],
                            "by": tx["sender"], "time": tx["timestamp"], "details": p})
        return out
