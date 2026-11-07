# Selected flak/fall damage adaptation

Worker staged `_perks.gsc` under obj/perk-damage-stage. Parent reviewed and
deployed after stopping the native server. Build/link exited zero; deployed
EXE SHA256 7B40804508A59485C47D19B1EC72F752B948A23B69CA266E5011C63FECE3FE4D.
Script SHA256 251D1B951435D2A6EE360484F03657FCE41537E88A98A9D3538A02989B9793B8.
No automated tests. Live damage behavior remains unconfirmed.

Parent checked the actual configured vendor/iw4/maps/mp/gametypes/_damage.gsc:
lines1169..1172 call cac_modified_damage then return false on zero damage,
before damage application. No later minimum-one rule revives this zero path.

This is an explicitly chosen IW4-based integration policy with CoDOL selected
table values, not a recovered original C1 damage script.

* Keep existing primary/explosive/falling categorization. The explosive helper
  includes direct grenade/projectile, both splash categories and explosive;
  explosive bullets retain the existing primary-damage category.
* Query selected modifier60 for explosions and52 for falling. The native API
  returns undefined with no selected numeric contribution; undefined leaves
  existing damage behavior intact. There is no hardcoded perk-name/scale.
* Keep existing damage additions and legacy blastshield/fall protection.
  After those and the existing xpScaler adjustment, multiply both damage and
  damageAdd by the selected defense factor. This composes with separately
  owned legacy effects, without applying selected protection a second time.
* Combat-high accounting and reduction operate on this defended amount.
  Retain the existing single final `int(damage + damageAdd)` conversion.
  No minimum-one clamp is introduced; selected fall scale0 returns0 even if
  an earlier additive adjustment exists.

Current selected-table examples: flak-jacket5 yields scale0.5; lightweight's
selected upgrade22 yields fall scale0. Selected ownership/aggregation and
unlocked upgrade selection remain native/runtime responsibilities.

No radius-damage or pre-script native multiplier was added. Any later native
replacement must remove this selected-defense script step in the same change
to avoid double application. Parent should verify the downstream callback
honors zero returned damage when reviewing the complete live pipeline.

Reviewed staged diff: one local variable, two category-specific reads and one
common scale application before combat-high. No other source changes.
