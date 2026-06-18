import os

TOKEN=os.getenv("BRIDGE_TOKEN","")
HOST=os.getenv("BRIDGE_HOST","0.0.0.0")
PORT=int(os.getenv("BRIDGE_PORT","8787"))
# Sessions with no hook activity for this many seconds are pruned (assumed dead/crashed).
SESSION_TIMEOUT=int(os.getenv("BRIDGE_SESSION_TIMEOUT","1800"))
# How often the bridge re-broadcasts a fresh snapshot so token counts and pruning stay live.
HEARTBEAT=int(os.getenv("BRIDGE_HEARTBEAT","15"))
LOG_LEVEL=os.getenv("BRIDGE_LOG_LEVEL","INFO").upper()
