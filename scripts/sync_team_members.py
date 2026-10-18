#!/usr/bin/env python3
"""Ensure every organization member belongs to a team.

Environment variables:
    GH_TOKEN  Token with the organization "Members: read and write" permission.
    ORG       Organization login.
    TEAM      Team slug to keep in sync.
    ROLE      Team role to assign: "member" (default) or "maintainer".
"""

from __future__ import annotations

import json
import os
import urllib.request

API = "https://api.github.com"
API_VERSION = "2022-11-28"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": "org-team-sync",
        "Content-Type": "application/json",
    }


def _request(method: str, url: str, payload: dict | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers=_headers())
    with urllib.request.urlopen(request) as response:
        body = response.read()
    return json.loads(body) if body else None


def _next_link(header: str | None) -> str | None:
    for part in (header or "").split(","):
        url, _, rel = part.partition(";")
        if 'rel="next"' in rel:
            return url.strip().strip("<>")
    return None


def paginate(path: str) -> list[dict]:
    url = f"{API}{path}"
    items: list[dict] = []
    while url:
        request = urllib.request.Request(url, headers=_headers())
        with urllib.request.urlopen(request) as response:
            items.extend(json.loads(response.read()))
            url = _next_link(response.headers.get("Link"))
    return items


def main() -> None:
    org = os.environ["ORG"]
    team = os.environ["TEAM"]
    role = os.environ.get("ROLE", "member")

    members = {user["login"] for user in paginate(f"/orgs/{org}/members?per_page=100")}
    current = {user["login"] for user in paginate(f"/orgs/{org}/teams/{team}/members?per_page=100")}

    missing = sorted(members - current)
    if not missing:
        print(f"Team '{team}' is already in sync ({len(current)} members).")
        return

    print(f"Adding {len(missing)} member(s) to '{team}':")
    for login in missing:
        _request("PUT", f"{API}/orgs/{org}/teams/{team}/memberships/{login}", {"role": role})
        print(f"  added: {login}")


if __name__ == "__main__":
    main()
