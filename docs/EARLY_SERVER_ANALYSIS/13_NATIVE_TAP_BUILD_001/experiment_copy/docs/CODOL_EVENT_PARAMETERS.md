# Native event parameter semantics

Event-name matching in `codol_event_map.inc` does not prove compatible event
arguments. `CODOL_EventParameterToWire` now resolves the measured forced-stance
reason enum for stand/crouch/prone: 0 forced, 1 blocked standing, 2 blocked
crouching, 3 blocked prone. Values outside that enum fail. `EV_NONE` has no
consumed argument and canonicalizes its value to zero. Other event parameters
remain unimplemented by this resolver, rather than being copied numerically.

Evidence: native `PM_CheckDuck` in `_bg_pmove.asm` emits those reason values;
alpha0022 `docs/movement_stance_fix.md` section 3 records the matching C1
`PM_UpdateStance` branches at 0x412954 through 0x412ed0. In contrast,
`docs/sound_support.md` explicitly marks the sound-alias event argument path
as unproven. Such events require further measurement or their own semantic
producer; this change does not claim weapon, sound, FX or entity-ID conversion.

`CODOL_ResolveEventParameters` resolves all four physical queue slots atomically.
Native entity/player queue helpers copy named event and parameter fields into
integer words before resolution. This is necessary because the retained entity
header declares its event arrays as float vectors despite their integer storage.
The helpers never numerically cast those float values.

The standalone fixture covers reason boundaries, unused-parameter canonicalization,
unknown events, null outputs, aliasing and late queue failure. The entity collector
fixture uses the production helper to carry a native stance event and reason into
the matching CoDOL queue slot; it also checks player queues and unchanged output
on an unsupported sound event. Both pass with 32-bit AddressSanitizer and
UndefinedBehaviorSanitizer.
Full Linux `make -j6 all test-codol` passes
(`/tmp/sh1x-resolved-events-linux.log`); the final expanded collector fixture
also passes separately under sanitizers after adding player-queue assertions.
The Windows server build passes (`/tmp/sh1x-resolved-events-win32.log`).

These helpers are available to frame binding resolvers. The live snapshot writer
is still IW3; complete native type-specific bindings and CoDOL frame assembly
remain required. No client-received stance event or playable match is verified.
