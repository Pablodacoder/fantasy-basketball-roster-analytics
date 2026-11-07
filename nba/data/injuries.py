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