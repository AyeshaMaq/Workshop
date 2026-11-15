"""
Builds the workshop notebooks (participant version + solutions) from one source.

    python tools/build_notebooks.py

In the cell sources below, an exercise looks like this:

    #>> hint shown to the participant | stub line the participant starts from
    the solution lines
    #<<

Participant notebooks get the hint and the stub. Solution notebooks get the code.
"""

import re
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent

SETUP = '''# Setup: run this cell first.
import os, sys
import numpy, pandas, matplotlib          # loads the packages in JupyterLite
try:
    import sklearn
except ImportError:
    print("scikit-learn not found: agents will use the built-in rule tree instead.")

if not os.path.isdir("wonders"):
    if os.path.isdir("../wonders"):
        sys.path.insert(0, "..")
    else:
        try:                                # Google Colab: upload the workshop zip
            from google.colab import files
            import zipfile
            print("Upload blockchain_wonders.zip")
            name = next(iter(files.upload()))
            zipfile.ZipFile(name).extractall(".")
            sys.path.insert(0, "blockchain_wonders")
        except ImportError:
            print("Cannot find the 'wonders' folder. Keep this notebook next to it.")

import wonders
print("Ready. wonders version", wonders.__version__)'''


def md(text):
    return ("md", text.strip("\n"))


def code(text):
    return ("code", text.strip("\n"))


# ==========================================================================
# Activity 1
# ==========================================================================
NB1 = [
md("""
# Activity 1: Build a Blockchain
**Blockchain Wonders workshop · about 30 minutes**

You will build a working blockchain from nothing, break it, and see why it is hard to cheat.

| Step | What you do | Idea |
|---|---|---|
| 1 | Fingerprint some data | hashing |
| 2 | Make a block and link blocks | the chain |
| 3 | Tamper with history | tamper evidence |
| 4 | Sign records | digital identity |
| 5 | Mine | proof of work |
| 6 | Run a network | consensus |

Cells marked **Your turn** have a `TODO`. If you get stuck, ask, or open the notebook with the same name in the `solutions` folder.
"""),
code(SETUP),
md("""
## 1. Hashing: a fingerprint for data

A hash function turns any data into a short fixed-length code. Two properties matter:

- the **same** data always gives the **same** code
- a **tiny** change in the data gives a **completely different** code
"""),
code('''
from wonders import sha256_hex

print(sha256_hex("Pay Ali 100"))
print(sha256_hex("Pay Ali 100"))   # same data, same fingerprint
print(sha256_hex("Pay Ali 900"))   # one character changed
'''),
md("**Your turn.** Hash your own name, then change one letter and hash it again."),
code('''
#>> put your name in the first line and a one-letter change in the second | mine = sha256_hex("...")
mine = sha256_hex("Ayesha")
#<<
#>> | changed = sha256_hex("...")
changed = sha256_hex("Ayesh4")
#<<
print(mine)
print(changed)
different = sum(a != b for a, b in zip(mine, changed))
print(f"{different} of 64 characters changed")
'''),
md("""
## 2. A block, and a chain of blocks

A block is a container of records. Its hash covers **everything** inside it, including the hash of the block before it. That backward reference is the chain.

**Your turn.** Finish `block_hash` so it returns the fingerprint of the whole block.
"""),
code('''
def make_block(index, records, previous_hash):
    block = {"index": index, "records": records, "previous_hash": previous_hash}
    block["hash"] = block_hash(block)
    return block

def block_hash(block):
    contents = {"index": block["index"],
                "records": block["records"],
                "previous_hash": block["previous_hash"]}
    #>> return the sha256_hex of contents | return None
    return sha256_hex(contents)
    #<<

genesis = make_block(0, ["Fund created with 1000"], "0" * 64)
block1  = make_block(1, ["Grant 100 to Ali"], genesis["hash"])
block2  = make_block(2, ["Grant 250 to Sara"], block1["hash"])
my_chain = [genesis, block1, block2]

for b in my_chain:
    print(b["index"], b["records"], "| prev", b["previous_hash"][:8], "| hash", b["hash"][:8])
'''),
md("""
**Your turn.** Write the checker. A chain is healthy when, for every block:

1. its stored hash equals a freshly computed hash, and
2. its `previous_hash` equals the hash of the block before it.
"""),
code('''
def check_chain(chain):
    for i, block in enumerate(chain):
        #>> if the stored hash is not equal to block_hash(block), return a message | pass
        if block["hash"] != block_hash(block):
            return f"Block {i} was changed"
        #<<
        #>> if i > 0 and previous_hash does not match the earlier block's hash, return a message | pass
        if i > 0 and block["previous_hash"] != chain[i - 1]["hash"]:
            return f"Link from block {i} to block {i - 1} is broken"
        #<<
    return "Chain is healthy"

print(check_chain(my_chain))
'''),
md("""
## 3. Tamper with history

Sara would like 2,500 instead of 250. Change the record and run the checker.
"""),
code('''
my_chain[2]["records"] = ["Grant 2500 to Sara"]
print(check_chain(my_chain))
'''),
md("""
The cheat is caught because the block no longer matches its fingerprint. A clever cheat recalculates the hash too. Try it.
"""),
code('''
my_chain[2]["records"] = ["Grant 250 to Sara"]    # put block 2 back as it was
print("restored:", check_chain(my_chain))

my_chain[1]["records"] = ["Grant 900 to Ali"]
my_chain[1]["hash"] = block_hash(my_chain[1])     # cover the tracks
print(check_chain(my_chain))
'''),
md("""
Now block 2 points to a hash that no longer exists. To hide one change, the cheat has to rewrite **every block after it**. Hold that thought for step 5.

## 4. Who wrote this record? Digital signatures

From here on we use the workshop library, which has the same ideas with more features.

Each participant has a **wallet**: a private key to sign with and a public key that anyone can use to check the signature.
"""),
code('''
from wonders import Wallet, make_transaction, verify_transaction

ali = Wallet("ali")
tx = make_transaction(ali, "grant_request", {"amount": 100, "purpose": "school books"})
print("signed by:", tx["sender"], "| address", tx["sender_address"])
print("signature valid?", verify_transaction(tx))
'''),
md("**Your turn.** Change the amount inside `tx` and verify again. What happens, and why?"),
code('''
#>> change tx["payload"]["amount"] to 9000 | ...
tx["payload"]["amount"] = 9000
#<<
print("signature valid?", verify_transaction(tx))
'''),
md("""
## 5. A real chain, and mining

`Blockchain` refuses records with bad signatures and makes every block cost some computing work (**proof of work**): the block's hash must start with a number of zeros, found by trial and error.
"""),
code('''
from wonders import Blockchain
from wonders.viz import draw_chain

ledger = Blockchain(difficulty=3)
sara = Wallet("sara")

ledger.record(ali,  "grant_request", {"amount": 100, "purpose": "school books"})
ledger.record(sara, "grant_request", {"amount": 250, "purpose": "sewing machine"})
ledger.record(ali,  "receipt",       {"amount": 100, "note": "books bought"})

print(ledger)
print("problems found:", ledger.audit())
draw_chain(ledger)
'''),
code('''
# The forged transaction from step 4 is refused
try:
    ledger.add_transaction(tx)
except ValueError as err:
    print(err)
'''),
md("**How expensive is mining?** Each extra zero multiplies the work. Run the experiment."),
code('''
from wonders import Block
from wonders.viz import draw_mining

results = []
for difficulty in range(1, 5):
    block = Block(1, [{"demo": "data"}], "0" * 64)
    attempts = block.mine(difficulty)
    results.append((difficulty, attempts + 1))
    print(f"difficulty {difficulty}: {attempts + 1:>7} attempts -> {block.hash[:16]}...")
draw_mining(results)
'''),
md("""
**Your turn.** Tamper with the real ledger: change Sara's amount in block 2, then audit and draw the chain.
"""),
code('''
#>> set ledger.chain[2].transactions[0]["payload"]["amount"] to 2500 | ...
ledger.chain[2].transactions[0]["payload"]["amount"] = 2500
#<<
for problem in ledger.audit():
    print(problem)
draw_chain(ledger, title="After tampering")
'''),
md("""
The signature fails (Sara did not sign 2,500) and the block's hash fails. To hide it the cheat would need Sara's private key **and** would need to re-mine this block and every later one.

## 6. Consensus: no single copy is the truth

Five independent nodes each keep their own copy. One of them cheats.
"""),
code('''
from wonders import Network

ledger = Blockchain(difficulty=3)
ledger.record(ali, "grant_request", {"amount": 100})
net = Network(["node-1", "node-2", "node-3", "node-4", "node-5"], ledger)

# a new block is announced; every node checks it for itself
block = ledger.record(sara, "grant_request", {"amount": 250})
print("accepted by:", net.broadcast(block))

# node-3 rewrites its own copy
net.nodes["node-3"].chain[1].transactions[0]["payload"]["amount"] = 99999

tip, agree, disagree = net.consensus()
print("majority agrees on", tip[:12], "->", agree)
print("out of step:", disagree)
'''),
md("**Your turn.** Repair the network, then check consensus again."),
code('''
#>> call net.repair() and print what it returns | ...
print("repaired:", net.repair())
#<<
tip, agree, disagree = net.consensus()
print("agree:", agree, "| out of step:", disagree)
'''),
md("""
## Discuss with your neighbour (3 minutes)

1. In step 3 the checker caught the cheat. Who has to run the checker for that to matter?
2. If three of five nodes cheat together, what does `consensus()` report? Try it.
3. Name one record in your own organisation that would benefit from being tamper-evident, and one that would not.

**Next:** Activity 2 puts AI agents on this ledger.
"""),
]

# ==========================================================================
# Activity 2
# ==========================================================================
NB2 = [
md("""
# Activity 2: Integrate Deterministic AI Agents
**Blockchain Wonders workshop · about 30 minutes**

A community fund receives micro-grant applications. AI agents recommend **APPROVE** or **REJECT**.
We want every recommendation to be:

- **reproducible**: same input and same model give the same output, every time
- **explainable**: we can show *why*
- **attributable**: we know *which agent* and *which model version* made it

Explainable AI answers **why**. The blockchain answers **what happened, who acted, with which model and rules, when, and whether the record has changed since.**

All data is synthetic.
"""),
code(SETUP),
md("## 1. The data"),
code('''
import pandas as pd
from wonders import make_applications, FEATURE_RANGES

history = pd.DataFrame(make_applications())
print(len(history), "past applications;", f"{history.approved.mean():.0%} approved")
history.head()
'''),
md("""
## 2. Train an agent and ask for a decision

The agent is a decision tree trained with a **fixed random seed**.
"""),
code('''
from wonders import Wallet, DeterministicAgent, sample_application, explain
from wonders.viz import draw_explanation

agent_a = DeterministicAgent(Wallet("agent-A", role="agent"), seed=11)
print(agent_a)

application = sample_application("APP-001")
print(application)

decision = agent_a.decide(application)
explain(decision)
draw_explanation(decision)
'''),
md("""
Read the explanation: the agent started from the overall approval rate, asked a few questions, and each answer moved the chance up or down.

**Your turn.** Change the application and see how the decision and explanation change. Try `prior_grants=3`, or `endorsements=1`.
"""),
code('''
#>> make a changed application, e.g. sample_application("APP-002", prior_grants=3) | what_if = sample_application("APP-002")
what_if = sample_application("APP-002", prior_grants=3)
#<<
d2 = agent_a.decide(what_if)
explain(d2)
draw_explanation(d2)
'''),
md("""
## 3. Deterministic or not?

**Your turn.** Ask the agent the same question 20 times and collect the answers.
"""),
code('''
from wonders import same_decision

answers = []
for _ in range(20):
    #>> append agent_a.decide(application) to answers | pass
    answers.append(agent_a.decide(application))
    #<<

all_same = all(same_decision(answers[0], a) for a in answers)
print("20 runs, all identical?", all_same)
'''),
md("For contrast, here is an agent that is **not** deterministic: it adds a little randomness, as many generative AI systems do by default."),
code('''
import random

def moody_agent(application):
    d = agent_a.decide(application)
    p = d["explanation"]["final_p_approve"] + random.uniform(-0.5, 0.5)
    return "APPROVE" if p >= 0.5 else "REJECT"

print([moody_agent(application) for _ in range(12)])
'''),
md("""
If the same application can be approved in the morning and rejected in the afternoon, nobody can check a decision after the fact. Determinism is what makes **verification by replay** possible.

## 4. A fingerprint for the model

The agent's `model_hash` is the hash of its entire decision tree.

**Your turn.** Create two more agents: one with the same seed as agent A, one with a different seed. Predict which hashes will match before you run the cell.
"""),
code('''
#>> create an agent with seed=11 and another with seed=22 | twin = None
twin = DeterministicAgent(Wallet("agent-twin", role="agent"), seed=11)
#<<
#>> | agent_b = None
agent_b = DeterministicAgent(Wallet("agent-B", role="agent"), seed=22)
#<<
print("agent A :", agent_a.model_hash[:16])
print("twin    :", twin.model_hash[:16], "(same seed)")
print("agent B :", agent_b.model_hash[:16], "(different seed)")
'''),
md("""
Same data, same settings, same seed: the same model, bit for bit. Change anything and the fingerprint changes. So the fingerprint tells us exactly **which model** made a decision.

## 5. Put the decision on the ledger

The decision record already carries its provenance. Look at it.
"""),
code('''
for key in ["application_id", "agent_id", "model_hash", "model_seed",
            "rules_version", "input_hash", "decision", "confidence", "decided_at"]:
    print(f"{key:<15} {decision[key]}")
'''),
md("**Your turn.** Write `record_decision`: the agent decides, then the agent's own wallet signs the decision onto the chain as a record of kind `\"decision\"`."),
code('''
from wonders import Blockchain
from wonders.viz import draw_chain

ledger = Blockchain(difficulty=3)

def record_decision(chain, agent, application):
    decision = agent.decide(application)
    #>> use chain.record(wallet, kind, payload) with the agent's wallet | pass
    chain.record(agent.wallet, "decision", decision)
    #<<
    return decision

record_decision(ledger, agent_a, sample_application("APP-001"))
record_decision(ledger, agent_b, sample_application("APP-001"))
record_decision(ledger, agent_a, sample_application("APP-002", prior_grants=3))
record_decision(ledger, agent_b, sample_application("APP-003", project_score=30, endorsements=1))

draw_chain(ledger)
pd.DataFrame([{"block": tx["block"], "signed by": tx["sender"],
               "application": tx["payload"]["application_id"],
               "decision": tx["payload"]["decision"],
               "model": tx["payload"]["model_hash"][:10],
               "time": tx["timestamp"]} for tx in ledger.transactions("decision")])
'''),
md("""
## 6. The auditor's questions

Six months later an auditor picks one decision from the ledger. Answer each question **using only the ledger and the registered agents**.
"""),
code('''
from wonders import verify_transaction, replay

record = ledger.transactions("decision")[2]
d = record["payload"]

print("What happened?      ", d["application_id"], "->", d["decision"])
print("Which agent acted?  ", record["sender"], "| signature valid:", verify_transaction(record))
print("Which model + rules?", d["model_hash"][:16], "|", d["rules_version"])
print("When?               ", record["timestamp"], "in block", record["block"])
print("Changed since?      ", "no" if ledger.is_valid() else "YES")
print("Why?")
for step in d["explanation"]["path"]:
    print("    ", step)
'''),
md("**Your turn.** The strongest check: re-run the decision with the registered agent and compare. Use `replay(agent, recorded_decision)`."),
code('''
#>> call replay with agent_a and d | reproduces = None
reproduces = replay(agent_a, d)
#<<
print("Decision reproduces exactly?", reproduces)
'''),
md("""
## 7. Break it

Someone edits the ledger so that APP-003, which was rejected, reads APPROVE.
"""),
code('''
target = ledger.chain[4].transactions[0]
print("before:", target["payload"]["application_id"], target["payload"]["decision"])
target["payload"]["decision"] = "APPROVE"

print("ledger audit:")
for problem in ledger.audit():
    print("   ", problem)
print("replay check passes?", replay(agent_b, target["payload"]))
draw_chain(ledger, title="After someone edited a decision")
'''),
md("""
Three independent alarms went off: the block hash, the agent's signature, and the replay.

## Discuss with your neighbour (3 minutes)

1. The explanation says *why the model decided*. Does it say whether the decision was *fair*? Who should judge that?
2. Agents A and B were trained on the same data but can disagree. What should happen then?
3. What would be lost if these agents were not deterministic?

**Next:** Activity 3 adds rules about who may do what.
"""),
]

# ==========================================================================
# Activity 3
# ==========================================================================
NB3 = [
md("""
# Activity 3: Implement Smart Governance Rules
**Blockchain Wonders workshop · about 30 minutes**

A ledger records what happened. It does not decide what is **allowed** to happen. That is the job of a **smart contract**: rules that run the same way for everyone and write what they did to the ledger.

Our contract turns agent recommendations into final decisions:

```
agents submit decisions  ->  contract checks the rules
validators vote          ->  contract counts the votes
contract finalises       ->  outcome goes on the ledger
```

You will write two rules by hand, then operate the full contract.
"""),
code(SETUP),
md("""
## 1. Write a rule: authorised participation

**Your turn.** Finish `may_submit`: an agent may submit only if its address is in the registry **and** its role there is `"agent"`.
"""),
code('''
from wonders import Wallet

registry = {}                                    # address -> role

def register(wallet, role):
    registry[wallet.address] = role

def may_submit(wallet):
    #>> return True only when registry has this wallet.address with role "agent" | return True
    return registry.get(wallet.address) == "agent"
    #<<

agent_a, stranger, validator = Wallet("agent-A"), Wallet("stranger"), Wallet("validator-1")
register(agent_a, "agent")
register(validator, "validator")

for w in (agent_a, stranger, validator):
    print(f"{w.name:<12} may submit? {may_submit(w)}")
'''),
md("""
## 2. Write a rule: voting

Two numbers define a vote:

- **quorum**: the share of validators who must take part
- **approval threshold**: the share of votes cast that must be YES

**Your turn.** Finish `tally`.
"""),
code('''
def tally(votes, n_validators, quorum, threshold):
    """votes is a list of True/False. Returns 'approved', 'rejected' or 'no quorum'."""
    turnout = len(votes) / n_validators
    #>> if turnout is below quorum, return "no quorum" | pass
    if turnout < quorum:
        return "no quorum"
    #<<
    yes_share = sum(votes) / len(votes)
    #>> return "approved" if yes_share reaches the threshold, otherwise "rejected" | return "approved"
    return "approved" if yes_share >= threshold else "rejected"
    #<<

print(tally([True, True, True, False], n_validators=5, quorum=0.6, threshold=0.6))   # approved
print(tally([True],                    n_validators=5, quorum=0.6, threshold=0.6))   # no quorum
print(tally([True, False, False],      n_validators=5, quorum=0.6, threshold=0.6))   # rejected
'''),
md("""
## 3. The full contract

`World` sets up everything from Activities 1 and 2: a ledger, three registered agents, five validators, an administrator, and a governance contract. The contract's behaviour is controlled by a **rules dictionary**.
"""),
code('''
from wonders import World, WEAK_RULES, RULE_HELP, sample_application

for rule, value in WEAK_RULES.items():
    print(f"{rule:<22} = {str(value):<12} {RULE_HELP[rule]}")
'''),
md("These default rules are deliberately weak. Start with a sensible set and run one case through."),
code('''
rules = {
    "require_registration": True,
    "check_model_hash": True,
    "min_agents": 2,
    "quorum": 0.6,
    "approval_threshold": 0.6,
    "one_vote_each": True,
}
world = World(rules)
contract = world.contract

app = sample_application("APP-100")
case_id = world.submit(app)                       # all three agents decide and submit
print("agents said:", [d["decision"] for d in contract.cases[case_id]["decisions"]])

print("before any votes:", contract.finalize(case_id)["status"])
'''),
md("**Your turn.** Have validators vote, then finalise. Use `contract.vote(validator_wallet, case_id, True_or_False, reason)`. The validators are in `world.validators`."),
code('''
#>> make at least three validators vote, then call contract.finalize(case_id) | result = contract.finalize(case_id)
for v in world.validators[:4]:
    contract.vote(v, case_id, True, "checked")
result = contract.finalize(case_id)
#<<
print(result["status"], "|", result["outcome"], "|", result["why"])
'''),
md("Everything the contract did is on the ledger."),
code('''
import pandas as pd
pd.DataFrame(contract.history(case_id))[["block", "kind", "by", "time"]]
'''),
md("""
## 4. The contract says no

An unregistered agent tries to submit. The contract refuses **and records the attempt**.
"""),
code('''
from wonders import DeterministicAgent, GovernanceError

outsider = DeterministicAgent(Wallet("outsider-bot", role="agent"), seed=5)
try:
    contract.submit_decision(outsider.wallet, outsider.decide(sample_application("APP-101")))
except GovernanceError as err:
    print("refused:", err)

print("violations on the ledger:", contract.violations())
'''),
md("**Your turn.** A validator tries to act as an agent. Submit a decision using `world.validators[0]` as the wallet and catch the error. What did the contract check?"),
code('''
real = world.agents[0].decide(sample_application("APP-102"))
try:
    #>> call contract.submit_decision with world.validators[0] and real | pass
    contract.submit_decision(world.validators[0], real)
    #<<
except GovernanceError as err:
    print("refused:", err)
'''),
md("""
## 5. Rules for human judgement

Two more rules bring people in where machines should not decide alone:

- `human_review_above`: large amounts need a human sign-off
- `on_conflict = "escalate"`: when agents disagree, a human decides
"""),
code('''
world = World({**rules, "human_review_above": 200, "on_conflict": "escalate"})
contract = world.contract

big = sample_application("APP-200", amount_requested=400)
world.submit(big)
world.votes("APP-200", yes=5)
r = contract.finalize("APP-200")
print(r["status"], "|", r["why"])
'''),
md("**Your turn.** You are the fund administrator (`world.admin`). Sign the case off with `contract.human_signoff(admin, case_id, \"APPROVE\" or \"REJECT\", note)` and finalise again."),
code('''
#>> call contract.human_signoff(...) then contract.finalize("APP-200") | r = contract.finalize("APP-200")
contract.human_signoff(world.admin, "APP-200", "APPROVE", "site visit completed")
r = contract.finalize("APP-200")
#<<
print(r["status"], "|", r["outcome"], "|", r["why"])
pd.DataFrame(contract.history("APP-200"))[["block", "kind", "by"]]
'''),
md("""
## 6. Design exercise

The fund's board has written this policy:

> *"Every application is assessed by all three agents. If they disagree, a person decides. Any request above 150 thousand rupees needs a person. A decision stands only if most validators took part and at least two-thirds of those voting agreed. Nobody outside the fund takes part."*

**Your turn.** Translate the policy into a rules dictionary.
"""),
code('''
board_rules = {
    #>> fill in the rules that express the board's policy | "require_registration": False,
    "require_registration": True,
    "min_agents": 3,
    "on_conflict": "escalate",
    "human_review_above": 150,
    "quorum": 0.6,
    "approval_threshold": 0.67,
    "one_vote_each": True,
    #<<
}

world = World(board_rules)
world.submit(sample_application("APP-300"))
world.votes("APP-300", yes=4, no=1)
r = world.contract.finalize("APP-300")
print("small request :", r["status"], r["outcome"])

world.submit(sample_application("APP-301", amount_requested=300))
world.votes("APP-301", yes=5)
print("large request :", world.contract.finalize("APP-301")["status"])
'''),
md("""
Expected: the small request is `final APPROVE`; the large one is `needs_human`.

## Discuss with your neighbour (3 minutes)

1. The rules dictionary is itself written to the ledger when the contract is deployed. Why does that matter?
2. Who should be allowed to change the rules, and how?
3. Which of today's rules would you never automate?

**Next:** Activity 4. Things go wrong.
"""),
]

# ==========================================================================
# Activity 4
# ==========================================================================
NB4 = [
md("""
# Activity 4: Governance Crisis Challenge
**Blockchain Wonders workshop · about 30 minutes · work in teams**

The community fund is live. Eight incidents are about to hit it.

Under the default weak rules, **every incident succeeds**. Your team must write a rules dictionary that:

1. blocks all eight incidents, **and**
2. still lets an honest application through.

| Time | What |
|---|---|
| 5 min | Watch the incidents happen |
| 15 min | Write your rules, test, improve |
| 10 min | Each team reports: what you changed and why |
"""),
code(SETUP),
md("## 1. Meet the incidents"),
code('''
from wonders import INCIDENTS, run_incident, scorecard, WEAK_RULES, RULE_HELP

for inc in INCIDENTS:
    print(f"{inc['n']}. {inc['title']:<24} {inc['card']}")
'''),
md("Watch each one succeed against the weak rules. Read the **Think** line for each."),
code('''
for n in range(1, 9):
    run_incident(n)
    print()
'''),
md("The baseline score:"),
code('''
from wonders.viz import draw_scorecard
draw_scorecard(scorecard(WEAK_RULES))
'''),
md("""
## 2. Investigate one incident

`run_incident` returns the whole system so you can look at the evidence. Pick the incident on your team's card.
"""),
code('''
import pandas as pd

world = run_incident(8)                     # change the number
print()
print("ledger audit:", world.chain.audit() or "no problems found")
pd.DataFrame([{"block": tx["block"], "kind": tx["kind"], "by": tx["sender"]}
              for tx in world.chain.transactions()]).tail(12)
'''),
md("""
## 3. Write your governance

The rules you can set:
"""),
code('''
for rule, value in WEAK_RULES.items():
    print(f"{rule:<22} (now {str(value):<11}) {RULE_HELP[rule]}")
'''),
md("**Your turn.** Edit `my_rules`, run the cell, read the scorecard, improve. Change one thing at a time so you learn which rule stops which incident."),
code('''
my_rules = {
    #>> change these values; add more rules from the list above | "require_registration": False,
    "require_registration": True,
    "check_model_hash": True,
    "replay_check": True,
    "validate_inputs": True,
    "min_agents": 2,
    "on_conflict": "escalate",
    "quorum": 0.6,
    "approval_threshold": 0.6,
    "one_vote_each": True,
    "human_review_above": 200,
    "audit_before_finalize": True,
    #<<
}

draw_scorecard(scorecard(my_rules))
'''),
md("Replay a single incident against your rules to see exactly how it was stopped."),
code('''
run_incident(3, my_rules);
'''),
md("""
## 4. Can you be too safe?

Test 9 is not an attack. It is an honest applicant, with one validator offline and one who votes no.

**Your turn.** Take your rules and make one of them extreme, for example `approval_threshold = 1.0` or `human_review_above = 0`. What happens to test 9?
"""),
code('''
#>> copy my_rules and make one rule extreme | too_strict = {**my_rules}
too_strict = {**my_rules, "approval_threshold": 1.0}
#<<
scorecard(too_strict);
'''),
md("""
Governance has two ways to fail: it lets bad things happen, or it stops good things from happening.

## 5. Team report

Fill this in and be ready to present in two minutes.

| Question | Your answer |
|---|---|
| Which incident did your team investigate? | |
| Which rule stopped it? | |
| Was it stopped by the **blockchain**, by **deterministic AI**, by **governance rules**, or by a **human**? | |
| One rule you added that has a cost. What is the cost? | |
| One incident this system still could not stop | |

## Closing questions for the room

1. Incident 3 was caught by re-running the model. What would you do if the AI were not deterministic?
2. Incident 8: the ledger was tamper-evident all along. Why did the weak system not notice?
3. Who writes the rules, and who can change them? Is that on the ledger too?
4. The central question of the workshop: **how can intelligent agents interact under transparent, deterministic, verifiable, and collectively governed rules?** What is your answer now?
"""),
]

NB0 = [
md("""
# Setup check
Run the cell below before the workshop starts. If it prints **All good**, you are ready.
"""),
code(SETUP),
code('''
from wonders import Blockchain, Wallet, DeterministicAgent, sample_application, scorecard

ledger = Blockchain(difficulty=2)
agent = DeterministicAgent(Wallet("check-agent"), seed=1)
ledger.record(agent.wallet, "decision", agent.decide(sample_application()))
assert ledger.is_valid()
print("ledger ok | agent type:", agent.kind)

import matplotlib.pyplot as plt
plt.figure(figsize=(3, 1)); plt.plot([0, 1, 2], [0, 1, 0]); plt.axis("off"); plt.show()
print("All good. See you at the workshop.")
'''),
]

NOTEBOOKS = {
    "00_setup_check": NB0,
    "01_build_a_blockchain": NB1,
    "02_deterministic_ai_agents": NB2,
    "03_smart_governance_rules": NB3,
    "04_governance_crisis_challenge": NB4,
}

OPEN = re.compile(r"^(\s*)#>>\s?(.*)$")


def render(source, solution):
    out, skipping = [], False
    for line in source.split("\n"):
        m = OPEN.match(line)
        if m:
            indent, rest = m.group(1), m.group(2)
            hint, _, stub = rest.partition("|")
            hint, stub = hint.strip(), stub.strip()
            if solution:
                if hint:
                    out.append(f"{indent}# {hint}")
            else:
                if hint:
                    out.append(f"{indent}# TODO: {hint}")
                if stub:
                    out.append(f"{indent}{stub}")
                skipping = True
            continue
        if line.strip() == "#<<":
            skipping = False
            continue
        if not skipping:
            out.append(line)
    return "\n".join(out)


def build():
    for name, cells in NOTEBOOKS.items():
        for solution in ((False,) if name.startswith("00") else (False, True)):
            nb = nbf.v4.new_notebook()
            nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python",
                                          "name": "python3"},
                           "language_info": {"name": "python"}}
            for i, (kind, text) in enumerate(cells):
                if kind == "md":
                    if solution and i == 0:
                        text = text.replace("\n", "  *(solutions)*\n", 1)
                    cell = nbf.v4.new_markdown_cell(text)
                else:
                    cell = nbf.v4.new_code_cell(render(text, solution))
                cell["id"] = f"{name[:2]}-{i:03d}"
                nb.cells.append(cell)
            folder = ROOT / ("solutions" if solution else "")
            folder.mkdir(exist_ok=True)
            nbf.write(nb, folder / f"{name}.ipynb")
            print("wrote", (folder / f"{name}.ipynb").relative_to(ROOT))


if __name__ == "__main__":
    build()
