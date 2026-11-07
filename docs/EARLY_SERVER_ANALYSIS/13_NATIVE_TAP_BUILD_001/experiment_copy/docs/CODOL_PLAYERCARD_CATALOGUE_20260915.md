# Playercard catalogue/network audit

Source changes and staged GSC; no build, tests, client writes, or live script changes.

The selected public profile currently holds cardIcon 5064 (pci_alpha1), cardBackground 5066 (pcb_alpha3), cardTitle 5061 (pct_default), and cardNameplate 0. Thus the title itself is currently default; the selected icon/background are not.

`_playercards.gsc` rejects values >=1024. It therefore leaves the icon at zero. It never calls a background setter. This is a confirmed producer gap, but the required mapping must be established before removing the guard.

C1 51dd90/51de80/51df70/51e060 accept unsigned values below1024 and store title/icon/nameplate/background directly at gclient3518/351c/3514/3520. Client state offsets AC/B0/B4/B8 have10-bit field widths in both the executable and current client memory. Native server currently implements only the first three setters.

Snapshot consumer46c9f1..46ca14 copies these fields directly to clientinfoB20/B24/B28/B2C. Card-cache filler68e7d0 copies title to record4, icon8, nameplateC, background10. UI getplayercardinfo5e3810 returns those cache values directly. No conversion was found in these consumers.

The marketplace IDs are legitimate C1 profile values, not just a Python invention: C1 default setup5b6310 resolves pci_default, pcb_default, pct_default via7286e0. That function reads mp/coMarketplaceItems.csv, column1 name -> column0 ID, then writes the ID directly via5904e0. Verified shipped table rows contain5059/5060/5061. The current profile values use the same catalogue. Local account card cache68e6c0 reads raw profile integers via591cd0.

The contradiction also exists in C1 lobby serialization:4a4d0e..4a4d5d reads raw profile icon/title/nameplate and passes each to59ee00 with bitcount10. A separate lobby playercard text message4a4f40/4b2d40 carries three full integers into party records; it is not yet established as the in-game clientinfo/card-cache producer.

Do not subtract5000, mask10 bits, widen only the server wire field, or change profile IDs without evidence. Any of those can silently select another cosmetic or corrupt snapshot decoding. The remaining lead is the authored in-game UI expression graph / catalogue lookup: it may reconstruct a compact card representation, or use another cache source. Need trace before claiming a working fix.

Offline `obj/playercard-hud720.bin` is the original common_mp menufile asset ui_mp/hud_720.txt (366824 bytes). Its embedded playercard menus start with names at67a9,8a32,a3c0,c274,e2c5. Its only literal integer5000 occurs at25db2, outside those menu headers; this alone is not evidence for a cosmetic base conversion. Shared expression/string references require stream-aware resolution.

## Resolved: authored C1 HUD consumes callsign row indices

The exact expression opcode-name array starts C1 CD08A8. Opcode80 is
`tablelookupbyrow` (CD09E8), opcode172 is `getplayercardinfo` (CD0B58).
In the original common_mp ui_mp/hud_720.txt menufile, the spectator card has
inline (not unresolved shared) table strings and these expressions:

- Expression around6D81: tableLookupByRow("mp/callsignBackground.csv", getplayercardinfo(2,0,6),4).
- Expression around7488: tableLookupByRow("mp/callsignIcon.csv", getplayercardinfo(3,0,6),4).
- Expression around7B10: tableLookupByRow("mp/callsignTitle.csv", getplayercardinfo(1,0,6),1).

Each entry is12 bytes (entrykind, operandkind/opcode, payload). The strings
follow their14-entry expression arrays at6DF9/7500/7B88. The killed-by and
top-player cards use the same row lookup expressions with shared references
to those strings. No arithmetic transformation of the row occurs.

C1's 5E3A50 jump table sends field1 to5E394F (cache4), field2 to5E3962
(cache8), field3 to5E3975 (cacheC). Therefore the earlier IW4-derived semantic
labels were wrong: clientStateAC is ICON, B0 TITLE, B4 BACKGROUND. B8 is the
remaining fourth card field. The initial observations above should not be
read as endorsing the old icon/nameplate labels.

Shipped callsign row lookup gives selected icon5064 -> pci_alpha1 -> row24;
background5066 -> pcb_alpha3 -> row33; title5061 -> pct_default -> row0.
The native ten-bit fields are sufficient. Profile marketplace IDs remain
unchanged. Lobby serialization's raw truncation is separate from the in-game
server script producer and is not used as the proposed mapping.

## Source written for parent review

Card-only block codol_script_player_builtins.c/.h now labels iconAC,
titleB0, backgroundB4, fourth/nameplateB8; retains all four bounded session
values, resets them together, and publishes all four. Added SetCardBackground
method implementation. Raw setter semantics remain integer table rows.

Staged obj/playercard-catalogue-stage/maps/mp/gametypes/_playercards.gsc
resolves each selected marketplaceID through coMarketplaceItems column0->1,
validates family pci/pct/pcb from column2, and resolves internal name to the
matching callsign table row. Missing/invalid selections are diagnosed without
rewriting profile values or inventing another cosmetic. Nameplate retains its
existing bounded raw handling in the actual fourth field.

Parent integration: register setcardbackground with CODOL_Scr_SetCardBackground;
review and deploy staged script together with rebuilt native source. No live
rendering proof yet. The selected title is currently the default by profile,
so only icon/background are expected to visibly change for this profile.
