
import json
import ssl
from pathlib import Path
from urllib.request import Request, urlopen

BASE_URL = "https://pi.hole/api"
CA_CERT = Path(__file__).resolve().parent / "certs" / "pihole-ca.crt"


def create_ssl_context():
    context = ssl.create_default_context(cafile=str(CA_CERT))
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


def authenticate(password):
    request = Request(
        f"{BASE_URL}/auth",
        data=json.dumps({"password": password}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(
        request,
        context=create_ssl_context(),
        timeout=10,
    ) as response:
        data = json.load(response)

    session = data["session"]

    if not session["valid"]:
        raise RuntimeError("Pi-hole authentication failed")

    return session["sid"]


def logout(sid):
    request = Request(
        f"{BASE_URL}/auth",
        headers={"X-FTL-SID": sid},
        method="DELETE",
    )

    with urlopen(
        request,
        context=create_ssl_context(),
        timeout=10,
    ):
        pass


def get_dns_summary(sid):
    request = Request(
        f"{BASE_URL}/stats/summary",
        headers={"X-FTL-SID": sid},
        method="GET",
    )

    with urlopen(
        request,
        context=create_ssl_context(),
        timeout=10,
    ) as response:
        data = json.load(response)

    stats = data["queries"]

    return {
        "total_queries": stats["total"],
        "blocked_queries": stats["blocked"],
        "percent_blocked": stats["percent_blocked"],
    }
