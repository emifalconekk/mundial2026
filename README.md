# 🏆 Mundial 2026 Predictor

Motor de predicción estadística para la Copa del Mundo 2026 (USA · Canada · México). Simula el torneo completo **100.000 veces** usando ratings Elo, distribuciones de Poisson y Monte Carlo, con un dashboard interactivo que se actualiza en tiempo real durante el campeonato.

---

## ✨ Qué hace

- **Simula 100k torneos completos** — fase de grupos, terceros clasificados y bracket de eliminación directa según el [fixture oficial FIFA 2026](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026)
- **Ratings Elo dinámicos** — scrapeados en vivo desde [eloratings.net](http://eloratings.net) o con fallback hardcodeado para los 48 equipos
- **Dos modos de predicción** — Modo Manual (ajustes propios) y Modo FIFA 26 (ponderado por overall de FIFA)
- **Lesiones y bajas** — podés marcar jugadores lesionados y el modelo ajusta el Elo del equipo automáticamente
- **Partidos en vivo** — se conecta a [football-data.org](https://football-data.org) para traer resultados reales y recalcular probabilidades
- **Dashboard embebido** — HTML autocontenido, sin servidor, abrís el archivo y listo

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
│   ├── model.py          → Motor Elo + Poisson + Monte Carlo vectorizado
│   ├── fetcher.py        → API football-data.org + scraping Elo ratings
│   └── predictor.py      → Orquestador: carga datos, corre simulaciones, genera HTML
├── data/
│   ├── squads.json       → Planteles de los 48 equipos con FIFA overall e importancia
│   ├── lesiones.json     → Estado de lesiones por equipo (editable desde el dashboard)
│   └── fifa_combos.bin   → Tabla oficial de combinaciones de terceros (495 combos, Anexo C FIFA)
├── dashboard.html        → Template del dashboard (fuente)
├── actualizar.bat        → Script Windows para actualizar y abrir el dashboard
├── .gitignore
└── README.md
```

> `data/predictions.json` y `mundial2026_predictor.html` se **generan automáticamente** al correr el predictor — no están en el repo.

---

## ⚙️ Cómo funciona

### 1. Ratings Elo
Cada equipo tiene un rating Elo (base ~2141 Argentina, ~1570 Curazao). La probabilidad de victoria se calcula como:

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

### 3. Fase de grupos (vectorizado)
Se generan N × 72 muestras Poisson de golpe con NumPy. Para cada simulación se rankean los equipos por puntos → diferencia de gol → goles a favor.

### 4. Bracket oficial FIFA 2026
Los 32 clasificados (24 ganadores/subcampeones + **8 mejores terceros**) se asignan al bracket según el Anexo C del reglamento FIFA. Las 495 combinaciones posibles de grupos están precalculadas en `data/fifa_combos.bin` (lookup O(1) por bitmask).

### 5. Eliminación directa
Cinco rondas (R32 → R16 → QF → SF → Final) también simuladas vectorialmente. Los empates se resuelven por penales (50/50).

### 6. Modo FIFA 26
Cuando está activo, el Elo de cada jugador se pondera por su FIFA overall y su importancia táctica para el equipo. Un equipo con titulares lesionados pierde Elo proporcionalmente.

---

## 🔑 API key (opcional)

Sin key funciona igual — usa fixture hardcodeado y Elo scrapeado. Con key tenés más llamadas y datos en tiempo real:

1. Registrarse gratis en [football-data.org](https://www.football-data.org/)
2. Copiar la API key
3. Setear la variable de entorno:

```bash
# Linux / macOS
export FOOTBALL_DATA_KEY=tu_key_aqui

# Windows (cmd)
set FOOTBALL_DATA_KEY=tu_key_aqui

# Windows (PowerShell)
$env:FOOTBALL_DATA_KEY="tu_key_aqui"
```

---

## 📊 Dashboard

El dashboard es un HTML 100% autocontenido (sin dependencias externas) generado por `predictor.py`. Incluye:

- **Ranking de campeones** con probabilidades por ronda (R32 → Final)
- **Toggle Manual / FIFA 26** para comparar los dos modelos
- **Próximos partidos** con probabilidades y marcadores más probables
- **Resultados recientes** ingresados desde la API
- **Tabla de grupos** con clasificación simulada
- **Planteles** — marcá lesionados y el modelo se recalcula automáticamente
- **Ajustes manuales de Elo** por equipo

---

## 🛠️ Dependencias

```
python >= 3.9
numpy
scipy
requests
```

Instalar con:
```bash
pip install numpy scipy requests
```

---

## 📝 Licencia

MIT — hacé lo que quieras con el código.
