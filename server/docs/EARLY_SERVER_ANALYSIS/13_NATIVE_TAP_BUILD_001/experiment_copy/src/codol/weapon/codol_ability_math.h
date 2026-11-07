/* C1 ability arithmetic for weapon and movement timing.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Pure functions, no engine state, so the server and the unit tests share
 * them. Each one reproduces a C1 x87 sequence; the addresses are C1.exe
 * 1.1.1.13. */
#ifndef CODOL_ABILITY_MATH_H
#define CODOL_ABILITY_MATH_H
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif

/* `fild msec; fdiv dword value; call 0xae0410` (0xae0410 is _ftol2_sse:
 * fstp qword, cvttsd2si). The quotient is truncated toward zero. Used by
 * modOffhandSpeedScale (28) at 0x41c35e, 0x41c4f2, 0x41c6b7, 0x41c6e0,
 * 0x41c919 and modWeaponRecoveryTimeScale (11) at 0x41d19c.
 * 1 and *out written; 0 when the value is not a positive finite divisor or
 * the quotient does not fit an int (C1 would store 0x80000000). */
int CODOL_AbilityDivideMsec(int msec, float value, int *out);

/* C1 PM_Weapon_BeginFire 0x41b4db..0x41b52f for an adsFireOnly weapon:
 *   scale = (float)(1.0 / def+0xa28)            0x41b4e4..0x41b4f7
 *   if ability 10: scale = (float)(scale / v10)  0x41b4fa..0x41b51a
 *   weaponDelay = ftol((1.0 - posFrac) * scale)  0x41b51d..0x41b52a
 * has_ability 0 reproduces the retained IW3 delay, computed with C1's
 * precision. 1 and *out written; 0 for a non-finite or oversize result. */
int CODOL_AdsFireOnlyDelay(float oo_pos_anim_length, float pos_frac,
                           int has_ability, float ads_value, int *out);

/* C1 mantle anim length 0x409843..0x40985c:
 * ftol((float)(numframes / framerate) * 1000.0). */
int CODOL_MantleAnimMsec(unsigned numframes, float framerate);

#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
