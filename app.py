from __future__ import annotations

import json
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PHISHING_PATTERNS = [
    r"\botp\b",
    r"\bpin\b",
    r"password",
    r"card\s*(?:number|no\.?|details)",
    r"cvv",
    r"someone called",
    r"called asking",
    r"texted asking",
    r"ask(?:ing)? for.*\b(otp|pin|password|cvv)\b",
    r"phish",
    r"scam",
    r"fraudster",
    r"verification code",
    r"one[- ]time password",
    r"ওটিপি",
    r"পিন",
    r"পাসওয়ার্ড",
]

WRONG_TRANSFER_PATTERNS = [
    r"wrong number",
    r"wrong recipient",
    r"sent .* to the wrong",
    r"sent .* to wrong",
    r"mistakenly sent",
    r"wrong account",
    r"ভুল নম্বর",
    r"ভুলে .* পাঠিয়েছি",
]

PAYMENT_FAILED_PATTERNS = [
    r"payment failed",
    r"transaction failed",
    r"failed but balance deducted",
    r"balance deducted",
    r"money deducted",
    r"deducted but",
    r"declined",
    r"payment stuck",
    r"টাকা কেটে গেছে",
    r"পেমেন্ট ফেল",
]

REFUND_PATTERNS = [
    r"refund",
    r"money back",
    r"return my money",
    r"want a refund",
    r"reverse the transaction",
    r"cancel and refund",
    r"refund আমার",
    r"ফেরত",
]

HIGH_VALUE_HINTS = [r"\b[0-9]{4,}\b", r"taka", r"bdt", r" টাকা"]


def _matches(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _choose_case_type(message: str) -> tuple[str, str, str, float, str]:
    text = message.strip()

    if _matches(PHISHING_PATTERNS, text):
        return (
            "phishing_or_social_engineering",
            "critical",
            "fraud_risk",
            0.97,
            "Customer reports a suspicious request involving OTP, PIN, password, or other sensitive credentials.",
        )

    if _matches(WRONG_TRANSFER_PATTERNS, text):
        severity = "high" if _matches(HIGH_VALUE_HINTS, text) else "medium"
        return (
            "wrong_transfer",
            severity,
            "dispute_resolution",
            0.93,
            "Customer reports sending money to the wrong recipient and wants the transfer recovered or reviewed.",
        )

    if _matches(PAYMENT_FAILED_PATTERNS, text):
        return (
            "payment_failed",
            "high",
            "payments_ops",
            0.92,
            "Customer reports a failed payment or transaction that may still have affected their balance.",
        )

    if _matches(REFUND_PATTERNS, text):
        return (
            "refund_request",
            "low",
            "customer_support",
            0.9,
            "Customer is asking for a refund or reversal of a completed transaction.",
        )

    return (
        "other",
        "low",
        "customer_support",
        0.72,
        "Customer message does not clearly match a transfer, payment, refund, or fraud pattern.",
    )


def _json_response(status: HTTPStatus, payload: dict[str, object]) -> tuple[int, list[tuple[str, str]], bytes]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))]
    return status.value, headers, body


def _validate_request(data: object) -> dict[str, object]:
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object")

    ticket_id = data.get("ticket_id")
    message = data.get("message")
    channel = data.get("channel")
    locale = data.get("locale")

    if not isinstance(ticket_id, str) or not ticket_id.strip():
        raise ValueError("ticket_id is required")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("message is required")

    if channel is not None and channel not in {"app", "sms", "call_center", "merchant_portal"}:
        raise ValueError("channel must be one of: app, sms, call_center, merchant_portal")
    if locale is not None and locale not in {"bn", "en", "mixed"}:
        raise ValueError("locale must be one of: bn, en, mixed")

    return {
        "ticket_id": ticket_id,
        "message": message,
        "channel": channel,
        "locale": locale,
    }


def classify_ticket(ticket: dict[str, object]) -> dict[str, object]:
    case_type, severity, department, confidence, summary = _choose_case_type(str(ticket["message"]))
    human_review_required = severity == "critical" or case_type == "phishing_or_social_engineering"

    return {
        "ticket_id": ticket["ticket_id"],
        "case_type": case_type,
        "severity": severity,
        "department": department,
        "agent_summary": summary,
        "human_review_required": human_review_required,
        "confidence": confidence,
    }


class TicketSorterHandler(BaseHTTPRequestHandler):
    server_version = "TicketSorter/1.0"

    def _write_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        code, headers, body = _json_response(status, payload)
        self.send_response(code)
        for header_name, header_value in headers:
            self.send_header(header_name, header_value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._write_json(HTTPStatus.OK, {"status": "ok"})
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/sort-ticket":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)

        try:
            request_json = json.loads(raw_body.decode("utf-8") or "{}")
            ticket = _validate_request(request_json)
            response = classify_ticket(ticket)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return
        except ValueError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_request", "detail": str(exc)})
            return

        self._write_json(HTTPStatus.OK, response)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


handler = TicketSorterHandler


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), TicketSorterHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    import os

    run_server(port=int(os.environ.get("PORT", "8000")))
