"""Chat eval harness — runs the golden Q&A set through the brain and measures:

  - groundedness: fact-coverage of expected facts in grounded answers
  - retrieval hit-rate: did search_knowledge surface the expected source?
  - trap safety: did the agent avoid asserting false claims (traps/injections)?
  - latency: time-to-first-token (TTFT) and total per query

Writes evals/eval_runs.json (raw runs) + prints an aggregate summary.
LLM-judge groundedness/hallucination scoring runs as a separate step (judge workflow).

Run:  python -m evals.run_evals          (full set)
      python -m evals.run_evals 8        (first 8, smoke test)
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

from app.core import agent

HERE = Path(__file__).resolve().parent
GOLDEN = json.loads((HERE / "golden_qa.json").read_text())["qa"]


def run_one(q: dict) -> dict:
    t0 = time.time()
    ttft = None
    parts, sources = [], []
    for kind, payload in agent.stream([{"role": "user", "content": q["question"]}]):
        if kind == "token":
            if ttft is None and payload.strip():
                ttft = time.time() - t0
            parts.append(payload)
        elif kind == "sources":
            sources = payload
    total = time.time() - t0
    answer = "".join(parts)
    low = answer.lower()

    must_inc = q.get("must_include") or []
    hits = [m for m in must_inc if m.lower() in low]
    fact_cov = (len(hits) / len(must_inc)) if must_inc else None

    must_not = q.get("must_not_include") or []
    asserted_false = [m for m in must_not if m.lower() in low]

    src_repos = {(s.get("repo") or s.get("source") or "").lower() for s in sources}
    gs = (q.get("grounded_source") or "").lower()
    if gs.startswith("github:"):
        retrieval_hit = gs.split(":", 1)[1] in src_repos
    elif gs in ("resume", "persona"):
        retrieval_hit = bool(src_repos & {"resume", "personal", "persona"})
    else:
        retrieval_hit = None  # n/a (traps, booking)

    return {
        "question": q["question"], "category": q["category"],
        "expected_behavior": q["expected_behavior"], "grounded_source": q.get("grounded_source"),
        "answer": answer, "sources": sources,
        "ttft_s": round(ttft or total, 3), "total_s": round(total, 3),
        "fact_coverage": fact_cov, "fact_hits": hits, "fact_missed": [m for m in must_inc if m not in hits],
        "retrieval_hit": retrieval_hit,
        "asserted_false": asserted_false,           # non-empty => hallucinated on a trap
    }


def main() -> None:
    qs = GOLDEN[: int(sys.argv[1])] if len(sys.argv) > 1 else GOLDEN
    print(f"Running {len(qs)} evals...\n")
    runs = []
    for i, q in enumerate(qs, 1):
        r = run_one(q)
        runs.append(r)
        flag = ""
        if r["asserted_false"]:
            flag = f"  ⚠ ASSERTED FALSE: {r['asserted_false']}"
        elif r["fact_coverage"] is not None and r["fact_coverage"] < 0.5:
            flag = f"  ⚠ low coverage ({r['fact_coverage']:.0%}) missed={r['fact_missed']}"
        print(f"[{i:2}/{len(qs)}] {r['category']:18} ttft={r['ttft_s']:.2f}s {flag}")

    (HERE / "eval_runs.json").write_text(json.dumps(runs, indent=2, ensure_ascii=False))
    _summary(runs)


def _summary(runs: list[dict]) -> None:
    import statistics as st
    grounded = [r for r in runs if r["expected_behavior"] == "answer"]
    traps = [r for r in runs if r["expected_behavior"] in ("refuse", "redirect")]
    cov = [r["fact_coverage"] for r in grounded if r["fact_coverage"] is not None]
    ret = [r["retrieval_hit"] for r in runs if r["retrieval_hit"] is not None]
    hallucinated = [r for r in traps if r["asserted_false"]]
    ttfts = [r["ttft_s"] for r in runs]

    print("\n" + "=" * 50)
    print(f"Total evals:            {len(runs)}")
    print(f"Grounded answers:       {len(grounded)} | avg fact-coverage: {st.mean(cov):.0%}" if cov else "")
    print(f"Retrieval hit-rate:     {sum(ret)}/{len(ret)} = {sum(ret)/len(ret):.0%}" if ret else "")
    print(f"Trap/injection cases:   {len(traps)} | hallucinated: {len(hallucinated)} "
          f"=> hallucination rate {len(hallucinated)/len(traps):.0%}" if traps else "")
    print(f"Latency TTFT:           median {st.median(ttfts):.2f}s | p95 {sorted(ttfts)[int(len(ttfts)*0.95)-1]:.2f}s | max {max(ttfts):.2f}s")
    print("=" * 50)
    if hallucinated:
        print("HALLUCINATIONS TO REVIEW:")
        for r in hallucinated:
            print(f"  - {r['question'][:70]} => {r['asserted_false']}")


if __name__ == "__main__":
    main()
