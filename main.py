from fastapi import FastAPI,HTTPException,BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yfinance as yf
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import threading
import time
from typing import Dict,List,Optional
import os

app = FastAPI(title="Stock Tracking Simulator")

#for frontend requests

app.add_middleware(
    CORSMiddleware,
    allow_origins=[""],
    allow_credentials=True,
    allow_methods=["*"],
    allow_header = ["*"],
)

#using 4 prominent stocks for demo
WATCHLIST = ["RELIANCE.NS","TCS.NS","INF,NS","HDFCBANK.NS"]

#Real time monitoring 
MONITORING_INTERVAL  = 5  #Checks for status every 5 seconds

portfolio: Dict[int,dict]={} #storage

alert_history: Dict[int,List[dict]]={}  #shows the alerts

#helper fucntions

def get_live_price(symbol: str):
    """Fetches the specific live price from Yahoo Finance API (Indian Market)."""
    try:
        ticker = yf.Ticker(symbol)
        
        # Try multiple methods to get the price
        try:
            # Method 1: Try fast_info first
            info = ticker.fast_info
            if hasattr(info, 'last_price') and info.last_price is not None:
                price = float(info.last_price)
                if price > 0:
                    return round(price, 2)
        except:
            pass
        
        try:
            # Method 2: Try getting info dictionary
            info_dict = ticker.info
            if 'currentPrice' in info_dict and info_dict['currentPrice']:
                price = float(info_dict['currentPrice'])
                if price > 0:
                    return round(price, 2)
            elif 'regularMarketPrice' in info_dict and info_dict['regularMarketPrice']:
                price = float(info_dict['regularMarketPrice'])
                if price > 0:
                    return round(price, 2)
        except:
            pass
        
        try:
            # Method 3: Get last close price from history (most reliable)
            hist = ticker.history(period="1d", interval="1m")
            if not hist.empty and 'Close' in hist.columns:
                price = float(hist['Close'].iloc[-1])
                if price > 0:
                    return round(price, 2)
        except:
            pass
        
        try:
            # Method 4: Try 1 day history with daily interval
            hist = ticker.history(period="1d")
            if not hist.empty and 'Close' in hist.columns:
                price = float(hist['Close'].iloc[-1])
                if price > 0:
                    return round(price, 2)
        except:
            pass
        
        return None
    except Exception as e:
        print(f"⚠️ Error fetching {symbol}: {e}")
        return None


def monitor_market():
    """
    Real-time market monitoring: Checks active portfolio stocks every 5 seconds
    for +/- 5% price movement from purchase price
    """
    if not portfolio:
        return

    timestamp = datetime.now().strftime('%H:%M:%S')
    # NOTE: This output appears in the SERVER CONSOLE where uvicorn is running
    print(f"\n[{timestamp}] 🔍 Real-time Market Scan...")
    
    for tx_id, data in portfolio.items():
        if data.get('status') != "ACTIVE":
            continue

        symbol = data['symbol']
        buy_price = data['buy_price']
        
        # Check if there's a simulated current price (for testing), otherwise fetch real-time
        if 'simulated_current_price' in data:
            current_price = data['simulated_current_price']
            print(f"   [SIMULATED] Using simulated price: ₹{current_price}")
        else:
            current_price = get_live_price(symbol)
        
        if current_price is None:
            continue
            
        # Calculate Percentage Change from purchase price
        percent_change = ((current_price - buy_price) / buy_price) * 100
        
        # Update current price in portfolio for tracking
        data['current_price'] = current_price
        data['percent_change'] = round(percent_change, 2)
        
        log_msg = f"   📊 {symbol}: Buy @ ₹{buy_price} | Current @ ₹{current_price} | Change: {percent_change:+.2f}%"
        print(log_msg)

        #  REAL-TIME ALERT LOGIC (5% threshold)
        alert_sent = data.get('alert_sent', False)
        alert_type = None
        
        if percent_change >= 5.0:
            alert_type = "PROFIT"
        elif percent_change <= -5.0:
            alert_type = "LOSS"
        
        # Trigger alert only if threshold crossed AND alert not already sent for this movement
        if alert_type and not alert_sent:
            trigger_alert(tx_id, symbol, alert_type, percent_change, current_price, buy_price)
            # Mark as alerted to prevent duplicates
            data['alert_sent'] = True
            data['alert_type'] = alert_type
            data['alert_triggered_at'] = datetime.now().isoformat()
            
            # Store in alert history
            if tx_id not in alert_history:
                alert_history[tx_id] = []
            alert_history[tx_id].append({
                "timestamp": datetime.now().isoformat(),
                "type": alert_type,
                "percent_change": round(percent_change, 2),
                "current_price": current_price,
                "buy_price": buy_price
            })

def trigger_alert(transaction_id: int, symbol: str, alert_type: str, percent: float, current_price: float, buy_price: float):
    """
    Triggers a real-time alert when stock moves ±5% from purchase price.
    This simulates a push notification/alert in a production system.
    """
    direction_emoji = "📈" if alert_type == "PROFIT" else "📉"
    direction_text = "GAIN" if alert_type == "PROFIT" else "LOSS"
    
    print("\n" + "="*60)
    print(f"🚨 REAL-TIME ALERT TRIGGERED! 🚨")
    print(f"{direction_emoji} Stock: {symbol}")
    print(f"   Transaction ID: #{transaction_id}")
    print(f"   Movement: {percent:+.2f}% ({direction_text})")
    print(f"   Purchase Price: ₹{buy_price}")
    print(f"   Current Price: ₹{current_price}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")

# Real-time monitoring scheduler - runs every 5 seconds for fast tracking
scheduler = BackgroundScheduler()
scheduler.add_job(monitor_market, 'interval', seconds=MONITORING_INTERVAL, id='market_monitor')
scheduler.start()
print(f"✅ Real-time market monitoring started (checking every {MONITORING_INTERVAL} seconds)")

# --- 4. API ENDPOINTS ---

@app.get("/")
def home():
    """Serve the web UI interface."""
    html_file = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_file):
        return FileResponse(html_file)
    return {"message": "Fintech Backend is Running. Go to /ui for web interface or /docs for API docs."}

@app.get("/ui")
def serve_ui():
    """Serve the web UI interface."""
    html_file = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_file):
        return FileResponse(html_file)
    raise HTTPException(status_code=404, detail="UI file not found")

@app.get("/stocks")
def list_stocks():
    """
    Core Feature 1 & 2: Lists the 4 tracked stocks with live prices.
    """
    data = []
    for symbol in WATCHLIST:
        try:
            price = get_live_price(symbol)
            data.append({
                "symbol": symbol, 
                "current_price": price if price else None,
                "status": "available" if price else "unavailable"
            })
        except Exception as e:
            print(f"⚠️ Error processing {symbol}: {e}")
            data.append({
                "symbol": symbol,
                "current_price": None,
                "status": "error",
                "error": str(e)
            })
    return {"market_data": data}

class BuyRequest(BaseModel):
    symbol: str

@app.post("/buy")
def buy_stock(order: BuyRequest):
    """
    Core Feature 3: Simulates buying a stock.
    Snapshots the current price as the 'buy_price'.
    """
    symbol = order.symbol.upper()
    
    # Validate stock
    if symbol not in WATCHLIST:
        raise HTTPException(status_code=400, detail="Stock not in supported watchlist")

    # Fetch real-time price for execution
    execution_price = get_live_price(symbol)
    
    if not execution_price:
        raise HTTPException(status_code=503, detail="Market data unavailable")

    # Create Transaction with real-time tracking enabled
    transaction_id = len(portfolio) + 1
    portfolio[transaction_id] = {
        "symbol": symbol,
        "buy_price": execution_price,
        "bought_at": datetime.now().isoformat(),
        "status": "ACTIVE",
        "alert_sent": False,  # Track if alert has been sent for this transaction
        "current_price": execution_price,
        "percent_change": 0.0
    }

    print(f"✅ Stock purchased: {symbol} at ₹{execution_price} (Transaction #{transaction_id})")
    print(f"   Monitoring for ±5% price movement...\n")

    return {
        "message": "Stock purchased successfully - Real-time monitoring enabled",
        "transaction_id": transaction_id,
        "details": portfolio[transaction_id]
    }

@app.get("/portfolio")
def view_portfolio():
    """View all active and tracked stock positions with current status."""
    # Add current prices for each position
    enriched_portfolio = {}
    for tx_id, data in portfolio.items():
        enriched_data = data.copy()
        if data.get('status') == "ACTIVE":
            current_price = get_live_price(data['symbol'])
            if current_price:
                enriched_data['current_price'] = current_price
                enriched_data['percent_change'] = round(((current_price - data['buy_price']) / data['buy_price']) * 100, 2)
        enriched_portfolio[tx_id] = enriched_data
    return {
        "portfolio": enriched_portfolio,
        "total_positions": len(portfolio),
        "active_positions": sum(1 for p in portfolio.values() if p.get('status') == 'ACTIVE')
    }

@app.get("/alerts")
def view_alerts():
    """View all triggered alerts history."""
    return {
        "alert_history": alert_history,
        "total_alerts": sum(len(alerts) for alerts in alert_history.values())
    }

@app.get("/alerts/latest")
def get_latest_alerts():
    """Get latest alerts for real-time updates (returns only recent alerts)."""
    # Get the most recent alert from each transaction
    latest_alerts = []
    for tx_id, alerts_list in alert_history.items():
        if alerts_list:
            latest = alerts_list[-1]  # Get most recent alert
            latest['transaction_id'] = tx_id
            latest_alerts.append(latest)
    
    # Sort by timestamp (most recent first)
    latest_alerts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return {
        "latest_alerts": latest_alerts[:10],  # Return top 10 most recent
        "total": len(latest_alerts)
    }

@app.post("/reset-alert/{transaction_id}")
def reset_alert(transaction_id: int):
    """Reset alert status for a transaction to enable new alerts if price moves again."""
    if transaction_id not in portfolio:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    portfolio[transaction_id]['alert_sent'] = False
    portfolio[transaction_id].pop('alert_type', None)
    portfolio[transaction_id].pop('alert_triggered_at', None)
    
    return {"message": f"Alert reset for transaction #{transaction_id}. Monitoring will trigger new alerts."}

# --- 5. SIMULATION HELPER (FOR TESTING ONLY) ---

class SimulatePriceRequest(BaseModel):
    simulated_current_price: float

@app.post("/simulate-price-movement/{transaction_id}")
def simulate_price_movement(transaction_id: int, request: SimulatePriceRequest):
    """
    TESTING ONLY: Simulate a current price movement for testing alerts.
    This sets a simulated current price that will be used instead of real market data.
    Allows testing alert logic without waiting for real market movements.
    """
    if transaction_id not in portfolio:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    buy_price = portfolio[transaction_id]['buy_price']
    simulated_current_price = request.simulated_current_price
    
    # Set simulated current price for monitoring
    portfolio[transaction_id]['simulated_current_price'] = simulated_current_price
    portfolio[transaction_id]['alert_sent'] = False  # Reset alert to test triggering
    
    percent_change = ((simulated_current_price - buy_price) / buy_price) * 100
    
    return {
        "message": f"Simulated current price for transaction #{transaction_id}",
        "buy_price": buy_price,
        "simulated_current_price": simulated_current_price,
        "expected_percent_change": round(percent_change, 2),
        "note": "Next monitoring cycle will use this simulated price. Alert will trigger if ±5% threshold is crossed."
    }

@app.delete("/simulate-price-movement/{transaction_id}")
def clear_simulation(transaction_id: int):
    """Clear simulated price and return to real-time market data."""
    if transaction_id not in portfolio:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    portfolio[transaction_id].pop('simulated_current_price', None)
    return {"message": f"Simulation cleared for transaction #{transaction_id}. Using real market data."}

@app.get("/status")
def system_status():
    """Get real-time system status and monitoring info."""
    return {
        "status": "running",
        "monitoring_interval_seconds": MONITORING_INTERVAL,
        "watchlist": WATCHLIST,
        "active_positions": sum(1 for p in portfolio.values() if p.get('status') == 'ACTIVE'),
        "total_alerts_triggered": sum(len(alerts) for alerts in alert_history.values()),
        "monitoring_enabled": scheduler.running
    }
                