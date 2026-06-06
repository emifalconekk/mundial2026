<div align="center">

# ⚽ Mundial 2026 Predictor

**Motor de simulación estadística para la Copa del Mundo 2026**

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-vectorizado-013243?style=flat&logo=numpy)
![Simulaciones](https://img.shields.io/badge/Simulaciones-100.000-brightgreen?style=flat)
![Equipos](https://img.shields.io/badge/Equipos-48-blue?style=flat)
![License](https://img.shields.io/badge/Licencia-MIT-yellow?style=flat)

Simula el torneo completo **100.000 veces** con Elo + Poisson + Monte Carlo.  
Dashboard HTML interactivo — sin servidor, abrís el archivo y listo.

</div>

---

## 🎯 Qué hace

| Feature | Detalle |
|---------|---------|
| 🎲 **Monte Carlo** | 100k simulaciones completas: grupos → R32 → R16 → QF → SF → Final |
| 📊 **Modelo Elo + Poisson** | Probabilidades de victoria y distribución de goles por partido |
| 🏥 **Ajuste por lesiones** | Marcás bajas y el Elo del equipo cae proporcionalmente |
| 🎮 **Modo FIFA 26** | Segunda simulación ponderada por overall de FIFA 26 |
| 📡 **Datos en vivo** | Resultados reales via football-data.org, recalcula tras cada partido |
| 🤖 **Auto-actualización** | Tarea diaria que busca lesiones, actualiza el modelo y regenera el HTML |

---

## 🚀 Inicio rápido

```bash
git clone https://github.com/emifalconekk/mundial2026
cd mundial2026
pip install numpy scipy requests
python src/predictor.py
```

Abrí `mundial2026_predictor.html` en el browser. Sin servidor, sin configuración extra.

```bash
# Modo rápido para testear (10k simulaciones, ~1 seg)
python src/predictor.py --quick
```

---

## 📁 Estructura

```
mundial2026/
├── src/
│   ├── model.py            Motor Elo + Poisson + Monte Carlo (vectorizado NumPy)
│   ├── fetcher.py          API football-data.org + scraping Elo ratings
│   ├── predictor.py        Orquestador principal → genera el HTML
│   └── update_ratings.py   Actualiza fifa_overall desde api-sports.io
├── data/
│   ├── squads.json         48 planteles con importancia táctica y FIFA overall
│   ├── lesiones.json       Bajas por equipo (se actualiza automáticamente)
│   └── fifa_combos.bin     495 combinaciones de terceros clasificados (Anexo C FIFA)
├── dashboard.html          Template del dashboard
└── actualizar.bat          Atajo Windows para regenerar y abrir
```

> `predictions.json` y `mundial2026_predictor.html` se generan al correr el predictor — no están en el repo.

---

## ⚙️ Cómo funciona el modelo

### Ratings Elo
```
P(A gana) = 1 / (1 + 10^((Elo_B - Elo_A) / 400))
```
Ratings base scrapeados de [eloratings.net](http://eloratings.net). Argentina ~2141 · Curazao ~1570.

### Goles esperados (Poisson)
```
λ_A = 1.35 × (1 + (P(A) - 0.5))
λ_B = 1.35 × (1 - (P(A) - 0.5))
```
Los marcadores se samplea de distribuciones Poisson independientes.

### Fase de grupos vectorizada
Se generan `N × 72` muestras Poisson de golpe con NumPy. 100k torneos en ~5 segundos.

### Bracket oficial FIFA 2026
32 clasificados = 24 primeros/segundos + **8 mejores terceros** según Anexo C del reglamento.  
Las 495 combinaciones posibles están precalculadas en `fifa_combos.bin` → lookup O(1) por bitmask de 12 bits.

### Ajuste por lesiones
```
Δ_Elo = Σ (imp / 100) × factor_posición
```
`imp` (0–100) es la importancia táctica del jugador. Se resta del Elo del equipo.

---

## 🤕 Lesiones activas

> Actualizado automáticamente al inicio del torneo — 5 jun 2026

| # | Equipo | Jugador | Pos | Imp | Estado |
|---|--------|---------|-----|-----|--------|
| 🔴 | 🇪🇸 España | Lamine Yamal | FW | 98 | Isquiotibial — duda para el debut |
| 🟡 | 🇧🇷 Brasil | Neymar | FW | 80 | Desgarro pantorrilla grado 2 |
| 🔴 | 🇺🇾 Uruguay | Giorgian de Arrascaeta | MF | 85 | Se pierde toda la fase de grupos |
| 🟡 | 🇨🇦 Canadá | Alphonso Davies | DF | 92 | Isquiotibial — duda para el debut |
| 🔴 | 🇦🇹 Austria | Christoph Baumgartner | MF | 75 | Descartado del torneo |

Bajas confirmadas ya excluidas de las convocatorias oficiales (no necesitan cargarse):
Éder Militão · Rodrygo · Hugo Ekitike · Serge Gnabry · Billy Gilmour

---

## 📊 Dashboard

El HTML generado es 100% autocontenido. Incluye:

- **Ranking de campeones** — probabilidades por ronda (R32 → Final)
- **Toggle Manual / FIFA 26** — compará los dos modelos en tiempo real
- **Próximos partidos** — probabilidades 1X2 + marcadores más probables
- **Resultados** — se actualizan desde la API tras cada partido
- **Tabla de grupos** — clasificación simulada
- **Planteles** — marcá lesiones, el modelo se recalcula al instante
- **Ajuste de Elo manual** — por equipo

---

## 🔄 Actualización automática de lesiones

Tarea diaria que corre de forma autónoma:

1. Busca noticias de las últimas 24hs en múltiples fuentes
2. Cruza contra `squads.json` (nombre exacto)
3. Agrega solo bajas **100% confirmadas**
4. Regenera `mundial2026_predictor.html`
5. Genera reporte: confirmadas / dudas / ya en el modelo

Para actualizar manualmente: editá `data/lesiones.json` y corré `python src/predictor.py`.

---

## 🔑 API key (opcional)

Sin key funciona con fixture hardcodeado y Elo scrapeado. Con key tenés resultados en tiempo real:

1. Registrate gratis en [football-data.org](https://www.football-data.org/)
2. Setear la variable de entorno:

```bash
# Linux / macOS
export FOOTBALL_DATA_KEY=tu_key

# Windows CMD
set FOOTBALL_DATA_KEY=tu_key

# PowerShell
$env:FOOTBALL_DATA_KEY="tu_key"
```

Para actualizar ratings de jugadores (api-sports.io, 100 req/día gratis):

```bash
export API_FOOTBALL_KEY=tu_key
python src/update_ratings.py
```

---

## 🗂️ Formato de squads.json

```json
{
  "Argentina": [
    { "name": "Lionel Messi",      "pos": "FW", "imp": 100, "fifa_overall": 91 },
    { "name": "Emiliano Martinez", "pos": "GK", "imp": 90,  "fifa_overall": 89 }
  ]
}
```

`pos`: GK / DF / MF / FW  
`imp` (0–100): importancia táctica — cuánto baja el Elo si está lesionado  
`fifa_overall` (0–99): activa el Modo FIFA si está presente en todos los jugadores

---

## 🛠️ Dependencias

```bash
pip install numpy scipy requests
```

Python 3.9+

---

## 📝 Licencia

MIT
