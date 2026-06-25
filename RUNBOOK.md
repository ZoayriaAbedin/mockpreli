# Deployment Runbook

This service is intentionally dependency-free and runs on the Python standard library.

## Local run

```bash
python app.py
```

The server listens on `0.0.0.0` and uses the `PORT` environment variable when present, defaulting to `8000`.

## Required routes

- `GET /health`
- `POST /sort-ticket`

## Deployment guidance

Use any platform that can run a Python process behind HTTPS, such as Render, Railway, Fly, EC2, Vercel serverless routing, or a lab environment.

For Vercel, the repository includes `vercel.json` rewrites so the public endpoints remain:

- `/health`
- `/sort-ticket`

Recommended start command:

```bash
python app.py
```

No secrets or API keys are required.

## Validation checklist

1. `GET /health` returns `{"status":"ok"}`.
2. `POST /sort-ticket` returns the required JSON fields.
3. Phishing and critical tickets set `human_review_required` to `true`.
4. The agent summary never asks for OTP, PIN, password, or full card number.
