import logging
import threading
import time
import os
from fastapi import FastAPI
from pydantic import BaseModel
import ccxt

# Configura il logging per il debug
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Configura l'API di Bybit
API_KEY = "nxoqf7Odgq8VJzGvgs"
API_SECRET = "sCrWE6r7tU0JQQ6dYJWa15gyySzdPquvjpLl"
bybit = ccxt.bybit({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'options': {'defaultType': 'future'},  # Spot o future
})

app = FastAPI()
trading_active = False  # Variabile di stato del bot

# Parametri di scalping
default_params = {
    "symbol": "BTC/USDT",
    "amount": 0.01,  # Quantità di BTC da tradare
    "profit_target": 0.2,  # Target di profitto in %
    "stop_loss": 0.1  # Stop loss in %
}

class TradingParams(BaseModel):
    symbol: str
    amount: float
    profit_target: float
    stop_loss: float

def scalping_bot(params):
    global trading_active
    symbol = params['symbol']
    amount = params['amount']
    profit_target = params['profit_target'] / 100
    stop_loss = params['stop_loss'] / 100

    while trading_active:
        try:
            # Ottieni il prezzo attuale
            ticker = bybit.fetch_ticker(symbol)
            entry_price = ticker['last']

            # Calcola take profit e stop loss
            take_profit = entry_price * (1 + profit_target)
            stop_loss_price = entry_price * (1 - stop_loss)

            # Esegui ordine di acquisto
            order = bybit.create_market_buy_order(symbol, amount)
            logging.info(f"Comprato a {entry_price}")

            # Controlla il prezzo per vendere
            while trading_active:
                ticker = bybit.fetch_ticker(symbol)
                current_price = ticker['last']

                if current_price >= take_profit or current_price <= stop_loss_price:
                    bybit.create_market_sell_order(symbol, amount)
                    logging.info(f"Venduto a {current_price}")
                    break
                time.sleep(1)  # Aspetta prima di controllare di nuovo

        except Exception as e:
            logging.error(f"Errore nel bot: {e}")

        time.sleep(2)  # Aspetta prima di un nuovo trade

@app.post("/start")
def start_trading(params: TradingParams):
    global trading_active
    if trading_active:
        return {"message": "Il bot è già attivo"}

    trading_active = True
    thread = threading.Thread(target=scalping_bot, args=(params.dict(),))
    thread.start()
    logging.info("Trading avviato con parametri: %s", params.dict())
    return {"message": "Trading avviato!"}

@app.post("/stop")
def stop_trading():
    global trading_active
    trading_active = False
    logging.info("Trading fermato.")
    return {"message": "Trading fermato!"}

@app.get("/status")
def status():
    return {"trading_active": trading_active}

@app.get("/debug")
def debug():
    try:
        response = bybit.fetch_ticker("BTC/USDT")
        logging.info("Risposta API Bybit: %s", response)
        if isinstance(response, dict) and "last" in response:
            return {"status": "success", "price": response["last"]}
        else:
            return {"status": "error", "message": "Formato risposta Bybit non valido", "response": response}
    except Exception as e:
        logging.error("Errore nel debug: %s", str(e))
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT", 8000))  # Usa la porta di Railway
        logging.info(f"Avvio del server sulla porta {port}")
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        logging.error(f"Errore durante l'avvio del server: {e}")
