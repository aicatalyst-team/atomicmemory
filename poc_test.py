#!/usr/bin/env python3
"""AutoPoC Test Script for AtomicMemory Core"""
import json, os, sys, time, urllib.request, urllib.error

SERVICE_URL = os.environ.get("SERVICE_URL", sys.argv[1] if len(sys.argv) > 1 else "")
API_KEY = os.environ.get("CORE_API_KEY", "poc-test-api-key-2026")
MAX_RETRIES = 5
RETRY_DELAY = 10
results = []


def test_scenario(name, description, method, path, body=None,
                  expected_status=200, expected_content=None, timeout=30,
                  auth=False):
    url = f"{SERVICE_URL.rstrip('/')}{path}"
    start = time.time()
    for attempt in range(MAX_RETRIES):
        try:
            if body:
                data = json.dumps(body).encode() if isinstance(body, dict) else body.encode()
                req = urllib.request.Request(url, data=data, method=method)
                req.add_header("Content-Type", "application/json")
            else:
                req = urllib.request.Request(url, method=method)
            if auth:
                req.add_header("Authorization", f"Bearer {API_KEY}")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                response_body = resp.read().decode()
                if status == expected_status:
                    if expected_content and expected_content not in response_body:
                        r = {"scenario_name": name, "status": "fail",
                             "output": response_body[:2000],
                             "error_message": f"Expected '{expected_content}' not in response",
                             "duration_seconds": round(time.time()-start, 2)}
                    else:
                        r = {"scenario_name": name, "status": "pass",
                             "output": response_body[:2000], "error_message": None,
                             "duration_seconds": round(time.time()-start, 2)}
                    results.append(r); return r
                elif attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY); continue
                else:
                    r = {"scenario_name": name, "status": "fail",
                         "output": response_body[:2000],
                         "error_message": f"Expected {expected_status}, got {status}",
                         "duration_seconds": round(time.time()-start, 2)}
                    results.append(r); return r
        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode()[:2000]
            except Exception:
                pass
            if e.code == expected_status:
                r = {"scenario_name": name, "status": "pass",
                     "output": body_text, "error_message": None,
                     "duration_seconds": round(time.time()-start, 2)}
                results.append(r); return r
            if attempt < MAX_RETRIES - 1:
                print(f"  Retry {attempt+1}/{MAX_RETRIES}: HTTP {e.code}", file=sys.stderr)
                time.sleep(RETRY_DELAY)
            else:
                r = {"scenario_name": name, "status": "fail", "output": body_text,
                     "error_message": f"HTTP {e.code}: {body_text[:200]}",
                     "duration_seconds": round(time.time()-start, 2)}
                results.append(r); return r
        except urllib.error.URLError as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  Retry {attempt+1}/{MAX_RETRIES}: {e}", file=sys.stderr)
                time.sleep(RETRY_DELAY)
            else:
                r = {"scenario_name": name, "status": "error", "output": "",
                     "error_message": f"Unreachable after {MAX_RETRIES} attempts: {e}",
                     "duration_seconds": round(time.time()-start, 2)}
                results.append(r); return r
        except Exception as e:
            r = {"scenario_name": name, "status": "error", "output": "",
                 "error_message": str(e),
                 "duration_seconds": round(time.time()-start, 2)}
            results.append(r); return r


# === SCENARIOS ===

# Scenario 1: Health Check (unversioned, no auth)
print("Running: health-check", file=sys.stderr)
test_scenario(
    name="health-check",
    description="Verify unversioned health endpoint returns 200 OK",
    method="GET",
    path="/health",
    expected_status=200,
    expected_content="ok",
    timeout=60,
    auth=False
)

# Scenario 2: Memory Health + Config (versioned, auth required)
print("Running: memory-health-config", file=sys.stderr)
test_scenario(
    name="memory-health-config",
    description="Verify versioned memory health endpoint returns config",
    method="GET",
    path="/v1/memories/health",
    expected_status=200,
    expected_content="ok",
    timeout=30,
    auth=True
)

# Scenario 3: Memory Stats (versioned, auth required)
print("Running: memory-stats", file=sys.stderr)
test_scenario(
    name="memory-stats",
    description="Verify memory stats endpoint works",
    method="GET",
    path="/v1/memories/stats?user_id=poc-test-user",
    expected_status=200,
    timeout=30,
    auth=True
)

# === END SCENARIOS ===

print(json.dumps({"results": results}, indent=2))
sys.exit(1 if any(r["status"] in ("fail", "error") for r in results) else 0)
