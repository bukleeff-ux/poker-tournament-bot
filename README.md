# 🃏 Poker Tournament Bot

A Telegram bot + Mini App (WebApp) for managing offline poker tournaments. Players register through the app, admins manage tournaments and set results, and a live leaderboard tracks points across all events.

## ✨ Features

- **🏆 Tournament Management** — create tournaments, set dates, open/close registration
- **📋 Player Registration** — in-app registration with duplicate protection
- **📊 Leaderboard** — automatic point scoring (1st → 3 pts, 2nd → 2 pts, 3rd → 1 pt)
- **👤 Player Profile** — personal stats: games played, wins, total points
- **🔐 Admin Panel** — full CRUD for tournaments and winner assignment (via bot + Mini App)
- **🔒 Auth** — HMAC-SHA256 validation of Telegram initData

## 🛠 Tech Stack

![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![python-telegram-bot](https://img.shields.io/badge/python--telegram--bot_21-2CA5E0?style=flat-square&logo=telegram&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)

- **python-telegram-bot 21** — async Telegram Bot API
- **FastAPI + Uvicorn** — REST API for the Mini App
- **aiosqlite** — async SQLite driver
- **Vanilla JS** — Mini App frontend (no framework)
- **python-dotenv** — environment variable management

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/buklee/poker-tournament-bot.git
cd poker-tournament-bot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create a `.env` file

```bash
cp .env.example .env
```

Fill in your credentials:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
WEBAPP_URL=https://your-tunnel-url.trycloudflare.com
```

> **WEBAPP_URL** — a public HTTPS URL pointing to this server (use [ngrok](https://ngrok.com) or [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) for local development).

### 4. Run

```bash
python bot.py       # starts the Telegram bot
python server.py    # starts the FastAPI server (Mini App backend)
```

Or run both in separate terminals.

## ⚙️ Configuration

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram bot token from [@BotFather](https://t.me/BotFather) |
| `ADMIN_IDS` | Comma-separated Telegram user IDs with admin access |
| `WEBAPP_URL` | Public HTTPS URL of the FastAPI server |

## 📁 Structure

```
poker-tournament-bot/
├── bot.py              # Telegram bot entry point
├── server.py           # FastAPI REST API
├── database.py         # aiosqlite schema & queries
├── auth.py             # Telegram initData HMAC validation
├── config.py           # Settings loaded from .env
├── keyboards.py        # Inline keyboard helpers
├── handlers/
│   ├── admin.py        # Admin ConversationHandler (tournament CRUD)
│   └── user.py         # User handlers (registration, leaderboard, profile)
├── static/
│   ├── index.html      # Mini App entry point
│   └── app.js          # Vanilla JS Mini App
├── .env.example
├── requirements.txt
└── README.md
```

## 📫 Contact

- **Telegram:** [@buklee](https://t.me/buklee)
- **Email:** bukleeff@gmail.com
