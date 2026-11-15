"""
wonders.agents - deterministic, explainable AI agents.

Scenario: a community fund receives micro-grant applications. AI agents
recommend APPROVE or REJECT. Every recommendation must be

* reproducible  - same input + same model  -> same output, every time
* explainable   - we can show WHY (the rules followed, and how much each
                  feature pushed the decision up or down)
* attributable  - we know WHICH agent and WHICH model version produced it

The data is synthetic. No real people are described.
"""

import random

from .chain import sha256_hex, now

FEATURES = ["project_score", "endorsements", "prior_grants",
            "household_income", "family_size", "amount_requested"]

# Allowed range of each input. Used for input validation.
FEATURE_RANGES = {
    "project_score":    (0, 100),      # panel score for the proposal
    "endorsements":     (0, 10),       # community members vouching for it
    "prior_grants":     (0, 5),        # grants already received
    "household_income": (10, 300),     # thousand PKR per month
    "family_size":      (1, 12),
    "amount_requested": (10, 500),     # thousand PKR
}

RULES_VERSION = "grant-policy-v1"


# --------------------------------------------------------------------------
# Synthetic data
# --------------------------------------------------------------------------

def make_applications(n=400, seed=7):
    """Create n synthetic applications with a 'fair' historical outcome."""
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        row = {
            "project_score": rng.randint(20, 100),
            "endorsements": rng.randint(0, 10),
            "prior_grants": rng.choice([0, 0, 0, 1, 1, 2, 3]),
            "household_income": rng.randint(15, 250),
            "family_size": rng.randint(1, 10),
            "amount_requested": rng.choice([25, 50, 75, 100, 150, 200, 300, 400]),
        }
        points = (0.05 * row["project_score"] + 0.25 * row["endorsements"]
                  - 0.6 * row["prior_grants"] - 0.008 * row["household_income"]
                  + 0.1 * row["family_size"] - 0.004 * row["amount_requested"])
        row["approved"] = int(points + rng.gauss(0, 0.4) > 3.2)
        rows.append(row)
    return rows


def sample_application(app_id="APP-001", **changes):
    """A ready-made application to experiment with."""
    app = {"application_id": app_id, "project_score": 82, "endorsements": 7,
           "prior_grants": 0, "household_income": 45, "family_size": 6,
           "amount_requested": 100}
    app.update(changes)
    return app


def validate_application(app):
    """Return a list of input problems (empty list = inputs are sane)."""
    problems = []
    for name, (low, high) in FEATURE_RANGES.items():
        value = app.get(name)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            problems.append(f"{name} is missing or not a number")
        elif not low <= value <= high:
            problems.append(f"{name}={value} is outside the allowed range {low}-{high}")
    return problems


# --------------------------------------------------------------------------
# The agent
# --------------------------------------------------------------------------

class DeterministicAgent:
    """An AI agent built on a decision tree with a FIXED random seed.

    If scikit-learn is not available the agent falls back to a small
    hand-written rule tree with the same interface.
    """

    def __init__(self, wallet, seed=42, max_depth=4, training_seed=7):
        self.wallet = wallet
        self.agent_id = wallet.name
        self.seed = seed
        self.max_depth = max_depth
        self.training_seed = training_seed
        self._nodes = self._train()
        self.model_hash = sha256_hex({"nodes": self._nodes, "features": FEATURES})

    # -- training ---------------------------------------------------------
    def _train(self):
        """Train, then store the tree as plain Python so it can be hashed.

        Each node: {feature, threshold, left, right, p_approve}
        A leaf has feature = None.
        """
        try:
            from sklearn.tree import DecisionTreeClassifier
        except ImportError:
            self.kind = "rules"
            return _FALLBACK_TREE
        self.kind = "decision-tree"
        data = make_applications(seed=self.training_seed)
        X = [[row[f] for f in FEATURES] for row in data]
        y = [row["approved"] for row in data]
        # max_features < all features makes the tree depend on the seed,
        # so "which seed was used" becomes part of the model's identity.
        model = DecisionTreeClassifier(max_depth=self.max_depth, max_features=4,
                                       min_samples_leaf=8, random_state=self.seed)
        model.fit(X, y)
        t = model.tree_
        nodes = []
        for i in range(t.node_count):
            counts = t.value[i][0]
            leaf = t.children_left[i] == -1
            nodes.append({
                "feature": None if leaf else FEATURES[int(t.feature[i])],
                "threshold": None if leaf else round(float(t.threshold[i]), 4),
                "left": int(t.children_left[i]),
                "right": int(t.children_right[i]),
                "p_approve": round(float(counts[1] / counts.sum()), 4),
            })
        return nodes

    # -- deciding ---------------------------------------------------------
    def decide(self, application):
        """Return a full decision record: outcome + explanation + provenance."""
        node = self._nodes[0]
        path = []
        contributions = {f: 0.0 for f in FEATURES}
        while node["feature"] is not None:
            feature, threshold = node["feature"], node["threshold"]
            value = application[feature]
            go_left = value <= threshold
            child = self._nodes[node["left"] if go_left else node["right"]]
            path.append(f"{feature} = {value} {'<=' if go_left else '>'} {threshold}")
            # how much this question moved the approval probability
            contributions[feature] += child["p_approve"] - node["p_approve"]
            node = child
        p = node["p_approve"]
        return {
            "application_id": application.get("application_id", "unknown"),
            "agent_id": self.agent_id,
            "model_kind": self.kind,
            "model_hash": self.model_hash,
            "model_seed": self.seed,
            "rules_version": RULES_VERSION,
            "input": {f: application[f] for f in FEATURES},
            "input_hash": sha256_hex({f: application[f] for f in FEATURES}),
            "decision": "APPROVE" if p >= 0.5 else "REJECT",
            "confidence": round(max(p, 1 - p), 4),
            "explanation": {
                "baseline_p_approve": self._nodes[0]["p_approve"],
                "path": path,
                "contributions": {f: round(c, 4) for f, c in contributions.items() if c},
                "final_p_approve": p,
            },
            "decided_at": now(),
        }

    def retrain(self, seed):
        """Change the model. The model hash changes with it."""
        self.seed = seed
        self._nodes = self._train()
        self.model_hash = sha256_hex({"nodes": self._nodes, "features": FEATURES})
        return self.model_hash

    def __repr__(self):
        return f"Agent({self.agent_id}, {self.kind}, model {self.model_hash[:10]}...)"


# Used only when scikit-learn cannot be imported.
_FALLBACK_TREE = [
    {"feature": "project_score", "threshold": 60.5, "left": 1, "right": 2, "p_approve": 0.42},
    {"feature": None, "threshold": None, "left": -1, "right": -1, "p_approve": 0.08},
    {"feature": "prior_grants", "threshold": 1.5, "left": 3, "right": 4, "p_approve": 0.66},
    {"feature": "endorsements", "threshold": 3.5, "left": 5, "right": 6, "p_approve": 0.78},
    {"feature": None, "threshold": None, "left": -1, "right": -1, "p_approve": 0.15},
    {"feature": None, "threshold": None, "left": -1, "right": -1, "p_approve": 0.35},
    {"feature": None, "threshold": None, "left": -1, "right": -1, "p_approve": 0.93},
]


# --------------------------------------------------------------------------
# Helpers used in the notebooks
# --------------------------------------------------------------------------

def explain(decision):
    """Print a decision record in plain language."""
    e = decision["explanation"]
    print(f"Application {decision['application_id']}: {decision['decision']} "
          f"(confidence {decision['confidence']:.0%}) by {decision['agent_id']}")
    print(f"  model {decision['model_hash'][:12]}...  rules {decision['rules_version']}")
    print(f"  Started from a baseline approval chance of {e['baseline_p_approve']:.0%}")
    for step in e["path"]:
        print(f"    asked: {step}")
    for feature, c in sorted(e["contributions"].items(), key=lambda kv: -abs(kv[1])):
        print(f"    {feature:<17} {'raised' if c > 0 else 'lowered'} the chance by {abs(c):.0%}")
    print(f"  Final approval chance: {e['final_p_approve']:.0%}")


def same_decision(a, b):
    """Compare two decision records, ignoring the time they were made."""
    strip = lambda d: {k: v for k, v in d.items() if k != "decided_at"}
    return strip(a) == strip(b)


def replay(agent, recorded_decision):
    """Re-run a recorded decision and report whether it reproduces."""
    again = agent.decide({"application_id": recorded_decision["application_id"],
                          **recorded_decision["input"]})
    return same_decision(again, recorded_decision)
