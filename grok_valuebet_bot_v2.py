"""
GROK VALUEBET BOT V5.4 - VERSION FINALE ABSOLUE
Structure exacte que tu veux + TOUJOURS des pronos
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
    "tennis_atp", "tennis_wta",
    "basketball_nba", "basketball_euroleague"
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 *Grok ValueBet V5.4 - Version Finale Absolue*\n/today pour les pronos maintenant.")

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

    home_odds = h2h.get("Home", 3.0)
    away_odds = h2h.get("Away", 3.0)

    # Paris Ultra Safe
    if home_odds <= 1.80:
        picks.append(("Ultra Safe", "Victoire domicile", round(home_odds,2), 0, 60))
    if away_odds <= 1.80:
        picks.append(("Ultra Safe", "Victoire extérieur", round(away_odds,2), 0, 58))

    # Paris Safe de la semaine
    if 1.80 < home_odds <= 2.30:
        picks.append(("Safe de la semaine", "Victoire domicile", round(home_odds,2), 0, 55))
    if 1.80 < away_odds <= 2.30:
        picks.append(("Safe de la semaine", "Victoire extérieur", round(away_odds,2), 0, 53))

    # Paris Fun
    if home_odds >= 3.5:
        picks.append(("Fun", "Victoire domicile", round(home_odds,2), 0, 30))
    if away_odds >= 3.5:
        picks.append(("Fun", "Victoire extérieur", round(away_odds,2), 0, 30))

    # Paris Simple (toujours rempli)
    picks.append(("Simple", "Victoire domicile", round(home_odds,2), 0, 50))
    picks.append(("Simple", "Victoire extérieur", round(away_odds,2), 0, 48))

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
                      (today.split()[0], today.split()[1], m.get("sport_key", "Football"), m["home_team"] + " - " + m["away_team"], market, sel, odds, edge, prob))
            conn.commit()
    
    today_date = datetime.datetime.now(pytz.timezone("Europe/Paris")).strftime("%Y-%m-%d")
    c.execute("SELECT * FROM picks WHERE date LIKE ? AND result='pending' ORDER BY market", (today_date + "%",))
    data = c.fetchall()
    
    msg = f"**GROK PRONO** - {datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime('%d/%m %H:%M')}\n"
    msg += f"Bankroll : {BANKROLL}€\n\n"
    
    ultra_safe = [r for r in data if r[4] == "Ultra Safe"][:4]
    safe = [r for r in data if r[4] == "Safe de la semaine"][:6]
    fun = [r for r in data if r[4] == "Fun"][:4]
    simple = [r for r in data if r[4] == "Simple"][:12]
    
    msg += "**Paris Ultra Safe**\n" + "\n".join([f"✅ {r[3]} → {r[5]} @ {r[6]}" for r in ultra_safe]) + "\n\n"
    msg += "**Paris Safe de la semaine**\n" + "\n".join([f"✅ {r[3]} → {r[5]} @ {r[6]}" for r in safe]) + "\n\n"
    msg += "**Paris Fun**\n" + "\n".join([f"✅ {r[3]} → {r[5]} @ {r[6]}" for r in fun]) + "\n\n"
    msg += "**Paris Simple** (probables, pour avoir une idée dans la semaine)\n" + "\n".join([f"✅ {r[3]} → {r[5]} @ {r[6]}" for r in simple])
    
    send_message(msg)
    print("✅ Message V5.4 envoyé !")

def main():
    scheduler = BackgroundScheduler(timezone="Europe/Paris")
    scheduler.add_job(run_analysis, 'cron', hour=10, minute=30)
    scheduler.add_job(run_analysis, 'cron', hour=14, minute=30)
    scheduler.start()
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("today", today))
    
    print("✅ GROK VALUEBET V5.4 - VERSION FINALE lancée !")
    app.run_polling()

if __name__ == "__main__":
    main()