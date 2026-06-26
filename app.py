#!/usr/bin/env python3
"""
Gauntlet — Daily Boss Run

A mobile-first, juicy retrieval-practice game for studying a certification exam.
First content: the Claude Certified Architect — Foundations (CCA-F) exam.

Design (governing rule, from the engagement research): every reward fires ONLY on a
successful effortful RETRIEVAL of a due item — never on time-on-app or passive review.
The game IS the retrieval. The north-star "Exam Readiness %" moves only when an item
graduates a spacing box on genuine recall.

Stack: pure Python stdlib http.server + a single-page front end (index.html) + an item
bank (items.json). The ONLY external call is AI grading of free-text "explain-back"
answers, routed to an OpenAI-compatible endpoint. If grading is slow or unavailable,
the server falls back to a keyword-overlap heuristic so the loop never stalls.

Run:  python3 app.py            (binds 0.0.0.0:8090 by default)
Env:
  GAUNTLET_PORT        port (default 8090)
  GAUNTLET_GRADER_MODEL  model for explain-back grading (default gpt-oss:120b)
  GAUNTLET_TOKEN       optional shared secret; if set, the page requires ?t=<token>
  OLLAMA_API_KEY       API key for the OpenAI-compatible grading endpoint
  OLLAMA_BASE_URL      base URL for the grading endpoint
                       (default https://ollama.com/v1/chat/completions)
"""
import json
import os
import re
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
ITEMS_PATH = ROOT / "items.json"
INDEX_PATH = ROOT / "index.html"
RUNS_DIR = ROOT / "runs"
PORT = int(os.environ.get("GAUNTLET_PORT", "8090"))
GRADER_MODEL = os.environ.get("GAUNTLET_GRADER_MODEL", "gpt-oss:120b")
TOKEN = os.environ.get("GAUNTLET_TOKEN", "").strip()
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "https://ollama.com/v1/chat/completions")

OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "").strip()
if not OLLAMA_KEY:
    print("[gauntlet] WARN: OLLAMA_API_KEY not set — explain-back will use the heuristic fallback only.", file=sys.stderr)


def heuristic_grade(user_text: str, rubric: list[str], answer: str) -> dict:
    """Cheap, instant fallback: how many rubric key-points does the answer touch?
    Used when AI grading is unavailable/slow so the loop never stalls."""
    u = re.sub(r"[^a-z0-9 ]", " ", (user_text or "").lower())
    u_words = set(w for w in u.split() if len(w) > 2)
    hits = 0
    for point in rubric:
        # a point is "hit" if a meaningful word from it appears in the user's answer
        p_words = [w for w in re.sub(r"[^a-z0-9 ]", " ", point.lower()).split() if len(w) > 3]
        if any(w in u_words for w in p_words):
            hits += 1
    frac = hits / max(1, len(rubric))
    score = round(frac, 2)
    if score >= 0.6:
        verdict, correct = "nailed", True
    elif score >= 0.3:
        verdict, correct = "partial", True
    else:
        verdict, correct = "missed", False
    note = f"You touched {hits}/{len(rubric)} key points." if user_text.strip() else "No answer entered."
    return {"correct": correct, "score": score, "verdict": verdict,
            "feedback": note, "grader": "heuristic"}


def ai_grade(prompt: str, user_text: str, answer: str, rubric: list[str]) -> dict:
    """Grade a free-text explain-back answer via an OpenAI-compatible endpoint. Returns a strict dict.
    Falls back to the heuristic on any error/timeout so the loop never blocks."""
    if not OLLAMA_KEY or not user_text.strip():
        return heuristic_grade(user_text, rubric, answer)
    rubric_str = "\n".join(f"- {p}" for p in rubric)
    sys_prompt = (
        "You are a fast, fair exam-prep grader for the Claude Certified Architect exam. "
        "You grade a student's free-text 'explain-back' answer against a rubric of key points. "
        "Be encouraging but honest. Reply with ONLY a compact JSON object, no prose, no markdown:\n"
        '{"verdict":"nailed"|"partial"|"missed","score":<0.0-1.0>,"feedback":"<one short sentence, max 22 words>"}\n'
        "verdict 'nailed' = covers most key points; 'partial' = some; 'missed' = few/none or wrong. "
        "feedback names the single most useful thing they got right or the key point they missed."
    )
    user_msg = (
        f"QUESTION:\n{prompt}\n\nKEY POINTS (rubric):\n{rubric_str}\n\n"
        f"MODEL ANSWER (reference):\n{answer}\n\nSTUDENT ANSWER:\n{user_text}\n\n"
        "Grade now. JSON only."
    )
    body = {
        "model": GRADER_MODEL,
        "messages": [{"role": "system", "content": sys_prompt},
                     {"role": "user", "content": user_msg}],
        "temperature": 0.2,
    }
    try:
        req = urllib.request.Request(
            OLLAMA_URL, data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {OLLAMA_KEY}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        content = data["choices"][0]["message"].get("content") or ""
        m = re.search(r"\{[\s\S]*\}", content)
        parsed = json.loads(m.group(0)) if m else {}
        verdict = parsed.get("verdict", "partial")
        if verdict not in ("nailed", "partial", "missed"):
            verdict = "partial"
        score = float(parsed.get("score", 0.5))
        score = max(0.0, min(1.0, score))
        feedback = str(parsed.get("feedback", "")).strip()[:200] or "Reviewed."
        return {"correct": verdict in ("nailed", "partial"), "score": round(score, 2),
                "verdict": verdict, "feedback": feedback, "grader": GRADER_MODEL}
    except Exception as e:  # noqa: BLE001
        print(f"[ai_grade fallback] {e}", file=sys.stderr)
        return heuristic_grade(user_text, rubric, answer)


def load_items() -> dict:
    return json.loads(ITEMS_PATH.read_text())


def log_run(summary: dict) -> None:
    """Append a finished-run summary to a daily JSONL — a durable record of runs."""
    try:
        RUNS_DIR.mkdir(exist_ok=True)
        now = datetime.now(timezone.utc)
        rec = {"ts": now.isoformat(), **summary}
        with open(RUNS_DIR / f"{now.strftime('%Y-%m-%d')}.jsonl", "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception as e:  # noqa: BLE001
        print(f"[log_run error] {e}", file=sys.stderr)


def authed(path: str) -> bool:
    if not TOKEN:
        return True
    return f"t={TOKEN}" in path


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quieter logs
        return

    def _send(self, code, body, ctype="application/json"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            if not authed(self.path):
                self._send(401, "Unauthorized — append ?t=<token> to the URL.", "text/plain")
                return
            self._send(200, INDEX_HTML, "text/html; charset=utf-8")
        elif self.path.startswith("/api/items"):
            try:
                self._send(200, json.dumps(load_items()))
            except Exception as e:  # noqa: BLE001
                self._send(500, json.dumps({"error": str(e)}))
        elif self.path == "/health":
            self._send(200, json.dumps({"ok": True, "grader": GRADER_MODEL, "key": bool(OLLAMA_KEY)}))
        elif self.path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(n) or "{}")
        except Exception as e:  # noqa: BLE001
            self._send(400, json.dumps({"error": f"bad request: {e}"}))
            return
        if self.path == "/api/grade":
            result = ai_grade(payload.get("prompt", ""), payload.get("user_text", ""),
                              payload.get("answer", ""), payload.get("rubric", []) or [])
            self._send(200, json.dumps(result))
        elif self.path == "/api/log":
            log_run(payload)
            self._send(200, json.dumps({"ok": True}))
        else:
            self._send(404, json.dumps({"error": "not found"}))


# index.html is read once at startup (served from disk so content edits don't need a code change).
INDEX_HTML = INDEX_PATH.read_text() if INDEX_PATH.exists() else "<h1>index.html missing</h1>"


if __name__ == "__main__":
    items = load_items()
    print(f"[gauntlet] {len(items['items'])} items across {len(items['exam']['domains'])} domains; "
          f"grader={GRADER_MODEL}; token={'on' if TOKEN else 'off'}", file=sys.stderr)
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[gauntlet] serving on 0.0.0.0:{PORT}", file=sys.stderr)
    srv.serve_forever()
