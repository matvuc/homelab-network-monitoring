import getpass
import requests

BASE_URL = "https://127.0.0.1/api"

password = getpass.getpass("Pi-hole password: ")

with requests.Session() as client:
    client.verify = False  # Local development only

    # Authenticate
    response = client.post(
        f"{BASE_URL}/auth",
        json={"password": password},
        timeout=10,
    )
    response.raise_for_status()

    session = response.json()["session"]

    if not session["valid"]:
        raise RuntimeError("Authentication failed")

    sid = session["sid"]

    try:
        # Retrieve statistics
        response = client.get(
            f"{BASE_URL}/stats/summary",
            headers={"X-FTL-SID": sid},
            timeout=10,
        )
        response.raise_for_status()

        stats = response.json()["queries"]

        print("Total DNS queries:", stats["total"])
        print("Blocked queries:", stats["blocked"])
        print("Blocked percentage:", stats["percent_blocked"])

    finally:
        # Close the authenticated session
        client.delete(
            f"{BASE_URL}/auth",
            headers={"X-FTL-SID": sid},
            timeout=10,
        )
