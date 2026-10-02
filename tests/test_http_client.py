import httpx

from agent import http_client


def test_sender_requires_authenticated_context(monkeypatch):
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))
    )
    monkeypatch.setattr(http_client, "_client", client)
    assert http_client.request("GET", "/bookings")["error"] == "UNAUTHENTICATED"


def test_sender_is_injected_and_errors_structured(monkeypatch):
    seen = []

    def handler(r):
        seen.append(r.headers.get("X-Customer-Phone"))
        return httpx.Response(
            409, json={"code": "MONTHLY_LIMIT", "detail": "Cupo agotado"}
        )

    monkeypatch.setattr(
        http_client, "_client", httpx.Client(transport=httpx.MockTransport(handler))
    )
    with http_client.customer_identity("+34600123456"):
        assert http_client.request("POST", "/bookings")["error"] == "MONTHLY_LIMIT"
    assert seen == ["+34600123456"]
    assert http_client.request("GET", "/bookings")["error"] == "UNAUTHENTICATED"
