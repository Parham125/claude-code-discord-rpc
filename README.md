# Discord RPC for Claude Code

Shows a Discord Rich Presence ("Clauding...") for your Claude Code sessions, with the
current project, live token usage, active model, and a session timer. Supports multiple
Claude Code sessions at once, aggregated into a single presence.

It is built for a split setup: Claude Code runs in a docker container on a home lab
server, while Discord runs on a separate local machine.

```
  ┌─ home lab container ───────────────┐         ┌─ your local PC ──────────────┐
  │  Claude Code ──hooks──► hook_send  │         │  systemd user service        │
  │                           │        │  ws +   │   client.py ──► Discord RPC  │
  │                           ▼        │  token  │        ▲                     │
  │                    bridge (FastAPI)│◄─────────────────┘                     │
  │                    :8787 on LAN    │         │                              │
  └────────────────────────────────────┘         └──────────────────────────────┘
```

- **`bridge/`** - FastAPI websocket server. Runs in the container. Hooks POST events to it;
  it tracks every session and broadcasts one aggregated snapshot to connected clients.
- **`hooks/`** - tiny stdlib-only sender fired by Claude Code hooks. Parses token usage and
  model from the session transcript and POSTs to the bridge. Never blocks the CLI.
- **`local/`** - the Discord client that runs on your machine as a systemd user service.

Discord only allows one Rich Presence per application, so multiple sessions are aggregated:
the presence shows details from the most recently active session plus combined counts
(`Thinking · 3 sessions · 6.5M tok`).

## Requirements

- **Python 3.9+** on both the server (bridge + hooks) and the local machine (client). On
  Debian/Ubuntu: `sudo apt install python3 python3-venv python3-pip`.
- **Claude Code** running on the server/container.
- **Discord desktop app** running and signed in on the local machine (Rich Presence needs the
  desktop client, not the browser).
- **Docker** is optional - only needed if you run the bridge via the included
  `bridge/Dockerfile` instead of directly with Python.

## 1. Create a Discord application

1. Go to https://discord.com/developers/applications, **New Application**, name it (e.g. "Claude Code").
2. Copy the **Application ID** (General Information). This is your `DISCORD_APP_ID`.
3. Under **Rich Presence > Art Assets**, upload the ready-made icons from **`assets/`** -
   set each one's key to its filename without `.png` (`claude`, `thinking`, `tool`, `idle`,
   `waiting`, `starting`). See `assets/README.md` for the full mapping. Keys must match
   exactly; uploads can take a few minutes to propagate.

## 2. Deploy the bridge (where Claude Code runs)

First generate a shared secret for `BRIDGE_TOKEN` (standard library, nothing to install):

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy `bridge/.env.example` to `bridge/.env` and set `BRIDGE_TOKEN` to that value. Then run the
bridge one of two ways.

**Option A - Docker** (uses the included `bridge/Dockerfile` and `bridge/docker-compose.yml`):

```bash
cd bridge
cp .env.example .env          # set BRIDGE_TOKEN
docker compose up -d --build
```

**Option B - plain Python** (no Docker):

```bash
cd bridge
python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set BRIDGE_TOKEN
python run.py
```

Either way the bridge listens on `0.0.0.0:8787`. From the local machine, reach it at the
server's LAN address (referred to below as `<BRIDGE_HOST>`).
Health check: `curl -H "X-Bridge-Token: <token>" http://<BRIDGE_HOST>:8787/api/v1/health`.

## 3. Wire up the Claude Code hooks (container)

The hooks must fire for every Claude Code session, so add them to the user-level
`~/.claude/settings.json`. See `hooks/settings.snippet.json` - add the two `env` vars
(`CLAUDE_RPC_URL`, `CLAUDE_RPC_TOKEN`) and **append** each hook entry to the matching event
array without removing your existing hooks. Point each command at your clone of
`hooks/hook_send.py` - it is pure standard-library Python 3, so there is nothing to install.

`CLAUDE_RPC_TOKEN` must equal the bridge's `BRIDGE_TOKEN`. `CLAUDE_RPC_URL` must point at
wherever the bridge is reachable **from Claude Code's environment** - the hook is just an HTTP
POST from wherever Claude Code runs:

- **Bridge as a plain process in the same host/container as Claude Code** ->
  `http://127.0.0.1:8787/api/v1/events`.
- **Bridge in Docker, Claude Code on the host** -> `http://127.0.0.1:8787/api/v1/events`
  (`docker compose` publishes `8787:8787` on the host).
- **Bridge and Claude Code in separate containers** -> put them on the same Docker network and
  use the bridge's service name (`http://bridge:8787/api/v1/events`), or the host address.

Tip: if Claude Code itself runs inside a container, running the bridge as a process in that
same container (`python run.py`) is simpler than Docker, since the hook can just use localhost.

## 4. Install the local client (your machine, where Discord runs)

```bash
cd local
./install.sh
# then edit ~/.config/discord-rpc-cc/env (DISCORD_APP_ID + BRIDGE_TOKEN), then:
systemctl --user daemon-reload
systemctl --user enable --now discord-rpc-cc.service
journalctl --user -u discord-rpc-cc.service -f
```

`install.sh` builds a venv at `~/.local/share/discord-rpc-cc/venv`, installs
`local/requirements.txt` (`pypresence`, `websockets`), copies `client.py`, and drops the
systemd user unit. Run `loginctl enable-linger $USER` if you want it running while logged out.
Discord must be the desktop app and running for presence to appear.

To run it without systemd (handy for a first test):

```bash
cd local
python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
DISCORD_APP_ID=... BRIDGE_HOST=<BRIDGE_HOST> BRIDGE_TOKEN=... python client.py
```

## What shows up

- **Title**: `Claude Code` (override with `DISCORD_APP_NAME`).
- **Details line**: `Clauding in <project>` (folder name of the most active session).
- **State line**: action + session count + tokens, e.g. `Running Bash · 2 sessions · 120K tok`.
- **Timer**: elapsed since the active session was first seen by the bridge.
- **Large image tooltip**: the model, e.g. `Opus 4.8`.

## Notes

- The token count is the output tokens Claude generated across the session (summed from the
  transcript in `hooks/hook_send.py` - change that line to include input/cache if you prefer).
- Sessions with no hook activity for `BRIDGE_SESSION_TIMEOUT` (default 30 min) are pruned, so
  a killed CLI eventually drops off.
- Discord rate-limits presence updates to ~once per 15s; the client coalesces bursts of tool
  events into a single update.
- **Flatpak/Snap Discord** keep their RPC socket in a sandboxed dir. The systemd unit symlinks
  it automatically; for a manual run, link it yourself first:
  `ln -sf $XDG_RUNTIME_DIR/app/com.discordapp.Discord/discord-ipc-0 $XDG_RUNTIME_DIR/discord-ipc-0`.
- Rich Presence only shows if Discord's **Settings > Activity Privacy > "Share your detected
  activities with others"** is enabled, and your status is not Invisible.
- The token is a shared secret over a plain LAN port. Keep the port on your trusted LAN only;
  do not forward it to the public internet without putting it behind TLS/a tunnel.

## License

MIT - see [LICENSE](LICENSE).

The default `claude.png` uses the Claude logo, which is a trademark of Anthropic; it is
included for convenience and is not affiliated with or endorsed by Anthropic. Swap it for your
own art (or one of the other icons) if you prefer. The status icons are from
[Lucide](https://lucide.dev) (ISC). This project is not affiliated with Anthropic or Discord.
