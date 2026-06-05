# 🏆 Mundial 2026 Predictor

Motor de predicción estadística para la Copa del Mundo 2026 (USA · Canada · México). Simula el torneo completo **100.000 veces** usando ratings Elo, distribuciones de Poisson y Monte Carlo, con un dashboard interactivo que se actualiza en tiempo real durante el campeonato.

---

## ✨ Qué hace

- **Simula 100k torneos completos** — fase de grupos, terceros clasificados y bracket de eliminación directa según el [fixture oficial FIFA 2026](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026)
- **Ratings Elo dinámicos** — scrapeados en vivo desde [eloratings.net](http://eloratings.net) o con fallback hardcodeado para los 48 equipos
- **Dos modos de predicción** — Modo Manual (ajustes propios) y Modo FIFA 26 (ponderado por overall de FIFA)
- **Lesiones y bajas** — marcás jugadores lesionados y el modelo ajusta el Elo del equipo automáticamente
- **Partidos en vivo** — se conecta a [football-data.org](https://football-data.org) para traer resultados reales y recalcular probabilidades
- **Dashboard embebido** — HTML autocontenido, sin servidor, abrís el archivo y listo
- **Actualización automática diaria** — tarea programada que busca lesiones, actualiza el modelo y regenera el dashboard

---

## 🖥️ Demo rápida

```bash
# Instalar dependencias (una sola vez)
pip install requests scipy numpy

# Correr el predictor (100k simulaciones, ~5 segundos)
python src/predictor.py

# O modo rápido para testear (10k simulaciones, ~1 segundo)
python src/predictor.py --quick
```

Después abrís `mundial2026_predictor.html` en el browser — el dashboard tiene los datos embebidos, no necesita servidor.

---

## 📁 Estructura

```
mundial2026/
├── src/
│   ├── model.py           → Motor Elo + Poisson + Monte Carlo vectorizado
│   ├── fetcher.py         → API football-data.org + scraping Elo ratings
│   ├── predictor.py       → Orquestador: carga datos, corre simulaciones, genera HTML
│   └── update_ratings.py  → Actualiza ratings Elo post-partido
├── data/
│   ├── squads.json        → Planteles de los 48 equipos con FIFA overall e importancia táctica
│   ├── lesiones.json      → Estado de lesiones por equipo (editable desde el dashboard)
│   └── fifa_combos.bin    → Tabla oficial de combinaciones de terceros (495 combos, Anexo C FIFA)
├── dashboard.html         → Template del dashboard (fuente)
├── actualizar.bat         → Script Windows para actualizar y abrir el dashboard
├── .gitignore
└── README.md
```

> `data/predictions.json` y `mundial2026_predictor.html` se **generan automáticamente** al correr el predictor — no están en el repo.

---

## ⚙️ Cómo funciona

### 1. Ratings Elo
Cada equipo tiene un rating Elo (Argentina ~2141, Curazao ~1570). La probabilidad de victoria se calcula como:

```
P(A gana) = 1 / (1 + 10^((Elo_B - Elo_A) / 400))
```

### 2. Goles esperados (Poisson)
Los goles esperados por equipo se derivan del rating Elo:

```
λ_A = 1.35 × (1 + (P(A) - 0.5))
λ_B = 1.35 × (1 - (P(A) - 0.5))
```

Los marcadores se samplea desde distribuciones Poisson independientes.

### 3. Fase de grupos (vectorizado con NumPy)
Se generan `N × 72` muestras Poisson de golpe. Para cada simulación se rankean los equipos por puntos → diferencia de gol → goles a favor. La vectorización permite correr 100k simulaciones en ~5 segundos en hardware modesto.

### 4. Bracket oficial FIFA 2026
Los 32 clasificados (24 ganadores/subcampeones + **8 mejores terceros**) se asignan al bracket según el Anexo C del reglamento FIFA. Las 495 combinaciones posibles de grupos están precalculadas en `data/fifa_combos.bin`:
- Formato: 10 bytes por entrada = 2 bytes bitmask (little-endian) + 8 bytes de índices de grupo
- Lookup O(1) por bitmask de 12 bits (un bit por grupo A–L)

### 5. Eliminación directa
Cinco rondas (R32 → R16 → QF → SF → Final) simuladas vectorialmente. Los empates se resuelven por penales (50/50).

### 6. Ajuste por lesiones
Cuando un jugador es marcado como lesionado, el Elo del equipo se reduce:

```
Δ_Elo = Σ (imp_jugador / 100) × factor_posición
```

donde `imp` (0–100) refleja la importancia táctica del jugador para el equipo.

### 7. Modo FIFA 26
Con `fifa_overall` activado en `squads.json`, el peso de cada jugador combina su importancia táctica y su overall FIFA. Permite comparar el modelo propio con uno basado en ratings de videojuego.

---

## 🤕 Lesiones activas en el modelo

Estado al inicio del torneo (5 jun 2026):

| Equipo | Jugador | Pos | Imp | Estado |
|--------|---------|-----|-----|--------|
| 🇪🇸 Spain | Lamine Yamal | FW | 98 | Isquiotibial — duda para el debut |
| 🇧🇷 Brazil | Neymar | FW | 80 | Desgarro pantorrilla grado 2 |
| 🇺🇾 Uruguay | Giorgian de Arrascaeta | MF | 85 | Pantorrilla — se pierde fase de grupos |
| 🇨🇦 Canada | Alphonso Davies | DF | 92 | Isquiotibial — duda para el debut |
| 🇦🇹 Austria | Christoph Baumgartner | MF | 75 | Lesión muscular — descartado del torneo |

Bajas confirmadas **no incluidas** porque ya no figuran en las convocatorias oficiales:
- 🇧🇷 Éder Militão (cirugía bíceps femoral) · Rodrygo (LCA)
- 🇫🇷 Hugo Ekitike (tendón de Aquiles)
- 🇩🇪 Serge Gnabry (aductor)
- 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Billy Gilmour (rodilla)

---

## 📊 Dashboard

El dashboard es un HTML 100% autocontenido generado por `predictor.py`. Incluye:

- **Ranking de campeones** con probabilidades por ronda (R32 → Final)
- **Toggle Manual / FIFA 26** para comparar los dos modelos
- **Próximos partidos** con probabilidades win/draw/loss y marcadores más probables
- **Resultados recientes** ingresados desde la API
- **Tabla de grupos** con clasificación simulada
- **Planteles con lesiones** — marcá bajas y el modelo se recalcula
- **Ajustes manuales de Elo** por equipo

---

## 🔄 Actualización automática de lesiones

El proyecto incluye una tarea programada que corre diariamente y de forma autónoma:

1. Busca noticias de lesiones de las últimas 24hs (múltiples fuentes)
2. Cruza contra `squads.json` (nombres exactos)
3. Agrega solo bajas **100% confirmadas** a `lesiones.json`
4. Regenera `mundial2026_predictor.html`
5. Genera un reporte con: confirmadas agregadas / dudas / ya en el modelo

Para actualizaciones manuales: editá `data/lesiones.json` directamente y volvé a correr `predictor.py`.

---

## 🔑 API key (opcional)

Sin key funciona igual — usa fixture hardcodeado y Elo scrapeado. Con key tenés resultados en tiempo real:

1. Registrarse gratis en [football-data.org](https://www.football-data.org/)
2. Setear la variable de entorno:

```bash
# Linux / macOS
export FOOTBALL_DATA_KEY=tu_key_aqui

# Windows (cmd)
set FOOTBALL_DATA_KEY=tu_key_aqui

# Windows (PowerShell)
$env:FOOTBALL_DATA_KEY="tu_key_aqui"
```

---

## 🗂️ Formato de datos

### `squads.json`
```json
{
  "Argentina": [
    { "name": "Lionel Messi", "pos": "FW", "imp": 100, "fifa_overall": 91 },
    { "name": "Emiliano Martinez", "pos": "GK", "imp": 90, "fifa_overall": 89 }
  ]
}
```
- `pos`: GK / DF / MF / FW
- `imp` (0–100): importancia táctica del jugador para el equipo
- `fifa_overall` (0–99): overall de FIFA 26 (activa el modo FIFA si está presente)

### `lesiones.json`
```json
{
  "Argentina": [],
  "France": ["Kylian Mbappe"],
  "Brazil": ["Neymar"]
}
```
Los nombres deben coincidir exactamente con `squads.json` (mayúsculas, tildes, todo).

---

## 🛠️ Dependencias

```
python >= 3.9
numpy
scipy
requests
```

```bash
pip install numpy scipy requests
```

---

## 📝 Licencia

MIT — hacé lo que quieras con el código.
