# Market Sentiment Monitor

A Python application that scrapes financial RSS feeds, analyzes market sentiment, and sends alerts via Telegram.

## Features

- 📰 Monitors major financial news sources (Yahoo Finance, CNBC, MarketWatch, Investing.com, Seeking Alpha)
- 📊 Sentiment analysis using keyword matching
- 🚨 Telegram alerts for strong bullish/bearish signals
- 📈 Summary reports of overall market sentiment
- 💾 Tracks seen articles to avoid duplicates
- ⏰ Runs continuously with configurable intervals

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Save the **bot token** you receive (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 3. Get Your Chat ID

**Method 1: Using @userinfobot**

1. Search for `@userinfobot` in Telegram
2. Start a chat with it
3. Your chat ID will be displayed

**Method 2: Using the API**

1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for `"chat":{"id":` in the response

### 4. Set Environment Variables

**Linux/Mac:**

```bash
export TELEGRAM_BOT_TOKEN='your_bot_token_here'
export TELEGRAM_CHAT_ID='your_chat_id_here'
```

**Windows (Command Prompt):**

```cmd
set TELEGRAM_BOT_TOKEN=your_bot_token_here
set TELEGRAM_CHAT_ID=your_chat_id_here
```

**Windows (PowerShell):**

```powershell
$env:TELEGRAM_BOT_TOKEN='your_bot_token_here'
$env:TELEGRAM_CHAT_ID='your_chat_id_here'
```

### 5. Run the Application

```bash
python market_sentiment_monitor.py
```

## How It Works

### Sentiment Analysis

The app analyzes headlines and summaries using keyword matching:

**Bullish Keywords:** rally, surge, gain, rise, bull, optimism, growth, etc.

**Bearish Keywords:** fall, drop, decline, bear, crash, plunge, recession, etc.

**Sentiment Levels:**

- 🟢 VERY BULLISH: Score > 2
- 🟢 Bullish: Score > 0
- ⚪ Neutral: Score = 0
- 🔴 Bearish: Score < 0
- 🔴 VERY BEARISH: Score < -2

### Alert Types

1. **Summary Report** - Sent every scan cycle with overall market sentiment
2. **Individual Alerts** - Sent for articles with strong sentiment (|score| >= 2)

### Data Sources

- Yahoo Finance
- CNBC Top News
- Investing.com
- MarketWatch
- Seeking Alpha

## Customization

### Change Scan Interval

Edit the `interval_minutes` parameter in `main()`:

```python
monitor.run_continuous(interval_minutes=15)  # Scan every 15 minutes
```

### Add More RSS Feeds

Add URLs to the `self.rss_feeds` list:

```python
self.rss_feeds = [
    "https://your-feed-url.com/rss",
    # ... more feeds
]
```

### Adjust Sentiment Keywords

Modify the `positive_keywords` and `negative_keywords` lists in `__init__`:

```python
self.positive_keywords = ['rally', 'surge', 'your_keyword']
self.negative_keywords = ['crash', 'decline', 'your_keyword']
```

### Change Alert Threshold

Modify the condition in `send_article_alert()`:

```python
if abs(score) < 3:  # Only alert for very strong signals
    return
```

## Running as a Background Service

### Using systemd (Linux)

1. Create a service file `/etc/systemd/system/market-monitor.service`:

```ini
[Unit]
Description=Market Sentiment Monitor
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/your/app
Environment="TELEGRAM_BOT_TOKEN=your_token"
Environment="TELEGRAM_CHAT_ID=your_chat_id"
ExecStart=/usr/bin/python3 market_sentiment_monitor.py
Restart=always

[Install]
WantedBy=multi-user.target
```

2. Enable and start the service:

```bash
sudo systemctl enable market-monitor
sudo systemctl start market-monitor
sudo systemctl status market-monitor
```

### Using screen (Linux/Mac)

```bash
screen -S market-monitor
python market_sentiment_monitor.py
# Press Ctrl+A, then D to detach
# Re-attach with: screen -r market-monitor
```

### Using nohup

```bash
nohup python market_sentiment_monitor.py > monitor.log 2>&1 &
```

## Troubleshooting

### No messages received

- Verify your bot token and chat ID are correct
- Make sure you've started a conversation with your bot
- Check if the bot has permission to send messages

### RSS feed errors

- Some feeds may be temporarily unavailable
- Check your internet connection
- The app will skip failed feeds and continue with others

### Too many/few alerts

- Adjust the sentiment threshold in `send_article_alert()`
- Modify the scan interval
- Customize keyword lists

## Example Output

```
📊 Market Sentiment Report
Time: 2024-02-14 09:30
Overall Sentiment: 🟢 BULLISH
Articles Analyzed: 15
Avg Score: 1.47

🚨 Market Alert

Sentiment: 🟢 VERY BULLISH (Score: 3)

S&P 500 Surges to Record High on Strong Earnings Beat

Source: Yahoo Finance
Link: https://...
```

## License

MIT License - Feel free to modify and use as needed!

## Disclaimer

This tool provides sentiment analysis based on keyword matching and should not be used as the sole basis for investment decisions. Always do your own research and consult with financial professionals.
