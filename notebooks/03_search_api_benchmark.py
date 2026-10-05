# ---
# jupyter:
#   jupytext:
#     formats: py:percent
# ---

# %% [markdown]
# # NB3 — FastAPI `/search` Endpoint + Latency Benchmark
#
# **Stack:** FastAPI + uvicorn + httpx (client). Searcher từ `app/search.py`.
# Maps to slide §7 (Production Patterns) + deliverable bullets 1, 4.
#
# > Mục tiêu: bọc `Searcher` thành REST API, đo P50/P95/P99 latency, đảm bảo
# > P99 < 50 ms cho hybrid mode (rubric threshold).

# %%
import _setup  # noqa: F401
import json
import time
from pathlib import Path

import httpx
from app.main import SearchResponse
from scripts.notebook_api import running_search_api

ROOT = Path(_setup.__file__).resolve().parent.parent
DATA = ROOT / "data"
golden = [json.loads(line) for line in (DATA / "golden_set.jsonl").open(encoding="utf-8")]

# %% [markdown]
# ## 1. Hàm đo độ trễ
#
# Đo 50 golden queries × 2 reps = 100 calls/mode, sau 10 warmup calls.
# Server-side `latency_ms` gồm embedding và retrieval; wall-clock gồm HTTP.

# %%
def percentile(values: list[float], p: float) -> float:
    n = len(values)
    if n == 0:
        return 0.0
    return sorted(values)[min(int(n * p), n - 1)]


def benchmark_mode(mode: str, reps: int = 2) -> dict[str, float]:
    server_latencies: list[float] = []
    wall_latencies: list[float] = []
    with httpx.Client(base_url=URL, timeout=30.0) as http:
        # Warm the full retrieval path; every measured call still embeds its query.
        for q in golden[:10]:
            http.get("/search", params={"q": q["query"], "mode": mode}).raise_for_status()
        for _ in range(reps):
            for q in golden:
                t0 = time.perf_counter()
                r = http.get("/search", params={"q": q["query"], "mode": mode})
                r.raise_for_status()
                wall_latencies.append((time.perf_counter() - t0) * 1000)
                server_latencies.append(r.json()["latency_ms"])
    return {
        "p50_server": percentile(server_latencies, 0.50),
        "p95_server": percentile(server_latencies, 0.95),
        "p99_server": percentile(server_latencies, 0.99),
        "p99_wall":   percentile(wall_latencies, 0.99),
    }


# %% [markdown]
# ## 2. API response, benchmark và rubric assertion
#
# Notebook chọn cổng trống, chờ `/healthz` ready và kiểm tra SearchResponse.
# Toàn bộ request và assertion nằm trong cùng context manager: server được
# dừng cả khi response sai, HTTP lỗi hoặc benchmark không đạt P99 < 50 ms.
# Không dừng API do người dùng mở ở terminal riêng.

# %%
with running_search_api(ROOT) as URL:
    print(httpx.get(f"{URL}/healthz").json())
    r = httpx.get(f"{URL}/search", params={"q": "cloud computing tự động mở rộng", "mode": "hybrid"})
    r.raise_for_status()
    body = r.json()
    SearchResponse.model_validate(body)
    print({k: v for k, v in body.items() if k != "hits"})
    print(f"latency_ms: {body['latency_ms']:.1f}")
    print(f"top-3 hits:")
    for h in body["hits"][:3]:
        print(f"  {h['doc_id']:>14}  score={h['score']:.4f}  {h['title']}")

    print("10 warmup calls + 100 measured calls per mode; server-side includes embedding.")
    print(f"  {'mode':10}  {'P50':>7}  {'P95':>7}  {'P99':>7}  {'P99(wall)':>9}")
    results = {}
    for mode in ("keyword", "semantic", "hybrid"):
        res = benchmark_mode(mode)
        results[mode] = res
        print(f"  {mode:10}  {res['p50_server']:>5.1f}ms  {res['p95_server']:>5.1f}ms  "
              f"{res['p99_server']:>5.1f}ms  {res['p99_wall']:>7.1f}ms")

    hybrid_p99 = results["hybrid"]["p99_server"]
    print(f"Hybrid P99 server-side: {hybrid_p99:.1f}ms")
    if hybrid_p99 < 50:
        print(f"PASS — hybrid P99 < 50ms ({hybrid_p99:.1f}ms)")
    else:
        print(f"WARN — hybrid P99 >= 50ms ({hybrid_p99:.1f}ms)")
        print("  Possible causes: cold cache, fastembed model not warm yet, or RRF depth=50 is too aggressive")
        print("  Check: re-run benchmark after 10 warm-up queries; or reduce RRF depth")

    assert hybrid_p99 < 50, f"Hybrid P99 {hybrid_p99:.1f}ms exceeds the 50ms rubric limit"

# %% [markdown]
# ## Deliverable evidence
#
# 1. Output §2: 1 single hybrid query response with `top-3 hits`.
# 2. Output §2: latency table P50/P95/P99 for keyword/semantic/hybrid.
# 3. Output §2: hybrid P99 < 50ms PASS.
#
# ---
#
# ## Vibe-coding callout
#
# **Delegate freely:** the FastAPI scaffolding (route definition, Pydantic
# response model, lifespan handler). AI generates this perfectly given the
# spec "GET /search?q=str&mode=Literal[...] returning SearchResponse with
# latency_ms field". `app/main.py` is exactly that pattern — review the diff,
# don't write it from scratch.
#
# **Think hard yourself:** *what to measure*. Server-side latency vs wall-clock
# vs client-side. P50 vs P95 vs P99. Cold vs warm. Single user vs concurrent.
# These are *judgement* decisions: nếu rubric chỉ check P99, optimization sẽ
# hướng vào tail latency, không phải mean. Đừng nhờ AI quyết định metric —
# chỉ nhờ implement metric đã chọn.
