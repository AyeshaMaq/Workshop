"""
wonders.viz - small pictures for the notebooks (matplotlib only).
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

INK, GOOD, BAD, SOFT = "#1f2a44", "#2a9d8f", "#d1495b", "#eef1f6"


def draw_chain(chain, title="The ledger", max_blocks=8):
    """Draw the last blocks as linked boxes. Broken blocks turn red."""
    blocks = chain.chain[-max_blocks:]
    target = "0" * chain.difficulty
    fig, ax = plt.subplots(figsize=(min(2.6 * len(blocks), 16), 2.6))
    for i, b in enumerate(blocks):
        pos = chain.chain.index(b)
        prev_ok = pos == 0 or b.previous_hash == chain.chain[pos - 1].hash
        ok = b.hash == b.compute_hash() and b.hash.startswith(target) and prev_ok
        colour = GOOD if ok else BAD
        ax.add_patch(FancyBboxPatch((i * 2.6, 0), 2.1, 1.7, boxstyle="round,pad=0.04",
                                    facecolor=SOFT, edgecolor=colour, linewidth=2.5))
        ax.text(i * 2.6 + 1.05, 1.42, f"Block {b.index}", ha="center", weight="bold", color=INK)
        ax.text(i * 2.6 + 1.05, 1.02, f"{len(b.transactions)} record(s)", ha="center",
                color=INK, fontsize=9)
        ax.text(i * 2.6 + 1.05, 0.62, f"prev {b.previous_hash[:8]}", ha="center",
                family="monospace", fontsize=8, color=INK if prev_ok else BAD)
        ax.text(i * 2.6 + 1.05, 0.26, f"hash {b.compute_hash()[:8]}", ha="center",
                family="monospace", fontsize=8, color=colour)
        if i:
            ax.annotate("", xy=(i * 2.6 - 0.04, 0.85), xytext=(i * 2.6 - 0.46, 0.85),
                        arrowprops=dict(arrowstyle="->", color=INK, lw=1.5))
    ax.set_xlim(-0.2, len(blocks) * 2.6)
    ax.set_ylim(-0.2, 2.0)
    ax.axis("off")
    ax.set_title(title, loc="left", color=INK, weight="bold")
    plt.show()


def draw_explanation(decision):
    """Bar chart: how much each feature pushed the decision up or down."""
    e = decision["explanation"]
    items = sorted(e["contributions"].items(), key=lambda kv: kv[1])
    if not items:
        print("The model did not need to ask any question for this decision.")
        return
    names, values = zip(*items)
    fig, ax = plt.subplots(figsize=(7, 0.55 * len(items) + 1.4))
    ax.barh(names, values, color=[GOOD if v > 0 else BAD for v in values])
    ax.axvline(0, color=INK, lw=1)
    ax.set_xlabel("change in approval chance")
    ax.set_title(f"{decision['application_id']}: {decision['decision']} by {decision['agent_id']}  "
                 f"(baseline {e['baseline_p_approve']:.0%} -> final {e['final_p_approve']:.0%})",
                 loc="left", fontsize=10, color=INK, weight="bold")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    plt.tight_layout()
    plt.show()


def draw_mining(results):
    """results: list of (difficulty, attempts)."""
    d, a = zip(*results)
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar([str(x) for x in d], a, color=INK)
    ax.set_yscale("log")
    ax.set_xlabel("difficulty (leading zeros required)")
    ax.set_ylabel("attempts (log scale)")
    ax.set_title("Each extra zero costs about 16x more work", loc="left",
                 color=INK, weight="bold", fontsize=10)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    plt.tight_layout()
    plt.show()


def draw_scorecard(rows):
    fig, ax = plt.subplots(figsize=(7, 0.42 * len(rows) + 0.8))
    labels = [r["test"] for r in rows][::-1]
    colours = [GOOD if r["passed"] else BAD for r in rows][::-1]
    ax.barh(labels, [1] * len(rows), color=colours)
    ax.set_xticks([])
    ax.set_title(f"Governance scorecard: {sum(r['passed'] for r in rows)} / {len(rows)}",
                 loc="left", color=INK, weight="bold")
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)
    plt.tight_layout()
    plt.show()
