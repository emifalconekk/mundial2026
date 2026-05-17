# Contexto del proyecto para Claude

Este archivo describe la arquitectura, decisiones de diseño y estado actual del proyecto para que Claude pueda asistir eficientemente sin necesidad de explorar el código desde cero.

---

## Qué es este proyecto

Motor de predicción estadística para el Mundial 2026. Corre 100.000 simulaciones Monte Carlo del torneo completo y genera un dashboard HTML interactivo con probabilidades por equipo, próximos partidos, resultados en vivo y ajustes manuales.

---

## Archivos clave

### `src/model.py`
El corazón del sistema. Totalmente vectorizado con NumPy.

**Funciones principales:**
- `elo_win_prob(elo_a, elo_b)` → probabilidad de victoria basada en Elo (base D=400)
- `expected_goals(elo_a, elo_b)` → λ_A y λ_B para samplear Poisson (base 1.35 goles)
- `match_probabilities(elo_a, elo_b, is_knockout)` → dict con win_a/draw/win_b y top marcadores
- `run_monte_carlo(elo_ratings, groups, played_results, n_simulations, elo_adjustments)` → dict `{team: {r32, r16, qf, sf, final, winner}}` con probabilidades

**Bracket FIFA 2026:**
- `_FIFA_FIXED_SLOTS` → 24 posiciones fijas del bracket (ganadores/subcampeones)
- `_THIRD_SLOTS` → 8 posiciones para los mejores terceros
- `_COMBO_LOOKUP` → array NumPy (4096×8) cargado desde `data/fifa_combos.bin`
  - 495 combinaciones del Anexo C del reglamento FIFA (C(12,8) combinaciones de grupos)
  - Lookup por bitmask de 12 bits: qué grupos pasaron su tercer clasificado
  - Formato binario: 10 bytes por entrada = 2 bytes bitmask (little-endian) + 8 bytes de índices de grupo

**Constantes:**
```python
ELO_K = 40          # factor K (no se usa directamente, es referencia)
ELO_D = 400         # divisor para probabilidades Elo
BASE_GOALS = 1.35   # goles esperados base por partido
N_SIMULATIONS = 100_000
```

**DEFAULT_GROUPS** — 12 grupos A-L con los 48 equipos del Mundial 2026.

---

### `src/fetcher.py`
Obtiene datos externos. Tiene fallback robusto para funcionar sin API.

**Funciones:**
- `get_fixtures()` → partidos del torneo (API o fallback con 72 partidos hardcodeados con fechas reales)
- `get_played_matches()` → solo los FINISHED
- `get_upcoming_matches()` → solo los SCHEDULED/TIMED
- `get_elo_ratings()` → scraping de eloratings.net o fallback con 48 equipos
- `_load_cache()` / `_save_cache()` → caché con escritura atómica (os.replace) y auto-recuperación si el JSON se corrompe

**API key:** se lee de `os.environ.get("FOOTBALL_DATA_KEY", "")`. Sin key funciona igual con fallback.

**Cache:** `data/cache.json`. Se escribe con tmp + rename atómico para evitar corrupción.

---

### `src/predictor.py`
Orquestador principal. Une todos los módulos.

**Flujo principal (`run()`):**
1. Carga Elo ratings (API o fallback)
2. Carga squads + lesiones desde `data/squads.json` y `data/lesiones.json`
3. Calcula ajustes de Elo por lesiones (`compute_elo_adjustments`)
4. Obtiene partidos jugados → convierte a `played_results` dict `{(home, away): (goles_h, goles_a)}`
5. Corre `run_monte_carlo` dos veces: modo manual y modo FIFA
6. Calcula probabilidades de próximos partidos (`get_next_matches_with_probs`)
7. Guarda `data/predictions.json`
8. Embebe todo en `mundial2026_predictor.html` via `embed_data_in_html`

**Formato `top_scorelines` (importante):**
El dashboard espera `[["1-0", 0.1163], ["2-0", 0.1007], ...]` — array de `[string, float]`.
El model.py devuelve `[{"home":1, "away":0, "prob":0.1163}]` — la conversión ocurre en `get_next_matches_with_probs`.

**Modo FIFA:**
- Activado si `data/squads.json` tiene campo `fifa_overall` en los jugadores
- `compute_fifa_importance_scores` → normaliza importancia táctica + FIFA overall → ajuste de Elo por lesiones
- Genera `predictions_fifa`, `squads_fifa`, `top_champions_fifa` separados

**Lesiones:**
`compute_elo_adjustments(squads, lesiones)` → por cada jugador lesionado, resta `imp * factor` al Elo del equipo.

---

### `dashboard.html`
Template HTML/JS autocontenido. `predictor.py` lo lee, inyecta `window.EMBEDDED_DATA = {...}` en el marcador `// __DATA_INJECT_HERE__` y guarda como `mundial2026_predictor.html`.

**Carga de datos (JS):**
```javascript
if(window.EMBEDDED_DATA){        // primero: datos embebidos (modo archivo local)
  DATA = window.EMBEDDED_DATA;
} else {
  fetch("data/predictions.json") // fallback: fetch (modo servidor)
}
```

**Toggle Manual/FIFA:** controlado por `FIFA_MODE` (bool global). `setupToggle()` lo habilita solo si `DATA.has_fifa_data && DATA.predictions_fifa`.

**Funciones de render:** `renderAll()` → llama a `setupToggle`, `renderStats`, `renderChampionList`, `renderFeaturedMatch`, `renderMatchesList`, `renderGroups`, `renderResults`.

---

### `data/squads.json`
48 equipos con jugadores clave. Formato:
```json
{
  "Argentina": [
    {"name": "Lionel Messi", "pos": "FW", "imp": 100, "fifa_overall": 91},
    ...
  ]
}
```
- `imp` (0-100): importancia táctica del jugador para el equipo
- `fifa_overall` (0-99): overall de FIFA 26

---

### `data/lesiones.json`
Estado de lesiones editable desde el dashboard. Formato:
```json
{
  "Argentina": [],
  "Francia": ["Kylian Mbappé"],
  ...
}
```
Los nombres deben coincidir exactamente con los de `squads.json`.

---

### `data/fifa_combos.bin`
Binario de 4950 bytes (495 × 10). Tabla precalculada de todas las combinaciones válidas de terceros clasificados según el Anexo C del reglamento FIFA 2026. No modificar manualmente.

---

## Qué NO está en el repo (generado automáticamente)

- `data/predictions.json` — generado por `predictor.py`
- `data/cache.json` — caché de la API
- `mundial2026_predictor.html` — HTML con datos embebidos

Para generarlos: `python src/predictor.py`

---

## Problemas conocidos y soluciones

**"Demo — corré predictor.py para datos reales"** en el dashboard:
→ Correr `python src/predictor.py` para generar el HTML con datos embebidos.

**`cache.json` corrupto:**
→ Se auto-recupera solo desde la versión actual de `fetcher.py`. Si tenés una versión vieja, borrá `data/cache.json` manualmente.

**Python no encontrado en Windows:**
→ Asegurarse de que Python esté en el PATH. Probar con `py` en lugar de `python` en los .bat.

**El toggle FIFA 26 está desactivado:**
→ Necesita `data/squads.json` con campo `fifa_overall` en los jugadores.

---

## Setup desde cero

```bash
git clone https://github.com/TU_USUARIO/mundial2026
cd mundial2026
pip install numpy scipy requests
python src/predictor.py
# Abrir mundial2026_predictor.html en el browser
```
