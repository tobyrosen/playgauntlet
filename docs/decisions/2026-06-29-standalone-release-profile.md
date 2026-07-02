# Use Standalone Software Release Profile

Date: 2026-06-29
Status: accepted

## Context

`gauntlet` is a browser-facing app, but the actual runtime is not the Astro `web-app` profile. It is a Python stdlib HTTP service with server endpoints, local JSONL logs, optional AI grading, and a static `index.html` client.

## Decision

Use the `standalone-software` release profile. Treat the repo as a Python application/service that happens to serve a web UI.

## Consequences

The repo carries Python package metadata, tests, contribution/security docs, issue templates, PR template, CODEOWNERS, and release-please version updates for both `version.txt` and `pyproject.toml`. It does not add Astro files or static-site build metadata that would misrepresent the app's runtime.

## Follow-up

Revisit only if the app is rewritten as an Astro/static web app or split into separate frontend and backend repos.
