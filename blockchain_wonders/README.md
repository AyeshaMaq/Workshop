# Blockchain Wonders: workshop code

Hands-on material for **"Blockchain Wonders: A Hands-On Journey Where Technology, Governance, AI, and Society Converge"** (Dr. Ayesha Maqbool).

Participants build, step by step, a small **Blockchain-Governed AI Agent System**: a community fund where AI agents recommend micro-grants, validators vote, a governance contract enforces the rules, and everything is written to a tamper-evident ledger. All data is synthetic.

## What is in this folder

| Item | What it is |
|---|---|
| `00_setup_check.ipynb` | One-minute check that a laptop is ready |
| `01_build_a_blockchain.ipynb` | Activity 1: hashing, blocks, linking, tampering, signatures, mining, consensus |
| `02_deterministic_ai_agents.ipynb` | Activity 2: reproducible decisions, explanations, provenance on the ledger |
| `03_smart_governance_rules.ipynb` | Activity 3: authorised participation, voting, human sign-off |
| `04_governance_crisis_challenge.ipynb` | Activity 4: eight incidents; teams design rules that survive them |
| `solutions/` | The same four notebooks, completed |
| `wonders/` | The Python library the notebooks use (readable, about 900 lines) |
| `instructor/` | Facilitator guide, answer key, printable incident cards |
| `extras/GrantGovernance.sol` | Optional Remix demonstration (Solidity) |
| `tests/` | Automated tests for the library |
| `tools/` | Scripts to rebuild the notebooks and to build a JupyterLite site |

## Three ways to run it

**A. On a laptop with Python (simplest for the instructor)**

```
pip install -r requirements.txt
jupyter lab
```

Open `00_setup_check.ipynb` and run it.

**B. Google Colab (participants need only a Google account)**

1. Open colab.research.google.com and upload a notebook.
2. Run the first cell. It asks for `blockchain_wonders.zip`; upload the zip.

**C. JupyterLite (participants need only a browser, no accounts)**

The instructor builds a small website once, before the workshop:

```
bash tools/build_jupyterlite.sh
```

Publish the resulting `site` folder (GitHub Pages or a university web server), or serve it on the room's network with `python -m http.server --directory site 8000`. Participants open the address and find the notebooks and the `wonders` folder already there.

Status: the build script has been run successfully. The built site has not been opened in a browser by the author of this package, so do a trial run on one laptop before the day.

## Requirements

Python 3.9 or newer with `numpy`, `pandas`, `matplotlib`, `scikit-learn`. No GPU, no API keys, no paid services. If scikit-learn is missing, the agents fall back to a built-in rule tree and everything still runs.

## Suggested timing (2-hour hands-on part)

| Minutes | Activity |
|---|---|
| 0 to 30 | 1. Build a Blockchain |
| 30 to 60 | 2. Integrate Deterministic AI Agents |
| 60 to 90 | 3. Implement Smart Governance Rules |
| 90 to 120 | 4. Governance Crisis Challenge (teams) and report-back |

## How the exercises work

Cells marked **Your turn** contain a `# TODO`. Each one is one to four lines of code. Participants who do not program can pair with someone who does, or follow along in `solutions/`.

## Check that everything works

```
python tests/test_wonders.py
```

## A note on the cryptography

The digital signatures are a toy version of RSA with very small keys, generated from each participant's name so that results are repeatable. It shows how signing and verifying work. It is not secure and must not be reused for anything real.
