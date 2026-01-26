"""Quick test to check if news fetching works"""
import yfinance as yf

symbols = ["AAPL", "TSLA", "NVDA", "MSFT", "META"]

print("Testing news fetching...\n")

for symbol in symbols:
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news

        if news and isinstance(news, list):
            print(f"{symbol}: {len(news)} News-Artikel gefunden")
            if len(news) > 0:
                print(f"  Erster Titel: {news[0].get('title', 'N/A')}")
        else:
            print(f"{symbol}: Keine News (news={type(news)})")
    except Exception as e:
        print(f"{symbol}: ERROR - {e}")
    print()
