# BO2 Emblem Ripper PS4/PS5

A Windows proxy tool for capturing Black Ops II emblems visible on PS5 and loading a selected capture into your own BO2 emblem editor session.

## Downloads

For normal use, download `BO2EmblemToolkit.exe` from this repository's **Releases** page. It is a precompiled Windows build; Python is not required.

The full readable Python source for that application is in this repository, including its web UI, proxy code, reference shape assets, build script, and PyInstaller specification.
See [BINARY_AUDIT.md](BINARY_AUDIT.md) for a repeatable verification against the shipped executable.

## What you need

- A Windows PC and a PS5 on the same local network
- The release `BO2EmblemToolkit.exe`, or Python 3.9+ if running from source
- Permission to set a proxy server in the PS5 network settings

## Quick start (precompiled app)

1. Download and run `BO2EmblemToolkit.exe` from Releases.
2. Keep its terminal window open. The control panel should open in your browser. If it does not, visit `http://localhost:8090`.
3. Note the LAN IP and port `8080` shown by the app.
4. On PS5: `Settings -> Network -> Settings -> Set Up Internet Connection -> Advanced Settings`.
5. Set `Proxy Server` to `Use`, then enter the app's IP address and port.
6. In the control panel, select `Capture`, then visit a player's BO2 profile/channel on the PS5.
7. Select a captured emblem, switch to `Show`, and open your own BO2 emblem editor to load it.

Switch the PS5 proxy back to `Do Not Use` when you are finished.

## Run from source

```powershell
python -m pip install -r requirements.txt
python run.py
```

On Windows, `start.bat` runs the same command. The source runtime depends only on Pillow.

## Build the Windows executable

Install Python 3.9+ and run:

```powershell
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean BO2EmblemToolkit.spec
```

The resulting file is `dist\BO2EmblemToolkit.exe`. Alternatively, run `build_exe.bat`; it installs the build dependency and creates the same output. The app icon, reference shapes, web UI, and license are bundled by the build configuration.

## Notes and troubleshooting

### `HTTPS traffic to auth3.prod.demonware.net`

Expected. This says the tool saw unrelated encrypted PlayStation/Demonware traffic and passed it through untouched. The proxy only changes the BO2 emblem endpoints it is designed to handle; it does not decrypt normal PSN traffic.

### `PIL.Image...DecompressionBombWarning`

This preview-library warning can appear when Pillow sees a very large local reference image. It is not evidence of malware, a virus, or an attack. Current source suppresses the warning for the trusted local shape assets used by this tool.

### `ConnectionAbortedError: [WinError 10053]`

This usually happens when the browser closes or refreshes while the local control panel is writing a response. It is a harmless local client disconnect, not proof that antivirus or another program is blocking the ripper. Current source handles these disconnects quietly.

### PS5 cannot connect after enabling the proxy

- Confirm the PC and PS5 are on the same network.
- Use the exact IP shown by the app, especially if using a Windows hotspot.
- Allow inbound TCP port `8080` in Windows Firewall for private networks.
- Keep the app open and re-test the connection after saving the proxy settings.

### Capture list is empty or a selected emblem does not load

- Verify the mode is `Capture` when opening another player's profile/channel.
- Verify the mode is `Show` and an emblem is selected before opening your editor.
- Restart BO2 or switch game modes before reopening the editor, since it commonly fetches emblem data only once per session.
- Emblems using shapes your account has not unlocked can be rejected by the game.

## Safety

This project is open source so you can inspect exactly what it does and build the executable yourself. It runs a local proxy for the narrow purpose of handling BO2 emblem requests and passes unrelated HTTPS traffic through. Windows SmartScreen may identify the release build as an unrecognized publisher because it is not code-signed; that is a publisher-reputation warning, not proof of malware.

## Local data

Captured emblems are stored in `saved/` beside the executable or source checkout. Local `saved/` content and `state.txt` are ignored by Git and are never included in releases.
