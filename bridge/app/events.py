import secrets, logging
from fastapi import APIRouter, Request, Response, HTTPException
from app import config
from app.hub import store, manager

log=logging.getLogger("bridge.events")
router=APIRouter(prefix="/api/v1")

def check_token(request):
    sent=request.headers.get("x-bridge-token","")
    if not config.TOKEN or not secrets.compare_digest(sent,config.TOKEN): raise HTTPException(status_code=401,detail={"error":"unauthorized","message":"Bad or missing bridge token","details":None})

@router.post("/events", status_code=204)
async def ingest(request: Request):
    check_token(request)
    try: ev=await request.json()
    except Exception: raise HTTPException(status_code=400,detail={"error":"bad_request","message":"Body must be JSON","details":None})
    if not isinstance(ev,dict) or not ev.get("session_id") or not ev.get("event"): raise HTTPException(status_code=422,detail={"error":"invalid_event","message":"session_id and event are required","details":None})
    store.apply(ev)
    await manager.broadcast(store.snapshot())
    log.debug("event %s for %s (%d sessions)",ev.get("event"),ev.get("session_id"),len(store.sessions))
    return Response(status_code=204)

@router.get("/health")
async def health():
    return {"status":"ok","sessions":len(store.sessions),"clients":len(manager.clients)}
