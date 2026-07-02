# Agent Context

## What This Is

`gauntlet` is a local-first Python web app for gamified retrieval-practice study sessions. It serves a mobile single-page app, loads questions from `items.json`, grades recall/explain answers, and logs completed runs.

## Why It Exists

The app turns exam prep into a daily recall loop where every reward is tied to effortful retrieval instead of passive review or time-on-app. It is designed to make weak clusters visible, move readiness only when recall succeeds, and keep the loop available on a phone over a LAN or Tailscale.

## Architecture

- Main entry point: `app.py`
- Core files/directories:
  - `app.py`: Python stdlib `ThreadingHTTPServer` service. It serves the app shell, exposes JSON endpoints, grades explain-back answers, and writes run logs.
  - `index.html`: complete mobile-first single-page app with localStorage progress, run construction, timers, feedback, audio/haptics, and payoff UI.
  - `items.json`: content bank and exam metadata. The current deck targets Claude Certified Architect - Foundations.
  - `runs/`: local JSONL run logs created at runtime and ignored by git.
  - `pyproject.toml`: local package metadata and release-please version target.
  - `tests/`: smoke tests for version alignment, item-bank shape, auth token behavior, and heuristic grading.
- Runtime/deployment shape: local Python 3.9+ HTTP service using only the standard library. It binds `0.0.0.0` on `GAUNTLET_PORT` and optionally calls an OpenAI-compatible grading endpoint. No database, hosted deployment, package registry publish, or external auth provider is part of v0.1.0.

## Develop, Run, Test

```sh
python -m pip install -e ".[dev]"
python3 app.py
python -m unittest discover -s tests
```

## Release Process

This repo follows the public software release standard:

- SemVer.
- Conventional Commits.
- release-please Release PRs.
- Toby-approved Release PR merge before publishing.
- GitHub Releases first; external registries only by explicit approval.

Release state is tracked in `version.txt` and `pyproject.toml`. `release-please-config.json` updates both.

## Current State

Seeded for public release at `0.1.0`. The repo is GitHub-only: release-please may create GitHub Releases after a Release PR is approved and merged, but PyPI and other registries are intentionally disabled.

## Gotchas

- `index.html` is read once at server startup into `INDEX_HTML`. Restart `app.py` after editing the front end.
- `GAUNTLET_TOKEN` is a lightweight URL secret only. It is useful on a trusted LAN or tailnet, but it is not full user auth and should not be treated as internet-grade security.
- Explain-back grading must never block the study loop. If `OLLAMA_API_KEY` is unset, the endpoint is slow, or parsing fails, `ai_grade()` falls back to `heuristic_grade()`.
- Browser progress lives in localStorage under `bossrun_v1`; server logs in `runs/` are summaries, not the canonical client-side progress store.
- `items.json` is the product content. Schema changes affect app behavior and should be tested with all four item formats.

## Decision Notes

Design decisions live in `docs/decisions/`.

Add a decision note when a choice affects public behavior, release shape, architecture, compatibility, security, publishing, or future maintenance.
