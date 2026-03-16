import MetaTrader5 as mt5
import time

# =====================================
# CONFIGURATION
# =====================================

MASTER_LOGIN = 298654914
MASTER_PASSWORD = "Goddid@001"
MASTER_SERVER = "Exness-MT5Trial9"

SLAVES = [
    {"login": 298654963, "password": "Slave@001", "server": "Exness-MT5Trial9"},
]

LOT_MULTIPLIER = 1.0
MAGIC = 777

# Smart entry protection
MAX_SLIPPAGE = 5        # allowed price difference (points)
REDUCE_LOT_AFTER = 3   # start reducing lot after this distance
MIN_LOT_FACTOR = 0.2    # minimum lot = 30% of original

SLEEP_TIME = 2


# =====================================
# CONNECTION
# =====================================

def connect(login, password, server):
    mt5.shutdown()
    mt5.initialize()
    authorized = mt5.login(login, password=password, server=server)
    return authorized


# =====================================
# SMART ENTRY LOGIC
# =====================================

def should_copy_trade(master_entry, current_price, stop_loss, base_lot):
    distance = abs(current_price - master_entry)
    sl_distance = abs(master_entry - stop_loss) if stop_loss != 0 else 0

    # Skip if too far from entry
    if distance > MAX_SLIPPAGE:
        return False, 0

    # Reduce lot if price moved
    if distance > REDUCE_LOT_AFTER and sl_distance > 0:
        risk_ratio = distance / sl_distance
        lot_factor = max(1 - risk_ratio, MIN_LOT_FACTOR)
        return True, base_lot * lot_factor

    return True, base_lot


# =====================================
# GET MASTER POSITIONS
# =====================================

def get_master_positions():
    connect(MASTER_LOGIN, MASTER_PASSWORD, MASTER_SERVER)
    positions = mt5.positions_get()
    return positions if positions else []


# =====================================
# OPEN TRADE ON SLAVE
# =====================================

def open_trade_on_slave(slave, master_pos):
    connect(slave["login"], slave["password"], slave["server"])

    symbol = master_pos.symbol
    order_type = mt5.ORDER_TYPE_BUY if master_pos.type == 0 else mt5.ORDER_TYPE_SELL

    tick = mt5.symbol_info_tick(symbol)
    current_price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

    master_entry = master_pos.price_open
    base_lot = master_pos.volume * LOT_MULTIPLIER

    copy_allowed, lot_to_use = should_copy_trade(
        master_entry,
        current_price,
        master_pos.sl,
        base_lot
    )

    if not copy_allowed:
        print("Skipped trade due to slippage protection")
        return None

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_to_use,
        "type": order_type,
        "price": current_price,
        "sl": master_pos.sl,
        "tp": master_pos.tp,
        "magic": MAGIC,
        "comment": f"copied_{master_pos.ticket}",
    }

    result = mt5.order_send(request)
    return result


# =====================================
# MODIFY SL / TP
# =====================================

def modify_trade(slave, position, master_pos):
    connect(slave["login"], slave["password"], slave["server"])

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": position.ticket,
        "sl": master_pos.sl,
        "tp": master_pos.tp,
    }

    mt5.order_send(request)


# =====================================
# CLOSE TRADE
# =====================================

def close_trade(slave, position):
    connect(slave["login"], slave["password"], slave["server"])

    order_type = mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY

    tick = mt5.symbol_info_tick(position.symbol)
    price = tick.bid if order_type == mt5.ORDER_TYPE_BUY else tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": order_type,
        "position": position.ticket,
        "price": price,
        "magic": MAGIC,
    }

    mt5.order_send(request)


# =====================================
# MAIN COPIER LOOP
# =====================================

def run_copier():
    print("Trade copier running...")

    copied_trades = {}

    while True:
        master_positions = get_master_positions()
        master_tickets = [pos.ticket for pos in master_positions]

        for slave in SLAVES:
            connect(slave["login"], slave["password"], slave["server"])
            slave_positions = mt5.positions_get() or []

            slave_map = {}
            for pos in slave_positions:
                if pos.comment and "copied_" in pos.comment:
                    master_ticket = int(pos.comment.split("_")[1])
                    slave_map[master_ticket] = pos

            # OPEN OR MODIFY
            for master_pos in master_positions:
                ticket = master_pos.ticket

                if ticket not in slave_map and ticket not in copied_trades:
                    result = open_trade_on_slave(slave, master_pos)
                    if result is not None:
                        copied_trades[ticket] = True

                if ticket in slave_map:
                    slave_pos = slave_map[ticket]
                    if slave_pos.sl != master_pos.sl or slave_pos.tp != master_pos.tp:
                        modify_trade(slave, slave_pos, master_pos)

            # CLOSE
            for ticket, slave_pos in slave_map.items():
                if ticket not in master_tickets:
                    close_trade(slave, slave_pos)
                    copied_trades.pop(ticket, None)

        time.sleep(SLEEP_TIME)


# =====================================
# START
# =====================================

run_copier()