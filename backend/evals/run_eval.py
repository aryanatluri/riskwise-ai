"""Measure the engine against hand-labelled contracts.

    python -m evals.run_eval              # rules-only
    LLM_PROVIDER=gemini LLM_MODEL=... LLM_API_KEY=... python -m evals.run_eval   # hybrid, on YOUR key

Use only synthetic or anonymised contracts here. Each case is <name>.txt plus
<name>.expected.json listing the policy rule codes that should be flagged.
Run it on every engine change and watch precision and recall.
"""

import json
import os
import sys
from pathlib import Path

from app.engine.analyzer import analyze_text
from app.engine.llm import LLMClient, LLMConfig
from app.engine.packs import DEFAULT_PACKS, default_policy_rules
from app.engine.rules import RuleView

CASES = Path(__file__).parent / "cases"
KEYS = ("code", "title", "domain", "mandate", "criticality", "constraints", "redline_template")


def main() -> int:
    llm = None
    if os.getenv("LLM_PROVIDER"):
        llm = LLMClient(
            LLMConfig(
                os.environ["LLM_PROVIDER"],
                os.environ["LLM_MODEL"],
                os.environ["LLM_API_KEY"],
                os.getenv("LLM_ENDPOINT"),
                os.getenv("LLM_API_VERSION"),
            )
        )
    tp = fp = fn = 0
    for txt in sorted(CASES.glob("*.txt")):
        spec = json.loads(txt.with_suffix(".expected.json").read_text())
        rules = [RuleView(**{k: r[k] for k in KEYS}) for r in default_policy_rules(spec["jurisdiction"])]
        res = analyze_text(txt.read_text(), rules, DEFAULT_PACKS[spec["jurisdiction"]], llm)
        got = {h.rule_code for h in res.hits if h.rule_code}
        want = set(spec["expected"])
        tp += len(got & want)
        fp += len(got - want)
        fn += len(want - got)
        status = "ok " if got == want else "DIFF"
        print(f"{status} {txt.stem:28} missed={sorted(want - got)} extra={sorted(got - want)}")
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    mode = "hybrid" if llm else "rules"
    print(f"\nprecision={precision:.2f} recall={recall:.2f}  (tp={tp} fp={fp} fn={fn}) mode={mode}")
    return 0 if fp == 0 and fn == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
