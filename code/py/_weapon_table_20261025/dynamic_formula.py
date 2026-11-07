# -*- coding: utf-8 -*-
"""Fix the dynamic weapon index formula from the measured retail anchors.

Measured (project reports, all from real runs):
  * CS_WEAPONS block base = 5960  (WeaponConfigStringBase)
  * retail's '** 646 0 0 8738 9321' sits at cs 7184
  * retail's '** 992 0 0 6206 9321' sits at cs 7204
  * stock weapon indices: m9_mp=646, vector_mp=1112, m4a1tech_mp=585
  * firstDynamicWeapon observed = 1224 (live gamestate) and 1147 (mp_battlecity)

So:  dynamic weapon index = cs_index - 5960
     7184 - 5960 = 1224   <-- matches firstDynamicWeapon exactly
"""
import io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE_CS = 5960
FIRST_DYN = 1224

pairs = [(7184, '** 646 0 0 8738 9321', 'm9_mp'),
         (7204, '** 992 0 0 6206 9321', '?')]

print('CS_WEAPONS base           =', BASE_CS)
print('first dynamic cs observed =', 7184, '-> weapon index', 7184 - BASE_CS)
print('reported firstDynamicWeapon =', FIRST_DYN)
print('MATCH:', 7184 - BASE_CS == FIRST_DYN)
print()
for cs, cfg, label in pairs:
    print('cs %-5d -> weapon index %-5d  %-28s (%s)' % (cs, cs - BASE_CS, cfg, label))
print()
print('=> dynamic weapon index = cs_index - 5960')
print('   (cs 5960 = weapon index 0 = none; cs 7184 = 1224 = first dynamic)')
