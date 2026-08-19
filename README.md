# BO2 Emblem Ripper PS4/PS5

`BO2EmblemToolkit.exe` is a Windows tool for capturing a Black Ops II emblem from another player's profile and loading that captured emblem into your own emblem editor session on PS5.

It works by running a small local proxy on your PC. Your console is pointed at that proxy through the normal PS5 network settings menu. The tool only cares about the old BO2 emblem-storage HTTP requests. Regular HTTPS traffic, including PSN sign-in, stays tunneled through untouched and is not decrypted by this app.

## What you need

- A Windows PC
- A PS5 on the same network as the PC
- `BO2EmblemToolkit.exe`
- A home network or Windows hotspot that both the PC and PS5 can use

## Files in this folder

- `BO2EmblemToolkit.exe`: the app
- `saved/`: your captured emblems created while using the app
- `state.txt`: the current mode used by the app

## First-time setup

1. Put `BO2EmblemToolkit.exe` in its own folder.
2. Double-click `BO2EmblemToolkit.exe`.
3. Leave the terminal window open.
4. Let the app open the control panel in your browser. If it does not open automatically, go to `http://localhost:8090`.
5. In the terminal window, look for the line that shows your proxy address, for example `192.168.1.42 : 8080`.
6. On your PS5, go to `Settings -> Network -> Settings -> Set Up Internet Connection`.
7. Pick your current connection, open `Advanced Settings`, and set `Proxy Server` to `Use`.
8. Enter the IP address and port shown by the app.
9. Save the settings and test the connection on the PS5.

## How to use it

### Capture an emblem

1. In the control panel, switch to `Capture`.
2. On the PS5, open the profile or channel of the player whose emblem you want.
3. Wait a few seconds for the emblem to appear in the captured list.
4. Optionally rename the captured emblem in the control panel so it is easier to recognize later.

### Load the captured emblem into your own editor

1. Click the captured emblem you want to use.
2. Switch the tool to `Show`.
3. On the PS5, open your own BO2 emblem editor.
4. The selected emblem should load in place of the emblem the game would normally fetch.
5. Save it in-game.

## Important behavior to know

- The BO2 emblem editor usually only fetches the emblem data once per game session. If you want to load a different captured emblem later, restart BO2 or switch to Zombies and back to Multiplayer before reopening the editor.
- If the emblem uses shapes or icons your account has not unlocked, the game may fail to display it correctly or refuse to save it. That is enforced by the game itself, not by this tool.
- The terminal window must stay open while you use the app. Closing it stops the proxy and the control panel.

## Common warnings, errors, and fixes

### The screenshot warning about `HTTPS traffic to auth3.prod.demonware.net`

This is expected and not a problem.

That line means the tool saw normal encrypted PlayStation or Demonware traffic that was not the BO2 emblem endpoint it actually modifies, so it tunneled that traffic through untouched. In plain English: the app noticed unrelated HTTPS traffic and deliberately left it alone.

### `PIL.Image.py:3578: DecompressionBombWarning`

This warning looks scary, but in this app it is not evidence of malware, a virus, or somebody attacking your PC.

It comes from Pillow, the image library used to render emblem previews. Pillow warns when an image has a very large pixel count. In this tool's case, that warning is tied to local trusted image assets used for rendering previews, not to remote code execution or a security breach.

If you see this warning by itself and the tool keeps working, it is generally safe to ignore.

### `ConnectionAbortedError: [WinError 10053] An established connection was aborted by the software in your host machine`

This message does not usually mean antivirus or some unknown program is attacking the app.

In this project, it most commonly happens when the local browser disconnects from the built-in control panel while the app is still sending a response. That is noisy, but it is not proof that the tool is unsafe or that some outside software is blocking the emblem ripper.

### The PS5 says there is no internet connection after I enable the proxy

Try these fixes:

1. Make sure the PS5 and the PC are on the same network.
2. If you are using a Windows hotspot, use the hotspot IP shown by the app, not your normal router IP.
3. Allow port `8080` through Windows Firewall for private networks.
4. Retest the connection on the PS5 after saving the proxy settings again.

### The control panel does not open

- Open `http://localhost:8090` manually in your browser.
- Make sure the app is still running.
- If another app is already using port `8090`, close that app and restart `BO2EmblemToolkit.exe`.

### The capture list stays empty

- Confirm the tool is in `Capture` mode.
- Make sure you opened another player's BO2 profile or channel on the console.
- Double-check that the PS5 proxy settings still point to this PC.

### The selected emblem does not appear in your editor

- Confirm the tool is in `Show` mode.
- Make sure you selected an emblem first.
- Restart the BO2 session or switch modes in-game to force the editor to fetch again.
- If the emblem uses locked shapes on your account, the game may reject it.

## Safety note

Based on the way this tool is designed, it is focused on a narrow job: intercepting BO2 emblem-storage traffic and letting all unrelated HTTPS traffic pass through untouched. The warning shown in your screenshot is not a sign of malware or spyware, and the app is not trying to decrypt PSN traffic.

As with any unsigned Windows utility, SmartScreen may warn that the publisher is unrecognized. That warning is about code signing reputation, not proof that the app is malicious.

## Tips

- Keep the app folder somewhere easy to find.
- Back up the `saved/` folder if you want to keep your captured emblems.
- Switch the PS5 proxy setting back to `Do Not Use` when you are done.
