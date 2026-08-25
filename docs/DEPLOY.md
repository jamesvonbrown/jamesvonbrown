# Running it somewhere permanent

The scanner has to be always-on, so a laptop that sleeps won't work.

## Which machine

**A spare computer at home** is the best option, and not just because it's
free: Facebook treats residential IPs far more kindly than datacenter ones. A
Mac mini, an old laptop with sleep disabled, or a Raspberry Pi 4 all work.

**A cloud VPS** ($5–12/month — Hetzner, DigitalOcean, Fly) is more reliable and
always up, but a datacenter IP is more likely to draw checkpoints from
Facebook. Fine if you're using demo/manual/eBay sources.

Either way the container is identical.

## Docker

```bash
cp .env.example .env      # fill it in — see SETUP.md
docker compose up -d --build
```

Serves on port 8000. `./data` holds the database, cached photos, listing
screenshots, and the browser profile — that's the directory to back up.

The image includes Chromium (~1.5GB). If you aren't scraping Facebook:

```bash
docker compose build --build-arg WITH_BROWSER=false
```

### Logging in through Docker

`flipscan login` needs a visible browser, which a container doesn't have. Two
options:

1. **Log in on the host, copy the profile in** (simplest):
   ```bash
   pip install -e ".[browser]" && playwright install chromium
   flipscan login
   # data/browser-profile/ is already mounted into the container
   ```
2. **Run the container with an X display forwarded** — more fiddly, rarely
   worth it.

## Without Docker (systemd)

```ini
# /etc/systemd/system/flipscan.service
[Unit]
Description=FlipScan
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=flipscan
WorkingDirectory=/opt/flipscan
Environment="PATH=/opt/flipscan/.venv/bin"
ExecStart=/opt/flipscan/.venv/bin/flipscan serve
Restart=always
RestartSec=10

# The service only needs its own directory.
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/flipscan/data

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now flipscan
journalctl -u flipscan -f
```

## macOS (launchd)

```xml
<!-- ~/Library/LaunchAgents/com.flipscan.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.flipscan</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/you/flipscan/.venv/bin/flipscan</string>
    <string>serve</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/you/flipscan</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict></plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.flipscan.plist
sudo pmset -a sleep 0          # stop the Mac sleeping
```

## Reaching it from outside the house

You need HTTPS for two reasons: Web Push refuses to work on an insecure origin,
and you'd otherwise be sending the API token in the clear.

**Tailscale** is the easiest and safest. Install it on the server and the
phone, and the app is reachable at `http://100.x.x.x:8000/app/` over the
private network with nothing exposed to the internet.

**Cloudflare Tunnel** gives a public HTTPS hostname with no open ports:

```bash
cloudflared tunnel --url http://localhost:8000
```

**Caddy**, if you have a domain and can forward 80/443 — automatic
certificates, one line of config:

```
flip.yourdomain.com {
    reverse_proxy localhost:8000
}
```

Then set `FLIPSCAN_PUBLIC_BASE_URL` to the HTTPS URL so notification links work.

## Backups

Everything that matters is in `data/`:

```bash
tar czf flipscan-$(date +%F).tar.gz data/
```

The valuable part is `flipscan.db` — it holds the price history and the sales
feedback that the calibration learns from. Losing it means starting the
learning over.

```bash
# SQLite-safe backup while running
sqlite3 data/flipscan.db ".backup data/backup.db"
```

## Health

`GET /health` needs no auth — point any uptime monitor at it.

`GET /api/status` (authenticated) reports the last scan, AI spend, and a
`warnings` array that surfaces the things that silently break a scanner: a
logged-out Facebook session, missing eBay keys, no notification channel.

The thing worth alerting on is **a scheduled scan that saw zero listings** — it
almost always means the session died.
