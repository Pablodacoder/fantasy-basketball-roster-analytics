import re
import time
import unicodedata
from datetime import datetime

import requests
from django.conf import settings

STATUS_MAP = {
    "available": "available",
    "active": "available",
    "probable": "probable",
    "questionable": "questionable",
    "day-to-day": "questionable",  # our assumption
    "doubtful": "doubtful",
    "out": "out",
    "out for season": "out",
    "suspension": "out",
}


def map_status(raw):
    return STATUS_MAP.get((raw or "").strip().lower())


SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}


def normalize_name(name):
    # "Nikola Jokić" -> "nikola jokic", "P.J. Washington Jr." -> "pj washington"
    name = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    name = name.lower().replace("-", " ")
    name = re.sub(r"[^a-z ]", "", name)
    return " ".join(part for part in name.split() if part not in SUFFIXES)


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"


def fetch_espn():
    response = requests.get(ESPN_URL, timeout=30)
    response.raise_for_status()
    rows = []
    for team in response.json().get("injuries", []):
        for item in team.get("injuries", []):
            athlete = item.get("athlete", {})
            rows.append({
                "player_name": athlete.get("displayName", ""),
                "team": team.get("displayName", ""),
                "raw_status": item.get("status", ""),
                "note": (item.get("shortComment") or item.get("longComment") or "")[:200],
                "reported_at": _parse_iso(item.get("date")),
            })
    return rows


BDL_URL = "https://api.balldontlie.io/v1/player_injuries"


def fetch_balldontlie():
    if not settings.BALLDONTLIE_API_KEY:
        raise RuntimeError("Set BALLDONTLIE_API_KEY in .env to use balldontlie")

    rows = []
    cursor = None
    while True:
        params = {"per_page": 100}
        if cursor:
            params["cursor"] = cursor
        response = requests.get(BDL_URL, headers={"Authorization": settings.BALLDONTLIE_API_KEY},
                                params=params, timeout=30)
        response.raise_for_status()
        body = response.json()
        for item in body.get("data", []):
            player = item.get("player", {})
            rows.append({
                "player_name": f"{player.get('first_name', '')} {player.get('last_name', '')}".strip(),
                "team": str(player.get("team_id", "")),
                "raw_status": item.get("status", ""),
                "note": (item.get("description") or "")[:200],
                "reported_at": None,
            })
        cursor = body.get("meta", {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(0.6)
    return rows


def fetch_official_report():
    # TODO: parse the NBA's official injury report PDF if it wins the comparison
    raise NotImplementedError("Official injury report parser isn't built yet")


SOURCES = {
    "espn": fetch_espn,
    "balldontlie": fetch_balldontlie,
    "official": fetch_official_report,
}


def fetch_injuries(source):
    if source not in SOURCES:
        raise ValueError(f"Unknown injury source '{source}'. Pick one of {list(SOURCES)}")
    return SOURCES[source]()