import feedparser
from datetime import datetime
import time
from typing import List, Dict, Tuple, Set
import json
import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from collections import defaultdict
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

load_dotenv()

class TickerSentimentMonitor:
    def __init__ (self, gmail_user: str, gmail_password: str, recipient_email: str, watch_tickers: List[str], mappings_file: str = 'ticker_mappings.json'):
        
        self.gmail_user = gmail_user
        self.gmail_password = gmail_password
        self.recipient_email = recipient_email
        self.watch_tickers = [ticker.upper() for ticker in watch_tickers]

        print("=" * 20)
        print("📊 Ticker-Specific Market Sentiment Monitor")
        print("=" * 20)

        self.ticker_to_names = self.load_ticker_mappings(mappings_file)
        self.ticker_to_names = {
            ticker: names for ticker, names in self.ticker_to_names.items() if ticker in self.watch_tickers
        }
        print(f"👀 Watching tickers: {', '.join(self.watch_tickers)}")
        print(f"🕐 Starting scan at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        start = time.time()

        self.tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
        self.model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
        load_time = time.time() - start
        print(f"✅ FinBERT loaded in {load_time:.2f} seconds")

        # RSS Feeds
        self.rss_feeds = [
            "https://feeds.finance.yahoo.com/rss/2.0/headline?s=yhoo,goog&region=US&lang=en-US",
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            "https://www.investing.com/rss/news.rss",
            "https://www.marketwatch.com/rss/topstories",
            "https://seekingalpha.com/market_currents.xml"
        ]
   
    def load_ticker_mappings(self, mapping_file: str) -> Dict[str, List[str]]:
        try:
            with open(mapping_file, 'r') as f:
                data = json.load(f)
            mappings = {}
            for ticker, info in data.items():
                mappings[ticker] = info.get('aliases', [ticker])
            return mappings
        except FileNotFoundError:
            print(f"⚠️ {mapping_file} not found. Using basic ticker-only matching.")
            return {ticker: [ticker] for ticker in self.watch_tickers}
        
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing {mapping_file}: {e}")
            print("⚠️ Using basic ticker-only matching.")
            return {ticker: [ticker] for ticker in self.watch_tickers}

    def _validate_mention(self, text: str, name: str, ticker: str) -> bool:
        """
        Validate that a name mention actually refers to the company
        Filters out false positives like "Open AI" vs "Opendoor"
        """
        text_lower = text.lower()
        
        # Special case filters for known false positives
        false_positive_filters = {
            'OPEN': {
                'exclude_phrases': ['openai', 'open ai', 'open-ai', 'open source'],
                'require_context': ['opendoor', 'real estate', 'housing']
            },
            'MSTR': {
                'exclude_phrases': ['armstrong', 'arm strong'],
                'require_context': ['microstrategy', 'bitcoin', 'saylor']
            },
            'FIG': {
                'exclude_phrases': ['figure', 'figures'],
                'require_context': [] 
            }
        }
        
        if ticker in false_positive_filters:
            filters = false_positive_filters[ticker]
            
            # Check exclusion phrases
            for exclude in filters['exclude_phrases']:
                if exclude in text_lower:
                    return False  # Found false positive phrase
        return True
    
    def extract_tickers(self, text: str) -> Set[str]:
        """
        Extract ticker symbold mentioned in text
        Returns: Set of tickers found
        """
        found_tickers = set()
        text_upper = text.upper()
        text_lower = text.lower()
        for ticker in self.watch_tickers:
            if ticker not in self.ticker_to_names:
                # Fallback: just check ticker symbol
                if ticker in text_upper:
                    found_tickers.add(ticker)
                continue
            aliases = self.ticker_to_names[ticker]
            for name in aliases:
                name_lower = name.lower()
                
                if name_lower in text_lower:
                    # Additional validation for ambiguous names
                    if self._validate_mention(text, name, ticker):
                        found_tickers.add(ticker)
                        break
        
        return found_tickers
    
    def analyse_sentiment(self, text: str) -> Tuple[str, float]:
        try:
            text = text[:512]
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            outputs = self.model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
            positive_prob = probs[0][0].item()
            negative_prob = probs[0][1].item()
            score = positive_prob - negative_prob
            
            if score > 0.5:
                sentiment = "VERY BULLISH"
            elif score > 0.1:
                sentiment = "Bullish"
            elif score < -0.5:
                sentiment = "VERY BEARISH"
            elif score < -0.1:
                sentiment = "Bearish"
            else:
                sentiment = "Neutral"
            
            return sentiment, score
            
        except Exception as e:
            return "Neutral", 0.0
        
    def fetch_and_analyse_articles(self) -> Tuple[List[Dict], Dict[str, List[Dict]]]:
        """
        Fetch articles and categorize by ticker
        Returns: (all_articles, ticker_articles_map)
        e.g. all_articles = [
            {'title': 'Apple surges', 'tickers': ['AAPL'], ...},
            {'title': 'Tesla drops', 'tickers': ['TSLA'], ...},
            {'title': 'Microsoft beats earnings', 'tickers': ['MSFT'], ...}
        ]
        e.g. ticker_articles = {
            'AAPL': [
                {'title': 'Apple surges', ...},
                {'title': 'iPhone sales strong', ...}
            ],
            'MSFT': [
                {'title': 'Microsoft beats earnings', ...}
            ],
            'TSLA': []  # No articles mentioning TSLA
        }
        """
        all_articles = []
        ticker_articles = defaultdict(list)
        
        print(f"\n📰 Fetching from {len(self.rss_feeds)} sources...")
        
        for i, feed_url in enumerate(self.rss_feeds, 1):
            try:
                feed = feedparser.parse(feed_url)
                source_name = feed.feed.get('title', feed_url)
                print(f"  [{i}/{len(self.rss_feeds)}] {source_name}...", end=" ")
                
                count = 0
                for entry in feed.entries[:10]:
                    title = entry.get('title', '')
                    summary = entry.get('summary', entry.get('description', ''))
                    link = entry.get('link', '')
                    
                    # Extract tickers mentioned
                    combined_text = f"{title} {summary}"
                    mentioned_tickers = self.extract_tickers(combined_text)
                    
                    # Analyse sentiment
                    sentiment, score = self.analyse_sentiment(combined_text)
                    
                    article = {
                        'title': title,
                        'link': link,
                        'published': entry.get('published', ''),
                        'summary': summary,
                        'source': source_name,
                        'sentiment': sentiment,
                        'score': score,
                        'tickers': list(mentioned_tickers)
                    }
                    
                    all_articles.append(article)
                    
                    # Add to ticker-specific lists
                    for ticker in mentioned_tickers:
                        ticker_articles[ticker].append(article)
                    
                    count += 1
                
                print(f"✅ {count} articles")
                
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print(f"\n✅ Total articles: {len(all_articles)}")
        print(f"📊 Articles mentioning your tickers:")
        for ticker in self.watch_tickers:
            count = len(ticker_articles.get(ticker, []))
            print(f"   {ticker}: {count} articles")
        # print(all_articles, dict(ticker_articles))
        return all_articles, dict(ticker_articles)

    def generate_html_report(self, all_articles: List[Dict], ticker_articles: Dict[str, List[Dict]]) -> str:
        """Generate comprehensive HTML email report"""
        
        # Calculate overall market sentiment
        if all_articles:
            avg_score = sum(a['score'] for a in all_articles) / len(all_articles)
            
            if avg_score > 0.3:
                overall = "🟢 BULLISH"
                color = "#28a745"
            elif avg_score > 0:
                overall = "🟢 Slightly Bullish"
                color = "#90EE90"
            elif avg_score < -0.3:
                overall = "🔴 BEARISH"
                color = "#dc3545"
            elif avg_score < 0:
                overall = "🔴 Slightly Bearish"
                color = "#FFA07A"
            else:
                overall = "⚪ Neutral"
                color = "#6c757d"
        else:
            avg_score = 0
            overall = "No Data"
            color = "#6c757d"
        
        # Build HTML
        html = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 900px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .tickers-watched {{
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                    margin-bottom: 20px;
                }}
                .ticker-tag {{
                    display: inline-block;
                    background-color: #667eea;
                    color: white;
                    padding: 5px 12px;
                    border-radius: 15px;
                    margin: 0 5px;
                    font-weight: bold;
                }}
                .section {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .section-title {{
                    font-size: 22px;
                    font-weight: bold;
                    margin-bottom: 15px;
                    border-bottom: 2px solid #667eea;
                    padding-bottom: 10px;
                }}
                .ticker-section {{
                    border-left: 4px solid #667eea;
                    padding-left: 15px;
                    margin-bottom: 20px;
                }}
                .ticker-header {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #667eea;
                    margin-bottom: 10px;
                }}
                .ticker-summary {{
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 15px;
                }}
                .article {{
                    margin-bottom: 15px;
                    padding-bottom: 15px;
                    border-bottom: 1px solid #eee;
                }}
                .article:last-child {{
                    border-bottom: none;
                }}
                .article-title {{
                    font-weight: bold;
                    margin-bottom: 5px;
                    font-size: 15px;
                }}
                .article-meta {{
                    font-size: 12px;
                    color: #666;
                    margin-bottom: 5px;
                }}
                .sentiment-badge {{
                    display: inline-block;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                    margin-right: 10px;
                }}
                .very-bullish {{ background-color: #28a745; color: white; }}
                .bullish {{ background-color: #d4edda; color: #155724; }}
                .bearish {{ background-color: #f8d7da; color: #721c24; }}
                .very-bearish {{ background-color: #dc3545; color: white; }}
                .neutral {{ background-color: #e2e3e5; color: #383d41; }}
                a {{ color: #667eea; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Daily Market & Ticker Sentiment Report</h1>
                <p>{datetime.now().strftime('%A, %B %d, %Y - %I:%M %p ET')}</p>
            </div>
        """
        
        # Overall Market Sentiment Section
        html += f"""
            <div class="section">
                <div class="section-title">🌐 Overall Market Sentiment</div>
                <div style="text-align: center; padding: 20px; background-color: {color}; color: white; border-radius: 8px; font-size: 24px; font-weight: bold;">
                    {overall}
                    <div style="font-size: 14px; margin-top: 8px;">
                        Based on {len(all_articles)} articles | Avg Score: {avg_score:.3f}
                    </div>
                </div>
            </div>
        """
        
        # Ticker-Specific Sections
        for ticker in self.watch_tickers:
            articles = ticker_articles.get(ticker, [])
            
            # Get ticker's full name from mappings
            ticker_name = ticker
            if ticker in self.ticker_to_names and self.ticker_to_names[ticker]:
                ticker_name = f"{ticker}"
            
            if articles:
                # Calculate ticker-specific sentiment
                ticker_avg = sum(a['score'] for a in articles) / len(articles)
                
                if ticker_avg > 0.3:
                    ticker_sentiment = "🟢 BULLISH"
                    ticker_color = "#28a745"
                elif ticker_avg > 0:
                    ticker_sentiment = "🟢 Slightly Bullish"
                    ticker_color = "#90EE90"
                elif ticker_avg < -0.3:
                    ticker_sentiment = "🔴 BEARISH"
                    ticker_color = "#dc3545"
                elif ticker_avg < 0:
                    ticker_sentiment = "🔴 Slightly Bearish"
                    ticker_color = "#FFA07A"
                else:
                    ticker_sentiment = "⚪ Neutral"
                    ticker_color = "#6c757d"
                
                html += f"""
                <div class="section">
                    <div class="ticker-section">
                        <div class="ticker-header">{ticker_name}</div>
                        <div class="ticker-summary">
                            <strong>Sentiment:</strong> <span style="color: {ticker_color}; font-weight: bold;">{ticker_sentiment}</span><br>
                            <strong>Articles Mentioning:</strong> {len(articles)}<br>
                            <strong>Average Score:</strong> {ticker_avg:.3f}
                        </div>
                        
                        <div style="font-weight: bold; margin-bottom: 10px; margin-top: 15px;">Recent Headlines:</div>
                """
                
                # Sort articles by sentiment score
                sorted_articles = sorted(articles, key=lambda x: abs(x['score']), reverse=True)
                
                for article in sorted_articles[:5]:  # Top 5 articles
                    # Determine badge class
                    if article['score'] > 0.5:
                        badge_class = "very-bullish"
                    elif article['score'] > 0.1:
                        badge_class = "bullish"
                    elif article['score'] < -0.5:
                        badge_class = "very-bearish"
                    elif article['score'] < -0.1:
                        badge_class = "bearish"
                    else:
                        badge_class = "neutral"
                    
                    html += f"""
                        <div class="article">
                            <div class="article-title">{article['title']}</div>
                            <div class="article-meta">
                                <span class="sentiment-badge {badge_class}">{article['sentiment']} ({article['score']:.2f})</span>
                                {article['source']}
                            </div>
                            <a href="{article['link']}" target="_blank">Read more →</a>
                        </div>
                    """
                
                html += """
                    </div>
                </div>
                """
            else:
                html += f"""
                <div class="section">
                    <div class="ticker-section">
                        <div class="ticker-header">{ticker_name}</div>
                        <p style="color: #666; font-style: italic;">No articles mentioning {ticker} today.</p>
                    </div>
                </div>
                """
        
        html += """
        </body>
        </html>
        """
        
        return html

    def send_email(self, subject: str, html_content: str):
        """Send HTML email via Gmail"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.gmail_user
            msg['To'] = self.recipient_email
            msg['Subject'] = subject
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(self.gmail_user, self.gmail_password)
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Email sent successfully to {self.recipient_email}")
            return True
            
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            return False
        
    def run_daily_scan(self):
        all_articles, ticker_articles = self.fetch_and_analyse_articles()
        html_report = self.generate_html_report(all_articles, ticker_articles)
        
        subject = f"📊 Market & {', '.join(self.watch_tickers[:3])} Sentiment - {datetime.now().strftime('%b %d')}"
        self.send_email(subject, html_report)
        print(f"✅ Daily scan complete!")

def main():
    gmail_user = os.environ.get('GMAIL_USER')
    gmail_password = os.environ.get('GMAIL_APP_PASSWORD')
    recipient_email = os.environ.get('RECIPIENT_EMAIL', gmail_user)
    watch_tickers_str = os.environ.get('WATCH_TICKERS', '')
    watch_tickers = [t.strip() for t in watch_tickers_str.split(',')]
    if not gmail_user or not gmail_password:
        print("❌ ERROR: Missing Gmail credentials!")
    if not watch_tickers_str:
         print("❌ ERROR: Missing tickers to monitor!")
    monitor = TickerSentimentMonitor(gmail_user, gmail_password, recipient_email, watch_tickers)
    monitor.run_daily_scan()

if __name__ == "__main__":
    main()
