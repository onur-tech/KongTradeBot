"""
Weather Paper Trading Simulator
Zeigt: Hätten wir diese Opportunity gekauft — was wäre passiert?
Simuliert verschiedene Einsatzgrößen: $1, $2, $5, $10
"""

import json
import requests
from datetime import datetime, timedelta

# Simulierte Einsatzgrößen testen
STAKE_SIZES = [1, 2, 5, 10]

def get_market_resolution(city: str, date: str, temp: str) -> dict:
    """Prüft wie ein Markt aufgelöst hat."""
    try:
        r = requests.get(
            f"https://gamma-api.polymarket.com/markets?"
            f"_q=temperature+{city}&closed=true&limit=20",
            timeout=10)
        markets = r.json() if r.ok else []
        for m in markets:
            q = m.get('question', '').lower()
            if city.lower() in q and date in q:
                return {
                    'resolved': True,
                    'winner': m.get('outcomes', []),
                    'question': m.get('question', '')
                }
    except Exception as e:
        return {'resolved': False, 'error': str(e)}
    return {'resolved': False}

def get_real_temperature(lat: float, lon: float, date: str) -> float | None:
    """Holt echte historische Temperatur von OpenMeteo."""
    try:
        r = requests.get(
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={lat}&longitude={lon}"
            f"&start_date={date}&end_date={date}"
            f"&daily=temperature_2m_max&timezone=auto",
            timeout=10)
        data = r.json() if r.ok else {}
        temps = data.get('daily', {}).get('temperature_2m_max', [])
        return temps[0] if temps else None
    except:
        return None

def simulate_trade(opportunity: dict) -> dict:
    """
    Simuliert einen Trade und berechnet Ergebnis.

    Beispiel opportunity:
    {
        'city': 'Istanbul',
        'date': '2026-04-20',
        'predicted_temp': 16.2,
        'market_price_cents': 6,
        'market_question': 'Highest temp Istanbul 16C?',
        'lat': 41.01, 'lon': 28.97
    }
    """
    city = opportunity['city']
    date = opportunity['date']
    price = opportunity['market_price_cents'] / 100
    predicted = opportunity['predicted_temp']

    # Echte Temperatur holen
    real_temp = get_real_temperature(
        opportunity.get('lat', 0),
        opportunity.get('lon', 0),
        date)

    # Gewonnen oder verloren?
    # Vereinfacht: wenn echte Temp in 1°C Nähe von Vorhersage = WON
    won = False
    if real_temp is not None:
        diff = abs(real_temp - predicted)
        won = diff <= 1.0

    # Berechne ROI für verschiedene Einsatzgrößen
    results = {}
    for stake in STAKE_SIZES:
        if won:
            payout = stake / price  # Payout bei Gewinn
            profit = payout - stake
            roi = (profit / stake) * 100
        else:
            profit = -stake
            roi = -100

        results[f'stake_{stake}'] = {
            'profit': round(profit, 2),
            'roi_pct': round(roi, 1),
            'payout': round(stake / price if won else 0, 2)
        }

    return {
        'city': city,
        'date': date,
        'predicted_temp': predicted,
        'real_temp': real_temp,
        'market_price_cents': opportunity['market_price_cents'],
        'won': won,
        'results': results
    }

def run_paper_trading_report(opportunities: list) -> None:
    """Erstellt vollständigen Paper Trading Report."""

    print("=" * 60)
    print("WEATHER PAPER TRADING REPORT")
    print(f"Analysiert: {len(opportunities)} Opportunities")
    print("=" * 60)

    wins = losses = 0
    total_profit_2 = 0  # Bei $2 Einsatz
    all_results = []

    for opp in opportunities:
        print(f"\n[+] {opp['city']} -- {opp['date']}")
        print(f"   Vorhersage: {opp['predicted_temp']}°C @ {opp['market_price_cents']}¢")

        result = simulate_trade(opp)
        all_results.append(result)

        real = result['real_temp']
        if real is not None:
            print(f"   Echte Temp: {real:.1f}°C")
            diff = abs(real - opp['predicted_temp'])
            print(f"   Differenz:  {diff:.1f}°C")
        else:
            print(f"   Echte Temp: N/A (OpenMeteo Fehler oder Datum in Zukunft)")

        outcome = "GEWONNEN" if result['won'] else "VERLOREN"
        print(f"   Ergebnis:   {outcome}")

        print(f"\n   {'Einsatz':>8} | {'Gewinn':>8} | {'ROI':>8} | {'Payout':>8}")
        print(f"   {'-'*40}")
        for stake in STAKE_SIZES:
            r = result['results'][f'stake_{stake}']
            profit_str = f"+${r['profit']:.2f}" if r['profit'] > 0 else f"-${abs(r['profit']):.2f}"
            roi_str = f"{r['roi_pct']:+.0f}%"
            payout_str = f"${r['payout']:.2f}" if result['won'] else "$0.00"
            print(f"   ${stake:>7} | {profit_str:>8} | {roi_str:>8} | {payout_str:>8}")

        if result['won']:
            wins += 1
            total_profit_2 += result['results']['stake_2']['profit']
        else:
            losses += 1
            total_profit_2 += result['results']['stake_2']['profit']

    # Zusammenfassung
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0

    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"Wins:      {wins}/{total} ({win_rate:.0f}%)")
    print(f"Losses:    {losses}/{total}")
    print(f"Gesamt P&L bei $2 Einsatz: ${total_profit_2:+.2f}")

    # Empfehlung
    print("\n--- EMPFEHLUNG ---")
    if win_rate >= 60 and total_profit_2 > 0:
        print("JA - LIVE schalten empfohlen (Win Rate + positiver P&L)")
    elif win_rate >= 50:
        print("ABWARTEN - Noch mehr DRY_RUN Daten sammeln (Win Rate grenzwertig)")
    else:
        print("NEIN - DRY_RUN fortsetzen (Win Rate zu niedrig)")

    # JSON Export
    output = {
        'timestamp': datetime.utcnow().isoformat(),
        'opportunities_analyzed': total,
        'wins': wins,
        'losses': losses,
        'win_rate_pct': round(win_rate, 1),
        'total_profit_2usd': round(total_profit_2, 2),
        'details': all_results
    }
    with open('scripts/weather_paper_trading_results.json', 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nErgebnisse gespeichert: scripts/weather_paper_trading_results.json")


if __name__ == '__main__':
    # Bekannte DRY_RUN Opportunities aus dem Bot-Log
    # Koordinaten: lat/lon aus core/weather_scout.py CITIES dict
    opportunities = [
        {
            'city': 'Istanbul',
            'date': '2026-04-20',
            'predicted_temp': 16.2,
            'market_price_cents': 6,
            'market_question': 'Will the highest temperature in Istanbul be 16°C on April 20?',
            'lat': 41.01,
            'lon': 28.95
        },
        {
            'city': 'Helsinki',
            'date': '2026-04-20',
            'predicted_temp': 12.5,
            'market_price_cents': 8,
            'market_question': 'Will the highest temperature in Helsinki be 12°C on April 20?',
            'lat': 60.17,
            'lon': 24.94
        },
        {
            'city': 'Beijing',
            'date': '2026-04-20',
            'predicted_temp': 24.0,
            'market_price_cents': 11,
            'market_question': 'Will the highest temperature in Beijing be 24°C on April 20?',
            'lat': 39.91,
            'lon': 116.39
        },
    ]

    run_paper_trading_report(opportunities)
