#!/usr/bin/env python3
"""
Polymarket Data Logger
Haalt prijzen, spreads en volume op voor geselecteerde markten.
Slaat op in CSV bestand.
"""

import requests
import csv
import os
from datetime import datetime, timezone

# === CONFIGURATIE ===
# Voeg hier market slugs toe die je wil volgen
# Vind slugs in de URL op polymarket.com (bijv. polymarket.com/event/fed-decision-january → slug = "fed-decision-january")
MARKET_SLUGS = [
    "fed-decision-in-january",
    "who-will-trump-nominate-as-fed-chair",
    "us-strikes-iran-by",
]

# Gamma API voor markt metadata
GAMMA_API = "https://gamma-api.polymarket.com"
# CLOB API voor orderbook data
CLOB_API = "https://clob.polymarket.com"

DATA_FILE = "data.csv"


def get_market_info(slug: str) -> dict | None:
    """Haal markt info op via Gamma API."""
    try:
        # Probeer eerst als event slug
        resp = requests.get(f"{GAMMA_API}/events?slug={slug}", timeout=10)
        if resp.ok and resp.json():
            event = resp.json()[0]
            # Pak eerste market van het event
            if event.get("markets"):
                market = event["markets"][0]
                return {
                    "slug": slug,
                    "question": market.get("question", event.get("title", slug)),
                    "token_id": market.get("clobTokenIds", [""])[0] if market.get("clobTokenIds") else "",
                    "condition_id": market.get("conditionId", ""),
                }
        
        # Probeer als market slug
        resp = requests.get(f"{GAMMA_API}/markets?slug={slug}", timeout=10)
        if resp.ok and resp.json():
            market = resp.json()[0]
            return {
                "slug": slug,
                "question": market.get("question", slug),
                "token_id": market.get("clobTokenIds", [""])[0] if market.get("clobTokenIds") else "",
                "condition_id": market.get("conditionId", ""),
            }
    except Exception as e:
        print(f"Fout bij ophalen markt {slug}: {e}")
    
    return None


def get_orderbook(token_id: str) -> dict:
    """Haal orderbook data op via CLOB API."""
    result = {
        "best_bid": None,
        "best_ask": None,
        "spread": None,
        "bid_depth": 0,
        "ask_depth": 0,
    }
    
    if not token_id:
        return result
    
    try:
        resp = requests.get(f"{CLOB_API}/book?token_id={token_id}", timeout=10)
        if resp.ok:
            book = resp.json()
            bids = book.get("bids", [])
            asks = book.get("asks", [])
            
            if bids:
                result["best_bid"] = float(bids[0].get("price", 0))
                result["bid_depth"] = sum(float(b.get("size", 0)) for b in bids)
            
            if asks:
                result["best_ask"] = float(asks[0].get("price", 0))
                result["ask_depth"] = sum(float(a.get("size", 0)) for a in asks)
            
            if result["best_bid"] and result["best_ask"]:
                result["spread"] = round(result["best_ask"] - result["best_bid"], 4)
    
    except Exception as e:
        print(f"Fout bij ophalen orderbook: {e}")
    
    return result


def get_price(token_id: str) -> dict:
    """Haal midpoint prijs op."""
    result = {"price": None, "midpoint": None}
    
    if not token_id:
        return result
    
    try:
        resp = requests.get(f"{CLOB_API}/midpoint?token_id={token_id}", timeout=10)
        if resp.ok:
            data = resp.json()
            result["midpoint"] = float(data.get("mid", 0))
            result["price"] = result["midpoint"]
    except Exception as e:
        print(f"Fout bij ophalen prijs: {e}")
    
    return result


def write_to_csv(rows: list[dict]):
    """Schrijf data naar CSV bestand."""
    file_exists = os.path.exists(DATA_FILE)
    
    fieldnames = [
        "timestamp",
        "slug", 
        "question",
        "price",
        "best_bid",
        "best_ask", 
        "spread",
        "bid_depth",
        "ask_depth",
    ]
    
    with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerows(rows)


def main():
    """Hoofdfunctie: haal data op voor alle markten."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    
    print(f"[{timestamp}] Data ophalen voor {len(MARKET_SLUGS)} markten...")
    
    for slug in MARKET_SLUGS:
        market = get_market_info(slug)
        
        if not market:
            print(f"  ⚠ Markt niet gevonden: {slug}")
            continue
        
        token_id = market.get("token_id", "")
        orderbook = get_orderbook(token_id)
        price_data = get_price(token_id)
        
        row = {
            "timestamp": timestamp,
            "slug": slug,
            "question": market.get("question", "")[:100],  # Trunceer lange vragen
            "price": price_data.get("price"),
            "best_bid": orderbook.get("best_bid"),
            "best_ask": orderbook.get("best_ask"),
            "spread": orderbook.get("spread"),
            "bid_depth": round(orderbook.get("bid_depth", 0), 2),
            "ask_depth": round(orderbook.get("ask_depth", 0), 2),
        }
        
        rows.append(row)
        print(f"  ✓ {slug}: prijs={row['price']}, spread={row['spread']}")
    
    if rows:
        write_to_csv(rows)
        print(f"  → {len(rows)} rijen geschreven naar {DATA_FILE}")
    else:
        print("  ⚠ Geen data om te schrijven")


if __name__ == "__main__":
    main()
