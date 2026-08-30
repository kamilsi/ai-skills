---
name: moonshine-game-streaming
description: >-
  Administers, monitors, configures, and debugs the Moonshine game streaming host on odyseusz
  (NVIDIA RTX 4060, Ubuntu 26.04 Wayland, HDR, 4K). Use when managing game streaming, adding
  games (Steam, GOG, Heroic), troubleshooting Moonlight client issues (Apple TV, macOS, webOS),
  tuning bitrates, adjusting HDR/codecs, managing systemd services, or resolving network/frame pacing bugs.
---

# Moonshine Game Streaming Host Administration Skill (`odyseusz`)

This skill provides a complete operational manual, troubleshooting playbook, and architecture reference for managing the **Moonshine** game streaming server on `odyseusz`.

---

## 🏛️ 1. Architecture & Core Concept

- **Host Name:** `odyseusz` (Ubuntu 26.04 LTS, pure Wayland session).
- **GPU:** NVIDIA GeForce RTX 4060 (Driver 595+, Vulkan 1.4, NVENC AV1/HEVC/H.264, 10-bit HDR).
- **Physical Monitor:** 34" LG Ultrawide 21:9 (2560x1080) attached via DisplayPort.
- **Server Software:** **Moonshine** (`hgaiser/moonshine`, written in Rust).
- **Streaming Protocol:** NVIDIA GameStream / Moonlight compatible.

### Why Moonshine (and NOT Sunshine / X11):
- **Isolated Virtual Headless Compositor:** Unlike Sunshine (which mirrors the physical monitor and was locking 16:9 clients to the physical 21:9 ultrawide aspect ratio), Moonshine spins up an isolated, headless Wayland session per client (`moonshine-session.service`).
- **Native Resolution & Aspect Ratio:** Moonshine renders at whatever resolution/refresh rate the client requests (e.g. **4K 16:9 3840x2160 @ 60Hz/100Hz**) without needing dummy plugs, EDID hacks, or altering the physical monitor.
- **Vulkan & Direct DMA-BUF:** Captures frames directly from GPU memory via DMA-BUF modifiers and encodes them in hardware using NVENC.

---

## ⚙️ 2. Essential Commands & Service Management

### Service Control
Moonshine runs as a systemd template unit for user `kamil`:
```bash
# Check service status
systemctl status moonshine@kamil

# View live streaming logs
journalctl -u moonshine@kamil -f -n 50

# Restart service (requires sudo for systemctl, or kill process as user kamil)
sudo systemctl restart moonshine@kamil
# Alternately, as user kamil (systemd will auto-restart it due to Restart=always):
killall moonshine
```

### Hardware Diagnostics & Healthcheck
```bash
# Run full Vulkan, NVENC, DMA-BUF, DRM render node diagnostics:
export XDG_RUNTIME_DIR=/run/user/1000 && moonshine healthcheck
```

### Client Pairing URL
When a new Moonlight client (Apple TV, Mac, iPad) initiates pairing:
- **LAN Web UI:** `http://192.168.1.15:47989/pin`
- **Tailscale Web UI:** `http://100.81.194.64:47989/pin`
- **Direct PIN Submission via CLI:**
  ```bash
  curl -X POST -d "uniqueid=0123456789ABCDEF&pin=1234" http://127.0.0.1:47989/submit-pin
  ```

---

## 📁 3. File Paths & Key Configurations

| Component | Path on `odyseusz` | Purpose |
| :--- | :--- | :--- |
| **Main Config** | `~/.config/moonshine/config.toml` | Server settings, ports, apps, scanners |
| **Box Art Covers** | `~/.config/moonshine/covers/` | PNG/JPG game cover images for Moonlight |
| **TLS Certificates**| `~/.config/moonshine/cert.pem`, `key.pem` | Moonlight pairing & encryption certs |
| **Startup Wrapper**| `/usr/bin/start-moonshine.sh` | Sets `XDG_RUNTIME_DIR` & `DBUS` environment |
| **Systemd Unit** | `/usr/lib/systemd/system/moonshine@.service`| System service template definition |
| **Steam Binary** | `/usr/games/steam` | **Important:** Ubuntu location for Steam |
| **Heroic Config** | `~/.config/heroic/` | GOG/Epic library, Proton configurations |
| **Heroic Games** | `~/Games/Heroic/` | Installed GOG/Epic game directories |

---

## 🎮 4. Game Configuration & Launching

### A. Steam Games (Automatic Discovery)
Configured via `[[application_scanner]]` in `~/.config/moonshine/config.toml`:
```toml
[[application]]
title = "Steam"
command = [
    "/usr/games/steam",
    "steam://open/bigpicture",
]
launch_timeout_secs = 2

[[application_scanner]]
type = "steam"
library = "$HOME/.local/share/Steam"
command = [
    "/usr/games/steam",
    "-bigpicture",
    "steam://rungameid/{game_id}",
]
launch_timeout_secs = 2
```

### B. GOG & Epic Games via Heroic (e.g. Cyberpunk 2077)
Define an explicit `[[application]]` entry in `~/.config/moonshine/config.toml`:
```toml
[[application]]
title = "Cyberpunk 2077"
command = [
    "/usr/bin/heroic",
    "--launch",
    "heroic://launch/gog/1423049311",
]
boxart = "/home/kamil/.config/moonshine/covers/cyberpunk2077.png"
launch_timeout_secs = 5
```
*Note:* GOG App ID for Cyberpunk 2077 is `1423049311`.

---

## 🚨 5. Known Issues & Troubleshooting Playbook

### 1. Error 503 on Launching Steam
- **Symptom:** Moonlight reports error 503; Moonshine log: `ERROR Main program '/usr/bin/steam' not found in PATH`.
- **Cause:** On Ubuntu/Debian, Steam is installed in `/usr/games/steam`, not `/usr/bin/steam`.
- **Fix:** Update `command` in `config.toml` to use `/usr/games/steam`.

### 2. High Dropped Frames (94%) / "Slow Connection" Warning on 4K Stream
- **Symptom:** Moonlight displays *"Slow connection to your PC / reduce bitrate"*; FPS drops to ~2-3 FPS with 90%+ dropped frames; Network ping is ~1ms.
- **Root Cause:**
  1. *Client Decoding Overload:* 4K @ 100 FPS at 150 Mbps causes client hardware decoder (e.g. Apple Silicon) to take >22ms per frame (against a 10ms frame deadline). Buffer overflows, forcing client to drop 94% of frames.
  2. *UDP Bursting:* At 150+ Mbps in 4K, UDP packets burst simultaneously and can overrun socket queues.
- **Fix:**
  - In Moonlight client settings, configure:
    - **Resolution:** 4K (3840x2160)
    - **Refresh Rate:** **60 FPS** (16.6ms budget)
    - **Bitrate:** **70 – 80 Mbps**
    - **Codec:** **HEVC (H.265)**
  - This drops client decode time to **~7ms**, frame queue delay to **0.02ms**, and network frame drop to **0.00%**.

### 3. "Low Bitrate" Warning in Static Steam Menus (False Positive)
- **Symptom:** Warning appears when sitting idle in menus.
- **Explanation:** In static scenes, NVENC compresses frames down to ~1-2 Mbps. Moonlight's heuristic bandwidth detector misinterprets the low throughput as a network slowdown. Once movement/gameplay starts, bitrate scales up automatically.

### 4. Direct LAN vs. Tailscale MTU Fragmentation
- **LAN IP (`192.168.1.15`):** Standard Ethernet MTU 1500, direct 0.3ms latency, zero encryption overhead. **Preferred for local streaming.**
- **Tailscale IP (`100.81.194.64`):** WireGuard tunnel MTU is 1280. Video packets of 1392 bytes will fragment if streamed over Tailscale. Use direct LAN IP when on the home network.

### 5. Apple TV 4K & LG OLED Refresh Rate Limits
- **tvOS Limitation:** Apple TV 4K limits 3rd party apps (including Moonlight) to **60 Hz maximum**.
- **HDR:** Fully supported (HDR10 10-bit) on LG OLED with <2ms decode time.
- **For 120 Hz on LG OLED:** Use *Moonlight for webOS* (installed via webOS Dev Manager directly on the LG TV) or connect a Mac/PC via HDMI 2.1.

### 6. Headless Session & Screen Lock
- Ensure lingering is active: `sudo loginctl enable-linger kamil`
- GNOME screen lock timeout is disabled (`gsettings set org.gnome.desktop.screensaver lock-enabled false`).
- Do not create desktop autostart locking scripts.
