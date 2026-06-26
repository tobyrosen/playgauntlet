# Gauntlet

A gamified daily retrieval-practice study app. The exam is the final boss. Each correct recall chips its health down.

## The Daily Boss Run

Every session is a "Daily Boss Run" — 12 items drawn from your weakest clusters, served in the optimal spacing order. One north-star metric: **Exam Readiness %**, which moves only when you successfully retrieve a spaced-due item. That's the whole game.

## Design philosophy

Every reward is tied to successful effortful **retrieval** of a spaced-due item — never to time-on-app, opens, or passive review. Specifically:

- Readiness % only moves on genuine recall (box advances on the Leitner scale)
- Correct answers give points, combo multipliers, and confetti; misses give a bonus re-review of the item later that same run
- Beat your own ghost: yesterday's score is shown at start; beat it
- Streaks are forgiving — a small freeze reserve saves your streak on missed days

What Gauntlet deliberately avoids: time-based XP, hearts/lives that punish learning, public leaderboards, and engagement tricks that reward opens rather than recall.

## Running

```
python3 app.py
```

Open `http://localhost:8090` (or the Tailscale/LAN address of the machine running it).

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `GAUNTLET_PORT` | `8090` | Port to bind |
| `OLLAMA_API_KEY` | *(required for AI grading)* | API key for the OpenAI-compatible grading endpoint |
| `OLLAMA_BASE_URL` | `https://ollama.com/v1/chat/completions` | Grading endpoint base URL |
| `GAUNTLET_GRADER_MODEL` | `gpt-oss:120b` | Model used to grade free-text explain-back answers |
| `GAUNTLET_TOKEN` | *(unset = open)* | Optional shared secret; if set, the page requires `?t=<token>` in the URL |

AI grading is used only for `explain`-format items (free-text "explain it in your own words"). If `OLLAMA_API_KEY` is not set, or if the grading endpoint is slow/unavailable, the server falls back instantly to a keyword-overlap heuristic so the loop never stalls.

## Content: items.json

The item bank is content-agnostic. The first deck covers the **Claude Certified Architect — Foundations (CCA-F)** exam (60 scenario-based multiple-choice questions, 120 minutes, 720/1000 to pass), but you can swap in any subject by replacing `items.json`.

### Schema

```json
{
  "exam": {
    "name": "...",
    "format": "...",
    "passing": "...",
    "domains": [
      { "id": "D1", "name": "Domain name", "weight": 0.27 }
    ]
  },
  "items": [
    {
      "id": "unique-id",
      "domain": "D1",
      "topic_cluster": "Cluster label",
      "format": "mcq | spot | recall | explain",
      "difficulty": 1,

      "prompt": "The question text.",

      // mcq / spot fields:
      "choices": ["Choice A", "Choice B", "Choice C", "Choice D"],
      "answer_index": 0,

      // recall fields:
      "answer": "canonical answer",
      "accept": ["answer", "alternate", "shorthand"],

      // explain fields (free-text, AI-graded):
      "answer": "A strong model answer.",
      "rubric": ["key point 1", "key point 2"],

      "explanation": "Shown after any answer to re-teach the concept."
    }
  ]
}
```

Item formats:
- `mcq` — multiple choice, tap the right option
- `spot` — "spot the wrong one" (three true, one false)
- `recall` — type the answer; checked against the `accept` list
- `explain` — free-text; graded by the AI endpoint against `rubric` key points

## Mobile and Tailscale

The UI is designed for mobile-first use. Run `app.py` on a always-on machine (Mac Mini, NAS, home server), expose it over Tailscale, and access it from any device on your tailnet. No internet exposure required; the `GAUNTLET_TOKEN` param adds a lightweight URL secret if you want it.

## Runs log

Each completed run is appended as a JSON line to `runs/YYYY-MM-DD.jsonl`. The `runs/` directory is excluded from git (see `.gitignore`).
