import MetaTrader5 as mt5
import time
import json
import os

# ==============================
# MASTER ACCOUNT
# ==============================
MASTER = {
    "login": 298654914,
    "password": "Goddid@001",
    "server": "Exness-MT5Trial9"
}

# ==============================
# SLAVE ACCOUNTS
# ==============================
SLAVES = [
    {"login": 298654963, "password": "Slave@001", "server": "Exness-MT5Trial9"},
]

# ==============================
# SETTINGS
# ==============================
LOT_MULTIPLIER = 1.0
MAGIC = 777
SYNC_DELAY = 2               # seconds between loops
MAX_ENTRY_PIPS = 5           # maximum price deviation for entry
POINTS_PER_PIP = 10
CONFIRM_LOOPS = 3            # loops to confirm master closed
GRACE_PERIOD = 5             # seconds after opening before allowing close
PERSIST_FILE = "copier_data.json"

# ==============================
# PERSISTENT STORAGE
# ==============================
def load_data():
    if os.path.exists(PERSIST_FILE):
        with open(PERSIST_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(PERSIST_FILE, "w") as f:
        json.dump(data, f, indent=4)

copier_data = load_data()
# structure: copier_data = {slave_login: {master_trade_key: {"slave_ticket": x, "open_time": y, "confirm_count": z}}}

# ==============================
# CONNECT
# ==============================
def connect(account):
    mt5.shutdown()
    if not mt5.initialize():
        print("MT5 initialize failed")
        return False
    authorized = mt5.login(account["login"], password=account["password"], server=account["server"])
    return authorized

# ==============================
# GET MASTER POSITIONS
# ==============================
def get_master_positions():
    if not connect(MASTER):
        return []
    positions = mt5.positions_get()
    return positions if positions else []

# ==============================
# HELPER: CREATE UNIQUE KEY FOR MASTER TRADE
# ==============================
def master_trade_key(pos):
    return f"{pos.symbol}_{pos.type}_{pos.price_open:.5f}"

# ==============================
# ENTRY DISTANCE CHECK
# ==============================
def entry_within_range(symbol, master_price, order_type):
    tick = mt5.symbol_info_tick(symbol)
    info = mt5.symbol_info(symbol)
    if not tick or not info:
        return False
    current_price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
    max_distance = MAX_ENTRY_PIPS * POINTS_PER_PIP * info.point
    return abs(current_price - master_price) <= max_distance

# ==============================
# OPEN TRADE
# ==============================
def open_trade_safe(slave, master_pos, is_existing=False):
    slave_id = str(slave["login"])
    key = master_trade_key(master_pos)

    if slave_id not in copier_data:
        copier_data[slave_id] = {}

    if key in copier_data[slave_id]:
        return  # already copied

    if not connect(slave):
        return

    if not is_existing and not entry_within_range(master_pos.symbol, master_pos.price_open, master_pos.type):
        print(f"Skipped master trade {key} — price moved too far")
        return

    tick = mt5.symbol_info_tick(master_pos.symbol)
    if not tick:
        return

    price = tick.ask if master_pos.type == mt5.ORDER_TYPE_BUY else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": master_pos.symbol,
        "volume": master_pos.volume * LOT_MULTIPLIER,
        "type": master_pos.type,
        "price": price,
        "sl": master_pos.sl,
        "tp": master_pos.tp,
        "magic": MAGIC,
        "comment": f"copied_{master_pos.ticket}",
    }

    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        copier_data[slave_id][key] = {
            "slave_ticket": result.order,
            "open_time": time.time() if not is_existing else 0,
            "confirm_count": 0
        }
        save_data(copier_data)
        print(f"Copied master trade {key} to slave {slave_id}")

# ==============================
# MODIFY SL/TP
# ==============================
def modify_trade(slave, slave_ticket, master_pos):
    if not connect(slave):
        return
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": slave_ticket,
        "sl": master_pos.sl,
        "tp": master_pos.tp,
    }
    mt5.order_send(request)

# ==============================
# CLOSE TRADE
# ==============================
def close_trade(slave, slave_ticket):
    if not connect(slave):
        return
    pos = mt5.positions_get(ticket=slave_ticket)
    if not pos:
        return
    pos = pos[0]
    tick = mt5.symbol_info_tick(pos.symbol)
    if not tick:
        return

    if pos.type == mt5.ORDER_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": pos.symbol,
        "volume": pos.volume,
        "type": order_type,
        "position": pos.ticket,
        "price": price,
        "magic": MAGIC,
    }
    mt5.order_send(request)
    print(f"Closed slave trade {slave_ticket}")

# ==============================
# SNAPSHOT EXISTING MASTER TRADES
# ==============================
def snapshot_existing_master_trades():
    positions = get_master_positions()
    if positions:
        for slave in SLAVES:
            slave_id = str(slave["login"])
            if slave_id not in copier_data:
                copier_data[slave_id] = {}
            for pos in positions:
                key = master_trade_key(pos)
                copier_data[slave_id][key] = {
                    "slave_ticket": pos.ticket,  # just mark as existing
                    "open_time": 0,
                    "confirm_count": 0
                }
    save_data(copier_data)
    print(f"Ignoring existing master trades at startup")

# ==============================
# MAIN COPIER LOOP
# ==============================
def run_copier():
    print("Persistent Smart Trade Copier Running...")
    snapshot_existing_master_trades()

    while True:
        master_positions = get_master_positions()
        master_keys = [master_trade_key(pos) for pos in master_positions]

        for slave in SLAVES:
            slave_id = str(slave["login"])
            if not connect(slave):
                continue

            slave_positions = mt5.positions_get()
            slave_map = {}
            if slave_positions:
                for pos in slave_positions:
                    if pos.comment and "copied_" in pos.comment:
                        key = pos.comment.split("_")[1]
                        slave_map[key] = pos

            # OPEN OR MODIFY
            for master_pos in master_positions:
                key = master_trade_key(master_pos)
                is_existing = copier_data.get(slave_id, {}).get(key, {}).get("open_time", 0) == 0
                open_trade_safe(slave, master_pos, is_existing=is_existing)
                slave_ticket = copier_data.get(slave_id, {}).get(key, {}).get("slave_ticket")
                if slave_ticket:
                    modify_trade(slave, slave_ticket, master_pos)

            # SAFE CLOSE
            for key, data in copier_data.get(slave_id, {}).items():
                slave_ticket = data["slave_ticket"]
                open_time = data["open_time"]
                confirm_count = data["confirm_count"]

                if key not in master_keys:
                    copier_data[slave_id][key]["confirm_count"] += 1
                    if copier_data[slave_id][key]["confirm_count"] >= CONFIRM_LOOPS and (time.time() - open_time) >= GRACE_PERIOD:
                        close_trade(slave, slave_ticket)
                        copier_data[slave_id][key]["confirm_count"] = 0
                        copier_data[slave_id][key]["open_time"] = 0
                        copier_data[slave_id][key]["slave_ticket"] = None
            save_data(copier_data)
        time.sleep(SYNC_DELAY)

run_copier()