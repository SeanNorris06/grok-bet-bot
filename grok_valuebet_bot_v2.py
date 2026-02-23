"""
GROK VALUEBET BOT V4.3 - VERSION ULTRA GÉNÉREUSE
Plus de pronos tous les jours + Ultra Safe strict
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

DB = "grok_bet_v4.db"
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS picks (date TEXT, time TEXT, sport TEXT, match TEXT, market TEXT, selection TEXT, odds REAL, edge REAL, prob REAL, result TEXT DEFAULT 'pending')''')
conn.commit()

SPORTS = ["soccer_france_ligue_one", "soccer_france_ligue_two", "soccer_spain_la_liga", "soccer_spain_segunda_division",
          "soccer_italy_serie_a", "soccer_italy_serie_b", "soccer_england_premier_league", "soccer_england_championship"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 *Grok ValueBet V4.3 est prêt !*\n/today pour les pronos maintenant.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 /today → Pronos immédiats\n/help → Aide\n/stats → Infos")

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Analyse en cours...")
    run_analysis()

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
    return matches[:60]

def calculate_picks(match):
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
    
    # Ultra Safe (strict)
    if h2h.get("Home"):
        dc_1x = p_home + p_draw
        odds = round(1 / dc_1x * 0.93, 2)
        edge = round((dc_1x - 1/odds) * 100, 1)
        if edge >= 9 and dc_1x >= 0.62:
            picks.append(("Ultra Safe", "1X", odds, edge, round(dc_1x*100,1)))
    
    # Picks Intéressants (très généreux)
    if h2h.get("Home"):
        dc_1x = p_home + p_draw
        odds = round(1 / dc_1x * 0.93, 2)
        edge = round((dc_1x - 1/odds) * 100, 1)
        if edge >= 2 and dc_1x >= 0.52:
            picks.append(("Intéressant", "1X", odds, edge, round(dc_1x*100,1)))
    
    if h2h.get("Away"):
        dc_x2 = p_draw + p_away
        odds = round(1 / dc_x2 * 0.93, 2)
        edge = round((dc_x2 - 1/odds) * 100, 1)
        if edge >= 2 and dc_x2 >= 0.52:
            picks.append(("Intéressant", "X2", odds, edge, round(dc_x2*100,1)))
    
    if totals and "Over 2.5" in totals:
        odds = totals["Over 2.5"]
        p_over = 0.56
        edge = round((p_over - 1/odds) * 100, 1)
        if edge >= 3:
            picks.append(("Intéressant", "Over 2.5", round(odds,2), edge, round(p_over*100,1)))
    
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
    
    msg = f"🔥 **GROK VALUEBET V4.3** - {datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime('%d/%m %H:%M')}\n💰 Bankroll : {BANKROLL:.0f}€\n\n"
    
    ultra_safe = [r for r in data if r[4] == "Ultra Safe"][:5]
    interesting = [r for r in data if r[4] == "Intéressant"][:12]
    
    if ultra_safe:
        msg += "🛡️ **ULTRA SAFE**\n"
        for r in ultra_safe:
            msg += f"✅ {r[3]} → {r[5]} @ {r[6]} (proba ~{r[8]}%)\n"
    else:
        msg += "🛡️ Pas d'Ultra Safe aujourd'hui\n\n"
    
    msg += "\n💎 **PICKS INTÉRESSANTS** (bons paris jouables cette semaine)\n"
    for r in interesting:
        msg += f"✅ {r[3]} → {r[5]} @ {r[6]} (edge +{r[7]}%)\n"
    
    if not interesting:
        msg += "😴 Aucun pari trouvé cette semaine (très rare)."
    
    send_message(msg)
    print("✅ Message V4.3 envoyé !")

def main():
    scheduler = BackgroundScheduler(timezone="Europe/Paris")
    scheduler.add_job(run_analysis, 'cron', hour=10, minute=30)
    scheduler.add_job(run_analysis, 'cron', hour=14, minute=30)
    scheduler.start()
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("today", today))
    
    print("✅ GROK VALUEBET V4.3 lancée !")
    app.run_polling()

if __name__ == "__main__":
    main()