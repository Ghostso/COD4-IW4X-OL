/* C1 hold-breath (scope steady) state, PM_UpdateHoldBreath 0x004188b0.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_PMOVE_C1_BREATH_H
#define CODOL_PMOVE_C1_BREATH_H

#include "codol_pmove_c1.h"

#ifdef __cplusplus
extern "C" {
#endif

/* C1 playerState weapon-flags bit 4 (ps+0x344), PWF_HOLDING_BREATH: set at
 * 0x418945, cleared at 0x41894e/0x41899b/0x4188f9 and by the fire path
 * 0x41889b. Same bit number as the retained IW3 producer (_bg_weapons.asm
 * PM_Weapon_70 `or edx,0x4`). */
#define CODOL_WEAP_HOLDING_BREATH 0x4u

/* The three words C1's PM_UpdateHoldBreath owns, captured before the retained
 * PM_Weapon runs its own IW3 hold-breath integration over them. */
typedef struct {
    float scale;
    int timer;
    int holding;
    int event_sequence;
} codol_hold_breath_save_t;

void CODOL_HoldBreathSaveC1(const struct playerState_s *ps,codol_hold_breath_save_t *out);
/* Restores the saved words, runs C1's update for this command and applies the
 * fire clear (0x418810) when PM_Weapon added a fire event this command. */
void CODOL_PM_UpdateHoldBreathC1(codol_pmove_c1_t *move,const codol_hold_breath_save_t *saved);
/* C1 BG_CanHoldBreath 0x421f00 for the scripted/HUD consumers. */
int CODOL_CanHoldBreathC1(const struct playerState_s *ps);
/* Drops the per-weapon scope-overlay cache, which is keyed by a raw WeaponDef
 * pointer. Call whenever those definitions can be freed -- today that is the
 * asset-category teardown, which releases the retired archives and the
 * composed weapon cores built from them. */
void CODOL_ResetBreathScopeCache(void);
/* Composed C1 definition bytes, replayed through attachment overrides like
 * the breath gate: def+0x694 overlayReticle != 0, and def+0xbd9 (weapon
 * refuses prone and dive, C1 0x412220/0x408ed3). */
int CODOL_WeaponScopeOverlayC1(unsigned weapon);
int CODOL_WeaponBlocksProneC1(unsigned weapon);

#ifdef __cplusplus
}
#endif
#endif
