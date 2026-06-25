# Ticket Sorter API

A small JSON API that classifies customer support tickets into case type, severity, department, and a short agent summary.

**Live Deployment:** https://mockpreli-gc6j.vercel.app/

## Endpoints

- `GET /health` returns service health.
- `POST /sort-ticket` classifies one ticket.

## Request

```json
{
  "ticket_id": "T-001",
  "channel": "app",
  "locale": "en",
  "message": "I sent 5000 taka to a wrong number this morning, please help me get it back"
}
```

## Response

```json
{
  "ticket_id": "T-001",
  "case_type": "wrong_transfer",
  "severity": "high",
  "department": "dispute_resolution",
  "agent_summary": "Customer reports sending money to the wrong recipient and wants the transfer recovered or reviewed.",
  "human_review_required": true,
  "confidence": 0.93
}
```

## Local Run

The service uses only the Python standard library, so there are no third-party packages to install.

Run the server with:

```bash
python app.py
```

If your hosting platform injects a port, the app reads it from `PORT`.

## Deployment Notes

The service is stateless and uses no secrets. It is Vercel-ready through the Python functions in `api/` and the rewrites in `vercel.json`.

For Vercel, deploy the repository as-is. The platform will expose:

- `GET /health` via `api/health.py`
- `POST /sort-ticket` via `api/sort_ticket.py`

If you deploy elsewhere, use this start command:

```bash
python app.py
```

Any platform-level HTTPS routing is sufficient because the app itself speaks plain HTTP behind the deployment proxy.

## Behavior Notes

- `human_review_required` is always `true` for phishing or critical tickets.
- The `agent_summary` never asks the customer for OTP, PIN, password, or full card details.
- The classifier is rules-based and does not require an LLM.
"# mockpreli" 
