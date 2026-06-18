#!/usr/bin/env python3
"""Local Discord Rich Presence client for Claude Code. Connects to the bridge over a
websocket, receives aggregated session snapshots, and mirrors them into Discord via
pypresence. Resilient to Discord or the bridge going away - it just reconnects."""
import os, asyncio, json, logging, websockets
from pypresence import AioPresence

APP_ID=os.getenv("DISCORD_APP_ID","")
HOST=os.getenv("BRIDGE_HOST","127.0.0.1")
PORT=os.getenv("BRIDGE_PORT","8787")
TOKEN=os.getenv("BRIDGE_TOKEN","")
LARGE_IMAGE=os.getenv("DISCORD_LARGE_IMAGE","claude")
APP_NAME=os.getenv("DISCORD_APP_NAME","Claude Code")
WS_URL=f"ws://{HOST}:{PORT}/ws?token={TOKEN}"
THROTTLE=15
DISCORD_RETRY=10
BRIDGE_RETRY=5
SMALL_IMAGE={"thinking":"thinking","tool":"tool","idle":"idle","waiting":"waiting","starting":"starting"}
logging.basicConfig(level=os.getenv("LOG_LEVEL","INFO").upper(),format="%(asctime)s %(levelname)s %(message)s")
log=logging.getLogger("cc-rpc")

def humantokens(n):
    if n>=1_000_000: return f"{n/1_000_000:.1f}M"
    if n>=1_000: return f"{n/1_000:.1f}K"
    return str(n)

def pretty_model(m):
    if not m: return "Claude"
    parts=m.lower().split("-")
    fam=next((p for p in parts if p in ("opus","sonnet","haiku","fable")),"")
    nums=[p for p in parts if p.isdigit()]
    ver=".".join(nums)
    return (fam.capitalize()+" "+ver).strip() if fam else "Claude"

def action_label(active):
    st=active.get("state","")
    if st=="tool": return ("Running "+active.get("tool","")).strip() or "Running a tool"
    if st=="thinking": return "Thinking"
    if st=="waiting": return "Waiting for input"
    if st=="idle": return "Idle"
    return "Starting"

def clip(text):
    text=text[:128]
    return text if len(text)>=2 else text+" "

def build_presence(snap):
    active=snap.get("active")
    if not active or snap.get("sessions",0)<1: return None
    action=action_label(active)
    bits=[action]
    n=snap.get("sessions",1)
    if n>1: bits.append(f"{n} sessions")
    bits.append(humantokens(snap.get("total_tokens",0))+" tok")
    return {"name":APP_NAME,"details":clip("Clauding in "+(active.get("project") or "a project")),"state":clip(" · ".join(bits)),"start":int(active.get("started_at",0)),"large_image":LARGE_IMAGE,"large_text":pretty_model(active.get("model","")),"small_image":SMALL_IMAGE.get(active.get("state",""),"claude"),"small_text":action}

async def apply(rpc, presence, applied):
    if presence==applied: return applied
    if presence is None: await rpc.clear(); log.info("cleared presence (no active sessions)")
    else: await rpc.update(**presence); log.info("presence: %s | %s",presence["details"],presence["state"])
    return presence

async def connect_discord():
    while True:
        try:
            rpc=AioPresence(APP_ID)
            await rpc.connect()
            log.info("connected to Discord")
            return rpc
        except Exception as e:
            log.warning("Discord not available (%s) - retrying in %ds",e,DISCORD_RETRY)
            await asyncio.sleep(DISCORD_RETRY)

async def apply_loop(rpc, state):
    """Applies the newest snapshot at most once per THROTTLE so bursts of tool events
    collapse into a single Discord update, staying under the ~15s presence rate limit."""
    while True:
        snap=state["snap"]
        pres=build_presence(snap) if snap is not None else None
        if snap is not None and pres!=state["applied"]:
            state["applied"]=await apply(rpc,pres,state["applied"])
            await asyncio.sleep(THROTTLE)
        else: await asyncio.sleep(1)

async def run_session(rpc):
    state={"snap":None,"applied":False}
    async with websockets.connect(WS_URL,ping_interval=20) as ws:
        log.info("connected to bridge at %s:%s",HOST,PORT)
        applier=asyncio.create_task(apply_loop(rpc,state))
        try:
            async for raw in ws:
                try: state["snap"]=json.loads(raw)
                except Exception: continue
        finally:
            applier.cancel()

async def main():
    if not APP_ID: log.error("DISCORD_APP_ID is not set - cannot start"); return
    if not TOKEN: log.error("BRIDGE_TOKEN is not set - cannot start"); return
    while True:
        rpc=await connect_discord()
        try: await run_session(rpc)
        except Exception as e: log.warning("bridge connection lost (%s) - reconnecting in %ds",e,BRIDGE_RETRY)
        finally:
            try: await rpc.close()
            except Exception: pass
        await asyncio.sleep(BRIDGE_RETRY)

if __name__=="__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
