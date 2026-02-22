"""
GROK VALUEBET BOT V3.3 - PRÊT POUR RAILWAY 24/7
"""

import os
import sqlite3
import requests
import datetime
import pytz
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
CHAT_ID = os.getenv("CHAT_ID")
BANKROLL = float(os.getenv("BANKROLL", "200"))

DB = "grok_bet_v3.db"
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS picks (date TEXT, time TEXT, sport TEXT, match TEXT, market TEXT, selection TEXT, odds REAL, edge REAL, prob REAL, result TEXT DEFAULT 'pending')''')
conn.commit()

SPORTS = ["soccer_france_ligue_one", "soccer_france_ligue_two", "soccer_spain_la_liga", "soccer_spain_segunda_division",
          "soccer_italy_serie_a", "soccer_italy_serie_b", "soccer_england_premier_league", "soccer_england_championship"]

def fetch_odds(days=7):
    matches = []
    max_date = datetime.datetime.now(pytz.utc) + datetime.timedelta(days=days)
    for sport in SPORTS:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
        params = {"apiKey": ODDS_API_KEY, "regions": "eu", "bookmakers": "winamax_fr", "markets": "h2h,totals", "oddsFormat": "decimal"}
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                for m in r.json():
                    commence = datetime.datetime.fromisoformat(m["commence_time"].replace("Z", "+00:00"))
                    if commence < max_date:
                        matches.append(m)
        except:
            pass
    return matches[:50]

def calculate_picks(match, is_test=False):
    picks = []
    h2h = None
    totals = None
    for bm in match.get("bookmakers", []):
        if bm["key"] != "winamax_fr": continue
        for market in bm["markets"]:
            if market["key"] == "h2h":
                h2h = {o["name"]: o["price"] for o in market["outcomes"]}
            elif market["key"] == "totals":
                totals = {o["name"]: o["price"] for o in market["outcomes"]}
    
    if not h2h: return picks
    
    p_home = 1 / h2h.get("Home", 3.0)
    p_draw = 1 / h2h.get("Draw", 3.5)
    p_away = 1 / h2h.get("Away", 3.0)
    total = p_home + p_draw + p_away
    p_home = p_home / total
    p_draw = p_draw / total
    p_away = p_away / total
    
    edge_min = 2 if is_test else 9
    
    if h2h.get("Home"):
        dc_1x = p_home + p_draw
        odds = round(1 / dc_1x * 0.93, 2)
        edge = round((dc_1x - 1/odds) * 100, 1)
        if edge >= edge_min and dc_1x >= 0.55:
            picks.append(("Double Chance", "1X", odds, edge, round(dc_1x*100,1)))
    
    if h2h.get("Away"):
        dc_x2 = p_draw + p_away
        odds = round(1 / dc_x2 * 0.93, 2)
        edge = round((dc_x2 - 1/odds) * 100, 1)
        if edge >= edge_min and dc_x2 >= 0.52:
            picks.append(("Double Chance", "X2", odds, edge, round(dc_x2*100,1)))
    
    if totals and "Over 2.5" in totals:
        odds = totals["Over 2.5"]
        p_over = 0.56
        edge = round((p_over - 1/odds) * 100, 1)
        if edge >= edge_min:
            picks.append(("Over/Under", "Over 2.5", round(odds,2), edge, round(p_over*100,1)))
    
    return picks

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def run_analysis(is_test=False):
    matches = fetch_odds()
    today = datetime.datetime.now(pytz.timezone("Europe/Paris")).strftime("%Y-%m-%d %H:%M")
    
    for m in matches:
        picks = calculate_picks(m, is_test)
        for market, sel, odds, edge, prob in picks:
            c.execute("INSERT INTO picks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')",
                      (today.split()[0], today.split()[1], m["sport"], m["home_team"] + " - " + m["away_team"], market, sel, odds, edge, prob))
            conn.commit()
    
    today_date = datetime.datetime.now(pytz.timezone("Europe/Paris")).strftime("%Y-%m-%d")
    c.execute("SELECT * FROM picks WHERE date LIKE ? AND result='pending' ORDER BY edge DESC", (today_date + "%",))
    data = c.fetchall()
    
    mode = "TEST FORCE" if is_test else "NORMAL ULTRA SAFE"
    msg = f"🔥 **GROK V3.3 24/7** - {datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime('%d/%m %H:%M')} ({mode})\n💰 Bankroll : {BANKROLL:.0f}€\n\n"
    
    if not data:
        msg += "😴 Rien d'assez intéressant aujourd'hui (le bot est strict, c'est bien)."
    else:
        safe = [r for r in data if r[7] >= 9][:5]
        realistic = [r for r in data if r[7] >= 4][:7]
        fun = [r for r in data if r[7] >= 10][:4]
        
        msg += "🛡️ **SAFE**\n" + "\n".join([f"✅ {r[3]} → {r[5]} @ {r[6]}" for r in safe]) + "\n\n"
        msg += "💎 **RÉALISTE**\n" + "\n".join([f"✅ {r[3]} → {r[5]} @ {r[6]}" for r in realistic]) + "\n\n"
        msg += "🚀 **FUN**\n" + "\n".join([f"🔥 {r[3]} → {r[5]} @ {r[6]}" for r in fun])
    
    send_message(msg)
    print("Message envoyé !")

def main():
    scheduler = BackgroundScheduler(timezone="Europe/Paris")
    scheduler.add_job(run_analysis, 'cron', hour=10, minute=30, kwargs={'is_test': False})
    scheduler.add_job(run_analysis, 'cron', hour=14, minute=30, kwargs={'is_test': False})
    scheduler.start()
    print("✅ Bot V3.3 lancé 24/7 sur Railway !")
    while True:
        pass  # garde le processus vivant

if __name__ == "__main__":
    main()