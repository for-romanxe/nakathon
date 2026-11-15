"""우주선 조정 이유(pipeline.adjustment_reason, 이슈 #47)를 실제 모델로 잰다.

입력은 데모 승무원 측정값 모양(ml/eval/v2/serving_findings.json)에서 수면·심박변이·심박만 바꾼 것이다.
temperature 0 이라 같은 입력은 같은 답이 나오므로, 반복하지 않고 입력을 바꿔 가며 잰다(대상 2 × 언어 2 × 입력 6).
근거는 ml/knowledge/export_evidence.py 가 만드는 파일과 같은 목록을 쓴다.

사용: MODEL=live python3 ml/eval/run_adjustment.py   → ml/eval/results/v2-adjustment-reason.json
"""
import json, os, pathlib, statistics, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml" / "knowledge"))
os.environ.setdefault("MODEL", "live")
import export_evidence      # noqa: E402
from backend.model import pipeline      # noqa: E402

BASE = json.loads((ROOT / "ml" / "eval" / "v2" / "serving_findings.json").read_text(encoding="utf-8"))
# (수면 시간, 수면 기준선, 수면 표준편차, 심박변이 z, 심박 z, 규칙 단계). 첫 줄이 #47 시연 수치 초안(수면 5.1h, 심박변이 -2.5)
INPUTS = [(5.1, 7.0, 0.75, -2.5, 0.0, "caution"), (6.75, 7.5, 0.3, -2.0, 2.5, "caution"), (4.6, 7.2, 0.8, -3.0, 1.2, "caution"),
          (5.8, 7.4, 0.8, 0.0, 0.0, "advisory"), (4.9, 6.9, 0.7, -2.2, 2.1, "caution"), (6.6, 7.5, 0.3, -3.4, 0.4, "advisory")]


def findings(sleep, base, sd, hrv_z, hr_z, level):
    rows = json.loads(json.dumps(BASE))
    for row in rows:
        z = {"sleep": (sleep - base) / sd, "hrv": hrv_z, "hr": hr_z}.get(row["metric"])
        if z is None:
            continue
        if row["metric"] == "sleep":
            row.update(value=sleep, baseline=base, sd=sd)
        else:
            row["value"] = round(row["baseline"] + z * row["sd"], 1)
        row.update(z=z, level=level if abs(z) >= 2 else "normal")
    return rows


def wait_for_server(seconds=240):
    url = os.environ.get("MODEL_URL", "http://127.0.0.1:8080").rstrip("/").removesuffix("/v1") + "/v1/models"
    for _ in range(seconds // 3):
        try:
            urllib.request.urlopen(url, timeout=3).read()
            return
        except OSError:
            time.sleep(3)
    sys.exit(f"model server not reachable at {url} after {seconds}s; start it first (backend/model/README.md)")


wait_for_server()
rows = []
for lang in ("ko", "en"):
    evidence = export_evidence.export(lang)
    for target in ("lighting", "schedule"):
        for n, case in enumerate(INPUTS, 1):
            start = time.time()
            got = pipeline.adjustment_reason(target, case[5], findings(*case), evidence, lang)
            rows.append({"lang": lang, "target": target, "input": n, "level": case[5], "seconds": round(time.time() - start, 1),
                         "hold": got["hold"], "verified": got["verified"], "reason": got["reason"], "cite_ids": got["cite_ids"],
                         "runs": got["runs"]})
            print(f"{lang} {target} #{n} {rows[-1]['seconds']}s hold={got['hold']} runs={[r['fails'] for r in got['runs']]} | {got['reason']}", flush=True)

first = sum(r["runs"][0]["ok"] for r in rows)
done = sum(not r["hold"] for r in rows)
secs = [r["seconds"] for r in rows[1:]]      # 첫 요청은 모델을 올리는 시간이 섞인다
summary = {"cases": len(rows), "passed_first_run": first, "passed_within_two_runs": done, "held": len(rows) - done,
           "distinct_reasons": len({r["reason"] for r in rows if r["reason"]}),
           "first_request_seconds": rows[0]["seconds"], "median_seconds": statistics.median(secs), "max_seconds": max(secs)}
out = ROOT / "ml" / "eval" / "results" / "v2-adjustment-reason.json"
out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False))
