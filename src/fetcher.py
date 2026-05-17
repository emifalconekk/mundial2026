"""
fetcher.py
Obtiene datos del Mundial 2026 desde football-data.org (API gratuita).
También hace scraping de Elo ratings desde eloratings.net.
"""

import requests
import json
import os
import time
from datetime import datetime

FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"
API_KEY = os.environ.get("FOOTBALL_DATA_KEY", "")
HEADERS = {"X-Auth-Token": API_KEY} if API_KEY else {}
WORLD_CUP_CODE = "WC"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "../data/cache.json")


def _load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            # Cache corrupto — se resetea solo
            try:
                os.remove(CACHE_FILE)
            except OSError:
                pass
    return {}


def _save_cache(data):
    cache_dir = os.path.dirname(CACHE_FILE)
    os.makedirs(cache_dir, exist_ok=True)
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, CACHE_FILE)  # atómico: nunca deja el archivo a medias


def _get(url, params=None, cache_key=None, max_age_minutes=15):
    cache = _load_cache()
    now = time.time()
    if cache_key and cache_key in cache:
        entry = cache[cache_key]
        if (now - entry["ts"]) / 60 < max_age_minutes:
            return entry["data"]
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"warning: Error fetching {url}: {e}")
        if cache_key and cache_key in cache:
            return cache[cache_key]["data"]
        return None
    if cache_key:
        cache[cache_key] = {"ts": now, "data": data}
        _save_cache(cache)
    return data


def _fixtures_fallback():
    """Fixture completo de la fase de grupos del Mundial 2026 (fuente: Al Jazeera/FIFA)."""
    def mk(home, away, date):
        return {
            "homeTeam": {"name": home}, "awayTeam": {"name": away},
            "utcDate": date, "stage": "GROUP_STAGE", "status": "SCHEDULED",
            "score": {"fullTime": {"home": None, "away": None}}
        }
    return [
        mk("Mexico",                 "South Africa",          "2026-06-11T19:00:00Z"),
        mk("South Korea",            "Czechia",               "2026-06-12T02:00:00Z"),
        mk("Canada",                 "Bosnia and Herzegovina","2026-06-12T19:00:00Z"),
        mk("United States",          "Paraguay",              "2026-06-13T01:00:00Z"),
        mk("Qatar",                  "Switzerland",           "2026-06-13T19:00:00Z"),
        mk("Brazil",                 "Morocco",               "2026-06-13T23:00:00Z"),
        mk("Haiti",                  "Scotland",              "2026-06-14T01:00:00Z"),
        mk("Australia",              "Turkey",                "2026-06-14T04:00:00Z"),
        mk("Germany",                "Curacao",               "2026-06-14T18:00:00Z"),
        mk("Netherlands",            "Japan",                 "2026-06-14T21:00:00Z"),
        mk("Ivory Coast",            "Ecuador",               "2026-06-15T00:00:00Z"),
        mk("Sweden",                 "Tunisia",               "2026-06-15T04:00:00Z"),
        mk("Spain",                  "Cape Verde",            "2026-06-15T17:00:00Z"),
        mk("Belgium",                "Egypt",                 "2026-06-15T22:00:00Z"),
        mk("Saudi Arabia",           "Uruguay",               "2026-06-15T23:00:00Z"),
        mk("Iran",                   "New Zealand",           "2026-06-16T04:00:00Z"),
        mk("France",                 "Senegal",               "2026-06-16T20:00:00Z"),
        mk("Iraq",                   "Norway",                "2026-06-16T23:00:00Z"),
        mk("Argentina",              "Algeria",               "2026-06-17T03:00:00Z"),
        mk("Austria",                "Jordan",                "2026-06-17T08:00:00Z"),
        mk("Portugal",               "DR Congo",              "2026-06-17T19:00:00Z"),
        mk("England",                "Croatia",               "2026-06-17T22:00:00Z"),
        mk("Ghana",                  "Panama",                "2026-06-18T00:00:00Z"),
        mk("Uzbekistan",             "Colombia",              "2026-06-18T04:00:00Z"),
        mk("Czechia",                "South Africa",          "2026-06-18T17:00:00Z"),
        mk("Switzerland",            "Bosnia and Herzegovina","2026-06-18T23:00:00Z"),
        mk("Canada",                 "Qatar",                 "2026-06-19T02:00:00Z"),
        mk("Mexico",                 "South Korea",           "2026-06-19T03:00:00Z"),
        mk("Scotland",               "Morocco",               "2026-06-19T23:00:00Z"),
        mk("United States",          "Australia",             "2026-06-19T23:00:00Z"),
        mk("Brazil",                 "Haiti",                 "2026-06-20T02:00:00Z"),
        mk("Turkey",                 "Paraguay",              "2026-06-20T08:00:00Z"),
        mk("Netherlands",            "Sweden",                "2026-06-20T19:00:00Z"),
        mk("Germany",                "Ivory Coast",           "2026-06-20T21:00:00Z"),
        mk("Ecuador",                "Curacao",               "2026-06-21T04:00:00Z"),
        mk("Tunisia",                "Japan",                 "2026-06-21T06:00:00Z"),
        mk("Spain",                  "Saudi Arabia",          "2026-06-21T17:00:00Z"),
        mk("Belgium",                "Iran",                  "2026-06-21T23:00:00Z"),
        mk("Uruguay",                "Cape Verde",            "2026-06-21T23:00:00Z"),
        mk("New Zealand",            "Egypt",                 "2026-06-22T05:00:00Z"),
        mk("Argentina",              "Austria",               "2026-06-22T19:00:00Z"),
        mk("France",                 "Iraq",                  "2026-06-22T22:00:00Z"),
        mk("Norway",                 "Senegal",               "2026-06-23T01:00:00Z"),
        mk("Jordan",                 "Algeria",               "2026-06-23T07:00:00Z"),
        mk("Portugal",               "Uzbekistan",            "2026-06-23T19:00:00Z"),
        mk("England",                "Ghana",                 "2026-06-23T21:00:00Z"),
        mk("Panama",                 "Croatia",               "2026-06-24T00:00:00Z"),
        mk("Colombia",               "DR Congo",              "2026-06-24T04:00:00Z"),
        mk("Switzerland",            "Canada",                "2026-06-24T23:00:00Z"),
        mk("Bosnia and Herzegovina", "Qatar",                 "2026-06-24T23:00:00Z"),
        mk("Scotland",               "Brazil",                "2026-06-24T23:00:00Z"),
        mk("Morocco",                "Haiti",                 "2026-06-24T23:00:00Z"),
        mk("Czechia",                "Mexico",                "2026-06-25T03:00:00Z"),
        mk("South Africa",           "South Korea",           "2026-06-25T03:00:00Z"),
        mk("Ecuador",                "Germany",               "2026-06-25T21:00:00Z"),
        mk("Curacao",                "Ivory Coast",           "2026-06-25T21:00:00Z"),
        mk("Japan",                  "Sweden",                "2026-06-26T01:00:00Z"),
        mk("Tunisia",                "Netherlands",           "2026-06-26T01:00:00Z"),
        mk("Turkey",                 "United States",         "2026-06-26T06:00:00Z"),
        mk("Paraguay",               "Australia",             "2026-06-26T06:00:00Z"),
        mk("Norway",                 "France",                "2026-06-26T20:00:00Z"),
        mk("Senegal",                "Iraq",                  "2026-06-26T20:00:00Z"),
        mk("Cape Verde",             "Saudi Arabia",          "2026-06-27T02:00:00Z"),
        mk("Uruguay",                "Spain",                 "2026-06-27T02:00:00Z"),
        mk("Egypt",                  "Iran",                  "2026-06-27T07:00:00Z"),
        mk("New Zealand",            "Belgium",               "2026-06-27T07:00:00Z"),
        mk("Panama",                 "England",               "2026-06-27T22:00:00Z"),
        mk("Croatia",                "Ghana",                 "2026-06-27T22:00:00Z"),
        mk("Colombia",               "Portugal",              "2026-06-28T02:30:00Z"),
        mk("DR Congo",               "Uzbekistan",            "2026-06-28T02:30:00Z"),
        mk("Algeria",                "Austria",               "2026-06-28T04:00:00Z"),
        mk("Jordan",                 "Argentina",             "2026-06-28T04:00:00Z"),
    ]


def get_teams():
    url = f"{FOOTBALL_DATA_BASE}/competitions/{WORLD_CUP_CODE}/teams"
    data = _get(url, cache_key="teams", max_age_minutes=60*24)
    if data and "teams" in data:
        return data["teams"]
    return []


def get_fixtures():
    """Obtiene todos los partidos del Mundial (jugados y por jugar)."""
    url = f"{FOOTBALL_DATA_BASE}/competitions/{WORLD_CUP_CODE}/matches"
    data = _get(url, cache_key="fixtures", max_age_minutes=15)
    if data and "matches" in data:
        return data["matches"]
    print("   Usando fixture hardcodeado (API no disponible)")
    return _fixtures_fallback()


def get_standings():
    url = f"{FOOTBALL_DATA_BASE}/competitions/{WORLD_CUP_CODE}/standings"
    data = _get(url, cache_key="standings", max_age_minutes=15)
    if data and "standings" in data:
        return data["standings"]
    return []


def get_played_matches():
    """Filtra solo los partidos ya jugados."""
    fixtures = get_fixtures()
    return [m for m in fixtures if m.get("status") == "FINISHED"]


def get_upcoming_matches():
    """Filtra los partidos que aun no se jugaron."""
    fixtures = get_fixtures()
    return [m for m in fixtures if m.get("status") in ("SCHEDULED", "TIMED")]


def get_elo_ratings():
    """
    Obtiene Elo ratings desde eloratings.net via scraping.
    Devuelve dict: {nombre_equipo: elo_rating}
    """
    try:
        resp = requests.get("http://eloratings.net/World.tsv", timeout=10)
        resp.raise_for_status()
        ratings = {}
        for line in resp.text.strip().split("\n")[1:]:
            parts = line.split("\t")
            if len(parts) >= 3:
                team = parts[1].strip()
                try:
                    elo = float(parts[2].strip())
                    ratings[team] = elo
                except ValueError:
                    pass
        if ratings:
            print(f"Elo ratings cargados: {len(ratings)} equipos")
            return ratings
    except Exception as e:
        print(f"warning: No se pudo obtener Elo de eloratings.net: {e}")
    return _elo_fallback()


def _elo_fallback():
    """Elo ratings de los 48 equipos del Mundial 2026 (Mayo 2026)."""
    return {
        "Argentina": 2141, "France": 2090, "England": 2063, "Spain": 2048,
        "Brazil": 2038, "Portugal": 2020, "Belgium": 1985, "Netherlands": 1975,
        "Germany": 1970, "Croatia": 1950, "Uruguay": 1935, "Colombia": 1920,
        "Norway": 1912, "Mexico": 1900, "United States": 1885, "Switzerland": 1880,
        "Sweden": 1865, "Senegal": 1860, "Morocco": 1855, "Japan": 1848,
        "South Korea": 1832, "Scotland": 1825, "Australia": 1815, "Turkey": 1812,
        "Czechia": 1808, "Canada": 1805, "Austria": 1800, "Ecuador": 1778,
        "Egypt": 1770, "Algeria": 1758, "Tunisia": 1750,
        "Bosnia and Herzegovina": 1748, "Ghana": 1738, "Ivory Coast": 1735,
        "Iran": 1730, "Saudi Arabia": 1720, "Panama": 1715, "Qatar": 1710,
        "Paraguay": 1700, "Uzbekistan": 1695, "Jordan": 1680, "South Africa": 1678,
        "Iraq": 1670, "DR Congo": 1665, "New Zealand": 1640, "Cape Verde": 1635,
        "Haiti": 1590, "Curacao": 1570,
    }


def get_match_summary(match):
    home = match.get("homeTeam", {}).get("name", "?")
    away = match.get("awayTeam", {}).get("name", "?")
    status = match.get("status", "?")
    score = match.get("score", {})
    ft = score.get("fullTime", {})
    home_goals = ft.get("home")
    away_goals = ft.get("away")
    date = match.get("utcDate", "")[:10]
    stage = match.get("stage", "")
    if status == "FINISHED" and home_goals is not None:
        return f"{date} [{stage}] {home} {home_goals}-{away_goals} {away}"
    else:
        return f"{date} [{stage}] {home} vs {away}"


if __name__ == "__main__":
    print("=== TEST FETCHER ===")
    elo = get_elo_ratings()
    top10 = sorted(elo.items(), key=lambda x: x[1], reverse=True)[:10]
    for team, rating in top10:
        print(f"  {team}: {rating}")
    fixtures = get_fixtures()
    print(f"\nTotal fixtures: {len(fixtures)}")
    upcoming = get_upcoming_matches()
    print(f"Proximos: {len(upcoming)}")
    if upcoming:
        print("Primeros 3:")
        for m in upcoming[:3]:
            print(f"  {get_match_summary(m)}")
