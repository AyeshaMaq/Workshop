"""
wonders.crisis - the Governance Crisis Challenge (Activity 4).

Eight incidents hit a community grant system run by AI agents, validators
and a governance contract. Under WEAK_RULES every incident succeeds.

Your team's job: write a rules dictionary that blocks all eight incidents
AND still lets an honest application go through.

    from wonders.crisis import run_incident, scorecard
    run_incident(1)              # watch incident 1 happen under weak rules
    run_incident(1, my_rules)    # try again with your rules
    scorecard(my_rules)          # test everything at once
"""

import copy

from .agents import DeterministicAgent, make_applications, FEATURES
from .chain import Blockchain, Wallet
from .governance import GovernanceContract, GovernanceError, WEAK_RULES

AGENT_SEEDS = {"agent-A": 11, "agent-B": 22, "agent-C": 33}
ROGUE_SEED = 99


class World:
    """A complete running system: ledger + contract + agents + validators."""

    def __init__(self, rules=None, difficulty=2):
        self.chain = Blockchain(difficulty=difficulty)
        self.admin = Wallet("fund-admin", role="admin")
        self.contract = GovernanceContract(self.chain, self.admin, rules)
        self.agents = [DeterministicAgent(Wallet(name, role="agent"), seed=seed)
                       for name, seed in AGENT_SEEDS.items()]
        self.validators = [Wallet(f"validator-{i}", role="validator") for i in range(1, 6)]
        for agent in self.agents:
            self.contract.register(self.admin, agent.wallet, "agent", agent=agent)
        for v in self.validators:
            self.contract.register(self.admin, v, "validator")

    def agent(self, name):
        return next(a for a in self.agents if a.agent_id == name)

    def submit(self, application, agents=None):
        """Each agent decides and submits. Returns the case id."""
        for agent in agents or self.agents:
            self.contract.submit_decision(agent.wallet, agent.decide(application))
        return application["application_id"]

    def votes(self, case_id, yes=5, no=0):
        """The first `yes` validators vote YES, the next `no` vote NO."""
        for v in self.validators[:yes]:
            self.contract.vote(v, case_id, True, "process looks fine")
        for v in self.validators[yes:yes + no]:
            self.contract.vote(v, case_id, False, "not convinced")


# --------------------------------------------------------------------------
# Test applications (found once, deterministically)
# --------------------------------------------------------------------------

_CASES = {}


def _test_cases():
    if _CASES:
        return _CASES
    agents = {n: DeterministicAgent(Wallet(n), seed=s) for n, s in AGENT_SEEDS.items()}
    rogue = DeterministicAgent(Wallet("agent-B"), seed=ROGUE_SEED)
    pool = [{f: row[f] for f in FEATURES} for row in make_applications(n=800, seed=123)]

    def first(test):
        for app in pool:
            if test(app, {n: a.decide(app)["decision"] for n, a in agents.items()}):
                return app
        raise RuntimeError("could not build a test case; check the scikit-learn install")

    _CASES["honest"] = first(lambda a, d: set(d.values()) == {"APPROVE"}
                             and a["amount_requested"] <= 100)
    _CASES["weak"] = first(lambda a, d: set(d.values()) == {"REJECT"})
    _CASES["conflict"] = first(lambda a, d: d["agent-A"] == "APPROVE" and d["agent-B"] == "REJECT"
                               and a["amount_requested"] <= 100)
    _CASES["rogue"] = first(lambda a, d: d["agent-B"] == "REJECT"
                            and rogue.decide(a)["decision"] == "APPROVE"
                            and a["amount_requested"] <= 100)
    _CASES["large"] = first(lambda a, d: set(d.values()) == {"APPROVE"}
                            and a["amount_requested"] >= 300)
    bad = dict(_CASES["honest"], project_score=820)          # typo: 82 -> 820
    _CASES["typo"] = bad
    return _CASES


def _case(name, app_id):
    return {"application_id": app_id, **_test_cases()[name]}


# --------------------------------------------------------------------------
# The incidents. Each returns (breached, what_happened).
# --------------------------------------------------------------------------

def _approved(case):
    return case["status"] == "final" and case["outcome"] == "APPROVE"


def incident_1(w):
    mallory = DeterministicAgent(Wallet("mallory-bot", role="agent"), seed=5)
    fake = mallory.decide(_case("weak", "INC1-APP"))
    fake["decision"] = "APPROVE"
    w.contract.submit_decision(mallory.wallet, fake)
    w.votes("INC1-APP")
    return _approved(w.contract.finalize("INC1-APP")), \
        "mallory-bot, never registered, pushed an APPROVE through for a weak application"


def incident_2(w):
    b = w.agent("agent-B")
    b.retrain(ROGUE_SEED)                         # nobody approved this change
    w.submit(_case("rogue", "INC2-APP"), agents=[b])
    w.votes("INC2-APP")
    return _approved(w.contract.finalize("INC2-APP")), \
        "agent-B silently swapped its model; the new model approved what the registered one rejects"


def incident_3(w):
    c = w.agent("agent-C")
    forged = c.decide(_case("weak", "INC3-APP"))
    forged["decision"] = "APPROVE"                # edited after the model ran
    w.contract.submit_decision(c.wallet, forged)
    w.votes("INC3-APP")
    return _approved(w.contract.finalize("INC3-APP")), \
        "an insider edited agent-C's REJECT into APPROVE before submitting it"


def incident_4(w):
    w.submit(_case("conflict", "INC4-APP"), agents=[w.agent("agent-A"), w.agent("agent-B")])
    w.votes("INC4-APP")
    return _approved(w.contract.finalize("INC4-APP")), \
        "agent-A said APPROVE, agent-B said REJECT; the first answer simply won"


def incident_5(w):
    w.submit(_case("typo", "INC5-APP"))
    w.votes("INC5-APP")
    return _approved(w.contract.finalize("INC5-APP")), \
        "a typing error (project_score 820 instead of 82) was approved without question"


def incident_6(w):
    app = _case("large", "INC6-APP")
    w.submit(app)
    w.votes("INC6-APP")
    return _approved(w.contract.finalize("INC6-APP")), \
        f"a grant of {app['amount_requested']} thousand PKR was paid with no human involved"


def incident_7(w):
    w.submit(_case("honest", "INC7-APP"))
    insider = w.validators[4]
    for _ in range(3):                            # votes three times, alone
        w.contract.vote(insider, "INC7-APP", True, "trust me")
    return _approved(w.contract.finalize("INC7-APP")), \
        "one validator voted three times and confirmed the case before anyone else looked"


def incident_8(w):
    w.submit(_case("weak", "INC8-OLD"))
    w.votes("INC8-OLD")
    w.contract.finalize("INC8-OLD")
    for block in w.chain.chain:                   # rewrite history
        for tx in block.transactions:
            if tx["kind"] == "decision" and tx["payload"]["application_id"] == "INC8-OLD":
                tx["payload"]["decision"] = "APPROVE"
    w.submit(_case("honest", "INC8-NEW"))
    w.votes("INC8-NEW")
    return w.contract.finalize("INC8-NEW")["status"] == "final", \
        "someone rewrote an old decision on the ledger and business carried on as usual"


def liveness(w):
    """An honest application must still get through."""
    w.submit(_case("honest", "HONEST-APP"))
    w.votes("HONEST-APP", yes=3, no=1)            # one validator is offline
    case = w.contract.finalize("HONEST-APP")
    return not _approved(case), \
        f"honest application ended as '{case['status']}' ({case.get('why', '')})"


INCIDENTS = [
    {"n": 1, "title": "The uninvited agent", "run": incident_1,
     "card": "A bot nobody has heard of starts submitting grant approvals.",
     "ask": "Who is allowed to take part, and how does the system know?"},
    {"n": 2, "title": "The silent model swap", "run": incident_2,
     "card": "A registered agent is retrained overnight. Nobody was told.",
     "ask": "How do we know WHICH model made a decision?"},
    {"n": 3, "title": "The edited decision", "run": incident_3,
     "card": "A decision record says APPROVE, but the model actually said REJECT.",
     "ask": "If the AI is deterministic, what can validators do that they could not do otherwise?"},
    {"n": 4, "title": "The disagreement", "run": incident_4,
     "card": "Two agents give opposite answers for the same application.",
     "ask": "Should a machine break the tie, or a person?"},
    {"n": 5, "title": "The typo", "run": incident_5,
     "card": "An application arrives with a project score of 820 out of 100.",
     "ask": "The AI was 'correct' for the data it saw. Who checks the data?"},
    {"n": 6, "title": "The big cheque", "run": incident_6,
     "card": "The largest grant of the year is approved fully automatically.",
     "ask": "Where should automation stop and human judgement begin?"},
    {"n": 7, "title": "The eager validator", "run": incident_7,
     "card": "A case is confirmed seconds after submission, on one person's votes.",
     "ask": "How many people must agree before something counts as agreed?"},
    {"n": 8, "title": "The rewritten past", "run": incident_8,
     "card": "An old REJECT on the ledger now reads APPROVE.",
     "ask": "A blockchain makes tampering evident. Evident to whom, and when?"},
]


# --------------------------------------------------------------------------
# Running incidents
# --------------------------------------------------------------------------

def _run(fn, rules):
    world = World(rules)
    try:
        breached, story = fn(world)
        blocked_by = None
    except GovernanceError as err:
        breached, story, blocked_by = False, "", err
    return world, breached, story, blocked_by


def run_incident(n, rules=None, verbose=True):
    """Play one incident against a fresh system. Returns the World so you
    can inspect world.chain and world.contract afterwards."""
    inc = INCIDENTS[n - 1]
    world, breached, story, blocked_by = _run(inc["run"], rules)
    if verbose:
        print(f"INCIDENT {n}: {inc['title']}")
        print(f"  {inc['card']}")
        if breached:
            print(f"  RESULT: BREACHED - {story}.")
            print(f"  Think: {inc['ask']}")
        elif blocked_by is not None:
            print(f"  RESULT: BLOCKED by the contract -> {blocked_by}")
        else:
            case = list(world.contract.cases.values())[-1]
            print(f"  RESULT: BLOCKED - case status '{case['status']}' ({case.get('why', '')})")
    return world


def scorecard(rules=None, verbose=True):
    """Test a rules dictionary against all incidents plus the honest case."""
    rows = []
    for inc in INCIDENTS:
        _, breached, _, _ = _run(inc["run"], rules)
        rows.append({"test": f"{inc['n']}. {inc['title']}", "passed": not breached})
    _, failed, story, blocked_by = _run(liveness, rules)
    honest_ok = not failed and blocked_by is None
    rows.append({"test": "9. Honest application still approved", "passed": honest_ok})
    score = sum(r["passed"] for r in rows)
    if verbose:
        for r in rows:
            print(f"  {'PASS' if r['passed'] else 'FAIL'}  {r['test']}")
        if not honest_ok:
            print(f"        -> {blocked_by or story}")
        print(f"\nScore: {score} / {len(rows)}")
        if score == len(rows):
            print("Your governance survives every incident and still serves honest applicants.")
        elif not honest_ok:
            print("Careful: rules that block everything also block the people you serve.")
    return rows
