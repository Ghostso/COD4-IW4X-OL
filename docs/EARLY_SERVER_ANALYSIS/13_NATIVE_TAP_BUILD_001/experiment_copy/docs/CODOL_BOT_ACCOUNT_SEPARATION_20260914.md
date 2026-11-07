# Bot account separation

First live training bot failed during connection: _persistence.gsc:19 read
totalShots without a secure profile. Native autoload reported uid0 attach
rejected. The script failure preceded server shutdown and command overflows.

The user's requested CSV loadouts should not attach a fabricated account.
Staged bot-stat changes under obj/bot-stats-stage provide mutable match-local
scalar/child counters and buffered shot/time counters. They start at zero,
accept real increments and never upload to an account. Human persistence
continues through its existing API. Bots do not earn account ranking/rest XP,
load profile playercards or process account challenge state. Ordinary mission
combat bookkeeping remains initialized.

CSV weapon/equipment/perk/appearance work is owned by the bot worker. These
script changes must be deployed together after review; the bot loadout path
still requires the CSV integration to avoid later human-profile reads.
Source staged, not built/deployed or live-verified yet. No tests.

Follow-up: CSV loadouts deployed in F352. The next live connection failed in
_awards.gsc:29 resetting persistent round awards. New overlay keeps match-stat
initialization and monitors, but skips bot account resets, personal best saves,
persistent award grants and end-of-match account award reads. Human paths remain
unchanged. Native SV_ClientEnterWorld also skips secure-profile autobind for
NA_BOT. Built and deployed D7D2B32A9946AC7097C908AFDD8A1750739CD68F8C218DD3ED999C750AE740AF.
One-bot live startup verification underway; no automated tests.
Latest run progressed through class equipment and appearance. Skipped bot-only
account perk unlocks and client killcam FX registration. Bots receive the CSV
base perks, not account-earned upgrades. A subsequent remote packet timeout was
fixed in SV_CheckTimeouts for connected native bots (zombie cleanup retained).
Build E6C49FDEFEEA7E126B5CEE0181B2299779B545CEC815914FB048544DDB38D0C1
completed one-bot spawn without the script shutdown. Combat quality pending.
