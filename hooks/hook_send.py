#!/usr/bin/env python3
"""Claude Code hook -> RPC bridge sender. Reads the hook JSON on stdin, parses token
usage and model from the transcript, and POSTs a compact event to the bridge. It must
never block or crash the CLI, so every failure path exits 0 silently."""
import sys, os, json, urllib.request

URL=os.getenv("CLAUDE_RPC_URL","http://127.0.0.1:8787/api/v1/events")
TOKEN=os.getenv("CLAUDE_RPC_TOKEN","")

def read_usage(path):
    total=0; model=""
    if not path or not os.path.isfile(path): return total,model
    try:
        with open(path,encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if not line: continue
                try: row=json.loads(line)
                except Exception: continue
                if row.get("type")!="assistant": continue
                msg=row.get("message",{})
                if msg.get("model"): model=msg["model"]
                u=msg.get("usage") or {}
                total+=u.get("output_tokens",0)
    except Exception: return total,model
    return total,model

def main():
    try: data=json.load(sys.stdin)
    except Exception: return
    event=data.get("hook_event_name","")
    sid=data.get("session_id","")
    if not sid or not event: return
    cwd=data.get("cwd","") or os.getcwd()
    payload={"session_id":sid,"event":event,"project":os.path.basename(cwd.rstrip("/")) or cwd,"tool":data.get("tool_name","")}
    if event!="SessionEnd":
        tokens,model=read_usage(data.get("transcript_path",""))
        payload["tokens"]=tokens
        if model: payload["model"]=model
    body=json.dumps(payload).encode()
    req=urllib.request.Request(URL,data=body,method="POST",headers={"Content-Type":"application/json","X-Bridge-Token":TOKEN})
    try: urllib.request.urlopen(req,timeout=1.5).read()
    except Exception: pass

if __name__=="__main__":
    main()
