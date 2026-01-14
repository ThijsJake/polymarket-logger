# Polymarket Data Logger

Automatisch Polymarket prijzen, spreads en orderbook depth loggen via GitHub Actions.

## Wat het doet

- Elke 5 minuten data ophalen voor geconfigureerde markten
- Opslaan in `data.csv` in deze repo
- Gratis (binnen GitHub Actions limits)

## Data die wordt gelogd

| Kolom | Beschrijving |
|-------|-------------|
| timestamp | UTC tijdstip |
| slug | Markt identifier |
| question | Markt vraag |
| price | Huidige prijs (midpoint) |
| best_bid | Beste biedprijs |
| best_ask | Beste laatprijs |
| spread | Verschil ask - bid |
| bid_depth | Totaal volume aan bids |
| ask_depth | Totaal volume aan asks |

## Setup

### 1. Fork of kopieer deze repo

Klik "Use this template" of fork naar je eigen account.

### 2. Enable Actions

Ga naar Settings → Actions → General → Stel in op "Allow all actions".

### 3. Pas markten aan (optioneel)

Edit `fetch_data.py` en verander `MARKET_SLUGS`:

```python
MARKET_SLUGS = [
    "fed-decision-january",      # Fed rentebesluit
    "trump-nominate-fed-chair",  # Fed Chair nominatie
    "us-strikes-iran",           # Geopolitiek
]
```

Vind slugs in Polymarket URLs, bijv:
- `polymarket.com/event/fed-decision-january` → slug = `fed-decision-january`

### 4. Trigger handmatig (voor test)

Ga naar Actions → "Polymarket Data Logger" → "Run workflow"

### 5. Check data

Na een paar runs verschijnt `data.csv` in je repo.

## Data analyseren

Download `data.csv` en open in Excel, of:

```python
import pandas as pd
df = pd.read_csv("data.csv")
df.plot(x="timestamp", y="price")
```

## Kosten

Gratis binnen GitHub Free tier (2000 minuten/maand).
Dit script gebruikt ~10 sec per run = ~600 runs/dag mogelijk.

## Limieten

- GitHub Actions schedule is minimum elke 5 min
- Kan vertraagd worden bij drukte op GitHub (soms 10-15 min)
- Voor snellere data: overweeg Oracle Cloud Free Tier

## Troubleshooting

**Actions draaien niet?**
- Check dat Actions enabled zijn in repo settings
- Eerste scheduled run kan tot 1 uur duren

**Geen data voor een markt?**
- Check of slug correct is
- Markt moet actief zijn op Polymarket
