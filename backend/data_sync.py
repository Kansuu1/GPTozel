# backend/data_sync.py
import os, json, threading
from pathlib import Path

CONFIG_PATH = os.getenv("CONFIG_PATH", "./config.json")
_lock = threading.Lock()

DEFAULT = {
    "threshold": int(os.getenv("MANUAL_THRESHOLD", "75")),
    "selected_coins": os.getenv("SELECTED_COINS","BTC,ETH,ADA,SOL,BNB").split(","),
    "timeframe": os.getenv("TIMEFRAME", "24h"),
    "cmc_api_key": os.getenv("CMC_API_KEY", ""),
    "telegram_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
    "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
    "allowed_user_ids": os.getenv("ALLOWED_USER_IDS", ""),
    "max_concurrent_coins": int(os.getenv("MAX_CONCURRENT_COINS","20"))
}

def read_config():
    with _lock:
        if not os.path.exists(CONFIG_PATH):
            Path(CONFIG_PATH).parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_PATH,"w") as f:
                json.dump(DEFAULT, f, indent=2)
            return DEFAULT.copy()
        with open(CONFIG_PATH,"r") as f:
            c = json.load(f)
        # ensure default keys
        for k,v in DEFAULT.items():
            if k not in c:
                c[k] = v
        return c

def update_threshold(val:int):
    with _lock:
        cfg = read_config()
        cfg["threshold"] = int(val)
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
        return cfg

def update_config(updates: dict):
    with _lock:
        # Read directly without calling read_config to avoid nested lock
        if not os.path.exists(CONFIG_PATH):
            cfg = DEFAULT.copy()
        else:
            with open(CONFIG_PATH, "r") as f:
                cfg = json.load(f)
        
        cfg.update(updates)
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
        return cfg