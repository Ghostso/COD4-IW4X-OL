# Harrier model shutdown — 2026-09-15

User attachment 2e076b17-9bba-42a7-883d-931161f953bd ends the match at inherited _airstrike.gsc:838: playfxontag requests tag_engine_right on vehicle_av8b_harrier_jet_opfor_mp. DObj dump identifies the actual model as void with two unrelated trim bones. Native PID94028 remained alive after shutdown; this is a fatal script error, not evidence of a native access violation. Snapshot overflow messages follow shutdown and are secondary in this capture.

The mounted common_gametype_mp.ff contains vehicle_av8b_harrier_jet_mp (type4 index10173, 30 bones), including all engine/wingtip, turret, barrel, flash and light tags used by the scripts. No OpFor Harrier occurs in the four common MP zone model inventories. Evidence and zone hashes: obj/harrier-model-audit/shipped-harrier-models.json.

Native overlays now select the shipped Harrier for both teams in _airstrike.gsc (flyby) and _harrier.gsc (hover vehicle). Removed obsolete OpFor precache. Ownership, team icons and effects remain intact. This is an explicit CoDOL asset adaptation; no recovered original CoDOL script is claimed. No global missing-tag suppression, fabricated bones or extra zone.

Script-only change; existing native binary retained. Restarted only native server after source review, requesting four bots and score7500. Client/lobby preserved. Script compilation/startup and actual Harrier behavior are recorded in the implementation ledger.