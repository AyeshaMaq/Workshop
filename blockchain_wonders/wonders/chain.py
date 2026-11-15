"""
wonders.chain - a small, readable blockchain for teaching.

Everything here uses only the Python standard library so it runs in
JupyterLite / Pyodide, Google Colab, or any local Python 3.9+.

Concepts covered
----------------
* hashing            -> sha256_hex()
* digital identity   -> Wallet (toy RSA signatures: TEACHING ONLY, not secure)
* transactions       -> make_transaction(), verify_transaction()
* blocks & linking   -> Block
* proof of work      -> Block.mine()
* immutability       -> Blockchain.audit()
* consensus          -> Network (majority vote of independent nodes)
"""

import copy
import hashlib
import json
import random
from datetime import datetime, timezone

# --------------------------------------------------------------------------
# Hashing
# --------------------------------------------------------------------------

def canonical(obj):
    """Turn any JSON-like object into ONE fixed text form.

    The same data must always give the same text, otherwise the same data
    would give different hashes. sort_keys does that for dictionaries.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256_hex(obj):
    """SHA-256 fingerprint of text or of any JSON-like object."""
    text = obj if isinstance(obj, str) else canonical(obj)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# Digital identity: toy RSA signatures
# --------------------------------------------------------------------------

def _is_prime(n, rng, rounds=20):
    """Miller-Rabin primality test."""
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29):
        if n % p == 0:
            return n == p
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for _ in range(rounds):
        a = rng.randrange(2, n - 1)
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _random_prime(bits, rng):
    while True:
        candidate = rng.getrandbits(bits) | (1 << (bits - 1)) | 1
        if _is_prime(candidate, rng):
            return candidate


class Wallet:
    """A participant's identity: a private key (secret) and a public key.

    * sign()   uses the PRIVATE key - only the owner can do it.
    * verify() uses the PUBLIC key  - anybody can do it.

    WARNING: the keys are tiny (128-bit toy RSA) and are generated from the
    owner's name so the workshop is reproducible. Never use this for real.
    """

    E = 65537

    def __init__(self, name, role="participant"):
        self.name = name
        self.role = role
        rng = random.Random("wonders-key-" + name)
        while True:
            p, q = _random_prime(64, rng), _random_prime(64, rng)
            phi = (p - 1) * (q - 1)
            if p != q and phi % self.E != 0:
                break
        self._n = p * q
        self._d = pow(self.E, -1, phi)          # the private key
        self.public_key = format(self._n, "x")  # the public key (hex text)
        self.address = sha256_hex(self.public_key)[:12]

    def sign(self, message):
        digest = int(sha256_hex(message), 16) % self._n
        return format(pow(digest, self._d, self._n), "x")

    def __repr__(self):
        return f"Wallet({self.name!r}, role={self.role!r}, address={self.address})"


def verify_signature(message, signature, public_key):
    """Check a signature using only the signer's PUBLIC key."""
    try:
        n = int(public_key, 16)
        digest = int(sha256_hex(message), 16) % n
        return pow(int(signature, 16), Wallet.E, n) == digest
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------
# Transactions
# --------------------------------------------------------------------------

def make_transaction(wallet, kind, payload):
    """Create a signed record. `kind` says what sort of record it is."""
    body = {
        "kind": kind,
        "sender": wallet.name,
        "sender_address": wallet.address,
        "payload": payload,
        "timestamp": now(),
    }
    return {**body, "public_key": wallet.public_key, "signature": wallet.sign(body)}


def verify_transaction(tx):
    """True if the transaction was really signed by the stated public key
    and has not been changed since."""
    try:
        body = {k: tx[k] for k in ("kind", "sender", "sender_address", "payload", "timestamp")}
        if sha256_hex(tx["public_key"])[:12] != tx["sender_address"]:
            return False
        return verify_signature(body, tx["signature"], tx["public_key"])
    except KeyError:
        return False


# --------------------------------------------------------------------------
# Blocks
# --------------------------------------------------------------------------

class Block:
    def __init__(self, index, transactions, previous_hash, timestamp=None, nonce=0):
        self.index = index
        self.timestamp = timestamp or now()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.compute_hash()

    def compute_hash(self):
        """The block's fingerprint covers EVERYTHING in the block,
        including the previous block's hash. That is the 'chain'."""
        return sha256_hex({
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        })

    def mine(self, difficulty):
        """Proof of work: change the nonce until the hash starts with
        `difficulty` zeros. Returns how many attempts it took."""
        target = "0" * difficulty
        attempts = 0
        self.hash = self.compute_hash()
        while not self.hash.startswith(target):
            self.nonce += 1
            attempts += 1
            self.hash = self.compute_hash()
        return attempts

    def __repr__(self):
        return (f"Block #{self.index} | {len(self.transactions)} tx | "
                f"prev {self.previous_hash[:10]}... | hash {self.hash[:10]}...")


# --------------------------------------------------------------------------
# The chain
# --------------------------------------------------------------------------

class Blockchain:
    def __init__(self, difficulty=3):
        self.difficulty = difficulty
        self.pending = []
        genesis = Block(0, [], "0" * 64, timestamp="2026-01-01T00:00:00+00:00")
        genesis.mine(difficulty)
        self.chain = [genesis]

    # -- writing ----------------------------------------------------------
    @property
    def last_block(self):
        return self.chain[-1]

    def add_transaction(self, tx):
        """Accept a transaction only if its signature is valid."""
        if not verify_transaction(tx):
            raise ValueError("Rejected: invalid signature on transaction")
        self.pending.append(tx)
        return tx

    def mine_block(self):
        """Pack all pending transactions into a new block and add it."""
        block = Block(len(self.chain), self.pending, self.last_block.hash)
        block.mine(self.difficulty)
        self.chain.append(block)
        self.pending = []
        return block

    def record(self, wallet, kind, payload):
        """Shortcut: sign a record, add it, and mine it into a block."""
        self.add_transaction(make_transaction(wallet, kind, payload))
        return self.mine_block()

    # -- reading ----------------------------------------------------------
    def transactions(self, kind=None):
        """All transactions on the chain, oldest first."""
        out = []
        for block in self.chain:
            for tx in block.transactions:
                if kind is None or tx["kind"] == kind:
                    out.append({**tx, "block": block.index})
        return out

    # -- verifying --------------------------------------------------------
    def audit(self):
        """Check the whole chain. Returns a list of problems (empty = healthy)."""
        problems = []
        target = "0" * self.difficulty
        for i, block in enumerate(self.chain):
            if block.hash != block.compute_hash():
                problems.append(f"Block {i}: contents do not match its hash (data was changed)")
            if not block.hash.startswith(target):
                problems.append(f"Block {i}: hash does not meet the proof-of-work target")
            if i > 0 and block.previous_hash != self.chain[i - 1].hash:
                problems.append(f"Block {i}: link to block {i - 1} is broken")
            for n, tx in enumerate(block.transactions):
                if not verify_transaction(tx):
                    problems.append(f"Block {i}, transaction {n}: signature is invalid")
        return problems

    def is_valid(self):
        return not self.audit()

    def copy(self):
        return copy.deepcopy(self)

    def __len__(self):
        return len(self.chain)

    def __repr__(self):
        return "\n".join(repr(b) for b in self.chain)


# --------------------------------------------------------------------------
# Consensus: many independent copies
# --------------------------------------------------------------------------

class Network:
    """A set of nodes, each holding its own copy of the ledger.

    Nobody is 'the server'. The agreed ledger is the valid chain that the
    majority of nodes hold.
    """

    def __init__(self, node_names, chain):
        self.nodes = {name: chain.copy() for name in node_names}

    def broadcast(self, block):
        """Every node checks the new block itself; honest nodes append it."""
        votes = {}
        for name, ledger in self.nodes.items():
            ok = (block.previous_hash == ledger.last_block.hash
                  and block.hash == block.compute_hash()
                  and block.hash.startswith("0" * ledger.difficulty)
                  and all(verify_transaction(tx) for tx in block.transactions))
            votes[name] = ok
            if ok:
                ledger.chain.append(copy.deepcopy(block))
        return votes

    def consensus(self):
        """Return (agreed_tip_hash, nodes_that_agree, nodes_that_disagree).
        Only chains that pass their own audit can win."""
        tally = {}
        for name, ledger in self.nodes.items():
            key = ledger.last_block.hash if ledger.is_valid() else "INVALID"
            tally.setdefault(key, []).append(name)
        valid = {k: v for k, v in tally.items() if k != "INVALID"}
        if not valid:
            return None, [], list(self.nodes)
        winner = max(valid, key=lambda k: len(valid[k]))
        agree = valid[winner]
        disagree = [n for n in self.nodes if n not in agree]
        return winner, agree, disagree

    def repair(self):
        """Nodes that disagree with the majority replace their copy."""
        winner, agree, disagree = self.consensus()
        if winner is None or len(agree) <= len(self.nodes) / 2:
            raise RuntimeError("No honest majority: the network cannot repair itself")
        good = self.nodes[agree[0]]
        for name in disagree:
            self.nodes[name] = good.copy()
        return disagree
