# CoDOL Discord Rich Presence

`tools/codol_discord_presence.py` runs beside C1 and the local dedicated server.
It does not modify either process. It reads C1's current `console_mp.log`, waits
for `CA_ACTIVE`, and confirms the same map and mode through `sh1x_status` on
the local match server. Discord then shows the actual mode, map, human and bot
counts. Leaving the match returns the activity to "In the lobby"; exiting C1
clears it. A stale server map or a playlist selection is never treated as a
match the player joined.

## Discord application setup

Use the existing **Call of Duty Online** application in the [Discord Developer
Portal](https://discord.com/developers/applications). Upload
`tools/discord-assets/codol.png` as a Rich Presence art asset with key
`codol`. The watcher uses this same official CoDOL icon in the lobby and on
every map; map and mode names remain in the activity text.

The other PNGs are optional shipped map artwork and are not used by the
watcher. The six maps are center crops of
their exact 1280×720 loading screens in `E:\codol-classic\main\iw_image_02.iwd`:
`loadscreen_mp_killhouse.iwi`, `loadscreen_mp_rust.iwi`,
`loadscreen_mp_nuked.iwi`, `loadscreen_zm_prototype_sh.iwi`,
`loadscreen_zm_asylum_sh.iwi`, and `loadscreen_zm_zombie_training.iwi`.
`codol.png` is a square crop of the official logo and character art in the
installed `E:\codol-classic\splash.bmp`. No generated artwork is used. The
reproducible extractor verifies the encrypted archive's original ZIP CRCs:

```powershell
python tools/extract_codol_discord_art.py --build-maps --output tools/discord-assets
```

The configured application ID is `1554730441825718272`, the user's CoDOL
application. `CODOL_DISCORD_APP_ID` can override it. The Matrix Online
application ID and assets are separate. No bot token or Discord account
credentials are needed. The desktop Discord client must be running and signed
in on the same Windows session as the game.

`bin/START-CODOL-SERVER.cmd` starts the watcher in the background after it
prepares the local RCON credential. It leaves an existing watcher running.
To start it without restarting the server, use PowerShell:

```powershell
& 'C:\Users\zz\Documents\ChatGPT\Call of Duty Online 1.1.1.13 Work\codol_1.1.1.13_alpha_server\tools\start_codol_discord_presence.ps1'
```

The watcher stays running across C1 and match restarts. It will reconnect if
Discord is closed and reopened. It reads the RCON password from the local
stack's existing credential file; it never prints or stores that password in
the presence payload. Output is written to
`%TEMP%\codol-11113-e2e-20260928\local-stack-logs\discord-presence.*.log`.

For a read-only state check without Discord or an application ID:

```powershell
python tools/codol_discord_presence.py --once
```

This integration deliberately publishes no presence when the client joins a
different game server: the local server cannot verify that remote session.
