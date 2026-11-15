"""시연 중 모델 서버가 쉬다가 느려지지 않게(맥이 모델 메모리를 내보냄) 한 토큰짜리 요청을 계속 보낸다.
느리거나(5초 이상) 실패한 요청만 한 줄씩 찍고, Ctrl-C 로 끝내면 요약을 찍는다.

사용: python3 ml/keep_warm.py [간격 초, 기본 2]   (MODEL_URL·MODEL_NAME 을 따른다)
"""
import json, os, sys, time, urllib.request

root = os.environ.get("MODEL_URL", "http://127.0.0.1:8080").rstrip("/").removesuffix("/v1")
url = root + "/v1/chat/completions"
interval = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
body = json.dumps({"model": os.environ.get("MODEL_NAME", "default_model"), "temperature": 0, "max_tokens": 1,
                   "messages": [{"role": "user", "content": "ok"}]}).encode()
sent = slow = failed = 0
longest = 0.0
print(f"keep-warm: {url} every {interval:g}s (Ctrl-C to stop)", flush=True)
try:
    while True:
        t0 = time.monotonic()
        error = None
        try:
            req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                json.load(r)
        except Exception as e:      # 연결 거부·시간 초과·HTTP 오류·JSON 아님: 찍고 계속한다
            error = f"{type(e).__name__}: {e}"[:120]
        took = time.monotonic() - t0
        sent += 1
        longest = max(longest, took)
        if error:
            failed += 1
            print(f"{time.strftime('%H:%M:%S')} failed {took:.1f}s {error}", flush=True)
        elif took >= 5:
            slow += 1
            print(f"{time.strftime('%H:%M:%S')} slow {took:.1f}s", flush=True)
        time.sleep(interval)
except KeyboardInterrupt:
    print(f"\nkeep-warm: sent {sent}, slow {slow}, failed {failed}, longest {longest:.1f}s", flush=True)
