# Heartbreaker aircraft targeting

Selected coPerkStatsTable row12 specialty_heartbreaker owns
modNoHeartbeat7, modNoSentryGuns20, modNoHelicopter44, modNoAirplane45.
Row9 specialty_coldblooded contributes only modNoRadar18.

Inherited IW4 _helicopter.gsc lines476/1029 and _harrier.gsc765 still use
specialty_coldblooded to skip target acquisition. No effective native script
override was found for either file. This protects the wrong selected perk.
Proposed narrow adaptation: change helicopter gates to HasAbilityModifier
modNoHelicopter and harrier gate to modNoAirplane, preserving existing IW4
LOS, team, owner, spawn-grace and targeting lifecycle. Native ability query
reads effective extension masks, and aggregation sets masks for server-only
44/45 as well as client effects. No new VM method required.

Native sentry20 was not resolved: C1 target validator57CA30 checks eFlagsEC,
336C and67ABC0 vehicle protection, not a direct ability20 gate. Do not insert
a guessed blanket native restriction into this generic target validator.
Mortar live regression superseded implementation before any script edits.

Parent subsequently reviewed native perk aggregation and HasAbilityModifier:
the effective ability masks include both client and server-only modifiers,
and queries read these masks rather than the script-only contribution.
Deployed native overlays for _helicopter and _harrier replace only the three
targeting gates with modNoHelicopter/modNoAirplane queries. Existing team,
LOS, spawn grace and ownership checks remain intact. No generic sentry change.

Built/deployed A01B8CD450840DB571E41D7C9DD1AEF0108E0EBF960B75D250B25FE7457E91CD
with mortar reward identity fix; log obj/build-mortar-perks-20260915.log.
No automated tests. Aircraft immunity behavior not yet live-verified.
