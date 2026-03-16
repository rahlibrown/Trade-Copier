# Trade-Copier

# MetaTrader 5 Smart Trade Copier

A **Python-based MetaTrader 5 trade copier** that mirrors trades from a **master account** to one or more **slave accounts** with built-in safety mechanisms such as slippage protection, lot scaling, persistent trade tracking, and smart close confirmation.

This project is designed for **algorithmic traders, prop firm traders, and portfolio managers** who want to replicate trades across multiple MT5 accounts automatically.

---

# Features

### 1. Master → Slave Trade Copying

Automatically copies trades opened on the **master MT5 account** to all configured slave accounts.

Supported operations:

* Open trades
* Modify Stop Loss / Take Profit
* Close trades

---

### 2. Smart Entry Protection

Prevents bad trade entries caused by price movement.

Controls include:

* Maximum entry deviation (pips)
* Slippage protection
* Optional lot reduction if price moves away from entry

This helps avoid copying trades at **unfavorable prices**.

---

### 3. Lot Scaling

Automatically adjusts trade size on slave accounts using a multiplier.

Example:

```
LOT_MULTIPLIER = 1.0
```

If master opens:

```
1.0 lot
```

Slave can open:

```
1.0 lot (1.0 multiplier)
0.5 lot (0.5 multiplier)
2.0 lot (2.0 multiplier)
```

---

### 4. Persistent Trade Tracking

The copier stores trade mappings in a JSON file:

```
copier_data.json
```

This ensures:

* Copier survives restarts
* Duplicate trades are prevented
* Trade states remain synchronized

---

### 5. Safe Trade Closing

Trades are only closed after confirmation loops to avoid accidental closure due to temporary sync issues.

Parameters:

```
CONFIRM_LOOPS
GRACE_PERIOD
```

This ensures **stable trade lifecycle management**.

---

### 6. Multi-Slave Account Support

Supports copying trades to **multiple slave accounts simultaneously**.

Example configuration:

```
SLAVES = [
    {"login": 298654963, "password": "...", "server": "..."},
    {"login": 81596668, "password": "...", "server": "..."}
]
```

---

# Project Structure

```
repo/
│
├── copier_ui.py
│   Persistent smart trade copier with safe execution logic
│
├── copier_faster.py
│   Optimized version with faster synchronization and symbol preloading
│
├── main2.py
│   Lightweight smart copier with slippage protection
│
└── copier_data.json
    Persistent storage for copied trades
```

---

# Requirements

Install dependencies:

```
pip install MetaTrader5
```

You must also have:

* MetaTrader 5 terminal installed
* Accounts logged into MT5
* Python 3.8+

---

# Configuration

Edit the configuration section in the script.

### Master Account

```
MASTER = {
    "login": YOUR_LOGIN,
    "password": "YOUR_PASSWORD",
    "server": "BROKER_SERVER"
}
```

### Slave Accounts

```
SLAVES = [
    {"login": LOGIN, "password": "PASSWORD", "server": "SERVER"}
]
```

---

# Running the Copier

Example:

```
python copier_faster.py
```

or

```
python copier_ui.py
```

The copier will begin monitoring the master account and synchronizing trades automatically.

---

# Core Settings

Example parameters:

```
LOT_MULTIPLIER = 1.0
SYNC_DELAY = 0.5
MAX_ENTRY_PIPS = 5
CONFIRM_LOOPS = 3
GRACE_PERIOD = 2
```

These settings control:

* trade size
* sync speed
* entry safety
* close confirmations

---

# How the Copier Works

1. Connect to the master MT5 account
2. Fetch open positions
3. Check slaves for matching trades
4. Open trades if they do not exist
5. Modify SL/TP if changed
6. Close slave trades when master closes

The copier runs in a **continuous synchronization loop**.

---

# Safety Design

This project includes several safeguards:

* Entry deviation checks
* Lot scaling
* Grace periods
* Close confirmation loops
* Persistent state tracking

These protections help prevent **trade duplication and bad entries**.

---

# Example Use Cases

* Copy trades between **personal MT5 accounts**
* Prop firm trade replication
* Signal distribution
* Portfolio management across multiple accounts

---

# Disclaimer

This software is for **educational and research purposes**.

Trading involves financial risk. Use at your own risk.

---

# Future Improvements

Possible enhancements:

* Web dashboard
* Telegram trade notifications
* Risk management module
* Trade filtering by symbol
* Docker deployment
* Cloud VPS auto-deployment

---

If you want, I can also help you create a **much more impressive README that gets attention on GitHub (like hedge fund level repos)** including:

* architecture diagrams
* workflow diagrams
* strategy explanation
* professional badges
* installation automation.
