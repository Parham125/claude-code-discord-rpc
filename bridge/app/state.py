import time, asyncio, json, logging
from app import config

log=logging.getLogger("bridge.state")
# Maps a hook event name to the session state it implies. SessionEnd is handled separately (removal).
EVENT_STATE={"SessionStart":"idle","UserPromptSubmit":"thinking","PreToolUse":"tool","PostToolUse":"thinking","Stop":"idle","SubagentStop":"thinking","Notification":"waiting"}

class SessionStore:
    def __init__(self):
        self.sessions={}

    def apply(self, ev):
        sid=ev.get("session_id")
        if not sid: return
        event=ev.get("event","")
        if event=="SessionEnd": self.sessions.pop(sid,None); return
        now=time.time()
        s=self.sessions.get(sid)
        if s is None: s={"project":"","state":"idle","tool":"","model":"","tokens":0,"started_at":now}; self.sessions[sid]=s
        s["last_activity"]=now
        if ev.get("project"): s["project"]=ev["project"]
        if ev.get("model"): s["model"]=ev["model"]
        if ev.get("tokens") is not None: s["tokens"]=ev["tokens"]
        s["state"]=EVENT_STATE.get(event,s["state"])
        s["tool"]=ev.get("tool","") if event=="PreToolUse" else ""
        if event=="SessionStart": s["started_at"]=now

    def prune(self):
        cutoff=time.time()-config.SESSION_TIMEOUT
        dead=[sid for sid,s in self.sessions.items() if s.get("last_activity",0)<cutoff]
        for sid in dead: self.sessions.pop(sid,None); log.info("pruned stale session %s",sid)
        return len(dead)

    def snapshot(self):
        items=list(self.sessions.values())
        total=sum(s.get("tokens",0) for s in items)
        active=max(items,key=lambda s:s.get("last_activity",0)) if items else None
        out={"type":"state","sessions":len(items),"total_tokens":total,"ts":time.time(),"active":None}
        if active is not None: out["active"]={"project":active["project"],"state":active["state"],"tool":active["tool"],"model":active["model"],"tokens":active["tokens"],"started_at":active["started_at"]}
        return out

class ConnectionManager:
    def __init__(self):
        self.clients=set()

    async def add(self, ws):
        self.clients.add(ws)

    def remove(self, ws):
        self.clients.discard(ws)

    async def broadcast(self, payload):
        if not self.clients: return
        raw=json.dumps(payload)
        dead=[]
        for ws in list(self.clients):
            try: await ws.send_text(raw)
            except Exception: dead.append(ws)
        for ws in dead: self.clients.discard(ws)
