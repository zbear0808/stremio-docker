# Stremio Server + VPN (Docker)

Self-hosted Stremio streaming server routed through a [Gluetun](https://github.com/qdm12/gluetun) VPN container (AirVPN / WireGuard by default). All torrent traffic stays inside the VPN tunnel.

## Architecture

```
┌─────────────────────────────────────────────┐
│  Docker                                     │
│                                             │
│  ┌───────────┐      ┌──────────────────┐    │
│  │  Gluetun  │◄─────│  stremio-server  │    │
│  │  (VPN)    │      │  (network_mode:  │    │
│  │           │      │   service:gluetun)│    │
│  └─────┬─────┘      └──────────────────┘    │
│        │                                    │
│   ports 11470 (HTTP) & 12470 (HTTPS)        │
│   exposed on 127.0.0.1                      │
└────────┼────────────────────────────────────┘
         │
    Your Mac (localhost)
```

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- An [AirVPN](https://airvpn.org/) account with a WireGuard configuration generated
  - Other VPN providers supported by Gluetun will also work — see the [Gluetun wiki](https://github.com/qdm12/gluetun-wiki)

---

## Quick Start

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd stremio-docker
```

### 2. Create your `.env` file

Copy the example and fill in your VPN credentials:

```bash
cp .env.example .env
```

Edit `.env` with the values from your AirVPN WireGuard config (or run the included helper script):

```bash
python3 parse_vpn_config.py AirVPN_*.conf
```

Your `.env` should contain at minimum:

| Variable | Description |
|---|---|
| `WIREGUARD_PRIVATE_KEY` | Your WireGuard private key |
| `WIREGUARD_PRESHARED_KEY` | Your WireGuard preshared key |
| `WIREGUARD_ADDRESSES` | Your assigned VPN IP (e.g. `10.x.x.x/32`) |
| `SERVER_REGIONS` | Preferred region (default: `America`) |

### 3. Start the stack

```bash
docker compose up -d
```

### 4. Verify it's running

```bash
# Check container health
docker compose ps

# Test the streaming server is reachable
curl http://127.0.0.1:11470

# Verify VPN is active (should return your VPN IP, not your real IP)
docker exec gluetun wget -qO- https://ipinfo.io/ip
```

---

## Connecting to the Stremio Frontend

You have two options: the **Stremio Web Player** (browser) or the **Stremio Desktop App** (macOS/Windows/Linux).

---

### Option A: Stremio Web Player (Browser)

The official web player lives at **[web.stremio.com](https://web.stremio.com)**. You need to point it at your local streaming server.

> [!IMPORTANT]
> Because `web.stremio.com` is served over **HTTPS**, your browser will block plain HTTP connections to your server (mixed-content policy). The Stremio server auto-generates a self-signed certificate on port **12470** to handle this.

#### Steps

1. Make sure your Docker stack is running (`docker compose up -d`)

2. Open the following URL in your browser:

   ```
   https://web.stremio.com/#/?streamingServer=https%3A%2F%2F127.0.0.1%3A12470
   ```

3. **Accept the self-signed certificate** — before the web player will work, you need to tell your browser to trust the Stremio server's certificate:
   - Open [https://127.0.0.1:12470](https://127.0.0.1:12470) directly in a new tab
   - You'll see a security warning — click **Advanced** → **Proceed to 127.0.0.1 (unsafe)**
   - You should see a JSON response from the server — this means the cert is now trusted for this session
   - Go back to the Stremio Web tab and refresh

4. Log in with your Stremio account

5. **Bookmark the URL** so you don't have to type the `streamingServer` parameter again

> [!TIP]
> If you see "Streaming Server is not available" in Settings, repeat step 3 to re-accept the certificate. You may need to do this each time the container recreates its certificate.

#### Alternative: Change server in Settings

1. Open [https://web.stremio.com](https://web.stremio.com)
2. Log in to your Stremio account
3. Go to **⚙ Settings**
4. Scroll to **Streaming Server**
5. Change the URL to `https://127.0.0.1:12470`
6. The status should show **Online** ✅

---

### Option B: Stremio Desktop App (macOS / Windows / Linux)

The desktop app has a built-in streaming server, but you want it to use **your Docker server** instead (so traffic goes through the VPN).

#### Steps

1. Download and install Stremio from [stremio.com/downloads](https://www.stremio.com/downloads)

2. **Quit the built-in server** — when you launch Stremio, it starts its own local server. You need to stop it since your Docker container is already using port 11470:
   - On **macOS**: Check for a Stremio Server icon in the menu bar and quit it, or:
     ```bash
     # Kill any local stremio-server process
     pkill -f stremio-server || true
     ```
   - On **Windows**: Right-click the Stremio Server tray icon → Quit

3. Make sure your Docker stack is running:
   ```bash
   docker compose up -d
   ```

4. Open the Stremio app — it will automatically detect and connect to the server at `http://127.0.0.1:11470` ✅

   > The desktop app uses HTTP (port 11470) since it's a native app and doesn't have the browser's mixed-content restriction.

5. **Verify the connection**: Go to **⚙ Settings** → scroll to **Streaming Server** → it should show status **Online**

> [!NOTE]
> If the desktop app doesn't connect automatically, go to Settings → Streaming Server and manually set the URL to `http://127.0.0.1:11470`.

---

## Ports Reference

| Port | Protocol | Used By | Description |
|------|----------|---------|-------------|
| `11470` | HTTP | Desktop app, local tools | Plain HTTP streaming server |
| `12470` | HTTPS | Stremio Web (browser) | HTTPS with auto-generated self-signed cert |

Both ports are bound to `127.0.0.1` (localhost only) for security.

---

## Managing the Stack

```bash
# Start
docker compose up -d

# Stop
docker compose down

# View logs
docker compose logs -f

# View only stremio-server logs
docker compose logs -f stremio-server

# Restart after config changes
docker compose down && docker compose up -d

# Check your VPN IP
docker exec gluetun wget -qO- https://ipinfo.io/ip
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Stremio Web says "Server not available" | Accept the self-signed cert at [https://127.0.0.1:12470](https://127.0.0.1:12470) first |
| Desktop app won't connect | Kill any local `stremio-server` process that's hogging port 11470 |
| Containers keep restarting | Check `docker compose logs gluetun` — likely a VPN credential issue |
| Slow speeds | Try a different `SERVER_REGIONS` or `SERVER_COUNTRIES` in `.env` |
| `curl: (7) Failed to connect` | Wait 10-20s after `docker compose up` for Gluetun to establish the VPN tunnel |

---

## File Structure

```
stremio-docker/
├── docker-compose.yml      # Main stack definition
├── .env.example            # Template for VPN credentials
├── .env                    # Your actual credentials (git-ignored)
├── .gitignore              # Keeps secrets and cache out of git
├── parse_vpn_config.py     # Helper to extract creds from .conf files
├── stremio-cache/          # Persistent server data (git-ignored)
└── README.md               # This file
```

