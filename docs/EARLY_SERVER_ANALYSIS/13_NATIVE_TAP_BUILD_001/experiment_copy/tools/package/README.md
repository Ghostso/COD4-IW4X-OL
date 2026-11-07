# sh1x server — Docker deployment (match server)

The native Call of Duty Online match server as one container. The lobby
(Demonware emulator) is deployed separately, on the same host.

| path | what it is |
|---|---|
| `gameserver/` | the image: 32-bit Linux `codol_dedrun` and `sh1x_svr_scripts.iwd` (scripts, rawfiles, bot waypoints and classes) |
| `game/` | shipped game files, mounted read-only: `c1_keys.bin`, `client_shipRetail/chinese/*.ff`, `main/*.iwd` |

`C1.exe` is not needed: `c1_keys.bin` holds the two regions the server reads
from it. **Keep this package private** — `game/` is Activision's content and
its decryption key.

## The lobby link

The lobby must run on the same host:

- it writes each player's session key and admission (`securitykey.bin`,
  `game_admissions.txt`) and profiles (`resources/`) into its state directory,
  which this compose file mounts at `/data` (`LOBBY_STATE_DIR` in `.env`);
- it starts matches over RCON, which the server accepts from loopback only
  (both use host networking). The server writes its RCON password to
  `native_server_rcon.txt` in that directory on first start if none exists;
  the lobby reads it from there. The container preserves an existing password
  and refuses an empty or malformed file instead of starting with a different
  credential;
- it advertises the match server to C1: set `CODOL_MM_HOST_IP` to this host's
  public IP and `CODOL_MM_HOST_PORT` to `GAME_PORT`.

## More than one match

The lobby places players with `handoff/match_instances.py`: it joins a match
that has other players, re-points an empty server, or starts another instance
when all are full. Inside Docker the lobby cannot start containers, so run the
extra match servers yourself (copy the `gameserver` service with another
`GAME_PORT` and its own home volume) and list every port in the lobby's
`CODOL_INSTANCE_PORTS`.

## Host requirements

- Linux x86-64 with Docker Engine and the compose plugin.
- 2+ fast vCPUs, 2–4 GB RAM for the match server, ~6 GB disk.
- Open **UDP 17733** (plus the lobby's 3074 udp/tcp and 3075 tcp).

## Deploying

```sh
curl -fsSL https://get.docker.com | sh
sudo ufw allow 22/tcp && sudo ufw allow 17733/udp && sudo ufw enable
rsync -avh --progress sh1x-server-dist/ user@vps:/opt/sh1x-server/     # from the build machine
cd /opt/sh1x-server && cp .env.example .env && nano .env              # LOBBY_STATE_DIR
docker compose up -d --build
docker compose logs -f gameserver
```

The log is `main/qconsole.log` in the `gameserver-home` volume:

```sh
docker compose exec gameserver tail -f /home/codol/main/qconsole.log
```

## Admission

The lobby admits players (website launch tokens when it has the website's
public key) and lists each admitted player's own session key in
`game_admissions.txt`. The server keys each player's encrypted connection from
that list, checks the connect's account id against it and names the player
with the lobby's gamertag; with `GAME_ADMISSION_REQUIRED=1` (the default)
nobody else gets in. Decisions appear in the log:

```
CoDOL admission: 203.0.113.7:28960 admitted as Nucleur (xuid 9d8f...)
CoDOL admission: 198.51.100.2:28960 (xuid 0000...) has no lobby admission; refused
```

## Updating

Rebuild on the development machine (`tools/build_codol_linux.sh`, then
`tools/codol_package.py --skip-game`), copy `gameserver/` over and
`docker compose up -d --build`. `game/` stays as it is.
