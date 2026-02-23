"""
GROK VALUEBET BOT V5.2 - VERSION FINALE ABSOLUE
Toujours des pronos garantis
"""

import os
import sqlite3
import requests
import datetime
import pytz
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
CHAT_ID = os.getenv("CHAT_ID")
BANKROLL = float(os.getenv("BANKROLL", "200"))

DB = "grok_bet_v5.db"
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS picks (date TEXT, time TEXT, sport TEXT, match TEXT, market TEXT, selection TEXT, odds REAL, edge REAL, prob REAL, result TEXT DEFAULT 'pending')''')
conn.commit()

SPORTS = [
    "soccer_france_ligue_one", "soccer_france_ligue_two",
    "soccer_spain_la_liga", "soccer_spain_segunda_division",
    "soccer_italy_serie_a", "soccer_italy_serie_b",
    "soccer_england_premier_league", "soccer_england_championship",
    "soccer_germany_bundesliga", "soccer_germany_2_bundesliga",
    "soccer_netherlands_eredivisie", "soccer_portugal_primeira_liga",
    "tennis_atp", "tennis_wta",
    "basketball_nba", "basketball_euroleague"
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 *Grok ValueBet V5.2 - Version Finale Absolue*\n/today pour les pronos maintenant.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 /today → Pronos immédiats\n/help → Aide\n/stats → Infos")

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Analyse en cours...")
    run_analysis()

def fetch_odds(days=8):
    matches = []
    max_date = datetime.datetime.now(pytz.utc) + datetime.timedelta(days=days)
    for sport in SPORTS:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
        params = {"apiKey": ODDS_API_KEY, "regions": "eu", "bookmakers": "winamax_fr", "markets": "h2h", "oddsFormat": "decimal"}
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                for m in r.json():
                    commence = datetime.datetime.fromisoformat(m["commence_time"].replace("Z", "+00:00"))
                    if commence < max_date:
                        matches.append(m)
        except:
            pass
    return matches[:100]

def calculate_picks(match):
    picks = []
    h2h = None
    for bm in match.get("bookmakers", []):
        if bm["key"] != "winamax_fr": continue
        for market in bm["markets"]:
            if market["key"] == "h2h":
                h2h = {o["name"]: o["price"] for o in market["outcomes"]}
    
    if not h2h: return picks

    # Pronos du Jour - TOUJOURS REMPLI (le favori de chaque match)
    home_odds = h2h.get("Home", 3.0)
    away_odds = h2h.get("Away", 3.0)
    
    if home_odds <= away_odds:
        picks.append(("Pronos du Jour", "Victoire domicile", round(home_odds,2), 0, 55))
    else:
        picks.append(("Pronos du Jour", "Victoire extérieur", round(away_odds,2), 0, 55))

    # Ultra Safe et Intéressants (optionnels)
    p_home = 1 / home_odds
    p_draw = 1 / h2h.get("Draw", 3.5)
    p_away = 1 / away_odds
    total = p_home + p_draw + p_away
    p_home = p_home / total
    p_draw = p_draw / total
    p_away = p_away / total

    if h2h.get("Home"):
        dc_1x = p_home + p_draw
        odds = round(1 / dc_1x * 0.93, 2)
        edge = round((dc_1x - 1/odds) * 100, 1)
        if edge >= 9 and dc_1x >= 0.62:
            picks.append(("Ultra Safe", "1X", odds, edge, round(dc_1x*100,1)))

    if h2h.get("Away"):
        dc_x2 = p_draw + p_away
        odds = round(1 / dc_x2 * 0.93, 2)
        edge = round((dc_x2 - 1/odds) * 100, 1)
        if edge >= 9 and dc_x2 >= 0.58:
            picks.append(("Ultra Safe", "X2", odds, edge, round(dc_x2*100,1)))

    return picks

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def run_analysis():
    matches = fetch_odds()
    today = datetime.datetime.now(pytz.timezone("Europe/Paris")).strftime("%Y-%m-%d %H:%M")
    
    for m in matches:
        picks = calculate_picks(m)
        for market, sel, odds, edge, prob in picks:
            c.execute("INSERT INTO picks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')",
                      (today.split()[0], today.split()[1], m["sport"], m["home_team"] + " - " + m["away_team"], market, sel, odds, edge, prob))
            conn.commit()
    
    today_date = datetime.datetime.now(pytz.timezone("Europe/Paris")).strftime("%Y-%m-%d")
    c.execute("SELECT * FROM picks WHERE date LIKE ? AND result='pending' ORDER BY edge DESC", (today_date + "%",))
    data = c.fetchall()
    
    msg = f"🔥 **GROK VALUEBET V5.2 - VERSION FINALE** - {datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime('%d/%m %H:%M')}\n"
    msg += f"💰 Bankroll : {BANKROLL:.0f}€\n\n"
    
    ultra_safe = [r for r in data if r[4] == "Ultra Safe"][:4]
    basic = [r for r in data if r[4] == "Pronos du Jour"][:15]
    
    if ultra_safe:
        msg += "🛡️ **ULTRA SAFE**\n" + "\n".join([f"✅ {r[3]} → {r[5]} @ {r[6]}" for r in ultra_safe]) + "\n\n"
    
    msg += "📌 **PRONOS DU JOUR** (toujours rempli)\n"
    for r in basic:
        msg += f"✅ {r[3]} → {r[5]} @ {r[6]}\n"
    
    send_message(msg)
    print("✅ Message V5.2 envoyé !")

def main():
    scheduler = BackgroundScheduler(timezone="Europe/Paris")
    scheduler.add_job(run_analysis, 'cron', hour=10, minute=30)
    scheduler.add_job(run_analysis, 'cron', hour=14, minute=30)
    scheduler.start()
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("today", today))
    
    print("✅ GROK VALUEBET V5.2 - VERSION FINALE lancée !")
    app.run_polling()

if __name__ == "__main__":
    main()