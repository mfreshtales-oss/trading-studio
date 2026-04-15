"""
agent.py — Autonomous overnight research loop.
Inspired by karpathy/autoresearch.

The agent runs for a single instrument, iteratively improving its strategy:
  1. Reads instruments/{symbol}/program.md (research goals)
  2. Reads current instruments/{symbol}/strategy.py
  3. Reviews recent experiment results from results/{symbol}/
  4. Asks Claude to propose one focused improvement
  5. Applies change, runs backtest.py --symbol {symbol}
  6. Keeps improvement if profit_factor rises; reverts otherwise
  7. Logs to results/{symbol}/experiment_log.json
  8. Repeats until max_iterations or target_profit_factor reached

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python agent.py --symbol XAUUSD
    python agent.py --symbol US30 --iterations 80 --target 2.0
    python agent.py --symbol BTCUSD --iterations 100 --target 3.0
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic

RESEARCH_DIR = Path(__file__).parent
MODEL        = "claude-sonnet-4-6"

ALL_INSTRUMENTS = ["XAUUSD", "US30", "NAS100", "SPX", "BTCUSD"]


# ─────────────────────────────────────────────────────────────
# Symbol-scoped paths
# ─────────────────────────────────────────────────────────────

def get_paths(symbol: str) -> dict[str, Path]:
    instrument_dir = RESEARCH_DIR / "instruments" / symbol
    results_dir    = RESEARCH_DIR / "results"     / symbol
    results_dir.mkdir(parents=True, exist_ok=True)
    return {
        "instrument_dir": instrument_dir,
        "strategy":       instrument_dir / "strategy.py",
        "program":        instrument_dir / "program.md",
        "results_dir":    results_dir,
        "log":            results_dir / "experiment_log.json",
        "best_strategy":  results_dir / "best_strategy.py",
    }


# ─────────────────────────────────────────────────────────────
# I/O helpers
# ─────────────────────────────────────────────────────────────

def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_recent_results(log_path: Path, n: int = 5) -> list[dict]:
    if not log_path.exists():
        return []
    with open(log_path) as f:
        log = json.load(f)
    return log[-n:]


def append_log(log_path: Path, entry: dict) -> None:
    log: list = []
    if log_path.exists():
        with open(log_path) as f:
            log = json.load(f)
    log.append(entry)
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)


def load_strategy_params(strategy_path: Path) -> dict:
    spec = importlib.util.spec_from_file_location("strategy_tmp", strategy_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.STRATEGY_PARAMS


# ─────────────────────────────────────────────────────────────
# Backtest runner
# ─────────────────────────────────────────────────────────────

def run_backtest(symbol: str) -> tuple[dict | None, str | None]:
    result = subprocess.run(
        [sys.executable, str(RESEARCH_DIR / "backtest.py"), "--symbol", symbol],
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
# Prompt builder
# ─────────────────────────────────────────────────────────────

def build_prompt(symbol: str, iteration: int, paths: dict, recent: list[dict]) -> str:
    program  = read_file(paths["program"])
    strategy = read_file(paths["strategy"])

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

    return f"""You are an autonomous trading strategy researcher optimizing a {symbol} strategy.

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
- Add a one-line comment above STRATEGY_PARAMS explaining your hypothesis.

Think step by step:
1. What pattern do you see in the experiment history?
2. What single change is most likely to improve profit_factor for {symbol}?
3. Write the updated strategy.py.
"""


# ─────────────────────────────────────────────────────────────
# Claude call
# ─────────────────────────────────────────────────────────────

def ask_claude(client: anthropic.Anthropic, prompt: str, symbol: str) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=(
            f"You are an expert algorithmic trading researcher specializing in {symbol}. "
            "Always respond with a single ```python … ``` code block containing "
            "the complete updated strategy.py file."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def extract_code(response: str) -> str | None:
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
    if "STRATEGY_PARAMS" in response:
        return response.strip()
    return None


# ─────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────

def main(symbol: str, max_iterations: int = 50, target_profit_factor: float = 2.5) -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    paths = get_paths(symbol)

    if not paths["strategy"].exists():
        print(f"ERROR: Strategy not found: {paths['strategy']}", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print("=" * 62)
    print(f"  AutoResearch — {symbol} Strategy Optimizer")
    print(f"  Model       : {MODEL}")
    print(f"  Max iters   : {max_iterations}")
    print(f"  Target PF   : {target_profit_factor}")
    print(f"  Results     : {paths['results_dir']}")
    print(f"  Started     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 62)

    best_pf       = 0.0
    best_strategy = read_file(paths["strategy"])

    # ── Baseline ─────────────────────────────────────────────
    print(f"\n[baseline] Running baseline backtest for {symbol} …")
    metrics, err = run_backtest(symbol)
    if err:
        print(f"[baseline] ERROR: {err}")
        print(f"           Make sure you ran: python fetch_data.py --symbol {symbol}")
        sys.exit(1)

    best_pf = metrics.get("profit_factor", 0.0)
    print(
        f"[baseline] pf={best_pf}  wr={metrics.get('win_rate')}  "
        f"totalR={metrics.get('total_r')}  trades={metrics.get('total_trades')}"
    )
    append_log(paths["log"], {
        "iteration": 0, "timestamp": datetime.now().isoformat(),
        "params": load_strategy_params(paths["strategy"]),
        "metrics": metrics, "improvement": False, "note": "baseline",
    })

    # ── Research loop ─────────────────────────────────────────
    for iteration in range(1, max_iterations + 1):
        print(f"\n[{iteration:>3}] Asking Claude for {symbol} improvement …")

        recent  = load_recent_results(paths["log"], 5)
        prompt  = build_prompt(symbol, iteration, paths, recent)

        try:
            response = ask_claude(client, prompt, symbol)
        except anthropic.APIError as exc:
            print(f"[{iteration:>3}] Claude API error: {exc} — skipping")
            time.sleep(10)
            continue

        new_code = extract_code(response)
        if not new_code:
            print(f"[{iteration:>3}] Could not extract Python code — skipping")
            continue

        # Backup
        backup = paths["results_dir"] / f"strategy_iter_{iteration:03d}.py"
        shutil.copy(paths["strategy"], backup)

        # Apply
        paths["strategy"].write_text(new_code, encoding="utf-8")

        # Validate
        try:
            params = load_strategy_params(paths["strategy"])
        except Exception as exc:
            print(f"[{iteration:>3}] strategy.py error: {exc} — reverting")
            shutil.copy(backup, paths["strategy"])
            continue

        # Backtest
        print(f"[{iteration:>3}] Backtesting {symbol} …")
        metrics, err = run_backtest(symbol)

        if err or not metrics:
            print(f"[{iteration:>3}] Backtest error: {err} — reverting")
            shutil.copy(backup, paths["strategy"])
            continue

        new_pf   = metrics.get("profit_factor", 0.0)
        improved = new_pf > best_pf
        marker   = "✓ NEW BEST" if improved else "✗"
        print(
            f"[{iteration:>3}] {marker}  pf={new_pf}  (best={best_pf})  "
            f"wr={metrics.get('win_rate')}  totalR={metrics.get('total_r')}  "
            f"trades={metrics.get('total_trades')}"
        )

        append_log(paths["log"], {
            "iteration": iteration, "timestamp": datetime.now().isoformat(),
            "params": params, "metrics": metrics, "improvement": improved,
        })

        if improved:
            best_pf       = new_pf
            best_strategy = new_code
            shutil.copy(paths["strategy"], paths["best_strategy"])
        else:
            paths["strategy"].write_text(best_strategy, encoding="utf-8")

        if best_pf >= target_profit_factor:
            print(f"\n  Target reached! profit_factor={best_pf} >= {target_profit_factor}")
            break

        time.sleep(2)

    # ── Summary ───────────────────────────────────────────────
    print("\n" + "=" * 62)
    print(f"  {symbol} research complete")
    print(f"  Best profit_factor : {best_pf}")
    print(f"  Best strategy      : {paths['best_strategy']}")
    print(f"  Experiment log     : {paths['log']}")
    print(f"  Finished           : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 62)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoResearch overnight strategy optimizer")
    parser.add_argument(
        "--symbol",
        default="XAUUSD",
        choices=ALL_INSTRUMENTS,
        help=f"Instrument to optimize. One of: {ALL_INSTRUMENTS} (default: XAUUSD)",
    )
    parser.add_argument("--iterations", type=int,   default=50,  help="Max iterations (default 50)")
    parser.add_argument("--target",     type=float, default=2.5, help="Target profit_factor (default 2.5)")
    args = parser.parse_args()
    main(symbol=args.symbol, max_iterations=args.iterations, target_profit_factor=args.target)
