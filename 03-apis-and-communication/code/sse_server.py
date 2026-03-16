"""
Server-Sent Events (SSE) Demo
==============================
One-way server push over plain HTTP. Simulates a stock ticker
that streams price updates to connected clients.

Run: python sse_server.py
Open: http://localhost:5002
"""

from flask import Flask, Response
import json
import time
import random

app = Flask(__name__)

stocks = {
    "AAPL": 185.50,
    "GOOGL": 141.25,
    "AMZN": 178.90,
    "MSFT": 415.60,
}


def generate_stock_updates():
    """Yield SSE-formatted stock price updates, one per second."""
    event_id = 0

    while True:
        symbol = random.choice(list(stocks.keys()))
        change = random.uniform(-2.0, 2.0)
        stocks[symbol] = round(stocks[symbol] + change, 2)

        data = {
            "symbol": symbol,
            "price": stocks[symbol],
            "change": round(change, 2),
            "direction": "up" if change > 0 else "down",
        }

        event_id += 1

        # SSE wire format: field per line, blank line terminates the event
        yield f"id: {event_id}\nevent: price_update\ndata: {json.dumps(data)}\n\n"

        time.sleep(1)


@app.route("/")
def home():
    return """
    <html>
    <head><title>SSE Stock Ticker</title></head>
    <body style="font-family: monospace; background: #1a1a2e; color: #eee; padding: 20px;">
        <h2>Live Stock Ticker (Server-Sent Events)</h2>
        <p>Prices update in real time via SSE - no polling, no WebSocket.</p>
        <div id="ticker" style="font-size: 18px;"></div>
        <hr>
        <pre id="log" style="color: #888; font-size: 12px;"></pre>

        <script>
            const prices = {};
            const source = new EventSource('/events');

            source.addEventListener('price_update', function(e) {
                const data = JSON.parse(e.data);
                const arrow = data.direction === 'up' ? '▲' : '▼';
                const color = data.direction === 'up' ? '#00ff88' : '#ff4444';

                prices[data.symbol] = `<span style="color:${color}">${data.symbol}: $${data.price.toFixed(2)} ${arrow} ${data.change > 0 ? '+' : ''}${data.change.toFixed(2)}</span>`;

                document.getElementById('ticker').innerHTML =
                    Object.values(prices).join(' &nbsp; | &nbsp; ');

                const log = document.getElementById('log');
                log.textContent = `Event ID: ${e.lastEventId} | ${JSON.stringify(data)}\\n` + log.textContent;
            });

            source.onerror = function() {
                console.log('SSE connection lost, auto-reconnecting...');
            };
        </script>
    </body>
    </html>
    """


@app.route("/events")
def events():
    return Response(
        generate_stock_updates(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"\n  SSE Stock Ticker running at http://localhost:5002")
    print(f"  Open in browser to see live prices, or:")
    print(f"    curl -N http://localhost:5002/events\n")

    app.run(port=5002, debug=False, threaded=True)
