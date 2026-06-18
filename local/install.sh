#!/usr/bin/env bash
# Installs the Claude Code Discord presence client as a systemd *user* service.
# Run on your local machine (the one running Discord), not on the home lab.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$HOME/.local/share/discord-rpc-cc"
CFG="$HOME/.config/discord-rpc-cc"
UNIT="$HOME/.config/systemd/user"
mkdir -p "$APP" "$CFG" "$UNIT"
echo "Creating virtualenv at $APP/venv"
python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install --quiet --upgrade pip
"$APP/venv/bin/pip" install --quiet -r "$SRC/requirements.txt"
cp "$SRC/client.py" "$APP/client.py"
cp "$SRC/discord-rpc-cc.service" "$UNIT/discord-rpc-cc.service"
if [[ ! -f "$CFG/env" ]]; then
  cp "$SRC/.env.example" "$CFG/env"
  echo
  echo ">> Edit $CFG/env and set DISCORD_APP_ID + BRIDGE_TOKEN, then run:"
else
  echo ">> Config already exists at $CFG/env (left untouched). To (re)start, run:"
fi
echo "   systemctl --user daemon-reload"
echo "   systemctl --user enable --now discord-rpc-cc.service"
echo "   journalctl --user -u discord-rpc-cc.service -f   # watch logs"
echo
echo "Tip: run 'loginctl enable-linger $USER' so it runs even when you are logged out."
