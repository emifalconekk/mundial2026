"""model.py - Motor de prediccion vectorizado (fase de grupos + knockout)."""
import numpy as np
from scipy.stats import poisson as _poisson
import pathlib

ELO_K         = 40
ELO_D         = 400
BASE_GOALS    = 1.35
N_SIMULATIONS = 100_000

DEFAULT_GROUPS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

# Bracket oficial R32 (slot, grupo_idx 0-11, 0=ganador/1=subcampeon)
_FIFA_FIXED_SLOTS = [
    (0,  0, 1), (1,  1, 1), (2,  5, 0), (3,  2, 1), (4,  4, 0),
    (6,  8, 0), (8,  10, 1), (9,  11, 1), (10,  7, 0), (11,  9, 1),
    (12,  3, 0), (14,  6, 0), (16,  2, 0), (17,  5, 1), (18,  4, 1),
    (19,  8, 1), (20,  0, 0), (22, 11, 0), (24,  9, 0), (25,  7, 1),
    (26,  3, 1), (27,  6, 1), (28,  1, 0), (30, 10, 0),
]
_THIRD_SLOTS = [5, 7, 13, 15, 21, 23, 29, 31]
_COMBO_COLS  = [3, 5,  2,  4,  0,  7,  1,  6]

def _build_combo_lookup():
    raw = (pathlib.Path(__file__).parent.parent / "data" / "fifa_combos.bin").read_bytes()
    arr = np.full((4096, 8), -1, dtype=np.int8)
    for i in range(0, len(raw), 10):
        bm = int.from_bytes(raw[i:i+2], "little")
        arr[bm] = list(raw[i+2:i+10])
    return arr

_COMBO_LOOKUP = _build_combo_lookup()
del _build_combo_lookup


def elo_win_prob(elo_a, elo_b):
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / ELO_D))


def expected_goals(elo_a, elo_b):
    p = elo_win_prob(elo_a, elo_b)
    return BASE_GOALS * (1.0 + (p - 0.5)), BASE_GOALS * (1.0 - (p - 0.5))


def match_probabilities(elo_a, elo_b, is_knockout=False):
    la, lb = expected_goals(elo_a, elo_b)
    win_a = draw = win_b = 0.0
    scorelines = {}
    for ga in range(8):
        pa = _poisson.pmf(ga, la)
        for gb in range(8):
            pb = _poisson.pmf(gb, lb)
            p = pa * pb
            scorelines[(ga, gb)] = p
            if ga > gb:    win_a += p
            elif ga == gb: draw  += p
            else:          win_b += p
    if is_knockout:
        win_a += draw * 0.5
        win_b += draw * 0.5
        draw = 0.0
    top = sorted(scorelines.items(), key=lambda x: -x[1])[:6]
    return {
        "win_a": round(win_a, 4), "draw": round(draw, 4), "win_b": round(win_b, 4),
        "lambda_a": round(la, 3), "lambda_b": round(lb, 3),
        "top_scorelines": [{"home": g[0], "away": g[1], "prob": round(p, 4)} for g, p in top],
    }


def run_monte_carlo(elo_ratings, groups=None, played_results=None,
                    n_simulations=None, elo_adjustments=None):
    if groups is None:         groups = DEFAULT_GROUPS
    if played_results is None: played_results = {}
    N           = n_simulations or N_SIMULATIONS
    rng         = np.random.default_rng()
    group_items = list(groups.items())
    n_groups    = len(group_items)
    all_teams   = [t for _, teams in group_items for t in teams]
    n_teams     = len(all_teams)
    ti          = {t: i for i, t in enumerate(all_teams)}
    adj         = elo_adjustments or {}
    elo_arr     = np.array([max(1400., elo_ratings.get(t, 1700.) + adj.get(t, 0.))
                            for t in all_teams], dtype=np.float64)

    # Partidos de grupos
    match_list = []
    for g_idx, (_, teams) in enumerate(group_items):
        for i in range(4):
            for j in range(i + 1, 4):
                la, lb = expected_goals(elo_arr[ti[teams[i]]], elo_arr[ti[teams[j]]])
                kf, kr = (teams[i], teams[j]), (teams[j], teams[i])
                if   kf in played_results: ov = played_results[kf]
                elif kr in played_results: ga, gb = played_results[kr]; ov = (gb, ga)
                else:                      ov = None
                match_list.append((g_idx, i, j, la, lb, ov))

    M      = len(match_list)
    la_arr = np.array([m[3] for m in match_list])
    lb_arr = np.array([m[4] for m in match_list])
    all_ga = rng.poisson(np.tile(la_arr, (N, 1))).astype(np.int32)
    all_gb = rng.poisson(np.tile(lb_arr, (N, 1))).astype(np.int32)
    for m_idx, (*_, ov) in enumerate(match_list):
        if ov is not None:
            all_ga[:, m_idx] = ov[0]
            all_gb[:, m_idx] = ov[1]

    pts   = np.zeros((N, n_groups, 4), dtype=np.int32)
    gd_st = np.zeros((N, n_groups, 4), dtype=np.int32)
    gf_st = np.zeros((N, n_groups, 4), dtype=np.int32)
    for m_idx, (g_idx, i, j, *_) in enumerate(match_list):
        ga = all_ga[:, m_idx]; gb = all_gb[:, m_idx]
        pts[:, g_idx, i] += (ga > gb).astype(np.int32) * 3 + (ga == gb).astype(np.int32)
        pts[:, g_idx, j] += (gb > ga).astype(np.int32) * 3 + (ga == gb).astype(np.int32)
        gd_st[:, g_idx, i] += (ga - gb).astype(np.int32)
        gd_st[:, g_idx, j] += (gb - ga).astype(np.int32)
        gf_st[:, g_idx, i] += ga
        gf_st[:, g_idx, j] += gb

    sort_key  = pts * 1_000_000 + (gd_st + 50) * 1_000 + gf_st
    order     = np.argsort(-sort_key, axis=2)
    grp_teams = np.array([[ti[t] for t in teams] for _, teams in group_items])
    ranked    = grp_teams[np.arange(n_groups)[None, :, None], order]
    qualified  = ranked[:, :, :2]
    thirds_arr = ranked[:, :, 2]

    ni = np.arange(N)[:, None]; gi = np.arange(n_groups)[None, :]
    third_loc  = order[:, :, 2]
    thirds_key = (pts[ni, gi, third_loc] * 1_000_000
                  + (gd_st[ni, gi, third_loc] + 50) * 1_000
                  + gf_st[ni, gi, third_loc])
    t_order = np.argsort(-thirds_key, axis=1)

    # Bracket
    if n_groups == 12:
        bracket = np.zeros((N, 32), dtype=np.int32)
        for slot, g_i, w_or_r in _FIFA_FIXED_SLOTS:
            bracket[:, slot] = qualified[:, g_i, w_or_r]
        best_grp = t_order[:, :8]
        bitmasks = np.zeros(N, dtype=np.int32)
        for bit in range(8):
            bitmasks |= (1 << best_grp[:, bit].astype(np.int32))
        assignments = _COMBO_LOOKUP[bitmasks]
        for slot, col in zip(_THIRD_SLOTS, _COMBO_COLS):
            grp = assignments[:, col].astype(np.int32)
            bracket[:, slot] = thirds_arr[np.arange(N), grp]
    else:
        best8   = thirds_arr[np.arange(N)[:, None], t_order[:, :8]]
        bracket = np.concatenate([qualified.reshape(N, n_groups * 2), best8], axis=1)
        for sim_i in range(N): rng.shuffle(bracket[sim_i])

    # Knockout
    ROUND_KEYS = ["r32", "r16", "qf", "sf", "final", "winner"]
    counts = {k: np.zeros(n_teams, dtype=np.int64) for k in ROUND_KEYS}
    for slot in range(bracket.shape[1]):
        np.add.at(counts["r32"], bracket[:, slot], 1)
    current = bracket.copy()
    for rnd in ROUND_KEYS[1:]:
        left = current[:, 0::2]; right = current[:, 1::2]
        el = elo_arr[left]; er = elo_arr[right]
        p  = 1.0 / (1.0 + 10.0 ** ((er - el) / ELO_D))
        la = BASE_GOALS * (1.0 + (p - 0.5))
        lb = BASE_GOALS * (1.0 - (p - 0.5))
        ga = rng.poisson(la).astype(np.int32)
        gb = rng.poisson(lb).astype(np.int32)
        tie       = ga == gb
        left_wins = (ga > gb) | (tie & (rng.random(tie.shape) < 0.5))
        current   = np.where(left_wins, left, right)
        for slot in range(current.shape[1]):
            np.add.at(counts[rnd], current[:, slot], 1)

    return {team: {k: int(counts[k][idx]) / N for k in ROUND_KEYS}
            for idx, team in enumerate(all_teams)}
