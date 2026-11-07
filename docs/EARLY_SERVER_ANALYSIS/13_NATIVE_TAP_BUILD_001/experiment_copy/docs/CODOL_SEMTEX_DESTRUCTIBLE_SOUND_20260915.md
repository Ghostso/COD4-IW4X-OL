# Semtex-triggered destructible sound failure

Read-only asset audit; no client/server/process changes or tests.

The reported script failure is `vehicle_car_exp` in alpha0022's simplified
`common_scripts/_destructible.gsc::destructible_explode`. The generic car alias
in the actual CoDOL common MP sound catalogue is **car_explode**.

Archives were decoded using `zone_assets.Zone(inflate_ff(path, verify=True))`
from `client_shipRetail/chinese` of the user's1.1.1.13 build. This is an asset
table match, not discovery from an arbitrary string inside a zone:

| Archive | Type | Index | Name | Zone-relative offset | Bytes |
|---|---:|---:|---|---|---:|
| common_mp.ff |11(sound)|3475|car_explode|0x283d83f|257662|
| common_mp.ff |11(sound)|3481|car_explode_police|0x28e23d5|355|
| common_mp.ff |30(FX)|1423|explosions/small_vehicle_explosion|0x10c202e|5443|
| common_mp.ff |30(FX)|1424|explosions/large_vehicle_explosion|0x10c3571|27611|

The generic list header is `FFFFFFFF FFFFFFFF 03000000`: inline name/head,
three entries. Its own asset data contains the three sample paths
`explosions/exp_car_close01.wav`, `exp_car_close02.wav`, `exp_car_close03.wav`.
The distinct police list is not a reason to replace all car types with it.

No sound asset named vehicle_car_exp was found in the verified common_mp,
patch_common_mp, common_gametype_mp or mp_bog_sh asset tables. The currently
requested small_vehicle_explosion effect is valid in common_mp. Generic car
sound can therefore use car_explode; explicit map/type overrides need their
own actual alias validation, since `sound_csv_include` may not be an alias.

Artifacts: `obj/semtex-vehicle-sound-assets-20260915.json`,
`obj/semtex-vehicle-fx-assets-20260915.json`,
`obj/semtex-car-explode-asset.bin`. Broader diagnostic JSON includes unrelated
sound candidates; the table above identifies the actual supported replacement.
Parent owns the destructible script correction and deployment. Archive presence
does not independently prove audibility in a current live scene.
