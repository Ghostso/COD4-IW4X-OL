# C1 reconnect profile identity

Observed qconsole: initial secure profile attached with nonzero connection UID
(line11287); subsequent map entry attempted uid0 (line22768), then script
getPlayerData(totalShots) failed because no secure profile was attached.

Proven producer/consumer mismatch:

- Initial CODOL_ReadConnectUserinfo requires exactly one16-hex xuid agreeing
  with the connect envelope.
- SV_UpdateUserinfo_f replaces the complete userinfo string with the later C1
  update. Such updates are not the initial connect envelope and can omit xuid.
- SV_ClearServer resets attached secure profiles while connected clients remain.
- ClientEnterWorld called AutoBind with mutable userinfo. AutoBind reparsed its
  now-missing xuid as0; AttachClientSecureProfile correctly rejected uid0.

Native fix: capture the nonzero16-hex initial connection UID separately from
mutable userinfo. Set it only after connection validation/slot selection; clear
before replacement attach, on real disconnect, and when a slot becomes a bot.
Map/profile resets intentionally preserve it. Automatic attachment exclusively
uses captured UID, so an omitted or substituted xuid in a later userinfo update
cannot lose/change the profile owner. No synthetic or shared anonymous identity
was introduced. This preserves the existing connect transport's trust boundary;
matching envelope/userinfo alone is structural consistency, not a new claim of
cryptographic authentication.

Files: codol_connect.c/h, narrow SV_DirectConnect/DropClient/AddTestClient sites
in sv_client.c, and AutoBind in codol_asset_commands.c. Parent separately owns
ClientEnterWorld rejection before scripts when a real player's profile cannot
be attached. That containment remains necessary for missing/unreadable profiles.

Source complete and handed to parent for review/build. No automated tests or
process changes performed by worker. Live map-reconnect verification pending.
