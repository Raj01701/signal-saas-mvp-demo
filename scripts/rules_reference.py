"""Write the rule-language function reference into ``knowledge/README.md``.

The table between the ``functions`` markers is generated from the docstrings in
``jyotish_engine.rules.dsl.FUNCTIONS``, so the guide never drifts from the code.

    uv run python scripts/rules_reference.py
"""

from __future__ import annotations

from pathlib import Path

from jyotish_engine.rules.dsl import FUNCTIONS

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "knowledge" / "README.md"
START, END = "<!-- functions:start -->", "<!-- functions:end -->"


def table() -> str:
    rows = ["| Function | Arguments | Meaning |", "|---|---|---|"]
    for name, function in FUNCTIONS.items():
        counts = " or ".join(str(n) for n in function.arities)
        rows.append(f"| `{name}` | {counts} | {function.doc} |")
    return "\n".join(rows)


def main() -> None:
    text = README.read_text(encoding="utf-8")
    before, rest = text.split(START)
    _, after = rest.split(END)
    README.write_text(f"{before}{START}\n{table()}\n{END}{after}", encoding="utf-8")
    print(f"wrote {len(FUNCTIONS)} functions to {README.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
