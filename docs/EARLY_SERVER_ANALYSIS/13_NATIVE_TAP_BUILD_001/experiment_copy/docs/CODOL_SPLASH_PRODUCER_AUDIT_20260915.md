# Splash producer and authored UI audit

No gameplay source change justified by this capture. No builds, tests, process
writes, restarts, UI input, or suppression rules added.

## Reliable payload is correct

Native ShowHudSplash sends C1 `w slot row optionalNumber`, as C1 sender51E530
and client dispatcher469E0E do. The third integer is not duration despite the
old source variable/comment name. Consumer4691F8 obtains duration from table
column4;46922D copies optionalNumber to slot+C. Records are cg+174384,
stride16. Consumer4692B1 gets menu name from column11 and opens it at4692C4.

The native sender searches splashTable column0 backward. All selected MP
coKillstreakStatsTable names have matching splash rows. Reward notification
calls this path from tryGiveKillstreak/rewardNotify. Existing IW4 notification
priority may replace queued lower-priority messages; no arbitrary rewrite of
those policies was made without evidence that they cause the reported issue.

## Actual winning C1 table verified

Read-only C1 PID100756 path checked against the supplied1.1.1.13 client.
Code signatures for DB hash4CB350 and lookup4CB540 verified before using their
native hash/entry-chain representation. The winning loaded splash table at
1F0B9C4 has919 rows and12 columns. Direct live cells match server-emitted rows:
0 promotion,17 firstblood,67 uav,71 helicopter_minigun,77 predator_missile,
105 rcbomb_mp,107 sr71_mp,170 callout_firstblood,437 ch_hardline_pro,
558 ch_fearless. Captured names/durations/menu fields are in
obj/c1-splash-table-live.json, reproducible probe obj/read-c1-splash-table.py.

Full offline comparison of original code_post_gfx914-row and patched919-row
tables shows insertions beginning at row206; they are not merely five appended
rows. Earlier sample-only parity must not be generalized. The actual client
winning table is the patched919-row layout and its sampled challenge rows
match the current server's emitted indices. MP killstreak and firstblood rows
are before the first insertion and agree in both versions. Comparison summary
is obj/splash-table-original-comparison.json.

## Original authored killstreak menu

common_mp menufile ui_mp/ingame.txt contains killstreak at blob4944A.
Its tempName derives splashTable row splashRowNum(0), column0. The icon
expression49DEB..49E63 is tableLookup(mp/coKillstreakStatsTable.csv,1,
localvarstring(tempName),15); the string is inline at49E6F. This is a real C1
catalogue consumer, not an overlooked IW4 killstreakTable reference.

## Observed notifications and limitations

Previous session log showed human slot0 rewards uav67, predator77, sr71107,
helicopter71 and challenge437/558, but no promotion row0. Global firstblood
callout170 went to every player while earned firstblood17 went to Training3.
Reference _events::firstBlood explicitly sends the personal medal and a
separate team/global playercard callout; seeing that callout alone does not
mean the viewer earned firstblood.

Current session emits human firstblood17, callout170, headshot2, rcbomb105,
mortar103, doublekill14, ch_fearless558, dogs109. Again no captured promotion0.
Do not describe an uncorrelated popup as a legitimate promotion.

At active commandTime176046 passive C1 capture had UIinitialized1,
hudDrawHud1, local952=1, UIflag16FC2E4=0, showSplashMenu1, inKillcam0.
Slot0 held row14/duration1500/optional50; slot1 row170/duration4000/optional0.
Both start fields were0 (already expired). Slots2..4 were allzero. This proves
those rows reached the client, not their prior visible rendering or the
visibility of an earlier earned reward. No globally disabled splash gate was
present at this sample. Earlier inactive captures were excluded from claims.

Next useful evidence is a simultaneous active slot/menu capture during an
actual reported incorrect popup or just-earned killstreak. No row remapping,
duplicate suppression, or fake rank-up filtering is warranted by current data.
