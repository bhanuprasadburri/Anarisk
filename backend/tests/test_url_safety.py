import http.server
import threading

import pytest

from app.core.config import Settings
from app.core.errors import DomainError
from app.services.url_inspector import (
    SafeFetcher, SsrfBlocked, UrlFetchDisabled, is_blocked_ip, validate_destination,
)


def S(**kw):
    return Settings(_env_file=None, secret_key="s" * 40, url_fetch_enabled=True, **kw)


def resolver(mapping):
    def r(host, port):
        if host not in mapping:
            raise OSError("nxdomain")
        return mapping[host]
    return r


@pytest.mark.parametrize("ip", ["127.0.0.1", "127.1.2.3", "10.0.0.1", "172.16.5.4", "192.168.1.1", "169.254.169.254", "0.0.0.0", "100.64.0.1", "224.0.0.1",
                                "240.0.0.1", "::1", "fe80::1", "fd12::1", "::", "::ffff:127.0.0.1", "::ffff:10.0.0.1", "64:ff9b::7f00:1", "2002:7f00:1::1", "not-an-ip"])
def test_blocked_ip_ranges(ip):
    assert is_blocked_ip(ip) is True


@pytest.mark.parametrize("ip", ["8.8.8.8", "93.184.216.34", "1.1.1.1", "2606:4700:4700::1111"])
def test_public_ips_allowed(ip):
    assert is_blocked_ip(ip) is False


@pytest.mark.parametrize("url", ["http://127.0.0.1/", "http://localhost/admin", "http://169.254.169.254/latest/meta-data/", "http://[::1]/", "http://2130706433/",
                                 "http://0x7f.0.0.1/", "https://intranet.corp/", "http://printer.local/", "http://svc.internal/", "http://foo.localhost/"])
def test_literal_and_special_hostnames_blocked(url):
    with pytest.raises(SsrfBlocked):
        validate_destination(url, settings=S(), resolver=resolver({}))


def test_dns_resolving_to_private_blocked_and_mixed_answers_blocked():
    r = resolver({"evil.example": ["10.1.1.1"], "mixed.example": ["93.184.216.34", "127.0.0.1"], "ok.example": ["93.184.216.34"], "v6.example": ["::1"]})
    for host in ("evil.example", "mixed.example", "v6.example"):
        with pytest.raises(SsrfBlocked, match="non-public"):
            validate_destination(f"https://{host}/", settings=S(), resolver=r)
    t = validate_destination("https://ok.example/path", settings=S(), resolver=r)
    assert t.ip == "93.184.216.34" and t.port == 443
    with pytest.raises(SsrfBlocked, match="resolved"):
        validate_destination("https://nonexistent.example/", settings=S(), resolver=r)


def test_scheme_port_userinfo_and_allowlist():
    ok = resolver({"ok.example": ["93.184.216.34"]})
    for bad in ("file:///etc/passwd", "gopher://ok.example/", "ftp://ok.example/", "javascript:alert(1)"):
        with pytest.raises(SsrfBlocked):
            validate_destination(bad, settings=S(), resolver=ok)
    with pytest.raises(SsrfBlocked, match="Port 22"):
        validate_destination("http://ok.example:22/", settings=S(), resolver=ok)
    with pytest.raises(SsrfBlocked, match="Port 8080"):
        validate_destination("http://ok.example:8080/", settings=S(), resolver=ok)
    with pytest.raises(SsrfBlocked, match="credentials"):
        validate_destination("http://user:pw@ok.example/", settings=S(), resolver=ok)
    with pytest.raises(SsrfBlocked, match="allowlist"):
        validate_destination("http://ok.example/", settings=S(url_fetch_domain_allowlist=["other.example"]), resolver=ok)
    assert validate_destination("http://ok.example/", settings=S(url_fetch_domain_allowlist=["ok.example"]), resolver=ok)


def test_fetch_disabled_by_default():
    with pytest.raises(UrlFetchDisabled):
        SafeFetcher(Settings(_env_file=None, secret_key="s" * 40)).fetch("https://example.com")
    assert Settings(_env_file=None).url_fetch_enabled is False


class FakeFetcher(SafeFetcher):
    """Simulates responses without touching the network; validation still runs on every hop."""
    def __init__(self, hops, **kw):
        super().__init__(**kw)
        self.hops, self.requested = hops, []

    def _request(self, target, deadline):
        self.requested.append((target.parsed.host, target.ip))
        return self.hops[target.parsed.host]


def test_redirect_to_private_address_is_blocked_on_every_hop():
    r = resolver({"start.example": ["93.184.216.34"], "rebind.example": ["10.0.0.5"]})
    f = FakeFetcher({"start.example": (302, {"location": "http://rebind.example/admin"}, b"", False)}, settings=S(), resolver=r)
    with pytest.raises(SsrfBlocked, match="non-public"):
        f.fetch("http://start.example/")
    assert f.requested == [("start.example", "93.184.216.34")]            # the internal host was never contacted
    f2 = FakeFetcher({"start.example": (301, {"location": "http://169.254.169.254/latest/meta-data"}, b"", False)}, settings=S(), resolver=r)
    with pytest.raises(SsrfBlocked):
        f2.fetch("http://start.example/")
    f3 = FakeFetcher({"start.example": (302, {"location": "file:///etc/passwd"}, b"", False)}, settings=S(), resolver=r)
    with pytest.raises(SsrfBlocked):
        f3.fetch("http://start.example/")


def test_redirect_limit_and_successful_redirect_chain_with_title():
    r = resolver({"a.example": ["93.184.216.34"], "b.example": ["93.184.216.35"]})
    loop = FakeFetcher({"a.example": (302, {"location": "http://b.example/"}, b"", False), "b.example": (302, {"location": "http://a.example/"}, b"", False)}, settings=S(), resolver=r)
    with pytest.raises(SsrfBlocked, match="Too many redirects"):
        loop.fetch("http://a.example/")
    ok = FakeFetcher({"a.example": (302, {"location": "/next"}, b"", False),
                      "b.example": (200, {"content-type": "text/html"}, b"<html><title>Hi &amp; bye</title></html>", False)}, settings=S(), resolver=r)
    ok.hops["a.example"] = (302, {"location": "http://b.example/page"}, b"", False)
    res = ok.fetch("http://a.example/")
    assert res.status == 200 and res.title == "Hi & bye" and res.redirects == ["http://b.example/page"] and len(res.sha256) == 64


def test_pinned_connection_real_socket_size_cap_and_title():
    """End-to-end over a real TCP socket (loopback allowed ONLY via the injected blocker for this test)."""
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = b"<title>Local Test</title>" + b"A" * 200_000
            self.send_response(200); self.send_header("Content-Type", "text/html"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def log_message(self, *a): pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    try:
        s = S(url_fetch_allowed_ports=[port], url_fetch_max_bytes=50_000)
        res = SafeFetcher(s, resolver=resolver({"pinned.example": ["127.0.0.1"]}), ip_blocker=lambda ip: False).fetch(f"http://pinned.example:{port}/")
        assert res.status == 200 and res.title == "Local Test" and res.truncated is True and res.size_bytes == 50_000
        with pytest.raises(SsrfBlocked):                                                  # default blocker refuses the same destination
            SafeFetcher(s, resolver=resolver({"pinned.example": ["127.0.0.1"]})).fetch(f"http://pinned.example:{port}/")
    finally:
        srv.shutdown()


def test_connection_failure_is_reported_not_leaked():
    import socket
    with socket.socket() as sock:                       # grab a port that is guaranteed to be closed
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    s = S(url_fetch_allowed_ports=[port], url_fetch_timeout_seconds=1)
    fetcher = SafeFetcher(s, resolver=resolver({"down.example": ["127.0.0.1"]}), ip_blocker=lambda ip: False)
    with pytest.raises(DomainError) as e:
        fetcher.fetch(f"http://down.example:{port}/")
    assert e.value.code == "fetch_failed" and e.value.status_code == 502 and "127.0.0.1" not in e.value.message


def test_inspect_endpoint_disabled_blocks_and_audits(client, f, world, settings, monkeypatch):
    h = world.h["inv"]
    e = f.website(h, world.brand["id"])
    r = client.post(f"/api/v1/entities/{e['id']}/inspect-url", headers=h, json={"url": "https://example.com"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "url_fetch_disabled"
    monkeypatch.setattr(settings, "url_fetch_enabled", True)
    for url in ("http://127.0.0.1:80/", "http://169.254.169.254/latest/meta-data/", "http://localhost/"):
        rr = client.post(f"/api/v1/entities/{e['id']}/inspect-url", headers=h, json={"url": url})
        assert rr.status_code == 422 and rr.json()["error"]["code"] in ("ssrf_blocked", "validation_error"), url
        if "localhost" not in url:
            assert rr.json()["error"]["code"] == "ssrf_blocked"
    assert client.post(f"/api/v1/entities/{e['id']}/inspect-url", headers=h, json={"url": "javascript:alert(1)"}).status_code == 422
    assert client.post(f"/api/v1/entities/{e['id']}/inspect-url", headers=world.h["owner"], json={"url": "https://example.com"}).status_code == 403


def test_inspection_result_stored_as_evidence(client, f, world, settings, monkeypatch):
    from app.services import url_inspection_service as svc
    from app.services.url_inspector import FetchResult
    h = world.h["inv"]
    e = f.website(h, world.brand["id"])
    monkeypatch.setattr(settings, "url_fetch_enabled", True)
    class Stub(SafeFetcher):
        def fetch(self, url): return FetchResult(final_url="https://acmebank-login.xyz/verify", status=200, content_type="text/html", size_bytes=10, truncated=False, sha256="d" * 64, title="Verify", redirects=[])
    orig = svc.inspect_entity_url
    monkeypatch.setattr("app.api.v1.entities.inspect_entity_url", lambda db, user, eid, url: orig(db, user, eid, url, fetcher=Stub()))
    r = client.post(f"/api/v1/entities/{e['id']}/inspect-url", headers=h, json={"url": "https://acmebank-login.xyz/verify"})
    assert r.status_code == 201 and r.json()["kind"] == "url_inspection" and r.json()["provenance"] == "collected" and r.json()["metadata"]["title"] == "Verify"
