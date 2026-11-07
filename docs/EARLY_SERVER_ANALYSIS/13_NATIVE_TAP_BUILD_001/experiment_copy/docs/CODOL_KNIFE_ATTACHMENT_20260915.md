# Throwing knife attachment

Parent-reviewed native code and retained missile callsites built successfully
without warnings; deployed SHA256
7D53C950B0D103DD1684964FEB937C500473913188085D213560C6E62CD942FE.
No automated tests; actual wall/body pickup behavior remains unverified.

The same missile settles at the trace-fraction impact position, retains its
weapon/model and pickup identity, and uses native G_EntLinkTo for a hit-bone
attachment. Bone names follow T5 hit locations and are checked against the
target DObj. Missing bones use the target-origin relative impact pose.
Damage receives the unchanged native G_Damage arguments before attachment.
Generation references protect against callbacks deleting/reusing either entity.

Corpse capture records the death generation and a serial. Synchronous lethal
damage can link directly to that corpse; later corpse creation transfers the
existing knife. Spawn detaches/transfers before the player origin is reset.
Entity free and map reset clear attachment state. Recovery keeps the previous
generation-safe trigger/death cleanup and one-round ammo transfer.

Direct wall hits use an explicit sh1x incidence policy, dot >0.7 (roughly45
degrees from the incoming surface normal); glancing hits retain bounce.
This meets the requested wall sticking behavior but is not claimed as
recovered proprietary server tuning. Body behavior is based on T5 native
link/corpse handling. C1 generic parent/tag evaluation has no missile exclusion;
the native snapshot link overlay applies after missile fields.

This deployment also includes reviewed IW4x map source updates: tropical
Favela fog/vision and the second palm's matching C1 animation tracks, plus
Killhouse's authored ambient_scoutsniper_ext0 alias present in C1 common_mp.
Shadow work remains closed following user confirmation.
