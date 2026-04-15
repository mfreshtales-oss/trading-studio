"""
agent.py — Autonomous overnight research loop.
Inspired by karpathy/autoresearch.

The agent:
  1. Reads program.md (your research goals)
  2. Reads current strategy.py
  3. Reviews recent experiment results
  4. Asks Claude to propose a single focused improvement
  5. Applies the change, runs backtest.py
  6. Keeps the improvement if profit_factor goes up; reverts otherwise
  7. Logs everything to results/experiment_log.json
  8. Repeats until max_iterations or target_profit_factor reached

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python agent.py
    python agent.py --iterations 100 --target 2.5
"""

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic

RESEARCH_DIR = Path(__file__).parent
RESULTS_DIR  = RESEARCH_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

STRATEGY_PATH  = RESEARCH_DIR / "strategy.py"
PROGRAM_PATH   = RESEARCH_DIR / "program.md"
LOG_PATH       = RESULTS_DIR  / "experiment_log.json"
BEST_PATH      = RESULTS_DIR  / "best_strategy.py"

MODEL = "claude-sonnet-4-6"


# ─────────────────────────────────────────────────────────────
# I/O helpers
# ─────────────────────────────────────────────────────────────

def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_recent_results(n: int = 5) -> list[dict]:
    if not LOG_PATH.exists():
        return []
    with open(LOG_PATH) as f:
        log = json.load(f)
    return log[-n:]


def append_log(entry: dict) -> None:
    log: list = []
    if LOG_PATH.exists():
        with open(LOG_PATH) as f:
            log = json.load(f)
    log.append(entry)
    with open(LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


def load_strategy_params() -> dict:
    spec = importlib.util.spec_from_file_location("strategy_tmp", STRATEGY_PATH)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.STRATEGY_PARAMS


# ─────────────────────────────────────────────────────────────
# Backtest runner
# ─────────────────────────────────────────────────────────────

def run_backtest() -> tuple[dict | None, str | None]:
    """Run backtest.py. Returns (metrics_dict, error_str)."""
    result = subprocess.run(
        [sys.executable, str(RESEARCH_DIR / "backtest.py")],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(RESEARCH_DIR),
    )
    if result.returncode != 0:
        return None, result.stderr or result.stdout
    try:
        metrics = json.loads(result.stdout)
        return metrics, metrics.get("error")
    except json.JSONDecodeError:
        return None, f"Could not parse backtest output:\n{result.stdout}"


# ─────────────────────────────────────────────────────────────
# Claude prompt builder
# ─────────────────────────────────────────────────────────────

def build_prompt(iteration: int, recent: list[dict]) -> str:
    program  = read_file(PROGRAM_PATH)
    strategy = read_file(STRATEGY_PATH)

    # Summarise experiment history
    if recent:
        best_run = max(recent, key=lambda x: x["metrics"].get("profit_factor", 0))
        best_pf  = best_run["metrics"].get("profit_factor", "N/A")
        history_lines = [
            f"Best profit_factor so far: {best_pf}",
            f"Best params: {json.dumps(best_run['params'], indent=2)}",
            "",
            f"Last {len(recent)} experiment(s):",
        ]
        for r in recent:
            m = r["metrics"]
            improved = "✓" if r.get("improvement") else "✗"
            history_lines.append(
                f"  {improved} iter={r['iteration']:>3}  "
                f"pf={m.get('profit_factor','?'):>6}  "
                f"wr={m.get('win_rate','?'):>5}  "
                f"totalR={m.get('total_r','?'):>6}  "
                f"trades={m.get('total_trades','?')}"
            )
        history = "\n".join(history_lines)
    else:
        history = "No previous experiments — this is iteration 1 (baseline)."

    return f"""You are an autonomous trading strategy researcher optimizing a XAUUSD scalping strategy.

## Research Programme
{program}

## Current strategy.py
```python
{strategy}
```

## Experiment History
{history}

## Your Task — Iteration {iteration}
Make ONE focused, motivated change to improve `profit_factor`.

Rules:
- Return ONLY the complete updated strategy.py file inside a ```python … ``` block.
- Do not add explanatory text outside the code block.
- `rr_ratio` must remain ≥ 5.0 (hard constraint).
- Keep `max_trades_per_day` ≤ 2.
- Do not import new libraries outside the standard library + pandas + numpy.
- Explain your hypothesis as a comment inside the code (one line above STRATEGY_PARAMS).

Think step by step before writing the code:
1. What pattern do you see in the experiment history?
2. What single change is most likely to improve profit_factor?
3. Write the updated strategy.py.
"""


# ─────────────────────────────────────────────────────────────
# Claude call
# ─────────────────────────────────────────────────────────────

def ask_claude(client: anthropic.Anthropic, prompt: str) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=(
            "You are an expert algorithmic trading researcher. "
            "Always respond with a single ```python … ``` code block containing "
            "the complete updated strategy.py file."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def extract_code(response: str) -> str | None:
    """Pull the first ```python ... ``` block from Claude's response."""
    tag = "```python"
    if tag in response:
        start = response.index(tag) + len(tag)
        end   = response.index("```", start)
        return response[start:end].strip()
    if "```" in response:
        start = response.index("```") + 3
        end   = response.index("```", start)
        code  = response[start:end].strip()
        if "STRATEGY_PARAMS" in code:
            return code
    # Fallback: whole response if it looks like Python
    if "STRATEGY_PARAMS" in response:
        return response.strip()
    return None


# ─────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────

def main(max_iterations: int = 50, target_profit_factor: float = 2.5) -> None:
    api_key = __import__("os").environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print("=" * 62)
    print(f"  AutoResearch — XAUUSD Strategy Optimizer")
    print(f"  Model       : {MODEL}")
    print(f"  Max iters   : {max_iterations}")
    print(f"  Target PF   : {target_profit_factor}")
    print(f"  Started     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 62)

    best_pf       = 0.0
    best_strategy = read_file(STRATEGY_PATH)

    # ── Baseline run ──────────────────────────────────────────
    print("\n[baseline] Running baseline backtest …")
    metrics, err = run_backtest()
    if err:
        print(f"[baseline] ERROR: {err}")
        print("           Make sure you ran fetch_data.py first.")
        sys.exit(1)

    best_pf = metrics.get("profit_factor", 0.0)
    print(
        f"[baseline] pf={best_pf}  wr={metrics.get('win_rate')}  "
        f"totalR={metrics.get('total_r')}  trades={metrics.get('total_trades')}"
    )
    append_log({
        "iteration":   0,
        "timestamp":   datetime.now().isoformat(),
        "params":      load_strategy_params(),
        "metrics":     metrics,
        "improvement": False,
        "note":        "baseline",
    })

    # ── Research loop ─────────────────────────────────────────
    for iteration in range(1, max_iterations + 1):
        print(f"\n[{iteration:>3}] Asking Claude for improvement …")

        recent  = load_recent_results(5)
        prompt  = build_prompt(iteration, recent)

        try:
            response = ask_claude(client, prompt)
        except anthropic.APIError as exc:
            print(f"[{iteration:>3}] Claude API error: {exc} — skipping")
            time.sleep(10)
            continue

        new_code = extract_code(response)
        if not new_code:
            print(f"[{iteration:>3}] Could not extract Python code from response — skipping")
            continue

        # Back up current strategy
        backup_path = RESULTS_DIR / f"strategy_iter_{iteration:03d}.py"
        shutil.copy(STRATEGY_PATH, backup_path)

        # Apply new strategy
        STRATEGY_PATH.write_text(new_code, encoding="utf-8")

        # Validate it loads
        try:
            params = load_strategy_params()
        except Exception as exc:
            print(f"[{iteration:>3}] strategy.py syntax/import error: {exc} — reverting")
            shutil.copy(backup_path, STRATEGY_PATH)
            continue

        # Run backtest
        print(f"[{iteration:>3}] Backtesting …")
        metrics, err = run_backtest()

        if err or not metrics:
            print(f"[{iteration:>3}] Backtest error: {err} — reverting")
            shutil.copy(backup_path, STRATEGY_PATH)
            continue

        new_pf     = metrics.get("profit_factor", 0.0)
        improved   = new_pf > best_pf
        symbol     = "✓ NEW BEST" if improved else "✗"
        print(
            f"[{iteration:>3}] {symbol}  pf={new_pf}  (best={best_pf})  "
            f"wr={metrics.get('win_rate')}  totalR={metrics.get('total_r')}  "
            f"trades={metrics.get('total_trades')}"
        )

        append_log({
            "iteration":   iteration,
            "timestamp":   datetime.now().isoformat(),
            "params":      params,
            "metrics":     metrics,
            "improvement": improved,
        })

        if improved:
            best_pf       = new_pf
            best_strategy = new_code
            shutil.copy(STRATEGY_PATH, BEST_PATH)
        else:
            # Revert to previous best
            STRATEGY_PATH.write_text(best_strategy, encoding="utf-8")

        if best_pf >= target_profit_factor:
            print(f"\n  Target reached! profit_factor={best_pf} >= {target_profit_factor}")
            break

        # Rate-limit safety
        time.sleep(2)

    # ── Summary ───────────────────────────────────────────────
    print("\n" + "=" * 62)
    print(f"  Research complete")
    print(f"  Best profit_factor : {best_pf}")
    print(f"  Best strategy      : {BEST_PATH}")
    print(f"  Experiment log     : {LOG_PATH}")
    print(f"  Finished           : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 62)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoResearch overnight strategy optimizer")
    parser.add_argument("--iterations", type=int, default=50, help="Max iterations (default 50)")
    parser.add_argument("--target",     type=float, default=2.5, help="Target profit_factor (default 2.5)")
    args = parser.parse_args()
    main(max_iterations=args.iterations, target_profit_factor=args.target)
