import asyncio, secrets, logging, contextlib, json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app import config
from app.hub import store, manager
from app.events import router

logging.basicConfig(level=config.LOG_LEVEL,format="%(asctime)s %(levelname)s %(name)s %(message)s")
log=logging.getLogger("bridge")

async def heartbeat():
    while True:
        await asyncio.sleep(config.HEARTBEAT)
        if store.prune(): pass
        await manager.broadcast(store.snapshot())

@contextlib.asynccontextmanager
async def lifespan(app):
    if not config.TOKEN: log.warning("BRIDGE_TOKEN is empty - the bridge will reject every client until it is set")
    task=asyncio.create_task(heartbeat())
    log.info("bridge listening on %s:%s",config.HOST,config.PORT)
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError): await task

app=FastAPI(title="Claude Code Discord RPC Bridge",lifespan=lifespan)
app.include_router(router)

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    token=ws.query_params.get("token","")
    if not config.TOKEN or not secrets.compare_digest(token,config.TOKEN): await ws.close(code=4401); return
    await ws.accept()
    await manager.add(ws)
    await ws.send_text(json.dumps(store.snapshot()))
    log.info("client connected (%d total)",len(manager.clients))
    try:
        while True: await ws.receive_text()
    except WebSocketDisconnect: pass
    finally:
        manager.remove(ws)
        log.info("client disconnected (%d total)",len(manager.clients))
