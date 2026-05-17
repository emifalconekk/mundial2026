"""predictor.py - Orquestador principal."""
import json, os, sys, time, math
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from fetcher import get_elo_ratings, get_played_matches, get_upcoming_matches
from model import run_monte_carlo, match_probabilities, DEFAULT_GROUPS, N_SIMULATIONS

OUTPUT_JSON   = os.path.join(os.path.dirname(__file__), "../data/predictions.json")
DASHBOARD_TPL = os.path.join(os.path.dirname(__file__), "../dashboard.html")
DASHBOARD_OUT = os.path.join(os.path.dirname(__file__), "../mundial2026_predictor.html")
SQUADS_FILE   = os.path.join(os.path.dirname(__file__), "../data/squads.json")
LESIONES_FILE = os.path.join(os.path.dirname(__file__), "../data/lesiones.json")

# Multiplicador por posicion para el score FIFA
POS_MULTIPLIER = {"FW": 1.15, "MF": 1.05, "DF": 0.90, "GK": 0.80}


def compute_elo_adjustments(squads, lesiones):
    """Calcula el delta de Elo por cada equipo segun sus bajas (modo manual)."""
    adjustments = {}
    for team, injured_list in lesiones.items():
        if not injured_list:
            continue
        team_players = {p["name"]: p["imp"] for p in squads.get(team, [])}
        total_impact = sum(team_players.get(p, 20) * 0.35 for p in injured_list)
        adjustments[team] = -round(total_impact, 1)
    return adjustments


def compute_fifa_importance_scores(squads):
    """
    Calcula la importancia de cada jugador usando Z-score sobre fifa_overall
    normalizado por plantel. Devuelve un dict identico en estructura a squads
    pero con el campo 'imp' recalculado.

    Formula:
      z = (overall_jugador - media_plantel) / std_plantel
      base = clip(50 + z * 22, 5, 95)
      imp = clip(round(base * pos_multiplier), 1, 99)
    """
    result = {}
    for team, players in squads.items():
        valid = [p for p in players if p.get("fifa_overall", 0) > 0]

        if not valid:
            # Sin datos FIFA: usar imp manual tal cual
            result[team] = [dict(p) for p in players]
            continue

        overalls = [p["fifa_overall"] for p in valid]
        mean = sum(overalls) / len(overalls)
        variance = sum((x - mean) ** 2 for x in overalls) / len(overalls)
        std = math.sqrt(variance) if variance > 0 else 1.0

        team_result = []
        for p in valid:
            z = (p["fifa_overall"] - mean) / std
            base = max(5.0, min(95.0, 50.0 + z * 22.0))
            multiplier = POS_MULTIPLIER.get(p.get("pos", "MF"), 1.0)
            imp = max(1, min(99, round(base * multiplier)))
            new_p = dict(p)
            new_p["imp"] = imp
            team_result.append(new_p)

        result[team] = team_result
    return result


def compute_elo_adjustments_fifa(squads_fifa, lesiones):
    """Igual que compute_elo_adjustments pero usando los imp calculados por FIFA."""
    return compute_elo_adjustments(squads_fifa, lesiones)


def get_forma_reciente(elo_ratings, played_results, n=5):
    """Ajusta el Elo base segun forma reciente dentro del torneo."""
    adjustments = {}
    team_results = {}
    for (home, away), (hg, ag) in played_results.items():
        for team, scored, conceded in [(home, hg, ag), (away, ag, hg)]:
            if team not in team_results:
                team_results[team] = []
            team_results[team].append(1.0 if scored > conceded else (0.5 if scored == conceded else 0.0))

    for team, results in team_results.items():
        recent = results[-n:]
        if not recent:
            continue
        delta = (sum(recent) / len(recent) - 0.5) * 30
        adjustments[team] = round(delta, 1)
    return adjustments


def parse_played_results(played_matches):
    results = {}
    for m in played_matches:
        home = m.get("homeTeam", {}).get("name", "")
        away = m.get("awayTeam", {}).get("name", "")
        score = m.get("score", {}).get("fullTime", {})
        hg, ag = score.get("home"), score.get("away")
        if home and away and hg is not None and ag is not None:
            results[(home, away)] = (int(hg), int(ag))
    return results


def get_next_matches_with_probs(upcoming, elo_ratings, elo_adjustments=None, n=10):
    result = []
    adj = elo_adjustments or {}
    for m in upcoming[:n]:
        home  = m.get("homeTeam", {}).get("name", "?")
        away  = m.get("awayTeam", {}).get("name", "?")
        date  = m.get("utcDate", "")[:10]
        stage = m.get("stage", "GROUP_STAGE")
        is_ko = stage not in ("GROUP_STAGE", "")
        elo_h = max(1400, elo_ratings.get(home, 1700) + adj.get(home, 0))
        elo_a = max(1400, elo_ratings.get(away, 1700) + adj.get(away, 0))
        probs = match_probabilities(elo_h, elo_a, is_knockout=is_ko)
        result.append({
            "date": date, "stage": stage, "home": home, "away": away,
            "win_home": probs["win_a"], "draw": probs["draw"], "win_away": probs["win_b"],
            "lambda_home": probs["lambda_a"], "lambda_away": probs["lambda_b"],
            "top_scorelines": [[f"{s['home']}-{s['away']}", s["prob"]] for s in probs["top_scorelines"]],
        })
    return result


def load_squads_and_lesiones():
    squads, lesiones = {}, {}
    if os.path.exists(SQUADS_FILE):
        with open(SQUADS_FILE, encoding="utf-8") as f:
            squads = json.load(f)
    if os.path.exists(LESIONES_FILE):
        with open(LESIONES_FILE, encoding="utf-8") as f:
            lesiones = json.load(f)
    return squads, lesiones


def embed_data_in_html(data):
    if not os.path.exists(DASHBOARD_TPL):
        return
    with open(DASHBOARD_TPL, "r", encoding="utf-8") as f:
        html = f.read()
    ts = data.get("generated_at", "")[:19]
    data_str = json.dumps(data, ensure_ascii=False)

    MARKER = "// __DATA_INJECT_HERE__"
    inject = (
        "// === DATOS EMBEBIDOS (" + ts + ") ===\n"
        "window.EMBEDDED_DATA = " + data_str + ";"
    )

    if MARKER in html:
        html = html.replace(MARKER, inject, 1)
    else:
        html = html.replace("// --- Data loading", inject + "\n\n// --- Data loading", 1)

    os.makedirs(os.path.dirname(os.path.abspath(DASHBOARD_OUT)), exist_ok=True)
    with open(DASHBOARD_OUT, "w", encoding="utf-8") as f:
        f.write(html)


def run(n_simulations=N_SIMULATIONS, verbose=True):
    if verbose:
        print("Mundial 2026 - Motor de prediccion")
        print("=" * 50)

    if verbose: print("\n[1/5] Cargando Elo ratings...")
    elo = get_elo_ratings()
    if verbose: print("   " + str(len(elo)) + " equipos cargados")

    if verbose: print("\n[2/5] Obteniendo resultados del Mundial 2026...")
    played   = get_played_matches()
    upcoming = get_upcoming_matches()
    played_results = parse_played_results(played)
    if verbose:
        print("   Jugados: " + str(len(played)) + " | Por jugar: " + str(len(upcoming)))

    if verbose: print("\n[3/5] Aplicando ajustes (lesiones + forma reciente)...")
    squads, lesiones = load_squads_and_lesiones()
    inj_adj   = compute_elo_adjustments(squads, lesiones)
    forma_adj = get_forma_reciente(elo, played_results)

    elo_adjustments = {}
    for team in set(inj_adj) | set(forma_adj):
        elo_adjustments[team] = inj_adj.get(team, 0) + forma_adj.get(team, 0)

    if verbose:
        bajas = {t: v for t, v in inj_adj.items() if v != 0}
        if bajas:
            for team, adj in bajas.items():
                print("   " + team + ": " + str(adj) + " Elo (" + ", ".join(lesiones.get(team, [])) + ")")
        else:
            print("   Sin bajas registradas")

    # ── Modo FIFA: calcular si hay datos disponibles ─────────────────────────
    has_fifa = any(
        p.get("fifa_overall", 0) > 0
        for players in squads.values()
        for p in players
    )
    squads_fifa = compute_fifa_importance_scores(squads) if has_fifa else squads
    inj_adj_fifa = compute_elo_adjustments_fifa(squads_fifa, lesiones)
    elo_adjustments_fifa = {}
    for team in set(inj_adj_fifa) | set(forma_adj):
        elo_adjustments_fifa[team] = inj_adj_fifa.get(team, 0) + forma_adj.get(team, 0)

    if verbose: print("\n[4/5] Corriendo " + str(n_simulations) + " simulaciones...")
    t0 = time.time()

    # Simulacion modo manual
    predictions = run_monte_carlo(
        elo_ratings=elo, groups=DEFAULT_GROUPS,
        played_results=played_results, n_simulations=n_simulations,
        elo_adjustments=elo_adjustments
    )

    # Simulacion modo FIFA (solo si hay datos)
    if has_fifa:
        if verbose: print("   + Simulacion modo FIFA...")
        predictions_fifa = run_monte_carlo(
            elo_ratings=elo, groups=DEFAULT_GROUPS,
            played_results=played_results, n_simulations=n_simulations,
            elo_adjustments=elo_adjustments_fifa
        )
    else:
        predictions_fifa = None

    elapsed = time.time() - t0
    if verbose: print("   Completado en " + str(round(elapsed, 1)) + "s")

    if verbose: print("\n[5/5] Generando archivos...")

    next_matches = get_next_matches_with_probs(upcoming, elo, elo_adjustments)
    recent_results = []
    for m in played[-20:]:
        score = m.get("score", {}).get("fullTime", {})
        recent_results.append({
            "date": m.get("utcDate", "")[:10],
            "stage": m.get("stage", ""),
            "home": m.get("homeTeam", {}).get("name", "?"),
            "away": m.get("awayTeam", {}).get("name", "?"),
            "home_goals": score.get("home"),
            "away_goals": score.get("away"),
        })

    top_champions = sorted(predictions.items(), key=lambda x: x[1]["winner"], reverse=True)[:16]
    top_champions_fifa = (
        sorted(predictions_fifa.items(), key=lambda x: x[1]["winner"], reverse=True)[:16]
        if predictions_fifa else None
    )

    output = {
        "generated_at":      datetime.now(timezone.utc).isoformat(),
        "simulations":       n_simulations,
        "elapsed_seconds":   round(elapsed, 1),
        "matches_played":    len(played),
        "matches_remaining": len(upcoming),
        "groups":            DEFAULT_GROUPS,
        "elo_ratings":       elo,
        # Modo manual
        "elo_adjustments":   elo_adjustments,
        "predictions":       predictions,
        "top_champions":     [{"team": t, **p} for t, p in top_champions],
        # Modo FIFA
        "has_fifa_data":     has_fifa,
        "elo_adjustments_fifa": elo_adjustments_fifa,
        "predictions_fifa":  predictions_fifa,
        "top_champions_fifa": [{"team": t, **p} for t, p in top_champions_fifa] if top_champions_fifa else None,
        # Comun
        "next_matches":      next_matches,
        "recent_results":    recent_results,
        "squads":            squads,
        "squads_fifa":       squads_fifa if has_fifa else None,
        "lesiones":          lesiones,
    }

    os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_JSON)), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    embed_data_in_html(output)

    if verbose:
        print("   predictions.json guardado")
        print("   Dashboard HTML generado")
        print("\nTop 10 — Modo Manual:")
        print("  " + "Equipo".ljust(22) + "Campeon  Final    Semis")
        print("  " + "-" * 46)
        for team, probs in top_champions[:10]:
            print(
                "  " + team.ljust(22) +
                str(round(probs["winner"]*100, 1)).rjust(6) + "%  " +
                str(round(probs["final"]*100, 1)).rjust(6) + "%  " +
                str(round(probs["sf"]*100, 1)).rjust(6) + "%"
            )
        if has_fifa and top_champions_fifa:
            print("\nTop 5 — Modo FIFA (datos disponibles):")
            for team, probs in top_champions_fifa[:5]:
                print("  " + team.ljust(22) + str(round(probs["winner"]*100, 1)).rjust(6) + "%")
        else:
            print("\n  [Modo FIFA: sin datos aun — se activa el 2 de junio]")

    return output


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sims", type=int, default=N_SIMULATIONS)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    run(n_simulations=10_000 if args.quick else args.sims)
