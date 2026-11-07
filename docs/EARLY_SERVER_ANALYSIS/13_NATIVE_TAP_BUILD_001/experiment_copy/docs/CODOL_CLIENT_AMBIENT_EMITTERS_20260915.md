# C1 authored ambient emitters

Read-only source/binary audit; no runtime changes, tests, or builds.

Killhouse's maps/mp/mp_killhouse_sh_fx.gsc loads FX names and invokes
maps/createfx/mp_killhouse_sh_fx::main only in the developer block guarded by
shouldRunServerSideEffects. This is not evidence that ordinary gameplay lacks
authored emitters: C1 has its own native rawfile parser.

- 44e0b0..44e0c3 registers numeric dvar `574`, default true, flags4, with its
  pointer stored at16b01b8. Loader42df70 tests current byte+0xc at42dfc7;
  client frame update42e1b0 tests the same enable value.
- Loader42df70 runs from450f5e and467cdf. It reads mapname and formats
  `maps/mp/%s_fx.gsc` (C41CA4) and `maps/createfx/%s_fx.gsc` (C41CB8).
  The FX mapping reader is42de50; placement reader42d9a0 resolves mounted
  rawfiles, copies their contents, and invokes parser42d730.
- The parser consumes authored text directly, including `createLoopSound()`
  (C41890, dispatch42d897 to42cc10), `createIntervalSound()` (C41968,
  dispatch42d8d1 to42cec0), and oneshot/loop FX forms.
- Frame call441c45 invokes42e0c0. It traverses sound entries with stride0x24
  and plays eligible loops through44f840 using authored position and alias.
  FX/interval update is separately gated by the same dvar.

Native server sv_main.c registers the descriptive `clientSideEffects` dvar.
That registration must not be confused with C1's proven numeric574 gate.
No server-side placed emitters were added: unconditionally executing the
developer createfx branch would risk duplicating the C1 native emitters.

If ambient audio remains missing, the next evidence needed is live dvar574,
placement counts/parser diagnostics, and sound alias resolution for the loaded
map. This audit proves the automatic client path, not that every alias played
successfully in the user's current session.

## Passive runtime capture

PID102092 was verified as the supplied C1.exe; disk SHA256
d990610732258b1d00dd6fe63d6691f294312a2e0562955a01ce16216115390d.
Runtime bytes at42df70,42e0c0,42c610 matched that file before inspecting state.
ReadProcessMemory-only capture is obj/c1-ambient-readonly-20260915.json.

At capture, dvar574 current value was1, remap count4, and the native sound
emitter bank contained10 entries. All had delay_min/max=-1, making them
eligible for the loop playback branch, and all had resolved alias pointers:
metal_sheet_knocking twice, vendingmachine_hum once, wood_creak_heavy once,
wood_creak_light three times, mtl_drum_pings twice, mtl_corrugate_rattle once
(each prefixed emt_). The JSON retains each authored position and alias address.

This establishes instantiated loop emitters beyond merely loaded sound assets.
It does not establish audible mixer output or continuous playback while in a
menu: no audio recording or execution breakpoint was used. A supplementary
client-context read was not a reliable active-gameplay check (context index2,
then an unavailable snapshot on follow-up), so it is not used as proof of
current game time or live gameplay. The automatic loop consumer is established
by source disassembly; the populated bank and enabled gate are runtime facts.
