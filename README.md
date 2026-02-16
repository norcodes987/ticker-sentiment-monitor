# 📊 Market Sentiment Monitor

An AI-powered bot that analyzes financial news sentiment for your stock portfolio and sends daily email reports at market close.

## 🎯 Features

- **📈 Ticker-Specific Tracking** - Monitor sentiment for YOUR stocks (AAPL, MSFT, NVDA, etc.)
- **🤖 AI-Powered Analysis** - Uses FinBERT (specialized for financial news)
- **📧 Daily Email Reports** - Beautiful HTML emails sent at 4 PM ET (market close)
- **🎨 Smart Filtering** - Avoids false positives (e.g., "OpenAI" vs "Opendoor")
- **🌐 Multi-Source** - Aggregates from Yahoo Finance, CNBC, MarketWatch, and more
- **⏰ Automated Scheduling** - Runs daily without manual intervention

---

## 📸 Example Report

You'll receive emails like this every day:

```
📊 Daily Market & Ticker Sentiment Report
Wednesday, February 14, 2024 - 04:00 PM ET

Watching: AAPL • MSFT • NVDA • TSLA

🌐 Overall Market Sentiment
🟢 BULLISH
Based on 48 articles | Avg Score: 0.45

📌 AAPL
Sentiment: 🟢 BULLISH (Score: 0.67)
Articles Mentioning: 12
Recent Headlines:
• Apple beats Q4 earnings expectations (VERY BULLISH +0.82)
• iPhone sales surge in China (Bullish +0.54)
...

📌 NVDA
Sentiment: 🟢 VERY BULLISH (Score: 0.81)
Articles Mentioning: 15
Recent Headlines:
• Nvidia announces new AI chip breakthrough (VERY BULLISH +0.91)
...
```

---

## 🚀 Quick Start

### Installation

```bash
# 1. Clone the repository

# 2. Install dependencies
pip install -r requirements_email.txt

# 3. Create .env file
cp .env.example .env

# 4. Edit .env with your credentials (see below)
nano .env  # or use any text editor
```

---

## 🔑 Gmail Setup

You need a **Gmail App Password** (not your regular password):

1. **Enable 2-Factor Authentication:**
   - Go to: https://myaccount.google.com/security
   - Enable "2-Step Verification"

2. **Create App Password:**
   - Go to: https://myaccount.google.com/apppasswords
   - App: **Mail**
   - Device: **Other** → "Market Sentiment Bot"
   - Click **Generate**
   - Copy the 16-character password

3. **Update .env file:**
   ```dotenv
   GMAIL_USER=your.email@gmail.com
   GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
   WATCH_TICKERS=AAPL,MSFT,NVDA,TSLA
   ```

---

## ⚙️ Configuration

### Supported Tickers

The bot includes mappings for:

- Major tech stocks (AAPL, MSFT, NVDA, GOOGL, META, etc.)
- ETFs (BOTZ, SPY, QQQ, etc.)
- Crypto-related (MSTR, COIN, IBIT, etc.)
- International stocks (3067.HK, etc.)

**Don't see your ticker?** Add it to `ticker_mappings.json`:

```json
{
  "YOUR_TICKER": {
    "name": "Company Name",
    "aliases": ["Company Name", "YOUR_TICKER", "Alternative Name"]
  }
}
```

---

## 🏃 Usage

### Run Once (Test)

```bash
python market_sentiment_json.py
```

You should receive an email within 2-3 minutes!

### Run Daily at Market Close

```bash
python run_at_market_close.py
```

This runs at **4:00 PM Eastern Time** every day, regardless of your timezone.

## 🤖 How It Works

1. **Fetches News** - Scans RSS feeds from Yahoo Finance, CNBC, MarketWatch, Seeking Alpha, Investing.com
2. **Extracts Tickers** - Identifies which articles mention your stocks
3. **Analyzes Sentiment** - Uses FinBERT AI to score sentiment (-1 to +1)
4. **Smart Filtering** - Avoids false positives using context validation
5. **Generates Report** - Creates beautiful HTML email with:
   - Overall market sentiment
   - Individual ticker sentiment scores
   - Top bullish/bearish headlines
   - Article links for further reading
6. **Sends Email** - Delivers to your inbox at 4 PM ET

---

## 📊 Sentiment Scoring

| Score Range  | Label           | Meaning                    |
| ------------ | --------------- | -------------------------- |
| > 0.5        | 🟢 VERY BULLISH | Strong positive sentiment  |
| 0.1 to 0.5   | 🟢 Bullish      | Positive sentiment         |
| -0.1 to 0.1  | ⚪ Neutral      | Mixed or neutral sentiment |
| -0.5 to -0.1 | 🔴 Bearish      | Negative sentiment         |
| < -0.5       | 🔴 VERY BEARISH | Strong negative sentiment  |

---

## 🛡️ Smart Filtering

The bot uses context validation to avoid false positives:

### Example: OPEN (Opendoor Technologies)

❌ **Rejects:**

- "OpenAI releases new model"
- "The market is open today"
- "Open source software"

✅ **Accepts:**

- "Opendoor Technologies beats earnings"
- "Real estate platform Opendoor..."

### Example: MSTR (MicroStrategy)

❌ **Rejects:**

- "Brian Armstrong discusses crypto"
- "Neil Armstrong's legacy"

✅ **Accepts:**

- "MicroStrategy buys more Bitcoin"
- "Michael Saylor's MicroStrategy..."

---
