"""Offline evaluation for Module 3: measure real Groq latency, tokens, cost and accuracy.

Run from the module-3-mlops folder (your Groq key must be available as GROQ_API_KEY):

    python -m evaluation.run_eval --limit 3          # quick smoke test, 3 questions
    python -m evaluation.run_eval                    # full run, 15 questions

Every configuration (model x temperature x repeat) becomes one MLflow run through the module's
existing MLflowTracker, and the summary is saved to evaluation/results/ so the Streamlit app can
show it. The public app never calls Groq.
"""
import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.scoring import check_answer, cost_usd, summarize  # noqa: E402

EVAL_DIR = ROOT / "evaluation"
RESULTS_DIR = EVAL_DIR / "results"
QUESTIONS_PATH = EVAL_DIR / "questions.json"

# USD per million tokens (input, output). Groq's list prices change, so check
# https://groq.com/pricing and update these two lines and PRICES_CHECKED before a new run.
PRICES_PER_MILLION = {
    "openai/gpt-oss-120b": (0.15, 0.60),
    "openai/gpt-oss-20b": (0.075, 0.30),
}
PRICES_CHECKED = "2026-11-23"

SYSTEM_PROMPT = "You are a concise assistant. Answer the question directly and briefly."
MAX_RETRIES = 5


def load_api_key():
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key or key.startswith("your_"):
        sys.exit("GROQ_API_KEY is not set. Put it in module-3-mlops/.env or set it in your shell.")
    return key


def create_completion(client, groq_module, model, question, temperature, max_tokens, effort):
    """One chat completion, tolerant of SDK differences."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    use_effort = bool(effort)
    token_arg = "max_completion_tokens"
    for _ in range(3):
        kwargs = {"model": model, "messages": messages, "temperature": temperature, token_arg: max_tokens}
        if use_effort:
            kwargs["extra_body"] = {"reasoning_effort": effort}
        try:
            return client.chat.completions.create(**kwargs)
        except TypeError:
            token_arg = "max_tokens"  # older SDK without max_completion_tokens
        except groq_module.BadRequestError as exc:
            if use_effort and "reasoning" in str(exc).lower():
                use_effort = False  # this model does not accept reasoning_effort
            else:
                raise
    raise RuntimeError("Could not build a valid request for this SDK version")


def timed_call(client, groq_module, model, question, temperature, max_tokens, effort):
    """Return (response, latency_seconds, error_text). Retries rate limits with backoff."""
    delay = 4.0
    last_error = ""
    for attempt in range(1, MAX_RETRIES + 1):
        start = time.perf_counter()
        try:
            resp = create_completion(client, groq_module, model, question, temperature, max_tokens, effort)
            return resp, time.perf_counter() - start, None
        except groq_module.RateLimitError as exc:
            last_error = f"rate limited: {str(exc)[:120]}"
            time.sleep(delay)
            delay = min(delay * 2, 60)
        except (groq_module.APIConnectionError, groq_module.APIStatusError) as exc:
            last_error = f"{type(exc).__name__}: {str(exc)[:120]}"
            if attempt >= 2:
                break
            time.sleep(2)
    return None, 0.0, last_error


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=list(PRICES_PER_MILLION))
    parser.add_argument("--temperatures", nargs="+", type=float, default=[0.0, 0.7])
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--reasoning-effort", default="low", help="low, medium, high, or empty to omit")
    parser.add_argument("--pause", type=float, default=0.5, help="seconds between calls")
    parser.add_argument("--limit", type=int, default=0, help="use only the first N questions (smoke test)")
    parser.add_argument("--experiment", default="llm-agent-v3")
    parser.add_argument("--no-mlflow", action="store_true")
    args = parser.parse_args()

    import groq  # installed with langchain-groq

    client = groq.Groq(api_key=load_api_key())
    data = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    questions = data["questions"][: args.limit or None]
    for model in args.models:
        if model not in PRICES_PER_MILLION:
            sys.exit(f"No price configured for {model}. Add it to PRICES_PER_MILLION.")

    tracker = None
    if not args.no_mlflow:
        from mlflow_tracking.tracker import MLflowTracker
        tracker = MLflowTracker(experiment_name=args.experiment)

    started = datetime.now(timezone.utc)
    run_summaries, detail_rows = [], []

    for model in args.models:
        price_in, price_out = PRICES_PER_MILLION[model]
        for temperature in args.temperatures:
            for repeat in range(1, args.repeats + 1):
                label = f"{model.split('/')[-1]} t={temperature} #{repeat}"
                print(f"\n=== {label}: {len(questions)} questions ===")
                rows = []
                for q in questions:
                    resp, latency, error = timed_call(
                        client, groq, model, q["prompt"], temperature, args.max_tokens, args.reasoning_effort
                    )
                    if error or resp is None:
                        answer, prompt_t, completion_t = "", 0, 0
                    else:
                        answer = resp.choices[0].message.content or ""
                        usage = resp.usage
                        prompt_t = int(getattr(usage, "prompt_tokens", 0) or 0)
                        completion_t = int(getattr(usage, "completion_tokens", 0) or 0)
                    passed = (not error) and check_answer(answer, q["check"])
                    row = {
                        "model": model, "temperature": temperature, "repeat": repeat,
                        "question_id": q["id"], "category": q["category"], "passed": passed,
                        "error": bool(error), "latency_s": round(latency, 3),
                        "prompt_tokens": prompt_t, "completion_tokens": completion_t,
                        "cost_usd": cost_usd(prompt_t, completion_t, price_in, price_out),
                        "answer": " ".join(answer.split())[:300] if not error else f"ERROR: {error}",
                    }
                    rows.append(row)
                    print(f"  {q['id']} {'PASS' if passed else 'FAIL'}  {latency * 1000:6.0f} ms  "
                          f"{completion_t:5d} tokens  {'ERROR ' + error if error else ''}")
                    time.sleep(args.pause)

                metrics = summarize(rows)
                params = {
                    "model": model, "temperature": temperature, "repeat": repeat,
                    "max_completion_tokens": args.max_tokens,
                    "reasoning_effort": args.reasoning_effort or "default",
                    "question_set_version": data["version"], "n_questions": len(questions),
                    "price_in_per_m": price_in, "price_out_per_m": price_out,
                    "prices_checked": PRICES_CHECKED,
                }
                run_id = "-"
                if tracker:
                    run_id = tracker.log_run(
                        params=params,
                        metrics={k: float(v) for k, v in metrics.items()},
                        tags={"source": "measured_groq_eval", "module": "module-3-mlops"},
                    )
                summary = {"run_id": run_id, "label": label, "model": model, "temperature": temperature,
                           "repeat": repeat, **metrics}
                run_summaries.append(summary)
                detail_rows.extend(rows)
                print(f"  -> accuracy {metrics['accuracy']:.1%} | p50 {metrics['latency_ms_p50']:.0f} ms | "
                      f"cost ${metrics['cost_usd_total']:.5f} | errors {metrics['error_count']}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "evaluated_at": started.isoformat(timespec="seconds"),
        "question_set": {"file": "questions.json", "version": data["version"], "n_questions": len(questions)},
        "settings": {"max_completion_tokens": args.max_tokens, "reasoning_effort": args.reasoning_effort or "default",
                     "repeats": args.repeats, "system_prompt": SYSTEM_PROMPT},
        "prices_per_million_usd": {m: {"input": p[0], "output": p[1]} for m, p in PRICES_PER_MILLION.items()},
        "prices_checked": PRICES_CHECKED,
        "groq_sdk": getattr(groq, "__version__", "unknown"),
        "runs": run_summaries,
        "notes": ("Measured against the Groq API from a single machine on a small fixed question set; "
                  "latency includes network time and varies with load. Accuracy is the share of answers "
                  "passing an automatic keyword, regex or number check, so one question is worth "
                  f"{1 / max(len(questions), 1):.1%}."),
    }
    (RESULTS_DIR / "eval_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with open(RESULTS_DIR / "eval_details.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(detail_rows[0].keys()))
        writer.writeheader()
        writer.writerows(detail_rows)
    print(f"\nWrote {RESULTS_DIR / 'eval_results.json'} and eval_details.csv")


if __name__ == "__main__":
    main()