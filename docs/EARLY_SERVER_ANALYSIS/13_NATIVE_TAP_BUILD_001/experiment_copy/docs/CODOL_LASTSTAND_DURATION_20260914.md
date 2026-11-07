# Selected last-stand duration

The retained IW4 script hardcoded 10 seconds for pistol last stand and 20
seconds for Final Stand. CoDOL's selected perk aggregation already stores
numeric server values for modPistolDeath (8) and modFinalStandTime (59), but
neither timer consumed them.

The alpha0022 extracted perk catalogue records pistoldeath 10, Final Stand
20, and laststandoffhand upgrade's modFinalStandTime 10. Both modifiers have
default 0 and minimum 0. The native getter resolves the currently mounted
ability table and reads the selected per-player contribution. No Python
runtime state is used.

The adaptation replaces only those two existing timer arguments with the
selected value. Missing selection retains the old forced-mode default; zero
remains zero. Die-hard mode and revive-versus-bleed-out policy are unchanged.
This follows IW4 timer lifecycle with CoDOL table parameters, not a claim that
the unavailable original CoDOL server script has been recovered. The separate
upgrade's revive policy still needs investigation.

Source staged in obj/laststand-perk-stage/_damage.gsc. No automated tests or
live last-stand outcome verified.
