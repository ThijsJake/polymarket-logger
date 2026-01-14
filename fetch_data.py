#!/usr/bin/env python3
"""
Polymarket Data Logger v2
Haalt prijzen, spreads en volume op voor geselecteerde markten.
"""

import requests
import csv
import os
from datetime import datetime, timezone

# === CONFIGURATIE ===
MARKET_SLUGS = [
    "fed-decision-in-january",
    "who-will-trump-nominate-as-fed-chair",
    "us-strikes-iran-by",
]

GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"
DATA_FILE = "data.csv"


def get_markets_for_event(slug: str) -> list[dict]:
    """Haal alle markets op voor een event slug."""
    markets = []
    
    try:
        # Haal event op met alle markets
        resp = requests.get(f"{GAMMA_API}/events?slug={slug}", timeout=10)
        if resp.ok and resp.json():
            event = resp.json()[0]
            
            for market in event.get("markets", []):
                # Haal token IDs - dit zijn YES en NO tokens
                clob_token_ids = market.get("clobTokenIds", [])
                
                if clob_token_ids and len(clob_token_ids) > 0:
                    # Eerste token is meestal YES
                    markets.append({
                        "slug": slug,
                        "question": market.get("question", ""),
                        "token_id": clob_token_ids[0],  # YES token
                        "outcome": market.get("outcomes", ["Yes"])[0] if market.get("outcomes") else "Yes",
                    })
            
            # Als geen markets met tokens, probeer event-level data
            if not markets and event.get("markets"):
                market = event["markets"][0]
                # Probeer outcomePrices te gebruiken als fallback
                outcome_prices = market.get("outcomePrices", "")
                if outcome_prices:
                    try:
                        prices = eval(outcome_prices) if isinstance(outcome_prices, str) else outcome_prices
                        if prices and len(prices) > 0:
                            markets.append({
                                "slug": slug,
                                "question": market.get("question", event.get("title", slug)),
                                "token_id": None,
                                "outcome": "Yes",
                                "price_from_gamma": float(prices[0]) if prices[0] else None,
                            })
                    except:
                        pass
                        
    except Exception as e:
        print(f"  Fout bij ophalen event {slug}: {e}")
    
    return markets


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
        print(f"  Fout bij ophalen orderbook: {e}")
    
    return result


def get_midpoint(token_id: str) -> float | None:
    """Haal midpoint prijs op."""
    if not token_id:
        return None
    
    try:
        resp = requests.get(f"{CLOB_API}/midpoint?token_id={token_id}", timeout=10)
        if resp.ok:
            data = resp.json()
            return float(data.get("mid", 0))
    except Exception as e:
        print(f"  Fout bij ophalen midpoint: {e}")
    
    return None


def get_price_from_gamma(slug: str) -> dict | None:
    """Fallback: haal prijs direct uit Gamma API."""
    try:
        resp = requests.get(f"{GAMMA_API}/events?slug={slug}", timeout=10)
        if resp.ok and resp.json():
            event = resp.json()[0]
            if event.get("markets"):
                market = event["markets"][0]
                outcome_prices = market.get("outcomePrices", "")
                
                # Parse outcome prices
                if outcome_prices:
                    if isinstance(outcome_prices, str):
                        # Format: '["0.95","0.05"]' of '[0.95,0.05]'
                        prices = eval(outcome_prices)
                    else:
                        prices = outcome_prices
                    
                    if prices and len(prices) > 0:
                        return {
                            "question": market.get("question", event.get("title", slug)),
                            "price": float(prices[0]) if prices[0] else None,
                            "volume": market.get("volume", "0"),
                            "liquidity": market.get("liquidity", "0"),
                        }
    except Exception as e:
        print(f"  Fout bij Gamma fallback voor {slug}: {e}")
    
    return None


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
        "volume",
        "liquidity",
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
        print(f"  Processing: {slug}")
        
        # Probeer eerst via CLOB (orderbook data)
        markets = get_markets_for_event(slug)
        
        if markets and markets[0].get("token_id"):
            # We hebben token IDs - gebruik CLOB API
            market = markets[0]  # Pak eerste market/outcome
            token_id = market["token_id"]
            
            orderbook = get_orderbook(token_id)
            midpoint = get_midpoint(token_id)
            
            row = {
                "timestamp": timestamp,
                "slug": slug,
                "question": market.get("question", "")[:100],
                "price": midpoint,
                "best_bid": orderbook.get("best_bid"),
                "best_ask": orderbook.get("best_ask"),
                "spread": orderbook.get("spread"),
                "bid_depth": round(orderbook.get("bid_depth", 0), 2),
                "ask_depth": round(orderbook.get("ask_depth", 0), 2),
                "volume": "",
                "liquidity": "",
            }
            print(f"    ✓ CLOB: prijs={midpoint}, spread={orderbook.get('spread')}")
            
        else:
            # Fallback naar Gamma API (alleen prijs, geen orderbook)
            gamma_data = get_price_from_gamma(slug)
            
            if gamma_data:
                row = {
                    "timestamp": timestamp,
                    "slug": slug,
                    "question": gamma_data.get("question", "")[:100],
                    "price": gamma_data.get("price"),
                    "best_bid": None,
                    "best_ask": None,
                    "spread": None,
                    "bid_depth": 0,
                    "ask_depth": 0,
                    "volume": gamma_data.get("volume", ""),
                    "liquidity": gamma_data.get("liquidity", ""),
                }
                print(f"    ✓ Gamma: prijs={gamma_data.get('price')}")
            else:
                print(f"    ⚠ Geen data gevonden")
                continue
        
        rows.append(row)
    
    if rows:
        write_to_csv(rows)
        print(f"\n→ {len(rows)} rijen geschreven naar {DATA_FILE}")
    else:
        print("\n⚠ Geen data om te schrijven")


if __name__ == "__main__":
    main()
