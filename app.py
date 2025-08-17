from flask import Flask, render_template, redirect, url_for
import requests
import pandas as pd
from flask_caching import Cache
import time

app = Flask(__name__)

# Configure cache
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})
CACHE_TIMEOUT = 900  # 15 minutes

def get_binance_symbols():
    url = "https://api.binance.com/api/v3/exchangeInfo"
    data = requests.get(url).json()
    return [s['symbol'] for s in data['symbols'] if s['quoteAsset'] == 'USDT' and s['status'] == 'TRADING']

def get_15m_change(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=2"
    try:
        data = requests.get(url).json()
        if isinstance(data, list) and len(data) == 2:
            open_price = float(data[0][1])
            close_price = float(data[1][4])
            change = ((close_price - open_price) / open_price) * 100
            return change
    except:
        pass
    return None

@cache.cached(timeout=CACHE_TIMEOUT, key_prefix='gainers_losers')
def fetch_gainers_losers():
    symbols = get_binance_symbols()
    results = []

    for symbol in symbols:
        change = get_15m_change(symbol)
        if change is not None:
            results.append({'symbol': symbol, 'change_15m': change})

    df = pd.DataFrame(results)
    gainers = df.sort_values(by='change_15m', ascending=False).head(10).to_dict(orient='records')
    losers = df.sort_values(by='change_15m', ascending=True).head(10).to_dict(orient='records')
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    return gainers, losers, timestamp

@app.route('/')
def index():
    gainers, losers, last_updated = fetch_gainers_losers()
    return render_template('index.html', gainers=gainers, losers=losers, last_updated=last_updated)

@app.route('/refresh')
def refresh():
    cache.delete('gainers_losers')  # Clear cache
    return redirect(url_for('index'))  # Reload page

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=10000)
