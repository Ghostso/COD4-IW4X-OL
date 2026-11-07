/* T5 scripted-animation GSC surface: the builtins that consume a %anim
 * reference variable.
 *
 * Registered from src/scr_vm_main.c:
 *   Scr_AddMethod("clearanim",                        CODOL_Scr_ClearAnim,                   qfalse);
 *   Scr_AddMethod("setanim",                          CODOL_Scr_SetAnim,                     qfalse);
 *   Scr_AddMethod("setanimlimited",                   CODOL_Scr_SetAnimLimited,              qfalse);
 *   Scr_AddMethod("setanimrestart",                   CODOL_Scr_SetAnimRestart,              qfalse);
 *   Scr_AddMethod("setanimknob",                      CODOL_Scr_SetAnimKnob,                 qfalse);
 *   Scr_AddMethod("setanimknoblimited",               CODOL_Scr_SetAnimKnobLimited,          qfalse);
 *   Scr_AddMethod("setanimknobrestart",               CODOL_Scr_SetAnimKnobRestart,          qfalse);
 *   Scr_AddMethod("setanimknoball",                   CODOL_Scr_SetAnimKnobAll,              qfalse);
 *   Scr_AddMethod("setanimknoballrestart",            CODOL_Scr_SetAnimKnobAllRestart,       qfalse);
 *   Scr_AddMethod("setflaggedanim",                   CODOL_Scr_SetFlaggedAnim,              qfalse);
 *   Scr_AddMethod("setflaggedanimlimited",            CODOL_Scr_SetFlaggedAnimLimited,       qfalse);
 *   Scr_AddMethod("setflaggedanimrestart",            CODOL_Scr_SetFlaggedAnimRestart,       qfalse);
 *   Scr_AddMethod("setflaggedanimknob",               CODOL_Scr_SetFlaggedAnimKnob,          qfalse);
 *   Scr_AddMethod("setflaggedanimknobrestart",        CODOL_Scr_SetFlaggedAnimKnobRestart,   qfalse);
 *   Scr_AddMethod("setflaggedanimknoblimited",        CODOL_Scr_SetFlaggedAnimKnobLimited,   qfalse);
 *   Scr_AddMethod("setflaggedanimknoblimitedrestart", CODOL_Scr_SetFlaggedAnimKnobLimitedRestart, qfalse);
 *   Scr_AddMethod("setflaggedanimknoball",            CODOL_Scr_SetFlaggedAnimKnobAll,       qfalse);
 *   Scr_AddMethod("setflaggedanimknoballrestart",     CODOL_Scr_SetFlaggedAnimKnobAllRestart,qfalse);
 *   Scr_AddMethod("setanimtime",                      CODOL_Scr_SetAnimTime,                 qfalse);
 *   Scr_AddMethod("getanimtime",                      CODOL_Scr_GetAnimTime,                 qfalse);
 *
 * See docs/CODOL_SCRIPTED_ANIMATION_20260920.md for the measurements these
 * follow and for what is deliberately not here.
 */
#ifndef CODOL_SCRIPT_ANIM_H
#define CODOL_SCRIPT_ANIM_H
#ifdef CODOL_SERVER
#include "scr_vm.h"
#ifdef __cplusplus
extern "C" {
#endif

void CODOL_Scr_ClearAnim(scr_entref_t ref);
void CODOL_Scr_SetAnim(scr_entref_t ref);
void CODOL_Scr_SetAnimLimited(scr_entref_t ref);
void CODOL_Scr_SetAnimRestart(scr_entref_t ref);
void CODOL_Scr_SetAnimKnob(scr_entref_t ref);
void CODOL_Scr_SetAnimKnobLimited(scr_entref_t ref);
void CODOL_Scr_SetAnimKnobRestart(scr_entref_t ref);
void CODOL_Scr_SetAnimKnobAll(scr_entref_t ref);
void CODOL_Scr_SetAnimKnobAllRestart(scr_entref_t ref);
void CODOL_Scr_SetFlaggedAnim(scr_entref_t ref);
void CODOL_Scr_SetFlaggedAnimLimited(scr_entref_t ref);
void CODOL_Scr_SetFlaggedAnimRestart(scr_entref_t ref);
void CODOL_Scr_SetFlaggedAnimKnob(scr_entref_t ref);
void CODOL_Scr_SetFlaggedAnimKnobRestart(scr_entref_t ref);
void CODOL_Scr_SetFlaggedAnimKnobLimited(scr_entref_t ref);
void CODOL_Scr_SetFlaggedAnimKnobLimitedRestart(scr_entref_t ref);
void CODOL_Scr_SetFlaggedAnimKnobAll(scr_entref_t ref);
void CODOL_Scr_SetFlaggedAnimKnobAllRestart(scr_entref_t ref);
void CODOL_Scr_SetAnimTime(scr_entref_t ref);
void CODOL_Scr_GetAnimTime(scr_entref_t ref);
/* T5 GScr_AnimScripted_SP / StopAnimScripted: the scripted-animation state
 * (codol_actor_lifecycle.cpp owns the actor half). */
void CODOL_Scr_AnimScripted(scr_entref_t ref);
void CODOL_Scr_StopAnimScripted(scr_entref_t ref);

#ifdef __cplusplus
}
#endif
#endif
#endif
