/* SPDX-License-Identifier: AGPL-3.0-or-later
 * Target offsets: alpha0022/spawn_player.py PS_* constants, including its
 * measured corrections at PM_CmdScale 0x4100B0 / PM_AddGravity 0x410AD4.
 */
#include "codol_weapon_bits.h"
#include "codol_engine_state.h"
#include "qcommon_io.h"
#include "codol_playerstate_ext.h"
#include "codol_obituary.h"
#include "codol_weapon_state.h"
#include "codol_sv_state.h"
#include "codol_recoil_state.h"
#include "codol_entitystate_ext.h"
#include "codol_loop_sound.h"
#include "codol_script_model_scale.h"
#include "codol_script_events.h"
#include "codol_sprint_state.h"
#include "codol_radar_state.h"
#include "codol_player_links_wire.h"
#include "codol_usercmd.h"
#include "codol_events.h"
#include "bg.h"
#include "codol_script_player_builtins.h"
#include "codol_weapon_flags.h"
#include "xassets/weapondef.h"
#include <math.h>
#include "codol_script_profile_vm.h"
#include "codol_frame_builder.h"
#include "codol_pmove_c1.h"
#include "codol_sway_phase.h"
#include "codol_variable_zoom.h"
#include "codol_killcam_trace.h"
#include <string.h>
#include <stdio.h>
#include <stddef.h>
int CODOL_OverlayEngineHudPresentation(codol_hud_element_t *wire,const hudelem_t *engine)
{
    static const struct { unsigned target; size_t source; int floating; } fields[]={
#define HUD_FIELD(target,name,floating) {target,offsetof(hudelem_t,name),floating}
        HUD_FIELD(0x04,x,1),HUD_FIELD(0x08,y,1),HUD_FIELD(0x0c,z,1),
        HUD_FIELD(0x14,fontScale,1),HUD_FIELD(0x18,fontScale,1),
        HUD_FIELD(0x28,alignOrg,0),HUD_FIELD(0x2c,alignScreen,0),
        HUD_FIELD(0x30,color,0),HUD_FIELD(0x34,fromColor,0),
        HUD_FIELD(0x38,fadeStartTime,0),HUD_FIELD(0x3c,fadeTime,0),
        HUD_FIELD(0x44,width,0),HUD_FIELD(0x48,height,0),
        HUD_FIELD(0x50,fromWidth,0),HUD_FIELD(0x54,fromHeight,0),
        HUD_FIELD(0x58,scaleStartTime,0),HUD_FIELD(0x5c,scaleTime,0),
        HUD_FIELD(0x60,fromX,1),HUD_FIELD(0x64,fromY,1),
        HUD_FIELD(0x68,fromAlignOrg,0),HUD_FIELD(0x6c,fromAlignScreen,0),
        HUD_FIELD(0x70,moveStartTime,0),HUD_FIELD(0x74,moveTime,0),
        HUD_FIELD(0x78,time,0),HUD_FIELD(0x7c,duration,0),
        HUD_FIELD(0x80,value,1),HUD_FIELD(0x88,sort,1),HUD_FIELD(0x8c,glowColor,0),
        HUD_FIELD(0x90,fxBirthTime,0),HUD_FIELD(0x94,fxLetterTime,0),
        HUD_FIELD(0x98,fxDecayStartTime,0),HUD_FIELD(0x9c,fxDecayDuration,0)
#undef HUD_FIELD
    };
    codol_hud_element_t result; unsigned i,j;
    if(!wire || !engine) return 0;
    result=*wire;
    for(i=0;i<sizeof(fields)/sizeof(fields[0]);++i) {
        uint32_t value; memcpy(&value,(const uint8_t *)engine+fields[i].source,4);
        if(fields[i].floating) { float number; memcpy(&number,&value,4); if(!isfinite(number)) return 0; }
        for(j=0;j<CODOL_HUD_FIELDS;++j) if(CODOL_HudFieldOffset(j)==fields[i].target) break;
        if(j==CODOL_HUD_FIELDS) return 0;
        result.field[j]=value;
    }
    for(j=0;j<CODOL_HUD_FIELDS;++j) if(CODOL_HudFieldOffset(j)==0x1c || CODOL_HudFieldOffset(j)==0x20) result.field[j]=0;
    *wire=result; return 1;
}

int CODOL_TranslateEngineHudFlags(unsigned engine_flags,unsigned *out)
{
    /* Retained HudElem_SetFlagForeground/HideWhenDead/HideWhenInMenu use
     * 1/2/4. C1 setters 0x5242f0/0x5243d0/0x524440 confirm those meanings.
     * C1 44b1e6 tests waypoint draw bit 8; 44aec5..44aef0 extracts
     * distance/rotating-edge/offscreen-only bits 0x10/0x20/0x40.
     * Unmapped text-style and server-only bits remain rejected. */
    if(!out || (engine_flags & ~0x7fu)) return 0;
    *out=engine_flags; return 1;
}
int CODOL_BuildEngineHudElement(codol_hud_element_t *wire,const hudelem_t *engine,const codol_hud_bindings_t *bindings)
{
    /* C1 type dispatch, documented in alpha0022/docs/hudelem.md section 4:
     * removes mapname/gametype and inserts static timer variants. Fonts 0..3
     * match IW3's default/bigfixed/smallfixed/objective names. */
    static const int types[]={0,1,2,3,-1,-1,4,5,6,8,9,11,12,13,7,10};
    codol_hud_element_t result={0}; unsigned i,target;
    if(!wire || !engine || !bindings || engine->type<=HE_TYPE_FREE || engine->type>=HE_TYPE_COUNT ||
       types[engine->type]<0 || engine->font<0 || engine->font>7 || engine->offscreenMaterialIdx ||
       engine->targetEntNum<0 || engine->targetEntNum>ENTITYNUM_NONE ||
       bindings->label>1023 || bindings->text>1023 || bindings->material>255 ||
       bindings->sound>31 || bindings->flags>1023 || bindings->font_scale_duration<0 ||
       bindings->font_scale_duration>60000 || !isfinite(bindings->font_scale_from)) return 0;
    if(!CODOL_OverlayEngineHudPresentation(&result,engine)) return 0;
    /* Native and C1 share the 2048-entity namespace: 2046 world, 2047 none. */
    target=(unsigned)engine->targetEntNum;
    for(i=0;i<CODOL_HUD_FIELDS;++i) switch(CODOL_HudFieldOffset(i)) {
    case 0x00: result.field[i]=(unsigned)types[engine->type]; break;
    case 0x10: result.field[i]=target; break;
    case 0x18: if(bindings->font_scale_duration) memcpy(&result.field[i],&bindings->font_scale_from,4); break;
    case 0x1c: result.field[i]=(uint32_t)bindings->font_scale_start; break;
    case 0x20: result.field[i]=(uint32_t)bindings->font_scale_duration; break;
    case 0x24: result.field[i]=(unsigned)engine->font; break;
    case 0x40: result.field[i]=bindings->label; break;
    case 0x4c: result.field[i]=bindings->material; break;
    case 0x84: result.field[i]=bindings->text; break;
    case 0xa0: result.field[i]=bindings->sound; break;
    case 0xa4: result.field[i]=bindings->flags; break;
    }
    *wire=result; return 1;
}
int CODOL_CollectEngineHud(codol_hud_state_t *wire,const hudElemState_t *engine,codol_hud_resolver_t resolve,void *context)
{
    codol_hud_state_t result={0}; unsigned array,i;
    if(!wire || !engine) return 0;
    for(array=0;array<2;++array) {
        const hudelem_t *elements=array ? engine->current : engine->archival;
        for(i=0;i<MAX_HUDELEMENTS;++i) {
            codol_hud_bindings_t bindings={0};
            if(elements[i].type==HE_TYPE_FREE) break;
            if(i>=CODOL_HUD_SLOTS || !resolve) { codol_player_failure="HUD element count/resolver"; return 0; }
            if(!resolve(context,elements+i,&bindings)) {
                static char why[160];
                snprintf(why,sizeof(why),"HUD %s element %u resolve (type %d font %d flags %d material %d label %d text %d sound %d)",
                    array ? "current" : "archival",i,elements[i].type,elements[i].font,elements[i].flags,
                    elements[i].materialIndex,elements[i].label,elements[i].text,elements[i].soundID);
                codol_player_failure=why; return 0;
            }
            if(!CODOL_BuildEngineHudElement(&result.elements[array][i],elements+i,&bindings)) {
                static char why[160];
                snprintf(why,sizeof(why),"HUD %s element %u build (type %d font %d target %d offscreen %d label %u text %u material %u flags %u)",
                    array ? "current" : "archival",i,elements[i].type,elements[i].font,elements[i].targetEntNum,
                    elements[i].offscreenMaterialIdx,bindings.label,bindings.text,bindings.material,bindings.flags);
                codol_player_failure=why; return 0;
            }
            ++result.count[array];
        }
    }
    *wire=result; return 1;
}
/* Bisect switch for the player-state families published after the wire audit
 * of 2026-09-10: the damage feedback block and the viewmodel/view-lock/prone
 * block. Both are mapped from measured C1 netfield names rather than from a
 * live capture, so a single dvar can take them back out without a rebuild if
 * the client disagrees. Defaults on; set codol_publishExtendedPlayerState 0
 * to withhold them. Plain storage, not a cvar_t, because this translation
 * unit is also linked into unit tests that do not carry the cvar system. */
int codol_publish_extended_ps = 1;
/* Reduce a signed engine value to an unsigned field of the given width.
 * The delta codec rejects a value wider than its field and fails the whole
 * frame with it (codol_delta.c), so a field whose value is a counter, an
 * accumulator or a byte-quantised angle is narrowed here instead of being
 * validated: wrapping such a value is harmless, dropping the frame is not. */
static uint32_t codol_field_bits(int value, unsigned width)
{
    uint32_t mask = width >= 32 ? UINT32_C(0xffffffff) : (UINT32_C(1) << width) - 1;
    if (value < 0) return 0;
    return (uint32_t)value & mask;
}
static int put(codol_player_fields_t *out, unsigned offset, uint32_t value)
{
    unsigned i;
    for (i = 0; i < CODOL_PLAYER_FIELDS; ++i) {
        if (CODOL_PlayerField(i)->offset == offset) { out->field[i] = value; return 1; }
    }
    return 0;
}
static int put_float(codol_player_fields_t *out, unsigned offset, float value)
{
    uint32_t word;
    if (!isfinite(value)) return 0;
    memcpy(&word, &value, sizeof(word));
    return put(out, offset, word);
}
int CODOL_OverlayEnginePlayerFlags(codol_player_fields_t *wire,const playerState_t *ps)
{
    unsigned i;
    if(!wire || !ps) return 0;
    for(i=0;i<CODOL_PLAYER_FIELDS;++i) if(CODOL_PlayerField(i)->offset==0x0ec) {
        /* The radar/EMP carriers are CoDOL-only bits that CODOL_OverlayEngineRadar
         * translates into C1's own fields; they are never C1 flags themselves. */
        wire->field[i]=(uint32_t)ps->eFlags&~(uint32_t)CODOL_PS_EF_RADAR_CARRIERS;
        return 1;
    }
    return 0;
}
int CODOL_OverlayEnginePlayerMode(codol_player_fields_t *wire, const playerState_t *ps)
{
    codol_player_fields_t out;
    if (!wire || !ps || ps->pm_type < 0 || ps->pm_type>9) return 0;
    out = *wire;
    if(!put(&out,0x004,(uint32_t)ps->pm_type) ||
       !put(&out,0x010,(uint32_t)ps->otherFlags)) return 0;
    *wire = out; return 1;
}
int CODOL_OverlayEnginePlayerAnimations(codol_player_fields_t *wire,const playerState_t *ps)
{
    codol_player_fields_t result;
    const codol_ps_ext_t *extension;
    if(!wire || !ps || ps->legsAnim<0 || ps->legsAnim>2047 ||
       ps->torsoAnim<0 || ps->torsoAnim>2047 ||
       ps->legsTimer<0 || ps->legsTimer>65535 ||
       ps->torsoTimer<0 || ps->torsoTimer>65535) return 0;
    result=*wire;
    extension=CODOL_PlayerStateExtConst(ps);
    /* C1 clone51ca2f records the allocated corpse-info slot in ps+e4.
     * Preserve that death's captured index through replay and spectating. */
    if(extension && extension->corpse_index>=8)return 0;
    if(!put(&result,0x0e4,extension ? extension->corpse_index : 0))return 0;
    /* C1 40d079/40d085 copy ps+c4/cc to es+d8/dc. These are tree
     * indices, separate from primary-hand weapon animation state. */
    /* C1 BG_SetAnim405ba0/405c0a gates changes on the leg/torso timers
     * at+c0/+c8; 405bfc/405c43 write them. Native animation producers
     * use playerState+88/+90 for the same timers. They are durations,
     * carried unchanged through archived player-state copies. */
    if(!put(&result,0x0c0,(unsigned)ps->legsTimer) ||
       !put(&result,0x0c8,(unsigned)ps->torsoTimer) ||
       !put(&result,0x0c4,(unsigned)ps->legsAnim) ||
       !put(&result,0x0cc,(unsigned)ps->torsoAnim)) return 0;
    *wire=result; return 1;
}
int CODOL_OverlayEngineMovement(codol_player_fields_t *wire, const playerState_t *ps)
{
    codol_player_fields_t out;
    unsigned i, ground;
    int dive_end_time;
    if (!wire || !ps || ps->clientNum < 0 || ps->clientNum >= 32 ||
        ps->bobCycle < 0 || ps->bobCycle > 255 || ps->movementDir < -128 || ps->movementDir > 127 ||
        ps->speed < 0 || ps->speed > 65535 || ps->gravity < 0 || ps->gravity > 65535 ||
        ps->pm_time < -32768 || ps->pm_time > 32767 ||
        ps->viewHeightTarget < -128 || ps->viewHeightTarget > 127 ||
        ps->viewHeightLerpTarget < -128 || ps->viewHeightLerpTarget > 127 ||
        (ps->viewHeightLerpDown != 0 && ps->viewHeightLerpDown != 1) ||
        ps->groundEntityNum < 0 || ps->groundEntityNum > ENTITYNUM_NONE ||
        !isfinite(ps->moveSpeedScaleMultiplier) || ps->moveSpeedScaleMultiplier < 0 ||
        !isfinite(ps->holdBreathScale) || ps->holdBreathScale < 0) return 0;
    /* Per-server-frame killcam/follow lifecycle trace; self-limiting on
     * level.time and a no-op unless codol_debugTrace is on.  This is the
     * per-client publish path, so it is reached every frame for every client
     * whose snapshot is built, including following spectators. */
    CODOL_KillcamTraceFrame();
    out = *wire;
    /* Retained PM_Weapon tests the sign of the low pm_flags word (0x8000)
     * before entering sprint. C1 0x41d477/0x41d47a instead tests +c & 0x4000.
     * Publish its level, including clearing it on exit; preserve other flags. */
    for(i=0;i<CODOL_PLAYER_FIELDS;++i) if(CODOL_PlayerField(i)->offset==0x00c) break;
    if(i==CODOL_PLAYER_FIELDS) return 0;
    /* The native C1 mover stores PMF_JUMPING 0x2000 directly and clears it
     * with C1's 0x00402000 landing-state mask. */
    /* PMF_LADDER is 8 in native bg_jump.cpp and C1 PM_CheckLadder
     * 415421. Stance bits are also shared: native PM_CheckDuck_170/320
     * and C1 412982/412aec set prone=1, crouched=2 and clear both for
     * standing. Carry the captured flags with the view-height transition. */
    /* PMF_MANTLE is 4 on both sides: retained Mantle_Check sets it and C1
     * PM_CheckMantle 0x40a0cd does the same. The server runs the mantle, so
     * it is published like the stance bits; without it (and the mantle block
     * below) every snapshot re-zeroed the client's mantle mid-climb and left
     * the player wedged in the ledge. */
    /* ADS 0x40 / ADS-button 0x10 and dive-to-prone 0x40000000 share numbering
     * with C1 (pmove.py PMF_ADS, PMF_ADS_BUTTON, PMF_DIVETOPRONE). */
    /* Shellshock: sh1x's retained producer now stores C1's 0x8000 directly. Every
     * C1 site testing +c & 0x8000 (0x523890, 0x538b1b, 0x561c09) goes straight
     * on to read ps+0x598, the shellshock block, which this state also
     * publishes; without the bit the client never renders the effect. */
    /* sh1x now stores C1 pm_flags directly. C1 PMF_FROZEN is 0x800 and
     * PMF_REMOTE_CONTROLLING is 0x80000; both pass through unchanged. */
    out.field[i]=(uint32_t)ps->pm_flags;
    /* C1 PM_UpdateStance reads ps+0x234 after the dive bit clears to keep
     * forcing prone for 100 ms. It is field 41 in the measured C1 table. */
    if(!CODOL_PlayerStateDiveEndTimeRead(ps,&dive_end_time) ||
       !put(&out,0x234,(uint32_t)dive_end_time)) return 0;
    /* C1 ps+0x333c (netfield 98, -97 TIME): ClientSpawn's level.time stamp,
     * consumed by PM_Weapon_CheckForChange 0x41b109 (200 ms stale weapon-0
     * gate). TIME encodes serverTime-relative, so it is a level.time value or
     * 0 (never spawned: C1 sends the same). */
    {
        int spawn_time;
        if(!CODOL_PlayerStateSpawnTimeRead(ps,&spawn_time) ||
           !put(&out,0x333c,(uint32_t)spawn_time)) return 0;
        {
            static int last[64]; static int lines;
            unsigned c=(unsigned)ps->clientNum;
            if(CODOL_TRACE_ON() && c<64 && lines<400 && spawn_time!=last[c]) {
                last[c]=spawn_time; ++lines;
                Com_Printf(CON_CHANNEL_SERVER,"CoDOL ps: client %u spawnTime %d published (commandTime %d)\n",
                    c,spawn_time,ps->commandTime);
            }
        }
    }
    /* Mantle block: yaw +0x258, timer +0x25c, transIndex +0x260, flags
     * +0x264 (7 bits), the same four words the retained mantleState_t holds
     * and C1 PM_CheckMantle/PM_MantleMove read back from the snapshot. */
    if(ps->mantleState.flags<0 || ps->mantleState.flags>127 || ps->mantleState.transIndex<0 ||
       ps->mantleState.transIndex>15 || !isfinite(ps->mantleState.yaw)) return 0;
    if(!put_float(&out,0x258,ps->mantleState.yaw) ||
       !put(&out,0x25c,(uint32_t)ps->mantleState.timer) ||
       !put(&out,0x260,(uint32_t)ps->mantleState.transIndex) ||
       !put(&out,0x264,(uint32_t)ps->mantleState.flags)) return 0;
    /* Damage feedback. Two families, both named in alpha0022's
     * playerstate_fields.py, which carries C1's netfield table verbatim from
     * .rdata:0x00C38CA8: the flinch and overlay at +0xd8 damageTimer (10 bits),
     * +0xdc damageDuration (16) and +0xe0 flinchYawAnim (2), and the
     * directional indicator at +0x17c damageEvent (8), +0x180 damageYaw (8),
     * +0x184 damagePitch (8) and +0x188 damageCount (7).
     *
     * The indicator run is corroborated independently: 8, 8, 8, 7 is the only
     * such width run in the whole 244-field table, and the retained engine's
     * own netfields give damageEvent 8, damageYaw 8, damagePitch 8 and
     * damageCount 7 in exactly that order (msg.c), with damageCount one of only
     * three 7-bit fields it has.
     *
     * Widths are hard limits: a value wider than its field fails
     * CODOL_WriteDeltaValue and drops the entire frame. These seven are all
     * counters, accumulators or byte-quantised angles, so they are reduced to
     * their field width rather than validated. Rejecting a frame because a
     * damage counter wrapped would cost far more than the wrap itself, and
     * damageEvent is defined modulo its width anyway. +0x18c damageFlags is a
     * single bit with no retained counterpart and is left alone. */
    if(codol_publish_extended_ps &&
      (!put(&out,0x0d8,codol_field_bits(ps->damageTimer,10)) ||
       !put(&out,0x0dc,codol_field_bits(ps->damageDuration,16)) ||
       !put(&out,0x0e0,codol_field_bits(ps->flinchYawAnim,2)) ||
       !put(&out,0x17c,codol_field_bits(ps->damageEvent,8)) ||
       !put(&out,0x180,codol_field_bits(ps->damageYaw,8)) ||
       !put(&out,0x184,codol_field_bits(ps->damagePitch,8)) ||
       !put(&out,0x188,codol_field_bits(ps->damageCount,7)))) return 0;
    /* View lock and prone orientation. The first-person viewmodel at +0x144
     * requires a model-bank binding and is handled by overlay_player.
     * +0x16c..+0x178 are four floats and
     * the retained viewAngleClampBase/Range are two vec2_t in that order;
     * +0x1a0..+0x1a8 are three floats and the retained proneDirection,
     * proneDirectionPitch and proneTorsoPitch are three consecutive floats;
     * +0x1ac is 2 bits for a small ViewLockTypes_t enum and +0x1b0 is 16 bits
     * for an entity number. Names from alpha0022 playerstate_fields.py.
     *
     * The view lock pair is what a turret or a mounted weapon needs to hold
     * the client's camera, and the clamp pair bounds how far it may look.
     * A float only fails the codec when it is not finite, so the guard below
     * is the whole risk; the integers are narrowed to their field width. */
    if(codol_publish_extended_ps) {
    if(!isfinite(ps->viewAngleClampBase[0]) || !isfinite(ps->viewAngleClampBase[1]) ||
       !isfinite(ps->viewAngleClampRange[0]) || !isfinite(ps->viewAngleClampRange[1]) ||
       !isfinite(ps->proneDirection) || !isfinite(ps->proneDirectionPitch) ||
       !isfinite(ps->proneTorsoPitch) || !isfinite(ps->meleeChargeYaw)) return 0;
    /* viewmodelIndex is published separately using the resolved model bank. */
    if(!put_float(&out,0x16c,ps->viewAngleClampBase[0]) ||
       !put_float(&out,0x170,ps->viewAngleClampBase[1]) ||
       !put_float(&out,0x174,ps->viewAngleClampRange[0]) ||
       !put_float(&out,0x178,ps->viewAngleClampRange[1]) ||
       !put_float(&out,0x1a0,ps->proneDirection) ||
       !put_float(&out,0x1a4,ps->proneDirectionPitch) ||
       !put_float(&out,0x1a8,ps->proneTorsoPitch) ||
       !put(&out,0x1ac,codol_field_bits((int)ps->viewlocked,2)) ||
       !put(&out,0x1b0,codol_field_bits(ps->viewlocked_entNum,16)) ||
       /* C1 PM_MeleeChargeUpdate 0x415c40 owns these three fields. */
       !put_float(&out,0x4a4,ps->meleeChargeYaw) ||
       !put(&out,0x4a8,codol_field_bits(ps->meleeChargeDist,8)) ||
       !put(&out,0x4ac,(uint32_t)ps->meleeChargeTime)) return 0;
    }
    /* Animation timers/indices (+0xc0..+0xcc), measured in alpha0022's
     * ps_offset_audit. */
    if(ps->legsTimer<0 || ps->legsTimer>0xffff || ps->torsoTimer<0 || ps->torsoTimer>0xffff ||
       ps->legsAnim<0 || ps->legsAnim>0x7ff || ps->torsoAnim<0 || ps->torsoAnim>0x7ff) return 0;
    if(!put(&out,0x0c0,(uint32_t)ps->legsTimer) || !put(&out,0x0c4,(uint32_t)ps->legsAnim) ||
       !put(&out,0x0c8,(uint32_t)ps->torsoTimer) || !put(&out,0x0cc,(uint32_t)ps->torsoAnim)) return 0;
    /* Native ENTITYNUM_WORLD/NONE are C1's 2046/2047: published as is. */
    ground = ps->groundEntityNum;
    if (!put(&out, 0x000, (uint32_t)ps->commandTime) ||
        /* C1's ADS weapon-sway phase, netfield 4, encoding -70, changeHint 3.
         * C1 seeds its drawn accumulator cg+0xBF980 from this word and replays
         * it forward through CG_PredictPlayerState, so a server that never
         * writes it re-seeds the client to 0 on every snapshot and the scoped
         * sway saw-tooths at the snapshot rate. Measured live before this
         * producer existed: phase == 3.00 * (predicted commandTime - snapshot
         * commandTime) with a seed of exactly 0. codol_playerstate.c:50
         * already force-sends this field whenever fWeaponPosFrac != 0, which
         * is C1's own rule (0x5a44b0); only the value was missing.
         * See docs/CODOL_SWAY_CAUSE_SWEEP_20260916.md. */
        !put(&out, 0x4a0, (uint32_t)CODOL_SwayPhase(ps)) ||
        /* C1 land-factor helper409260 reads +8 and compares against1700,
         * matching native Jump_GetLandFactor's pm_time duration. Jump start
         * writes +b8/+bc at409443/40942b (time and starting origin.z). */
        !put(&out, 0x008, (uint32_t)ps->pm_time) ||
        !put(&out, 0x0b8, (uint32_t)ps->jumpTime) ||
        !put_float(&out, 0x0bc, ps->jumpOriginZ) ||
        !put(&out, 0x018, ps->bobCycle) || !put(&out, 0x0e8, (uint32_t)ps->movementDir) ||
        !put(&out, 0x090, ps->gravity) || !put(&out, 0x098, ps->speed) ||
        /* C1 46be37/46bf0c enters/leaves its real killcam when deltaTime
         * (+a50) becomes nonzero/zero; the inKillcam UI expression5df490
         * reads that resulting state. SV_GetArchivedClientInfo already adds
         * the archive time displacement to native deltaTime, and the forced
         * follow producer supplies killCamEntity (including2047 for none).
         * Publish both captured fields. An archived camera alone does not
         * activate C1's killcam HUD, playercard or visual lifecycle.
         * Preserve the native entity selector outside replay too: C1 only
         * consumes +a54 while its killcam state is active (46c08c..46c0b8). */
        !put(&out, 0x0a50, (uint32_t)ps->deltaTime) ||
        /* C1 0x0046c0b8 recognises 2047 alone as "no killcam entity"; every
         * other value indexes the centity array at 0x0046c0eb.  The native
         * field has exactly one writer (SpectatorClientEndFrame's forced-follow
         * arm) so anything outside 0..2047 - including the -1 sentinel the
         * session field uses and a never-initialised 0 - has to become
         * ENTITYNUM_NONE here rather than reaching the wire as entity 0.
         * ClientSpawn now seeds the field with ENTITYNUM_NONE as well. */
        !put(&out, 0x0a54, (uint32_t)((ps->killCamEntity < 0 ||
                                       ps->killCamEntity > ENTITYNUM_NONE)
                                          ? ENTITYNUM_NONE : ps->killCamEntity)) ||
        /* C1 selector byte516394, read431276. Captured playerstate owns
         * this value through snapshot/archive/follow copies and spawn clear. */
        !put(&out, 0x230, (uint32_t)ps->locationSelectionInfo & 255u) ||
        /* C1 PM_CmdScale4101a5 reads the lean float at+94. */
        !put_float(&out, 0x094, ps->leanf) ||
        !put(&out, 0x0a8, ground) || !put(&out, 0x140, ps->clientNum) ||
        /* C1 CG_OffsetFirstPersonView 0x4711aa treats zero as a link to
         * entity 0 and skips adding viewHeightCurrent. Normal playerstate
         * must explicitly carry ENTITYNUM_NONE; the captured link overlay
         * replaces this only for playerLinkWeaponViewToDelta. */
        !put(&out, 0x1ec, ENTITYNUM_NONE) ||
        !put(&out, 0x158, (uint32_t)ps->viewHeightTarget) ||
        /* C1 PM_GetMoveScale 40ffc6..40ffe7 consumes the transition
         * start, target height and down flag in this order. */
        !put(&out, 0x160, (uint32_t)ps->viewHeightLerpTime) ||
        !put(&out, 0x164, (uint32_t)ps->viewHeightLerpTarget) ||
        !put(&out, 0x168, (uint32_t)ps->viewHeightLerpDown) ||
        !put_float(&out, 0x15c, ps->viewHeightCurrent) ||
        !put_float(&out, 0x254, ps->moveSpeedScaleMultiplier) ||
        /* C1 PM_UpdateHoldBreath 0x4188b0 reads and writes holdBreathScale
         * +0x24c (netfield 34) and holdBreathTimer +0x250 (netfield 193,
         * 16 bits) and the client predicts it from every snapshot; the
         * scope sway multiplier is this scale. Never sending them re-based
         * the client to 0 each snapshot. Timer maximum is hold+gasp
         * (5500 ms, ability 13 extends it) so 16 bits hold it. */
        !put_float(&out, 0x24c, ps->holdBreathScale) ||
        !put(&out, 0x250, (uint32_t)(ps->holdBreathTimer < 0 ? 0 :
                                     ps->holdBreathTimer > 0xffff ? 0xffff : ps->holdBreathTimer))) return 0;
    /* C1 PM_UpdateVariableZoom 0x418480 owns the scope's zoom level +0x5c4
     * (2 bits) and its melee-key latch +0x5cc (1 bit); the client replays its
     * commands from these every snapshot, so a server that never wrote them
     * snapped every variable-zoom change back to the first level. */
    {
        uint32_t zoom_level, zoom_latch;
        CODOL_VariableZoomWire(ps->clientNum, &zoom_level, &zoom_latch);
        if (!put(&out, 0x5c4, zoom_level) || !put(&out, 0x5cc, zoom_latch)) return 0;
    }
    for (i = 0; i < 3; ++i) {
        if (!put_float(&out, 0x01c+4*i, ps->origin[i]) ||
            !put_float(&out, 0x028+4*i, ps->velocity[i]) ||
            /* C1 ladder trace415435/415447/415452 reads and negates
             * these three ladder-normal components. Native playerState
             * carries the vector as vLadderVec, independently of position. */
            !put_float(&out, 0x0ac+4*i, ps->vLadderVec[i]) ||
            !put_float(&out, 0x09c+4*i, ps->delta_angles[i]) ||
            !put_float(&out, 0x14c+4*i, ps->viewangles[i])) return 0;
    }
    *wire = out; return 1;
}

int CODOL_OverlayEngineWeaponSelection(codol_player_fields_t *wire, const playerState_t *ps,
                                      unsigned alt_weapon)
{
    codol_player_fields_t out;
    int weapon, alt, offhand;
    if (!wire || !ps) return 0;
    weapon = CODOL_WeaponToWire(ps->weapon);
    alt = CODOL_WeaponToWire(alt_weapon);
    offhand = CODOL_WeaponToWire((unsigned)ps->offHandIndex);
    if (weapon < 0 || alt < 0 || offhand < 0) return 0;
    out = *wire;
    /* Measured weapon_spawn.py PS_WEAPON/PS_ALTMODE_WEAPON/PS_OFFHAND_WEAPON. */
    if (!put(&out, 0x33c, weapon) || !put(&out, 0x340, alt) || !put(&out, 0x328, offhand)) return 0;
    /* C1 takes the melee viewmodel animation, damage, range, rate, knife
     * models and sounds from a row of mp/coKnifeStatsTable.csv, not from the
     * held weapon. 0x47c1c0 selects the row from ps+0x338 as a 1-based index
     * (0x47c5e0 / 0x48095e `mov edx,[esi+0x338]`), and 0x47c090 applies it:
     * 0x47c0f3 `test ebx,ebx / je 0x47c113` skips the override when there is
     * no row, and 0x47c0df then falls the empty name back to names[1], the
     * IDLE animation. That is why an unset field reads as "no melee
     * animation" for every zm gun whose own slot 7 is empty -- which is the
     * deliberate shipped state: def+0xbf0 ("owns its melee anims", tested at
     * 0x47c0e5) is 0 on every ordinary zm gun.
     *
     * Row 13 zknife_standard is the zombies knife: 150 damage and
     * viewmodel_knife_melee_slice, which already ships in common_gametype_zm.
     * Row 14 zknife_bowie is the Bowie upgrade, a pure row swap -- the same
     * carried-knife mechanic World at War and Black Ops use. Rows 13..16 are
     * gated by 0x41fd8d..0x41fde1 on g_gametype starting with "zm", which our
     * serverinfo satisfies (codol_sv_state.c:115).
     *
     * mp and coop stay at 0 until the loadout melee choice is wired through;
     * their guns carry their own slot 7, so they animate either way. */
    if (!put(&out, 0x338, CODOL_ServerMeleeRow())) return 0;
    *wire = out; return 1;
}
int CODOL_OverlayEngineOffhandSelection(codol_player_fields_t *wire,const unsigned slots[3])
{
    codol_player_fields_t out;
    static const uint32_t offset[3]={0x32c,0x330,0x334};
    int weapon; unsigned i;
    if(!wire || !slots) return 0;
    out=*wire;
    for(i=0;i<3;++i) {
        /* Nothing selected stays nothing; every other index must have a
         * registered asset mapping, exactly like the weapon fields above. */
        if(!slots[i]) weapon=0;
        else if((weapon=CODOL_WeaponToWire(slots[i]))<0) return 0;
        if(!put(&out,offset[i],(uint32_t)weapon)) return 0;
    }
    *wire=out; return 1;
}
int CODOL_OverlayEngineAim(codol_player_fields_t *wire,const playerState_t *ps)
{
    codol_player_fields_t out;
    if(!wire || !ps || !isfinite(ps->fWeaponPosFrac) || ps->fWeaponPosFrac<0 || ps->fWeaponPosFrac>1 ||
       !isfinite(ps->aimSpreadScale) || ps->aimSpreadScale<0 || ps->aimSpreadScale>255) return 0;
    out=*wire;
    /* C1 fire ADS selector reads +348 at 0x41b7e7; aim-spread integration
     * (0x418b70) owns the 0..255 float at +34c. Native fields are +f4/+628.
     * Both target netfields use the exact float-word XOR codec (-88). */
    if(!put_float(&out,0x348,ps->fWeaponPosFrac) || !put_float(&out,0x34c,ps->aimSpreadScale)) return 0;
    /* C1 BG_CalcSpread 0x422660 and spread integration 0x418b70 read
     * ps+0x354 (netfield 209, 6 bits) and ps+0x358 (210, 2 bits): state 2
     * forces min=max=override, state 1 caps max and the client clears the
     * state itself at 0x418e28..0x418e4f once band*aimSpreadScale reaches the
     * target (codol_pmove_c1.c:208 mirrors it). PlayerCmd_SetSpreadOverride /
     * ResetSpreadOverride write the native fields; the C1 methods at
     * 0x513080/0x513130 do the same. A value the 6-bit field cannot carry is
     * rejected like every other overlay failure. */
    if(ps->spreadOverride<0 || ps->spreadOverride>=64 ||
       ps->spreadOverrideState<0 || ps->spreadOverrideState>3) return 0;
    if(!put(&out,0x354,(uint32_t)ps->spreadOverride) ||
       !put(&out,0x358,(uint32_t)ps->spreadOverrideState)) return 0;
    {
        static uint32_t last[64]; static int lines;
        unsigned c=(unsigned)ps->clientNum;
        uint32_t key=((uint32_t)ps->spreadOverride<<8)|(uint32_t)ps->spreadOverrideState|0x80000000u;
        if(CODOL_TRACE_ON() && c<64 && lines<400 && key!=last[c]) {
            last[c]=key; ++lines;
            Com_Printf(CON_CHANNEL_SERVER,"CoDOL ps: client %u spreadOverride %d state %d aimSpreadScale %.2f\n",
                c,ps->spreadOverride,ps->spreadOverrideState,ps->aimSpreadScale);
        }
    }
    *wire=out; return 1;
}
int CODOL_TranslateEngineWeaponState(unsigned engine_state,unsigned *out)
{
    unsigned state;
    if(!out) return 0;
    /* Retained _bg_weapons.asm PM_Weapon_1900: fire 5; rechamber writes 6;
     * PM_Weapon_2220/2330/2340: melee init/fire/end 12/13/14.
     * C1 fire 0x41b618, rechamber 0x41909a and melee 0x41bd30/41bcd0/
     * 41bc00 establish CoDOL's corresponding states (alpha0022 weapon_fsm
     * and melee_support). CoDOL inserts states; never use a blanket +1. */
    switch(engine_state) {
    case 0: state=0; break;
    /* Retained PM_Weapon_2270 and C1 0x419abb: normal/alternate raise. */
    case 1: state=1; break;
    case 2: state=2; break;
    case 5: state=6; break;
    case 6: state=7; break;
    /* IW3 PM_SetReloadingState: 7 + (old == 10); reload-start 9, end 11.
     * C1 0x419476: 8 + (old == 11); 0x419605 starts 10, end is 12. */
    case 7: state=8; break;
    case 8: state=9; break;
    case 9: state=10; break;
    case 10: state=11; break;
    case 11: state=12; break;
    case 12: state=13; break;
    case 13: state=14; break;
    case 14: state=15; break;
    /* Native offhand init/prepare/hold/fire/post-fire/end and main-weapon
     * detonation. C1 merges the native fire/post-fire stages into 19;
     * its separate offhand detonation state 20 has no direct native phase. */
    case 15: state=16; break;
    case 16: state=17; break;
    case 17: state=19; break;
    case 18: state=18; break;
    case 19: state=19; break;
    case 20: state=21; break;
    case 21: state=22; break;
    /* CoDOL's offhand detonation, C1 state 20. It is the one phase of that
     * sequence the retained engine had no number for, which is also why the
     * native offhand ranges are 15..20 where C1's are 16..21: the native range
     * is the preimage of the C1 range minus this state, not an off-by-one.
     * src/codol_weapon_state.h documents the number and the branches that were
     * extended to see it; the producer is PM_Weapon_OffHandPrepare, following
     * C1 0x41c433. */
    case CODOL_WEAPONSTATE_OFFHAND_DETONATE: state=20; break;
    /* Retained PM_Weapon sprint entry/loop/exit write 22/23/24.
     * C1 0x41d0a3/0x41d0fc/0x41d171 write 23/24/25. */
    case 22: state=23; break;
    case 23: state=24; break;
    case 24: state=25; break;
    /* CoDOL dolphin-dive phases (codol_weapon_state.h): C1 0x41d1f0,
     * 0x41d350 and 0x41d2a0 write 31/32/33. */
    case CODOL_WEAPONSTATE_DIVE_IN: state=31; break;
    case CODOL_WEAPONSTATE_DIVE_LOOP: state=32; break;
    case CODOL_WEAPONSTATE_DIVE_OUT: state=33; break;
    default: return 0;
    }
    *out=state; return 1;
}
int CODOL_ResolveEngineWeaponState(unsigned engine_state,unsigned engine_animation,
                                   unsigned *out)
{
    unsigned animation;
    if(!out) return 0;
    if(CODOL_TranslateEngineWeaponState(engine_state,out)) return 1;
    if(engine_animation & ~0x21fu) return 0;
    animation=engine_animation & 0x1fu;
    if(engine_state==3 || engine_state==4) {
        /* C1 alternate drop is its inserted state 5. Normal, quick and empty
         * drops retain the state selected by the retained producer. */
        if(animation==17) { *out=5; return 1; }
        /* Normal, quick and empty drops (10/19/21) -- and a drop whose
         * animation the producer did not restart, which C1 produces itself
         * while sprinting (0x41991c) -- keep the retained state. */
        *out=engine_state; return 1;
    }
    /* Retained night-vision wear/remove 25/26 correspond to C1 29/30.
     * Their animation mapping is still unsupported by snapshot composition,
     * but movement gates need the phase number before that later adapter. */
    if(engine_state==25) { *out=29; return 1; }
    if(engine_state==26) { *out=30; return 1; }
    return 0;
}
/* Native weapon animation -> C1's numbering, for any phase. Up to 12 the two
 * tables agree; C1 inserts the two fast reloads after 13 and 15 (0x419425,
 * 0x41939e), so 17..25 sit two higher, and past the sprint trio it holds 31
 * (offhand prepare, 0x41c4c4), 32 (detonation, 0x41c478/0x41ce5f) and the
 * dive animations 35..40 (0x41d1f0..0x41d3be).
 *
 * A phase can legitimately carry an animation its own producer did not write:
 * C1 keeps the drop's animation when an offhand interrupts it (0x41c2e3), the
 * sprint's when an offhand leaves a sprint (0x41c302), and skips the drop
 * animation while sprinting (0x41991c). The retained machine reaches the same
 * pairs, and the VPS logged frames refused for them (weaponstate 4 with a
 * reload or raise animation, weaponstate 5 with idle). Such a pair is
 * published as it is instead of dropping the whole frame, which cost the
 * client a delta baseline and replayed its prediction. */
static int translate_weapon_animation(const playerState_t *ps,unsigned animation,unsigned *out)
{
    switch(animation) {
    case 13: *out=ps && CODOL_PlayerStateHandRead(ps)->primary_reload_fast ? 14 : 13; return 1;
    case 14: *out=ps && CODOL_PlayerStateHandRead(ps)->primary_reload_fast ? 16 : 15; return 1;
    case 15: *out=17; return 1;
    case 16: *out=18; return 1;
    case 26: *out=31; return 1;
    case 27: *out=32; return 1;
    case CODOL_HAND_ANIM_RELOAD_FAST: *out=14; return 1;
    case CODOL_HAND_ANIM_RELOAD_EMPTY_FAST: *out=16; return 1;
    case CODOL_ANIM_DIVE: *out=36; return 1;
    case CODOL_ANIM_DIVE_EMPTY: *out=39; return 1;
    }
    if(animation<=12) { *out=animation; return 1; }
    if(animation>=17 && animation<=25) { *out=animation+2; return 1; }
    return 0;
}
int CODOL_OverlayEnginePrimaryWeaponPhase(codol_player_fields_t *wire,const playerState_t *ps,unsigned animation)
{
    unsigned state;
    if(!ps || !CODOL_TranslateEngineWeaponState((unsigned)ps->weaponstate,&state)) return 0;
    return CODOL_OverlayEngineWeaponPhase(wire,ps,state,animation);
}
int CODOL_OverlayEngineReloadPhase(codol_player_fields_t *wire,const playerState_t *ps)
{
    unsigned animation,raw;
    if(!ps || ps->weaponstate<7 || ps->weaponstate>11) return 0;
    raw=(unsigned)ps->weapAnim;
    if(raw & ~0x21fu) return 0;
    /* Retained PM_SetReloadingState/PM_BeginWeaponReload/PM_Weapon_890
     * use animations 13/14/15/16 and toggle 0x200. C1 0x419425/41939e,
     * 0x4195ee and alpha0022 A_RELOAD_END establish 13/15/17/18, toggle
     * 0x400. Names are separate WeaponDef slots, not these animation IDs. */
    switch(raw & 0x1fu) {
    case 13: animation=CODOL_PlayerStateHandRead(ps)->primary_reload_fast ? 14 : 13; break;
    case 14: animation=CODOL_PlayerStateHandRead(ps)->primary_reload_fast ? 16 : 15; break;
    case 15: animation=17; break;
    case 16: animation=18; break;
    default: if(!translate_weapon_animation(ps,raw&0x1fu,&animation)) return 0; break;
    }
    if(raw & 0x200u) animation|=0x400u;
    return CODOL_OverlayEnginePrimaryWeaponPhase(wire,ps,animation);
}
int CODOL_OverlayEngineSprintPhase(codol_player_fields_t *wire,const playerState_t *ps)
{
    unsigned raw,animation;
    if(!ps || ps->weaponstate<22 || ps->weaponstate>24) return 0;
    raw=(unsigned)ps->weapAnim;
    if(raw & ~0x21fu) return 0;
    /* Native PM_Weapon entry/loop/exit use 23/24/25 and restart 0x200.
     * C1 0x41d0ca/0x41d139/0x41d1c8 use 25/26/27 and restart 0x400.
     * WeaponDef animation-name slots are a separate numbering scheme. */
    switch(raw & 0x1fu) {
    case 23: animation=25; break;
    case 24: animation=26; break;
    case 25: animation=27; break;
    default: if(!translate_weapon_animation(ps,raw&0x1fu,&animation)) return 0; break;
    }
    if(raw & 0x200u) animation|=0x400u;
    return CODOL_OverlayEnginePrimaryWeaponPhase(wire,ps,animation);
}
/* The dive phases: the native animation says normal or empty magazine, the
 * phase says in/loop/out -- C1 35/36/37 or 38/39/40. */
static int translate_dive_phase(unsigned native_state,unsigned raw,unsigned *out_state,
                                unsigned *out_animation)
{
    unsigned animation=raw&0x1fu;
    if(native_state<CODOL_WEAPONSTATE_DIVE_IN || native_state>CODOL_WEAPONSTATE_DIVE_OUT ||
       (raw & ~0x21fu) || !CODOL_TranslateEngineWeaponState(native_state,out_state)) return 0;
    if(animation==CODOL_ANIM_DIVE || animation==CODOL_ANIM_DIVE_EMPTY)
        animation=(animation==CODOL_ANIM_DIVE_EMPTY ? 38u : 35u)+(native_state-CODOL_WEAPONSTATE_DIVE_IN);
    else if(!translate_weapon_animation(NULL,animation,&animation)) return 0;
    if(raw & 0x200u) animation|=0x400u;
    *out_animation=animation; return 1;
}
int CODOL_OverlayEngineDivePhase(codol_player_fields_t *wire,const playerState_t *ps)
{
    unsigned state,animation;
    if(!ps || !translate_dive_phase((unsigned)ps->weaponstate,(unsigned)ps->weapAnim,
                                    &state,&animation)) return 0;
    return CODOL_OverlayEngineWeaponPhase(wire,ps,state,animation);
}
int CODOL_OverlayEngineWeaponDropPhase(codol_player_fields_t *wire,const playerState_t *ps)
{
    unsigned raw,animation,state;
    if(!ps || (ps->weaponstate!=3 && ps->weaponstate!=4)) return 0;
    raw=(unsigned)ps->weapAnim;
    if(raw & ~0x21fu) return 0;
    if(!CODOL_ResolveEngineWeaponState((unsigned)ps->weaponstate,raw,&state)) return 0;
    /* Retained PM_BeginWeaponChange uses states 3/4 even for alternate
     * drops, identified by animation 17. C1 0x4198d4/0x4198e4 instead
     * selects animation 19/state 5. Normal/quick/empty animations are
     * selected at C1 0x41993f..0x41994d; ordinary states at 0x4199e1.
     * Consequently a state-only mapping of native drop is insufficient. */
    switch(raw & 0x1fu) {
    case 10: animation=10; break;
    case 17: animation=19; break;
    case 19: animation=21; break;
    case 21: animation=23; break;
    default: if(!translate_weapon_animation(ps,raw&0x1fu,&animation)) return 0; break;
    }
    if(raw & 0x200u) animation|=0x400u;
    return CODOL_OverlayEngineWeaponPhase(wire,ps,state,animation);
}
int CODOL_OverlayEngineWeaponRaisePhase(codol_player_fields_t *wire,const playerState_t *ps)
{
    unsigned raw,animation;
    if(!ps || (ps->weaponstate!=1 && ps->weaponstate!=2)) return 0;
    raw=(unsigned)ps->weapAnim;
    if(raw & ~0x21fu) return 0;
    /* Native PM_Weapon_2180/1150/1140/2090/1130 select normal, first,
     * alternate, quick and empty raise animations. C1 counterparts:
     * 0x419ec5/419e71/419e2a/419eb2/419e55. State setter 0x419abb
     * preserves the normal (1) versus alternate (2) distinction. */
    switch(raw & 0x1fu) {
    case 11: animation=11; break;
    case 12: animation=12; break;
    case 18: animation=20; break;
    case 20: animation=22; break;
    case 22: animation=24; break;
    default: if(!translate_weapon_animation(ps,raw&0x1fu,&animation)) return 0; break;
    }
    if(raw & 0x200u) animation|=0x400u;
    return CODOL_OverlayEnginePrimaryWeaponPhase(wire,ps,animation);
}
int CODOL_OverlayEngineWeaponPhase(codol_player_fields_t *wire,const playerState_t *ps,unsigned state,unsigned animation)
{
    codol_player_fields_t result;
    if(!wire || !ps || state>63 || animation>2047 || ps->weaponTime<-32768 || ps->weaponTime>32767 ||
       ps->weaponDelay<-32768 || ps->weaponDelay>32767 ||
       ps->weaponRestrictKickTime<0 || ps->weaponRestrictKickTime>32767 ||
       ps->weaponShotCount>7) return 0;
    result=*wire;
    /* C1 primary hand: weapAnim +0x268, weaponTime +0x26c,
     * weaponDelay +0x270, weaponstate +0x278 (alpha0022 weapon_fsm.py). */
    if(!put(&result,0x268,animation) || !put(&result,0x26c,(uint32_t)ps->weaponTime) ||
       !put(&result,0x270,(uint32_t)ps->weaponDelay) || !put(&result,0x278,state)) return 0;
    /* Complete the hand, not just its visible phase. C1 41ad0d decrements
     * +274, 41adc9 consumes the fresh burst-pull latch at +27c, and 41aab5
     * consumes shotCount at +280. The retained primary machine produces
     * those same values at ps+50, weapFlags bit100, and ps+f0: its
     * PM_Weapon_170 arms the latch and PM_Weapon_1900 consumes it on the
     * first shot. Sending zeros makes each correction reopen a semi-auto
     * trigger or discard a burst already in progress. */
    if(!put(&result,0x274,(uint32_t)ps->weaponRestrictKickTime) ||
       !put(&result,0x27c,((unsigned)ps->weapFlags>>8)&1u) ||
       !put(&result,0x280,ps->weaponShotCount)) return 0;
    *wire=result; return 1;
}
int CODOL_OverlayEnginePrimaryWeapon(codol_player_fields_t *wire,const playerState_t *ps)
{
    unsigned raw,animation;
    if(!ps) return 0;
    switch(ps->weaponstate) {
    case 1: case 2: return CODOL_OverlayEngineWeaponRaisePhase(wire,ps);
    case 3: case 4: return CODOL_OverlayEngineWeaponDropPhase(wire,ps);
    case 7: case 8: case 9: case 10: case 11: return CODOL_OverlayEngineReloadPhase(wire,ps);
    case 22: case 23: case 24: return CODOL_OverlayEngineSprintPhase(wire,ps);
    case CODOL_WEAPONSTATE_DIVE_IN: case CODOL_WEAPONSTATE_DIVE_LOOP:
    case CODOL_WEAPONSTATE_DIVE_OUT: return CODOL_OverlayEngineDivePhase(wire,ps);
    case 15: case 16: case 17: case 18: case 19: case 20: case 21:
    case CODOL_WEAPONSTATE_OFFHAND_DETONATE:
        return CODOL_OverlayEngineOffhandPhase(wire,ps);
    case 0: case 5: case 6: case 12: case 13: case 14: break;
    default: return 0;
    }
    raw=(unsigned)ps->weapAnim;
    if(raw & ~0x21fu) return 0;
    animation=raw&0x1fu;
    /* Native PM_Weapon_1360/1950 and C1 0x41b7e0..0x41b817 select
     * hip fire 2/3 and ADS fire 5/6 (second ID means empty). Rechamber
     * uses 4/7, as at C1 0x419087/0x41908b. Ready resets to idle 0.
     * Preserve the selected branch; do not recompute it from ammo or ADS. */
    /* A ready weapon normally carries the idle animation, but a player who
     * died, was stunned or took fall damage keeps the last animation the
     * movement code left (PM_Weapon does not run for the dead), and C1 shows
     * the same leftover. Publish a known fire/rechamber/melee animation with
     * the ready state instead of refusing the whole frame; anything else
     * falls back to idle. */
    /* Idle 0 and force-idle 1 both pass: C1 0x41b1a0 publishes 1 when a drop
     * is cancelled back to the weapon already held, which the retained
     * PM_Weapon_2000 reproduces; folding it to 0 changed the client's view. */
    if(ps->weaponstate==0 && animation>9) animation=0;
    /* Fire 5 and rechamber 6 normally carry 2/3/5/6 and 4/7. Any other
     * animation is one the phase inherited (idle, a drop, a detonation); it
     * is translated and published rather than refusing the frame. */
    if((ps->weaponstate==5 && animation!=2 && animation!=3 && animation!=5 && animation!=6) ||
       (ps->weaponstate==6 && animation!=4 && animation!=7)) {
        if(!translate_weapon_animation(ps,animation,&animation)) return 0;
        if(raw&0x200u) animation|=0x400u;
        return CODOL_OverlayEnginePrimaryWeaponPhase(wire,ps,animation);
    }
    /* Retained PM_Weapon_460/charge branch select 8/9. C1 0x41bef8..
     * 0x41bf09 selects the same normal/charge animations. The existing
     * state mapper translates native melee 12..14 into CoDOL 13..15. */
    if(ps->weaponstate>=12 && ps->weaponstate<=14 && animation!=8 && animation!=9) {
        /* The melee end state has been seen carrying a raise/drop animation
         * (native 20). Translate it the way the drop/raise phases do: native
         * numbers up to 16 are shared, later ones sit two higher in C1's
         * table (it inserts two reload animations). */
        if(animation>16) animation+=2;
    }
    if(raw&0x200u) animation|=0x400u;
    return CODOL_OverlayEnginePrimaryWeaponPhase(wire,ps,animation);
}
int CODOL_OverlayEngineOffhandPhase(codol_player_fields_t *wire,const playerState_t *ps)
{
    unsigned raw,animation;
    if(!ps || ((ps->weaponstate<15 || ps->weaponstate>21) &&
               ps->weaponstate!=CODOL_WEAPONSTATE_OFFHAND_DETONATE)) return 0;
    raw=(unsigned)ps->weapAnim;
    if(raw & ~0x21fu) return 0;
    animation=raw&0x1fu;
    /* C1 init 0x41c282/337, prepare 0x41c3c5/40d/4c4, hold 0x41c536,
     * throw 0x41c66d/70a, end 0x41c887/938 and detonation 0x41ce43/5f.
     * The throw uses animation 2, not the detonation animation 32. */
    switch(ps->weaponstate) {
    /* Init normally plays the quick drop 19 (C1 21); C1 keeps a drop's or a
     * sprint's own animation when the offhand interrupts it (0x41c2e3,
     * 0x41c302), so any other animation is translated as it stands. */
    case 15:
        if(!translate_weapon_animation(ps,animation,&animation)) return 0;
        break;
    case 16: case 18:
        if(animation==18) animation=20; /* Throwback preparation. */
        else if(!translate_weapon_animation(ps,animation,&animation)) return 0;
        break;
    case 17: case 19:
        if(animation!=2 && !translate_weapon_animation(ps,animation,&animation)) return 0;
        break;
    /* Offhand end normally carries animation 20 (C1 22). After a C4
     * detonation the retained machine enters the end state with the
     * detonation animation 27 still in weapAnim (2026-09-15 live: state
     * 20 anim 0x1b right after a triple C4 kill). Refusing it rejected
     * the whole frame, forced an overflow recovery and a non-delta
     * resend that crashed C1; keep C1's detonation animation 32 instead. */
    case 20:
        if(!translate_weapon_animation(ps,animation,&animation)) return 0;
        break;
    case 21: if(!translate_weapon_animation(ps,animation,&animation)) return 0; break;
    /* C1 0x41c478 plays animation 32 for the offhand detonation, the same one
     * 0x41ce5f plays for the main weapon's; the producer reuses the retained
     * detonation animation 27 that PM_Weapon_520 already establishes for it. */
    case CODOL_WEAPONSTATE_OFFHAND_DETONATE:
        if(!translate_weapon_animation(ps,animation,&animation)) return 0;
        break;
    }
    if(raw&0x200u) animation|=0x400u;
    return CODOL_OverlayEnginePrimaryWeaponPhase(wire,ps,animation);
}

static int codol_health_word(int value)
{
    return value < -32768 ? -32768 : value > 32767 ? 32767 : value;
}
int CODOL_OverlayEngineHealth(codol_player_array_updates_t *updates, const playerState_t *ps)
{
    if (!updates || !ps) return 0;
    /* IW3 g_client_fields.cpp / g_client_mp.cpp and CoDOL's stat reader at
     * 0x5A1D24..0x5A1DAA agree on health slot 0 and max health slot 2.
     * The wire slot is sixteen bits but script health is a full int (the
     * killstreak test hook and god-mode scripts use 100000). Saturate: a
     * rejected frame stops that client's snapshots for as long as the value
     * lasts, which froze a predator user's view for the whole ride. */
    updates->stats[0] = codol_health_word(ps->stats[0]);
    /* Slot 1 is the dead yaw. C1 LookAtKiller (0x5205a0) stores
     * vectoyaw(killer - victim) there (retained player_die: gclient+0x14c);
     * the death camera (0x470882) and PM_UpdateViewAngles' dead branch
     * (0x414e6d, 999 = free look) read it from ps+0x194 once pm_type
     * reaches 8. Never publishing it left every death camera at yaw 0. */
    updates->stats[1] = codol_health_word(ps->stats[1]);
    updates->stats[2] = codol_health_word(ps->stats[2]);
    updates->stats_mask |= 7;
    return 1;
}
int CODOL_OverlayEngineGrenadeState(codol_player_fields_t *wire,const playerState_t *ps)
{
    codol_player_fields_t out; unsigned owner,i;
    const codol_ps_ext_t *extension;
    unsigned throwback=0;
    if(!wire || !ps || ps->grenadeTimeLeft<-32768 || ps->grenadeTimeLeft>32767 ||
       ps->throwBackGrenadeTimeLeft<-32768 || ps->throwBackGrenadeTimeLeft>32767 ||
       ps->throwBackGrenadeOwner<0 || ps->throwBackGrenadeOwner>ENTITYNUM_NONE) return 0;
    out=*wire; owner=(unsigned)ps->throwBackGrenadeOwner; /* same namespace as C1 */
    extension=CODOL_PlayerStateExtConst(ps);
    if(extension && extension->throwback_weapon && ps->throwBackGrenadeTimeLeft>0) {
        if(extension->use_hint_weapon<2 || extension->use_hint_weapon>701)return 0;
        throwback=(unsigned)extension->use_hint_weapon-1;
    }
    /* C1 hold sets +34 at 0x41c561; expiry uses -1 at 0x41cd1d.
     * Throwback availability tests +3c at 0x421dec/0x421e45, matching
     * native BG_GetFirstAvailableOffhand's throwBackGrenadeTimeLeft.
     * C1 prepare/end set/clear +344 bit 2 (0x41c3d5/0x41c946), matching
     * retained native weapFlags bit 2. Other weapon flags stay untouched. */
    for(i=0;i<CODOL_PLAYER_FIELDS;++i) if(CODOL_PlayerField(i)->offset==0x344) break;
    if(i==CODOL_PLAYER_FIELDS) return 0;
    out.field[i]=(out.field[i]&~UINT32_C(2))|((uint32_t)ps->weapFlags&2u);
    if(!put(&out,0x034,(uint32_t)ps->grenadeTimeLeft) ||
       !put(&out,0x038,owner) || !put(&out,0x03c,(uint32_t)ps->throwBackGrenadeTimeLeft) ||
       !put(&out,0x040,throwback)) return 0;
    *wire=out; return 1;
}
/* The animation and state tables the primary phase producers above already
 * establish, applied to a hand whose values are supplied rather than read out
 * of the retained single-hand playerState. Native drop animation 17 selects
 * CoDOL state 5, exactly as CODOL_OverlayEngineWeaponDropPhase does. */
static int translate_hand_phase(unsigned native_state,unsigned raw,unsigned *out_state,unsigned *out_animation)
{
    unsigned state,animation=raw&0x1fu;
    if(raw & ~0x21fu) return 0;
    /* The dive phases carry their own animation pair (see above). */
    if(native_state>=CODOL_WEAPONSTATE_DIVE_IN && native_state<=CODOL_WEAPONSTATE_DIVE_OUT)
        return translate_dive_phase(native_state,raw,out_state,out_animation);
    /* CODOL_TranslateEngineWeaponState deliberately omits the native drop
     * states: CoDOL keeps 3 and 4 and adds 5 for the alternate drop, which the
     * animation selects, exactly as CODOL_OverlayEngineWeaponDropPhase does. */
    if(native_state==3 || native_state==4) state=native_state;
    else if(!CODOL_TranslateEngineWeaponState(native_state,&state)) return 0;
    switch(native_state) {
    /* Idle 0 and force-idle 1 (C1 0x41b1a0, a drop cancelled back). */
    case 0: if(animation>9) animation=0; break;
    case 3: case 4:
        if(animation==17) state=5;
        if(!translate_weapon_animation(NULL,animation,&animation)) return 0;
        break;
    /* Fire/rechamber carry their own animations; melee (a player-wide phase
     * the second hand also performs) carries 8/9, both shared numbers. Every
     * other phase, and an animation a phase inherited, goes through the same
     * table as the primary hand: see translate_weapon_animation. */
    default:
        if(!translate_weapon_animation(NULL,animation,&animation)) return 0;
        break;
    }
    if(raw & 0x200u) animation|=0x400u;
    *out_state=state; *out_animation=animation; return 1;
}
int CODOL_OverlayEngineSecondaryWeapon(codol_player_fields_t *wire,int dual_wield,
    const codol_engine_hand_t *hand)
{
    codol_player_fields_t out; unsigned state,animation;
    if(!wire) return 0;
    out=*wire;
    /* Wire field 123 is the one-bit akimbo flag at +0x35c (C1 0x419d68). */
    if(!put(&out,0x35c,dual_wield?1u:0u)) return 0;
    if(!dual_wield) {
        /* C1 0x4180ec clears the second hand outright. */
        if(!put(&out,0x284,0)||!put(&out,0x288,0)||!put(&out,0x28c,0)||
           !put(&out,0x290,0)||!put(&out,0x294,0)||!put(&out,0x298,0)||
           !put(&out,0x29c,0)) return 0;
        *wire=out; return 1;
    }
    if(!hand || hand->time<-32768 || hand->time>32767 || hand->delay<-32768 ||
       hand->delay>32767 || hand->restrict_time<-32768 || hand->restrict_time>32767 ||
       hand->shot_count>7 || hand->fresh_pull>1) return 0;
    if(!translate_hand_phase(hand->state,hand->animation,&state,&animation)) return 0;
    /* The three-bit counter at +0x280 + hand*0x1c: C1 clears this hand's copy
     * when a reload opens (0x419576) and its burst helper tests it at 0x41aab5.
     * The one-bit flag at +0x27c + hand*0x1c is that hand's fresh trigger
     * pull, armed by C1 at 0x41ab10 and read back at 0x41adc9. */
    if(!put(&out,0x284,animation)||!put(&out,0x288,(uint32_t)hand->time)||
       !put(&out,0x28c,(uint32_t)hand->delay)||!put(&out,0x290,(uint32_t)hand->restrict_time)||
       !put(&out,0x294,state)||!put(&out,0x298,hand->fresh_pull)||
       !put(&out,0x29c,hand->shot_count)) return 0;
    *wire=out; return 1;
}
int CODOL_OverlayEngineWeaponSwitchControl(codol_player_fields_t *wire,const playerState_t *ps)
{
    unsigned i;
    if(!wire || !ps) return 0;
    for(i=0;i<CODOL_PLAYER_FIELDS;++i) if(CODOL_PlayerField(i)->offset==0x344) {
        /* C1 480f37/4817af reject selection for mask 0x880: global disable
         * plus the IW4-compatible weapon-switch restriction. */
        wire->field[i]=(wire->field[i]&~UINT32_C(0x800)) |
            ((ps->weapFlags&CODOL_WEAP_SWITCH_DISABLED) ? UINT32_C(0x800) : 0);
        return 1;
    }
    return 0;
}
int CODOL_OverlayEngineWeaponUseControl(codol_player_fields_t *wire,const playerState_t *ps)
{
    unsigned i;
    if(!wire || !ps) return 0;
    for(i=0;i<CODOL_PLAYER_FIELDS;++i) if(CODOL_PlayerField(i)->offset==0x344) {
        /* C1 41a7b0 consumes bit 1 as a reload request, exactly like the
         * retained PM_Weapon_CheckForReload_20. C1 41bc00/41ca9d gate
         * main/offhand weapon actions with the shared global-disable bit.
         * Bit 4 is PWF_HOLDING_BREATH (C1 PM_UpdateHoldBreath 0x418945, HUD
         * breath hint 0x45765c) and bits 8/0x10 are the crosshair friendly/
         * enemy flags CG_GetCrosshairColor reads at 0x43c509/0x43c546; all
         * three carry the same bit numbers in the retained producers
         * (_bg_weapons.asm PM_Weapon_70, codol_lookat.c). */
        wire->field[i]=(wire->field[i]&~UINT32_C(0x9d))|((uint32_t)ps->weapFlags&UINT32_C(0x9d));
        /* C1 CG weapon-pickup hint 0x481105..0x48113b is suppressed by bit
         * 0x100000 (disableWeaponPickup 0x5145c3 / enableWeaponPickup
         * 0x5145dc); the native bit has the same number. C1 PM 0x41979a sets
         * bit 0x1000 while the incoming weapon's def+0x340 == 3 (riot shield)
         * and G_UpdateClientState 0x50d1a6 mirrors it to clientState 0x01c;
         * the native producer keeps it at 0x200000 (0x1000 is the offhand
         * disable there). */
        wire->field[i]=(wire->field[i]&~UINT32_C(0x101000)) |
            ((ps->weapFlags&CODOL_WEAP_PICKUP_DISABLED) ? UINT32_C(0x100000) : 0) |
            ((ps->weapFlags&CODOL_WEAP_RIOTSHIELD_NEXT) ? UINT32_C(0x1000) : 0);
        /* C1 keeps the armed barrel of a double-barrel weapon in this word
         * at bit 0x100 (written 0x41bad9/0x41bae5, read 0x41ae4e). The
         * retained weapFlags uses that bit number for its own fresh-pull
         * latch, which publishes to ps+0x27c instead, so the value here comes
         * from the hand bundle and never from ps->weapFlags. Without it the
         * client's armed barrel is reset by every snapshot and the second
         * trigger can never release its pin. */
        wire->field[i]=(wire->field[i]&~UINT32_C(0x100)) |
            (CODOL_WeaponStateSecondBarrelArmed(ps) ? UINT32_C(0x100) : 0);
        /* Crosshair bits as they leave for the wire, on transition only. */
        {
            static uint32_t last[64]; static int lines;
            unsigned c=(unsigned)ps->clientNum;
            if(CODOL_TRACE_ON() && c<64 && lines<400 && (wire->field[i]&0x18u)!=(last[c]&0x18u)) {
                last[c]=wire->field[i]; ++lines;
                Com_Printf(CON_CHANNEL_SERVER,"CoDOL crosshair wire: client %u netfield(0x344) 0x%x weapFlags 0x%x\n",
                    c,(unsigned)wire->field[i],(unsigned)ps->weapFlags);
            }
        }
        return 1;
    }
    return 0;
}
int CODOL_OverlayEngineOffhandControl(codol_player_fields_t *wire,const playerState_t *ps)
{
    unsigned i;
    if(!wire || !ps) return 0;
    for(i=0;i<CODOL_PLAYER_FIELDS;++i) if(CODOL_PlayerField(i)->offset==0x344) {
        /* C1 41c5a0 tests these separate frag/tactical/special restrictions. */
        wire->field[i]=(wire->field[i]&~UINT32_C(0xe0000)) |
            ((ps->weapFlags&CODOL_WEAP_OFFHAND_DISABLED) ? UINT32_C(0xe0000) : 0);
        return 1;
    }
    return 0;
}

int CODOL_OverlayEngineInventory(codol_player_array_updates_t *updates, const playerState_t *ps,
                                const uint32_t used_before[CODOL_WEAPON_BIT_WORDS])
{
    codol_player_array_updates_t out;
    unsigned weapon, slot = 0;
    if (!updates || !ps || CODOL_WeaponBitsOwned(ps, 0)) return 0; /* null weapon cannot be owned */
    out = *updates;
    memset(out.weapon_index, 0, sizeof(out.weapon_index));
    memset(out.weapon_flags, 0, sizeof(out.weapon_flags));
    /* Omission means inheritance in this section, so send all fifteen slots,
     * including explicit index-zero/flags-zero records for inventory removals. */
    out.weapons_mask = out.weapon_index_mask = 0x7fff;
    for (weapon = 1; weapon < CODOL_WEAPON_SLOTS; ++weapon) {
        int mapped;
        if (!CODOL_WeaponBitsOwned(ps, weapon)) continue;
        if (slot == 15 || (mapped = CODOL_WeaponToWire(weapon)) < 0) return 0;
        out.weapon_index[slot] = mapped;
        out.weapon_flags[slot] = used_before &&
            (used_before[weapon >> 5] & (UINT32_C(1) << (weapon & 31))) ? 1 : 0;
        /* Bit 1 is the record's byte 1, IW4's PlayerEquippedWeaponState
         * dualWielding (C1 reader 5a1ee6 `mov [ebx+1],dl`). C1 dual-wields
         * only when this byte AND the definition's +0xbd5 are both set:
         * BG_IsDualWielding 417f69/417f6f, BG_GetLastWeaponHand 422961/422967
         * (the PM_Weapon hand loop 41dc2d and the CG viewmodel hand loop
         * bound 480a43) and PM weapon change 419d4b/419d51, which derives
         * ps+0x35c from them on every predicted switch. With it clear the
         * client draws one gun and predicts one hand, so the attack-2
         * trigger is run as ADS while the server fires the second hand.
         * The server's own machine (CODOL_WeaponIsDualWield) keys on the
         * definition byte alone, so publish exactly that per owned weapon,
         * before it is raised, which is when C1 reads it. */
        if(CODOL_WeaponIsDualWield(weapon))
            out.weapon_flags[slot] |= 2u;
        if(weapon < CODOL_PS_EXT_WEAPON_BITS &&
           (CODOL_PlayerStateHandRead(ps)->fast_mag[weapon>>5] &
            (UINT32_C(1)<<(weapon&31)))) out.weapon_flags[slot] |= 4u;
        /* C1 5a1ebd..5a1f04 reads five individual bits into the inventory
         * record's five bytes. PM_CheckForRechamber 418fa3 reads byte3 for
         * hand0 (byte4 for hand1), clearing it only when the bolt delay
         * completes at 418fce. The retained primary's per-weapon bitset is
         * set when firing and cleared by its delayed rechamber/reload.
         * Omitting it cancels the client's pending bolt/pump on every snap. */
        if(CODOL_WeaponBitsRechamberTest(ps, weapon))
            out.weapon_flags[slot] |= 8u;
        /* Read the captured playerState, never the live per-client machine. */
        /* The hand bundle's latch is CODOL_PS_EXT_WEAPON_BITS wide, the same
         * CODOL_WEAPON_SLOTS this scan runs to; the guard only documents that
         * an index past the latch has no second-hand latch rather than a read
         * past the array. */
        if(weapon < CODOL_PS_EXT_WEAPON_BITS &&
           (CODOL_PlayerStateHandRead(ps)->second_rechamber[weapon>>5] &
            (UINT32_C(1)<<(weapon&31)))) out.weapon_flags[slot] |= 16u;
        ++slot;
    }
    *updates = out; return 1;
}

int CODOL_BuildEngineAmmoBindings(codol_engine_player_bindings_t *out,const playerState_t *ps,
    const codol_weapon_registry_t *registry,struct WeaponDef *const definitions[CODOL_WEAPON_SLOTS])
{
    codol_engine_player_bindings_t next;
    unsigned weapon,i,clip_count=0,reserve_count=0,owned=0;
    if(!out || !ps || !registry || !definitions || CODOL_WeaponBitsOwned(ps,0)) return 0;
    next=*out;
    for(i=0;i<16;++i) { next.clips[i]=(codol_ammo_binding_t){-1,-1,-1}; next.reserves[i]=(codol_ammo_binding_t){-1,0,-1}; }
    next.clip_mask=next.reserve_mask=0x7fff;
    for(weapon=1;weapon<CODOL_WEAPON_SLOTS;++weapon) {
        const struct WeaponDef *def; int wire,ammo,clip;
        if(!CODOL_WeaponBitsOwned(ps,weapon)) continue;
        if(++owned>15 || !(def=definitions[weapon]) || (wire=CODOL_WeaponToWire(weapon))<0 ||
           !CODOL_GetWeaponKeys(registry,(unsigned)wire,&ammo,&clip) ||
           def->iAmmoIndex<0 || def->iAmmoIndex>=128 ||
           (clip>=0 && (def->iClipIndex<0 || def->iClipIndex>=128))) return 0;
        for(i=0;i<reserve_count;++i) if(next.reserves[i].wire_key==ammo) break;
        if(i<reserve_count) { if(next.reserves[i].engine_index!=def->iAmmoIndex) return 0; }
        else next.reserves[reserve_count++]=(codol_ammo_binding_t){def->iAmmoIndex,ammo,-1};
        if(clip<0) {
            /* No clip key: C1 0x41f3f0 gives an unlimited-ammo definition
             * (def+0x560, minigun_zm) clip index -1, yet its server still
             * records the magazine under that -1 through the find-or-allocate
             * 0x41e360 (setweaponammoclip 0x5147a0, ammo init 0x527919). The
             * client needs that record: PmoveSingle raises the firing marker
             * eFlags 0x200 (0x4162c6) only when 0x415f20 finds a record keyed
             * def+0x570 holding rounds, and CG_Player's spin-up update
             * (0x484ff0/0x484dd0) spins the barrel and starts fireLoopSound
             * from that bit. Unbound slots also read back as key -1 (1023 on
             * the wire, 0x5a1ded), with no rounds, so the record must sit in a
             * bound slot ahead of them. The engine still keeps this weapon's
             * magazine at iClipIndex; publish it there once. */
            if(def->iClipIndex<0 || def->iClipIndex>=128) continue;
            for(i=0;i<clip_count;++i) if(next.clips[i].wire_key==-1) break;
            if(i==clip_count) next.clips[clip_count++]=(codol_ammo_binding_t){def->iClipIndex,-1,-1};
            continue;
        }
        for(i=0;i<clip_count;++i) if(next.clips[i].wire_key==clip) break;
        if(i<clip_count) { if(next.clips[i].engine_index!=def->iClipIndex) return 0; }
        else next.clips[clip_count++]=(codol_ammo_binding_t){def->iClipIndex,clip,-1};
    }
    *out=next; return 1;
}

int CODOL_OverlayEngineAmmo(codol_player_array_updates_t *updates, const playerState_t *ps,
                           uint16_t clip_mask, const codol_ammo_binding_t clips[16],
                           uint16_t reserve_mask, const codol_ammo_binding_t reserves[16])
{
    codol_player_array_updates_t out;
    unsigned i;
    if (!updates || !ps || (clip_mask && !clips) || (reserve_mask && !reserves)) return 0;
    out = *updates;
    for (i = 0; i < 16; ++i) {
        if (clip_mask & (1u << i)) {
            int index = clips[i].engine_index, key = clips[i].wire_key, count;
            int left = clips[i].left_ammo;
            if(left < -1) return 0;
            if(left == -1) left = 0;
            /* key -1 with an engine index is the unlimited-ammo record
             * (CODOL_BuildEngineAmmoBindings); -1/-1 is an unbound slot. */
            if (index < -1 || index >= 128 || key < -1 || key > 1022) return 0;
            count = index == -1 ? 0 : ps->ammoclip[index];
            if (count < 0 || count > 511 || left > 511 || (index == -1 && left)) return 0;
            out.clip_index[i] = key;
            /* Both hands are always published so an old CoDOL off-hand count
             * cannot survive a weapon or slot change. The second magazine
             * comes from the caller's per-hand weapon state; a single-hand
             * weapon binds -1 and publishes zero. */
            out.clip_presence[i] = 3;
            out.clip_ammo[i][0] = count; out.clip_ammo[i][1] = left;
        }
        if (reserve_mask & (1u << i)) {
            int index = reserves[i].engine_index, key = reserves[i].wire_key, count;
            if (index < -1 || index >= 128 || key < 0 || key > 1023) return 0;
            count = index == -1 ? 0 : ps->ammo[index];
            if (count < 0 || count > 2047) return 0;
            out.reserve_type[i] = key; out.reserve_ammo[i] = count;
        }
    }
    out.clip_mask |= clip_mask; out.reserve_mask |= reserve_mask;
    *updates = out; return 1;
}

static int put_client(codol_client_state_t *out, unsigned offset, uint32_t value)
{
    unsigned i;
    for (i = 0; i < CODOL_CLIENT_FIELDS; ++i)
        if (CODOL_ClientField(i)->offset == offset) { out->field[i] = value; return 1; }
    return 0;
}
int CODOL_OverlayEngineClient(codol_client_state_t *wire, const clientState_t *cs,
                             const codol_client_assets_t *assets)
{
    codol_client_state_t out;
    unsigned i, team, vehicle;
    if (!wire || !cs || !assets || cs->clientIndex < 0 || cs->clientIndex >= 32 ||
        cs->modelindex < 0 || assets->model >= 2048 || (!!cs->modelindex != !!assets->model)) return 0;
    if(cs->attachedVehEntNum<0 || cs->attachedVehEntNum>ENTITYNUM_NONE || cs->attachedVehEntNum==ENTITYNUM_WORLD) return 0;
    /* Native ClientEndFrame writes ownerNum-1 or ENTITYNUM_NONE (2047).
     * C1 50d4f4..50d55f writes the same owner entity or 2047 to cs+bc.
     * The native ride-slot index is a separate, not yet mapped property. */
    vehicle=(unsigned)cs->attachedVehEntNum;
    switch (cs->team) {
    case TEAM_FREE: team = 0; break;
    case TEAM_RED: team = 1; break;
    case TEAM_BLUE: team = 2; break;
    /* C1 team getter50e080 reads clientState+4 (gclient346c): jump-table
     * entry6 returns spectator. Entry3 has no team string. ClientState base
     * 3468 is independently used as the CS[1280+clientIndex] key50e933.
     * The team netfield is three bits, unlike the head-icon team field. */
    case TEAM_SPECTATOR: team = 6; break;
    default: return 0;
    }
    out = *wire; out.number = cs->clientIndex;
    if (!put_client(&out, 0x004, team) || !put_client(&out, 0x014, assets->model) ||
        !put_client(&out,0x0bc,vehicle)) return 0;
    /* Third-person animation conditions (C1 BG 0x407184..0x4071b7 copies
     * ci+0xb14/0xb18/0xb1c into the akimbo/dive/shield condition slots) plus
     * the rider vehicle entity and colour selector. Widths: 1/1/4/11/8. */
    if(assets->dual_wield>1 || assets->riot_shield_next>1 || assets->dive_state>15 ||
       assets->vehicle_entity>=2047 || assets->colour_index>255) return 0;
    if(!put_client(&out,0x018,assets->dual_wield) || !put_client(&out,0x01c,assets->riot_shield_next) ||
       !put_client(&out,0x0a8,assets->dive_state) || !put_client(&out,0x12c,assets->vehicle_entity) ||
       !put_client(&out,0x134,assets->colour_index)) return 0;
    if(assets->action_slot_help>7 || !put_client(&out,0x010,assets->action_slot_help)) return 0;
    {
        static uint32_t last[32]; static int lines;
        unsigned c=(unsigned)cs->clientIndex;
        uint32_t key=0x80000000u|assets->dual_wield|(assets->riot_shield_next<<1)|(assets->dive_state<<2)|
            (assets->vehicle_entity<<6)|(assets->colour_index<<17);
        if(CODOL_TRACE_ON() && c<32 && lines<400 && key!=last[c]) {
            last[c]=key; ++lines;
            Com_Printf(CON_CHANNEL_SERVER,"CoDOL cs: client %u dualWielding %u riotShieldNext %u diveState %u vehicleEnt %u colour %u\n",
                c,assets->dual_wield,assets->riot_shield_next,assets->dive_state,assets->vehicle_entity,assets->colour_index);
        }
    }
    for (i = 0; i < 16; ++i) {
        unsigned model = 0, tag = 0;
        if (i < 6) {
            model = assets->attach_model[i]; tag = assets->attach_tag[i];
            if (cs->attachModelIndex[i] < 0 || cs->attachTagIndex[i] < 0 ||
                model >= 2048 || tag >= 64 ||
                (!!cs->attachModelIndex[i] != !!model) || (!!cs->attachTagIndex[i] != !!tag) ||
                (!model && tag)) return 0;
        }
        if (!put_client(&out, 0x020+4*i, model) || !put_client(&out, 0x060+4*i, tag)) return 0;
    }
    /* Rank and prestige. clientState +0xA0 is the scoreboard's rank column:
     * C1 copies it at 0x46c964 into clientInfo+0x60, and the playercard row
     * builder (0x68e7d0) reads clientInfo+0x60 into card row +0x14. +0xA4 is
     * copied alongside it into clientInfo+0x64 and card row +0x18, is likewise
     * eight bits, and is prestige by position and by IW4's ordering.
     * SetRank produces these fields in clientState (native +305c/+3060;
     * C1 rank writer 51dd18 -> client+3508). Publish the supplied captured
     * state, including archived killcam states. The IW4-only profile store
     * is not authoritative: C1 declares rank itself, so that legacy lookup
     * can be absent even when SetRank has already produced a valid rank. */
    if (!put_client(&out, 0x0a0, codol_field_bits(cs->rank, 8)) ||
        !put_client(&out, 0x0a4, codol_field_bits(cs->prestige, 8))) return 0;
    /* netname belongs to CS[1280+clientIndex]. Never copy it to 0xC0..0xCC:
     * those are CoDOL perk masks. The vehicle-seat fields still need their own map. */
    *wire = out; return 1;
}

static int put_entity(codol_entity_state_t *out, unsigned offset, uint32_t value)
{
    unsigned i;
    for (i = 0; i < CODOL_ENTITY_FIELDS; ++i)
        if (CODOL_EntityField(out->type, i)->offset == offset) { out->field[i] = value; return 1; }
    return 0;
}
static int entity_float(codol_entity_state_t *out, unsigned offset, float value)
{
    uint32_t word;
    if (!isfinite(value)) return 0;
    memcpy(&word, &value, sizeof(word));
    return put_entity(out, offset, word);
}
int CODOL_OverlayEngineEffectEvent(codol_entity_state_t *wire,const entityState_t *es,unsigned effect)
{
    if(!wire || !es || es->eType!=ET_EVENTS+EV_PLAY_FX ||
       CODOL_EntityTypeToWire(es->eType)!=(int)wire->type || !effect || effect>=320) return 0;
    /* Retained Scr_PlayFX stores the effect index in eventParm (+9c).
     * C1 helper543a70 creates event87 at543ad4 then writes the selector
     * to entity+ac at543ae2. Client consumer444f10 reads centity+190
     * (nextState+ac), accepts1..319 at444f26..444f30 and indexes the
     * complete effect array16d9c88 at444f36. Preserve the mapped ID's
     * full width despite the stock script producer's byte conversion.
     * Angles/position remain trajectory fields. */
    return put_entity(wire,0x0ac,effect);
}
/* Generic event temp entity: the translated parameter in +0xac (11 bits). */
int CODOL_OverlayEngineEventParameter(codol_entity_state_t *wire,unsigned parameter)
{
    if(!wire || parameter>2047) return 0;
    return put_entity(wire,0x0ac,parameter);
}
/* Melee hit/miss temp entity. C1's own producer (the server half of C1.exe,
 * 0x573c98..0x573ce1) creates event 52 (character struck) or 53 (anything
 * else) at the trace end and writes the struck entity's number to +80
 * (0x573cab/0x573cad), the attacker's weapon word to +d4 (0x573cb3/0x573cc1)
 * and its weapon-model byte to +e6 (0x573cdb/0x573ce1). The client plays the
 * hit on that entity: its event-52 handler loads [es+80] into eax and calls
 * CG_PlayEntitySoundAlias 0x44f4c0 with melee_hit (0x8430da3..0x8478812),
 * and the knife and shield variants read [es+80] the same way (0x839ea5a,
 * 0x8351656); 0x44f4c0 positions the sound at cg_entities[n].lerpOrigin.
 * Leaving +80 unset published entity 0, so every client heard every knife
 * hit at player 0 - for the host, on top of themselves wherever they were.
 * The retained Weapon_Melee_internal keeps the struck entity in
 * otherEntityNum and the weapon pair in weapon/weaponModel, as IW3 does. */
/* The mp/coKnifeStatsTable.csv row every player carries (ps+0x338, and
 * es+0x64 for everyone else): zknife_standard (13) in zombies, none in mp and
 * coop until the loadout melee choice is wired through. One rule for the
 * playerstate and the melee event, so the two cannot disagree. */
unsigned CODOL_ServerMeleeRow(void)
{
    const char *zone = CODOL_ServerZoneType();
    return (zone && zone[0]=='z' && zone[1]=='m' && !zone[2]) ? 13u : 0u;
}
int CODOL_OverlayEngineMeleeEvent(codol_entity_state_t *wire,const entityState_t *es)
{
    codol_entity_state_t out;
    unsigned i,found=0;
    int weapon;
    /* +d6 is the attacker's knife row: C1 0x573cc8..0x573cd4 copies the
     * attacker's es+64 there when the attacker is a player with a row, zero
     * otherwise, and the event-52 handler reads it back (0x84b81c9 movzx
     * [es+d6], then the same (row-1)*0x5c+0x150e210 lookup), whose columns
     * 17..20 are the row's own melee sounds. CODOL_MeleeHitEvent captures it
     * in un2. */
    if(!wire || !es || (es->eType!=ET_EVENTS+EV_MELEE_HIT && es->eType!=ET_EVENTS+EV_MELEE_MISS) ||
       CODOL_EntityTypeToWire(es->eType)!=(int)wire->type ||
       es->otherEntityNum<0 || es->otherEntityNum>ENTITYNUM_NONE ||
       (unsigned)es->weaponModel>15 || (unsigned)es->un2>65535u) return 0;
    /* The struck entity is what places the sound; the weapon only refines
     * it. An attacker whose weapon has no wire slot (an actor's bite)
     * publishes no weapon rather than losing the hit. */
    weapon=CODOL_WeaponToWire((unsigned)es->weapon);
    if(weapon<0 || weapon>65535) weapon=0;
    out=*wire;
    if(!put_entity(&out,0x080,(uint32_t)es->otherEntityNum)) return 0;
    for(i=0;i<CODOL_ENTITY_FIELDS;++i) {
        const codol_entity_field_t *field=CODOL_EntityField(out.type,i);
        if(!field) continue;
        if(field->offset==0x0d4) {
            out.field[i]=((unsigned)es->un2<<16)|(unsigned)weapon;
            found|=1;
        } else if(field->offset==0x0e4) {
            out.field[i]=(out.field[i]&UINT32_C(0xff00ffff))|
                ((unsigned)es->weaponModel<<16);
            found|=2;
        }
    }
    if(found!=3) return 0;
    *wire=out; return 1;
}
/* Bullet hit temp entities. C1's own producer, in its finishPlayerDamage
 * (0x51bf79..0x51c074), queues two events for a bullet that hits a player:
 *   EV_BULLET_HIT (60) for everyone but the victim - weapon word +d4
 *     (0x51bf98), DirToByte(dir) +ac (0x51bfb2), surface 7 flesh +90
 *     (0x51bfbb), the retained flag +e0 (0x51bfc5), the SHOOTER's entity
 *     number +80 (0x51bfcd) and the victim's +88 (0x51bfd5);
 *   EV_BULLET_HIT_CLIENT_SMALL/LARGE (63/64) for the victim only - weapon
 *     +d4 (0x51c018), surface +90 (0x51c01f), shooter +80 (0x51c02b) and
 *     the victim's client number +9c (0x51c03d).
 * The retained producers keep the same values natively: shooter in
 * otherEntityNum, surface in surfType, weapon, the flag in un1, the client
 * number in clientNum, and CODOL_SERVER stores the victim + 1 in un2
 * (_g_client_script_cmd_mp.asm). Only the direction byte used to reach the
 * wire, so C1 took every impact as flesh-less surface 0 fired by entity 0. */
int CODOL_OverlayEngineBulletHit(codol_entity_state_t *wire,const entityState_t *es)
{
    codol_entity_state_t out;
    unsigned i,found=0;
    int weapon;
    int client_hit=es && (es->eType==ET_EVENTS+EV_BULLET_HIT_CLIENT_SMALL ||
                          es->eType==ET_EVENTS+EV_BULLET_HIT_CLIENT_LARGE);
    if(!wire || !es || (es->eType!=ET_EVENTS+EV_BULLET_HIT && !client_hit) ||
       CODOL_EntityTypeToWire(es->eType)!=(int)wire->type ||
       es->otherEntityNum<0 || es->otherEntityNum>ENTITYNUM_NONE ||
       (unsigned)es->surfType>31) return 0;
    if(client_hit && (es->clientNum<0 || es->clientNum>=64)) return 0;
    if(!client_hit && ((unsigned)es->un1.helicopterStage>255 ||
       (es->un2 && (es->un2<1 || es->un2>ENTITYNUM_NONE+1)))) return 0;
    weapon=CODOL_WeaponToWire((unsigned)es->weapon);
    if(weapon<0 || weapon>65535) weapon=0;
    out=*wire;
    if(!put_entity(&out,0x080,(uint32_t)es->otherEntityNum) ||
       !put_entity(&out,0x090,(uint32_t)es->surfType)) return 0;
    if(client_hit) {
        if(!put_entity(&out,0x09c,(uint32_t)es->clientNum)) return 0;
    } else {
        if(!put_entity(&out,0x0e0,(uint32_t)es->un1.helicopterStage)) return 0;
        if(es->un2 && !put_entity(&out,0x088,(uint32_t)(es->un2-1))) return 0;
    }
    for(i=0;i<CODOL_ENTITY_FIELDS;++i) {
        const codol_entity_field_t *field=CODOL_EntityField(out.type,i);
        if(field && field->offset==0x0d4) {
            out.field[i]=(out.field[i]&UINT32_C(0xffff0000))|(unsigned)weapon;
            found=1;
        }
    }
    if(!found) return 0;
    *wire=out; return 1;
}
int CODOL_OverlayEngineTriggeredEffect(codol_entity_state_t *wire,const entityState_t *es,unsigned effect)
{
    codol_entity_state_t out;
    if(!wire || !es || es->eType!=ET_FX || wire->type!=ET_FX || !effect || effect>255) return 0;
    out=*wire;
    /* Retained SpawnFX sets type8 and un1's effect ID; TriggerFX writes
     * time2. C1 client442510 compares centity+160 (nextState+7c) to its
     * last-play stamp+40, then calls4423d0 with that trigger time442536.
     * The effect helper reads nextState+e0 at4423fa. An untouched zero
     * stamp remains dormant; preserve explicit script times verbatim. */
    if(!put_entity(&out,0x0e0,effect) || !put_entity(&out,0x07c,(uint32_t)es->time2)) return 0;
    *wire=out; return 1;
}
/* C1 is client and server in one binary, so its own producer defines this
 * wire contract. The helper behind playsoundatpos writes the registered
 * alias index to entityState +ac at 0x54d038 and the unowned sentinel 2046
 * to +80 at 0x54d03e; its entity-origin variant writes the same index at
 * 0x54d1d4 and the emitting entity number at 0x54d1de. Both wire fields are
 * eleven bits wide in the shared event table, so the byte-wide sound bank
 * and a 1022-entity world both fit; the six-bit +9c field could not carry
 * either. The alias name reaches the client through the sound bank the
 * asset publisher mirrors at CS 3395+index.
 * owner uses the engine-side convention of codol_script_sound.h: zero for an
 * unowned sound, entity number plus one otherwise, because retained
 * producers leave otherEntityNum zeroed and entity 0 is a real player. */
int CODOL_OverlayEngineSoundEvent(codol_entity_state_t *wire,const entityState_t *es,
                                  unsigned sound,unsigned owner)
{
    codol_entity_state_t out;
    if(!wire || !es || (es->eType!=ET_EVENTS+EV_SOUND_ALIAS &&
        es->eType!=ET_EVENTS+EV_SOUND_ALIAS_AS_MASTER) ||
       CODOL_EntityTypeToWire(es->eType)!=(int)wire->type ||
       !sound || sound>255 || owner>ENTITYNUM_WORLD) return 0;
    out=*wire;
    if(!put_entity(&out,0x0ac,sound) ||
       !put_entity(&out,0x080,owner ? owner-1 : ENTITYNUM_WORLD)) return 0;
    *wire=out; return 1;
}
int CODOL_OverlayEngineLoopEffect(codol_entity_state_t *wire,const entityState_t *es,unsigned effect)
{
    codol_entity_state_t out;
    if(!wire || !es || es->eType!=ET_LOOP_FX || wire->type!=ET_LOOP_FX ||
       !effect || effect>255 || es->lerp.u.loopFx.period<=0) return 0;
    out=*wire;
    /* Client loop reader442560 loads cull distance at centity+13c
     * (nextState+58), squares it for the distance check442601..44260c,
     * then loads INTEGER period at+140 (nextState+5c) at442616 and adds
     * it to the next-play time44263a/44265c. Use these consumer semantics:
     * the stock script producer562d9e/562da1 writes conflicting values.
     * Effect reader4423d0 loads centity+1c4 (nextState+e0) at4423fa and
     * indexes the effect array44242d. Type9 netfields are float/32/8 bits.
     * Native storage keeps effect in un1 (+d4), cull at54, period at58.
     * A positive period is essential: the client's catch-up loop repeatedly
     * adds it until the next-play time exceeds the current time. */
    if(!put_entity(&out,0x0e0,effect) ||
       !entity_float(&out,0x058,es->lerp.u.loopFx.cullDist) ||
       !put_entity(&out,0x05c,(uint32_t)es->lerp.u.loopFx.period)) return 0;
    *wire=out; return 1;
}
int CODOL_OverlayEnginePlane(codol_entity_state_t *wire,const entityState_t *es,unsigned model)
{
    codol_entity_state_t out;
    if(!wire || !es || wire->type!=ET_PLANE || es->eType!=ET_PLANE ||
       (unsigned)es->lerp.u.plane.ownerClient>=64 ||
       (unsigned)es->lerp.u.plane.enemyIcon>15 ||
       (unsigned)es->lerp.u.plane.friendlyIcon>15 || model>=2048 ||
       (!!es->index!=!!model))return 0;
    out=*wire;
    /* C1 spawnplane54c8ee..54c8f4. These three words are captured in the
     * existing native plane archive anonymous.data[0..2], never live lookup. */
    if(!put_entity(&out,0x058,(unsigned)es->lerp.u.plane.ownerClient) ||
       !put_entity(&out,0x05c,(unsigned)es->lerp.u.plane.enemyIcon) ||
       !put_entity(&out,0x060,(unsigned)es->lerp.u.plane.friendlyIcon) ||
       !put_entity(&out,0x098,model))return 0;
    *wire=out;return 1;
}
/* C1 script movers carry the entity whose decals they inherit at +58
 * (11 bits; LerpEntityStateScriptMover.entToTakeMarksFrom in IW4). C1's own
 * script-mover init 0x567960 stores 0x7ff (ENTITYNUM_NONE) there next to
 * eType 6, and CG's entity reset 0x46ba24..0x46ba48 calls
 * CG_TransferDObjMarksToScriptMover 0x46b610 for any other value. Left at
 * the zero default, every mover entering a snapshot asked the client to move
 * entity 0's marks onto it ("couldn't transfer from ent #0", or
 * FX_TransferDObjMarksFromEntToEnt matching a crate model against player 0's
 * DObj). No script here implements transferMarksToNewScriptModel, so the
 * field is always none. */
#define CODOL_SCRIPTMOVER_NO_MARK_SOURCE 0x7ffu
int CODOL_OverlayEngineModelEntity(codol_entity_state_t *wire,const entityState_t *es,
                                   unsigned model,int brush_model)
{
    codol_entity_state_t out;
    unsigned entry,tree;
    if(!wire || !es || brush_model || es->solid==SOLID_BMODEL || model>=2048 ||
       (!!es->index!=!!model) || (es->eType!=ET_GENERAL && es->eType!=ET_SCRIPTMOVER) ||
       wire->type!=(unsigned)es->eType) return 0;
    /* Retained G_DObjUpdate_170 writes the model index at native +88.
     * C1 ordinary script movers use their lerp-union model selector +5c:
     * 43e80f reads centity+140, then43e97a resolves cgs.models[selector].
     * General entities instead read +98 at43e96e. Brush movers have their
     * own +98 inline-model publication below, never this DObj path. */
    out=*wire;
    if(!put_entity(&out,es->eType==ET_SCRIPTMOVER ? 0x05c : 0x098,model)) return 0;
    if(es->eType==ET_SCRIPTMOVER) {
        if(!put_entity(&out,0x058,CODOL_SCRIPTMOVER_NO_MARK_SOURCE)) return 0;
        /* C1 570b0a publishes the full weapon index at +68 on the linked
         * script_model; 43e83a/43e619 use it for the composed world gun.
         * Native anonymous.data[4] is already preserved by mover archives. */
        int weapon=CODOL_WeaponToWire((unsigned)es->lerp.u.scriptMover.weaponIndex);
        if(weapon<0 || !put_entity(&out,0x068,(unsigned)weapon)) return 0;
    }
    if(CODOL_EntityStateModelAnim(es,&entry,&tree)) {
        /* Captured tree/index belong to this snapshot's state. C1's direct
         * play arm43fd14 requires timestamp06c zero, including explicit clear. */
        if(!put_entity(&out,0x060,entry) || !put_entity(&out,0x094,tree) ||
           !put_entity(&out,0x06c,0)) return 0;
    }
    *wire=out; return 1;
}
int CODOL_OverlayObituary(codol_entity_state_t *wire,const entityState_t *state)
{
    codol_entity_state_t out;
    unsigned victim,attacker,code;
    if(!wire || wire->type!=128 ||
       !CODOL_DecodeObituary(state,&victim,&attacker,&code)) return 0;
    out=*wire;
    if(!put_entity(&out,0x080,victim) || !put_entity(&out,0x084,attacker) ||
       !put_entity(&out,0x0ac,code&255u) || !put_entity(&out,0x0e0,(code>>8)&255u)) return 0;
    *wire=out;
    return 1;
}
int CODOL_OverlayEngineBrushEntity(codol_entity_state_t *wire,const entityState_t *es,unsigned model_count)
{
    codol_entity_state_t out;
    if(!wire || !es || (es->eType!=ET_GENERAL && es->eType!=ET_SCRIPTMOVER) ||
       wire->type!=(unsigned)es->eType || es->solid!=SOLID_BMODEL ||
       !es->index || (unsigned)es->index>=model_count || (unsigned)es->index>=2048) return 0;
    out=*wire;
    /* C1 model-prefix parser 0x56acf9 and link routine 0x5d881c.
     * The selector is a map inline-model index, not a CS_MODELS slot. */
    if(!put_entity(&out,0x098,(unsigned)es->index) ||
       !put_entity(&out,0x0a8,0xffffff)) return 0;
    if(es->eType==ET_SCRIPTMOVER &&
       !put_entity(&out,0x058,CODOL_SCRIPTMOVER_NO_MARK_SOURCE)) return 0;
    *wire=out; return 1;
}
int CODOL_ResolveEngineEntityEventParameters(const entityState_t *es,uint32_t out[4])
{
    uint32_t events[4],parameters[4];
    if(!es) return 0;
    memcpy(events,es->events,sizeof(events)); memcpy(parameters,es->eventParms,sizeof(parameters));
    return CODOL_ResolveEventParameters(events,parameters,out);
}
int CODOL_ResolveEnginePlayerEventParameters(const playerState_t *ps,uint32_t out[4])
{
    uint32_t events[4],parameters[4];
    if(!ps) return 0;
    memcpy(events,ps->events,sizeof(events)); memcpy(parameters,ps->eventParms,sizeof(parameters));
    return CODOL_ResolveEventParameters(events,parameters,out);
}
int CODOL_ResolveEnginePlayerEventParametersVisible(const playerState_t *ps,uint32_t out[4],
                                                     unsigned *visibleSlots)
{
    uint32_t result[4],events[4],parameters[4];
    unsigned visible=0,i;
    if(!ps || !out || !visibleSlots) return 0;
    memcpy(events,ps->events,sizeof(events));
    memcpy(parameters,ps->eventParms,sizeof(parameters));
    for(i=0;i<4;++i) {
        if(CODOL_EventToWire(events[i])>=0 &&
           CODOL_EventParameterToWire(events[i],parameters[i],result+i)==1) {
            visible|=1u<<i;
        } else {
            result[i]=0;
        }
    }
    memcpy(out,result,sizeof(result));
    *visibleSlots=visible;
    return 1;
}
int CODOL_OverlayEngineSpinUpCharge(codol_player_fields_t *wire,float charge)
{
    codol_player_fields_t out;
    if(!wire || !(charge>=0.0f) || charge>1.0f) return 0;
    out=*wire;
    /* Wire field 171. C1 clamps the same value to 0..1 at 0x418456. */
    if(!put_float(&out,0x5c0,charge)) return 0;
    *wire=out; return 1;
}
int CODOL_OverlayEnginePlayerEventsWithShotsVisible(codol_player_fields_t *wire,const playerState_t *ps,
                                   const uint32_t parameters[4],const codol_engine_shot_record_t shots[4],
                                   unsigned visibleSlots)
{
    codol_player_fields_t out; unsigned sequence,i;
    if(!wire || !ps || !parameters || (visibleSlots&~15u)) return 0;
    /* The counter belongs to the state, not to whoever is receiving it: the
     * retained producers advance a per-playerState epoch beside
     * ps->eventSequence, and this publishes that epoch modulo 2048, the width
     * of the C1 field. A recipient-side accumulator could not do that: a
     * spectator whose source rewinds from live to archived would keep counting
     * forward instead of carrying the archived state's own counter. */
    if(!CODOL_PlayerStateEventSequence(ps,&sequence)) return 0;
    out=*wire;
    for(i=0;i<4;++i) {
        int mapped;
        if(!(visibleSlots&(1u<<i))) {
            if(!put(&out,0x0f4+4*i,0) || !put(&out,0x104+4*i,0)) return 0;
            continue;
        }
        mapped=shots && shots[i].known ?
            CODOL_PlayerFireEventToWire(ps->events[i],shots[i].hand,shots[i].last_shot) :
            CODOL_EventToWire(ps->events[i]);
        if(mapped<0 || parameters[i]>2047 || !put(&out,0x0f4+4*i,mapped) ||
           !put(&out,0x104+4*i,parameters[i])) return 0;
    }
    /* C1 CG_CheckPlayerstateEvents 0x45d680 consumes this primary queue.
     * Its second loop reads 0x118 and 0x120/0x130, not 0x114. Leave the
     * remaining event counters to their producers instead of duplicating F0. */
    if(!put(&out,0x0f0,sequence)) return 0;
    *wire=out; return 1;
}
int CODOL_OverlayEnginePlayerEventsWithShots(codol_player_fields_t *wire,const playerState_t *ps,
                                   const uint32_t parameters[4],const codol_engine_shot_record_t shots[4])
{
    return CODOL_OverlayEnginePlayerEventsWithShotsVisible(wire,ps,parameters,shots,15u);
}
/* The queue without shot records behaves exactly as before. */
int CODOL_OverlayEnginePlayerEvents(codol_player_fields_t *wire,const playerState_t *ps,
                                   const uint32_t parameters[4])
{
    return CODOL_OverlayEnginePlayerEventsWithShots(wire,ps,parameters,NULL);
}
static int overlay_shellshock(codol_player_fields_t *wire,const playerState_t *ps)
{
    const codol_ps_ext_t *ext=CODOL_PlayerStateExtConst(ps);
    codol_player_fields_t out=*wire;
    unsigned i,found=0;
    if((unsigned)ps->shellshockIndex>=16 || (unsigned)ps->shellshockDuration>65535) return 0;
    /* C1 StopShellShock 538a84..538aae and FadeOutShellShock538b15..538b87
     * establish index590/time594/duration598 and pm_flags8000. The retained
     * GScr_ShellShock/StopShellShock path has been changed to the same flag. */
    for(i=0;i<CODOL_PLAYER_FIELDS;++i) {
        switch(CODOL_PlayerField(i)->offset) {
        case 0x590: out.field[i]=(uint32_t)ps->shellshockIndex; found|=1; break;
        case 0x594: out.field[i]=(uint32_t)ps->shellshockTime; found|=2; break;
        case 0x598: out.field[i]=(uint32_t)ps->shellshockDuration; found|=4; break;
        case 0x59c: out.field[i]=ext && ext->poisoned ? 1u : 0u; found|=16; break;
        case 0x00c: found|=8; break;
        }
    }
    if(found!=31) return 0;
    *wire=out; return 1;
}

const char *codol_player_failure;
int CODOL_OverlayEngineViewhands(codol_player_fields_t *wire,unsigned model)
{
    if(!wire || model>=2048) return 0;
    return put(wire,0x148,model);
}
int CODOL_OverlayEngineViewmodel(codol_player_fields_t *wire,const playerState_t *ps,unsigned model)
{
    if(!wire || !ps || ps->viewmodelIndex<0 || model>=2048 ||
       (!!ps->viewmodelIndex!=!!model)) return 0;
    return put(wire,0x144,model);
}
/* Records which overlay step rejected the frame; the name is what the trace
 * prints, so the failing conversion is identified without a debugger. */
#define STEP(call) (codol_player_failure=#call,(call))
static int overlay_player(codol_player_fields_t *wire,codol_player_array_updates_t *updates,
    codol_hud_state_t *hud,const playerState_t *ps,const codol_engine_player_bindings_t *bindings,
    const codol_hud_state_t *captured_hud)
{
    codol_player_fields_t fields;
    codol_player_array_updates_t arrays;
    codol_hud_state_t collected;
    if(!wire || !updates || !hud || !ps || !bindings) return 0;
    fields=*wire; arrays=*updates;
    if(!STEP(CODOL_OverlayEngineMovement(&fields,ps)) ||
       !STEP(CODOL_OverlayEngineSprint(&fields,ps)) ||
       !STEP(CODOL_OverlayEnginePlayerMode(&fields,ps)) ||
       !STEP(CODOL_OverlayEnginePlayerFlags(&fields,ps)) ||
       !STEP(CODOL_OverlayEngineRadar(&fields,ps)) ||
       !STEP(CODOL_OverlayEngineThermal(&fields,ps)) ||
       !STEP(CODOL_OverlayEngineStun(&fields,ps)) ||
       !STEP(overlay_shellshock(&fields,ps)) ||
       !STEP(CODOL_OverlayEnginePlayerAnimations(&fields,ps)) ||
       !STEP(CODOL_OverlayEngineWeaponSelection(&fields,ps,bindings->alt_weapon)) ||
       !STEP(CODOL_OverlayEngineViewmodel(&fields,ps,bindings->viewmodel_index)) ||
       !STEP(CODOL_OverlayEngineViewhands(&fields,bindings->viewhands_index)) ||
       !STEP(CODOL_OverlayEngineOffhandSelection(&fields,bindings->offhand_slot)) ||
       !STEP(CODOL_OverlayEnginePrimaryWeapon(&fields,ps)) ||
       !STEP(CODOL_OverlayEngineSecondaryWeapon(&fields,(int)bindings->dual_wield,&bindings->second_hand)) ||
       !STEP(CODOL_OverlayEngineAim(&fields,ps)) ||
       !STEP(CODOL_OverlayEngineGrenadeState(&fields,ps)) ||
       !STEP(CODOL_OverlayEngineOffhandControl(&fields,ps)) ||
       !STEP(CODOL_OverlayEngineWeaponSwitchControl(&fields,ps)) ||
       !STEP(CODOL_OverlayEngineWeaponUseControl(&fields,ps)) ||
       !STEP(CODOL_OverlayEngineRecoilScale(&fields,ps)) ||
       !STEP(CODOL_OverlayEngineHealth(&arrays,ps)) ||
       !STEP(CODOL_OverlayEngineInventory(&arrays,ps,bindings->used_before)) ||
       !STEP(CODOL_OverlayEngineAmmo(&arrays,ps,bindings->clip_mask,bindings->clips,
           bindings->reserve_mask,bindings->reserves)) ||
       !STEP(CODOL_OverlayEngineSpinUpCharge(&fields,bindings->spinup_charge)) ||
       !STEP(CODOL_OverlayEnginePlayerEventsWithShotsVisible(&fields,ps,bindings->event_parameters,
            bindings->shots,bindings->event_suppressed_slots ^ 15u)) ||
       /* C1 fills two player event queues and the client replays both;
        * the scripted one lives in the extension and is published here. */
       !STEP(CODOL_OverlayEngineScriptEventsVisible(&fields,ps,bindings->script_event_parameters,
           bindings->script_event_suppressed_slots ^ 15u)) ||
       !STEP(CODOL_OverlayEnginePlayerLinks(&fields,ps))) {
        static char why[200];
        snprintf(why,sizeof(why),"%s [weaponstate %d weapAnim 0x%x weapon %d offhand %d pm_type %d pm_flags 0x%x]",
            codol_player_failure ? codol_player_failure : "?",ps->weaponstate,(unsigned)ps->weapAnim,
            ps->weapon,ps->offHandIndex,ps->pm_type,(unsigned)ps->pm_flags);
        codol_player_failure=why; return 0;
    }
    if(captured_hud) {
        codol_player_failure="captured HUD element count";
        if(captured_hud->count[0]>CODOL_HUD_SLOTS || captured_hud->count[1]>CODOL_HUD_SLOTS) return 0;
        collected=*captured_hud;
    } else if(!CODOL_CollectEngineHud(&collected,&ps->hud,bindings->hud_resolve,bindings->hud_context)) return 0;
    codol_player_failure=NULL;
    *wire=fields; *updates=arrays; *hud=collected; return 1;
}
int CODOL_OverlayEnginePlayer(codol_player_fields_t *wire,codol_player_array_updates_t *updates,
    codol_hud_state_t *hud,const playerState_t *ps,const codol_engine_player_bindings_t *bindings)
{ return overlay_player(wire,updates,hud,ps,bindings,NULL); }
/* Translate the retained per-client objective array into section 5's slots.
 *
 * G_RunFrame already does the hard part: it copies level.objectives into
 * ps->objective every frame, filtered by the client's team, and zeroes the
 * state of any objective this client must not see (_g_main_mp.asm:1020-1060,
 * stride 0x1c both sides). So this is a pure translation, not a policy.
 *
 * The two state enumerations agree: OBJST_EMPTY 0, OBJST_ACTIVE 1,
 * OBJST_CURRENT 4 (q_shared.h) are exactly the values C1's drawers accept,
 * with 0 meaning the free slot. The retained array holds sixteen entries and
 * C1 reads thirty-two; the other sixteen come through the bindings.
 *
 * teamNum is not on the wire: the filtering above is what replaces it. The
 * sixth field is read by neither drawer and is left zero. */
static void seed_objectives(codol_hud_state_t *hud, const playerState_t *ps,
                            const codol_engine_player_bindings_t *bindings)
{
    unsigned i;
    if (!hud || !ps) return;
    memset(hud->objectives, 0, sizeof(hud->objectives));
    for (i = 0; i < CODOL_OBJECTIVE_SLOTS; ++i) {
        /* 0..15 from the retained copy; 16..31 from the bound high slots
         * (codol_script_objectives.c), filtered by the same team rule. */
        const objective_t *o = i < 16 ? &ps->objective[i]
            : bindings && bindings->high_objectives_bound && i - 16 < 16
                ? &bindings->high_objectives[i - 16] : NULL;
        codol_objective_t *slot = &hud->objectives[i];
        unsigned axis;
        if (!o) continue;
        if ((unsigned)o->state >= OBJST_NUMSTATES || o->state == OBJST_EMPTY) continue;
        for (axis = 0; axis < 3; ++axis) {
            float v = o->origin[axis];
            if (!isfinite(v)) { v = 0.0f; }
            memcpy(&slot->field[axis], &v, sizeof(slot->field[axis]));
        }
        slot->state = (uint32_t)o->state & 7u;
        /* The icon is a C1 material-bank slot, not the native CS_MATERIALS
         * index; see objective_icon in codol_engine_player_bindings_t. */
        slot->field[3] = codol_field_bits(bindings && bindings->objective_icons_bound
            ? (int)bindings->objective_icon[i] : o->icon, 12);
        /* Anything but 0x7ff is read as a client number by the drawer, so an
         * entity number that is not a client slot must not be forwarded. */
        slot->field[4] = (o->entNum >= 0 && o->entNum < MAX_CLIENTS)
            ? (uint32_t)o->entNum : CODOL_OBJECTIVE_NONE;
        slot->field[5] = 0;
    }
}
int CODOL_OverlayEnginePlayerWithHud(codol_player_fields_t *wire,codol_player_array_updates_t *updates,
    codol_hud_state_t *hud,const playerState_t *ps,const codol_engine_player_bindings_t *bindings,
    const codol_hud_state_t *captured_hud)
{
    if(!captured_hud) return 0;
    if(!overlay_player(wire,updates,hud,ps,bindings,captured_hud)) return 0;
    seed_objectives(hud,ps,bindings);
    return 1;
}
int CODOL_OverlayEngineEntityEvents(codol_entity_state_t *wire,const entityState_t *es)
{
    codol_entity_state_t out;
    unsigned sequence;
    unsigned i;
    if (!wire || !es || CODOL_EntityTypeToWire(es->eType)!=(int)wire->type) return 0;
    /* The counter belongs to the entity state being serialized, not to a
     * per-entity-number accumulator shared by every recipient: the producers
     * advance an epoch beside es->eventSequence and this publishes it modulo
     * 2048 (codol_entitystate_ext.h). */
    if(!CODOL_EntityStateEventSequence(es,&sequence)) return 0;
    out=*wire;
    /* G_AddEvent_10 writes integer words through entityState's legacy vec4_t
     * declaration, then masks eventSequence with 0xff. Do not convert floats. */
    for(i=0;i<4;++i) {
        uint32_t event; int mapped;
        memcpy(&event,&es->events[i],sizeof(event));
        mapped=CODOL_EventToWire(event);
        if(mapped<0 || !put_entity(&out,0x0b4+4*i,(uint32_t)mapped)) return 0;
    }
    if(!put_entity(&out,0x0b0,sequence)) return 0;
    *wire=out; return 1;
}
int CODOL_OverlayEngineEntityEventQueue(codol_entity_state_t *wire,const entityState_t *es,
                                      const uint32_t parameters[4])
{
    codol_entity_state_t result; unsigned i;
    if(!wire || !es || !parameters) return 0;
    result=*wire;
    if(!CODOL_OverlayEngineEntityEvents(&result,es)) return 0;
    /* Measured entity tables: +c4/+c8/+cc/+d0 use codec -93 (11 bits),
     * C1 reader 0x5a07a2. Each parameter accompanies its corresponding
     * event at +b4/+b8/+bc/+c0; preserve physical queue slot order. */
    for(i=0;i<4;++i)
        if(parameters[i]>2047 || !put_entity(&result,0x0c4+4*i,parameters[i])) return 0;
    *wire=result; return 1;
}
int CODOL_OverlayEngineEntityEventQueueVisible(codol_entity_state_t *wire,const entityState_t *es,
                                             const uint32_t parameters[4],unsigned visibleSlots)
{
    codol_entity_state_t result;
    unsigned i,sequence;
    if(!wire || !es || !parameters || (visibleSlots & ~15u) ||
       CODOL_EntityTypeToWire(es->eType)!=(int)wire->type ||
       !CODOL_EntityStateEventSequence(es,&sequence)) return 0;
    result = *wire;
    /* The caller explicitly selects the slots to publish. Suppressed slots
     * need no mapping, but still occupy their original place in the queue. */
    for(i=0;i<4;++i) {
        uint32_t event=0,parameter=0;
        if(visibleSlots & (1u << i)) {
            uint32_t native_event; int mapped;
            memcpy(&native_event,&es->events[i],sizeof(native_event));
            mapped=CODOL_EventToWire(native_event);
            if(mapped<0 || parameters[i]>2047) return 0;
            event=(uint32_t)mapped; parameter=parameters[i];
        }
        if(!put_entity(&result,0x0b4+4*i,event) ||
           !put_entity(&result,0x0c4+4*i,parameter)) return 0;
    }
    if(!put_entity(&result,0x0b0,sequence)) return 0;
    *wire = result;
    return 1;
}

static int trajectory(codol_entity_state_t *out, unsigned offset, const trajectory_t *tr)
{
    unsigned mode, i;
    switch (tr->trType) {
    case TR_STATIONARY: mode = 0; break;
    case TR_INTERPOLATE: mode = 1; break;
    case TR_LINEAR: mode = 2; break;
    case TR_LINEAR_STOP: mode = 3; break;
    case TR_SINE:
        if (tr->trDuration <= 0) return 0;
        mode = 4; break;
    case TR_GRAVITY: mode = 5; break;
    case TR_GRAVITY_C1_6: mode = (unsigned)tr->trType; break;
    case TR_ACCELERATE:
    case TR_DECELERATE:
        if (tr->trDuration <= 0) return 0;
        mode = (unsigned)tr->trType; break;
    /* C1 entity lerp dispatch 0x443337 handles 9 outside the parametric
     * evaluator. Cleanup 0x46b59c owns the corresponding physics handle.
     * Native ScriptEntCmd_PhysicsLaunch writes C1 mode 9 to both tracks. */
    case TR_PHYSICS: mode = (unsigned)tr->trType; break;
    /* Native ragdoll producer uses C1 values. Client 4434f2..443522
     * dispatches 10..12 to ragdoll rendering; 40cca8 evaluates their tracks. */
    case TR_RAGDOLL:
    case TR_RAGDOLL_GRAVITY:
    case TR_RAGDOLL_INTERPOLATE: mode = (unsigned)tr->trType; break;
    default: return 0;
    }
    /* C1 BG_EvaluateTrajectory (0x40CA40): stop=3, sine=4, gravity=5.
     * Gravity is fixed at 800 in both the client and retained IW3 evaluator. */
    if (tr->trDuration < 0 || !put_entity(out, offset, mode) ||
        !put_entity(out, offset+4, (uint32_t)tr->trTime) ||
        !put_entity(out, offset+8, tr->trDuration)) return 0;
    for (i = 0; i < 3; ++i)
        if (!entity_float(out, offset+12+4*i, tr->trBase[i]) ||
            !entity_float(out, offset+24+4*i, tr->trDelta[i])) return 0;
    return 1;
}
int CODOL_OverlayEngineTrajectories(codol_entity_state_t *wire, const entityState_t *es)
{
    codol_entity_state_t out;
    if (!wire || !es || wire->type > 255 || es->number < 0 || es->number >= ENTITYNUM_WORLD) return 0;
    out = *wire; out.number = es->number; out.field[0] = out.type;
    /* Corrected entity_codec.py layout: origin is pos.trBase at 0x18,
     * not pos.trDelta at 0x24 as older snapshot_sections.py comments claimed. */
    if (!trajectory(&out, 0x00c, &es->lerp.pos) || !trajectory(&out, 0x030, &es->lerp.apos)) return 0;
    *wire = out; return 1;
}

int CODOL_OverlayEngineMissile(codol_entity_state_t *wire, const entityState_t *es)
{
    codol_entity_state_t out;
    int weapon;
    if (!wire || !es || es->eType != ET_MISSILE || wire->type != 4 ||
        (unsigned)es->lerp.u.missile.flightMode > 1 ||
        (weapon = CODOL_WeaponToWire(es->weapon)) < 0) return 0;
    out = *wire;
    /* alpha0022/docs/projectile_wire.md: C1 0x443BE5 selects a projectile
     * model through bg_weaponDefs using es+0xD4. es+0x54 is scene scale;
     * leaving it zero makes the missile invisible. IW3 has no scale member. */
    /* C1 538256/538261 writes the script-selected flight mode to es+5c;
     * the type4 netfield is two bits. Read the captured state, never the live
     * gentity that happens to have this archived state's entity number. */
    /* C1 rocket spawn 530cc2/530cc8 stores level time at58 and530d10
     * applies its launch delay. The retained producer stores that timestamp
     * in missile.launchTime (native54), already carried by archive deltas. */
    if (!CODOL_OverlayEngineTrajectories(&out, es) ||
        !put_entity(&out, 0x058, (uint32_t)es->lerp.u.missile.launchTime) ||
        !put_entity(&out, 0x05c, (uint32_t)es->lerp.u.missile.flightMode) ||
        !put_entity(&out, 0x0d4, (uint32_t)weapon) || !entity_float(&out, 0x054, 1.0f)) return 0;
    /* Owner client (+9c, six bits) and team (+a4, two bits) the compass
     * colours the missile with; T5 packs the same pair into es.faction. The
     * launch stamps them into the retained clientNum/iHeadIconTeam
     * (CODOL_ApplyRocketWeaponLock), so an archived state answers for itself.
     * A missile no launch stamped (a grenade) publishes owner 0 as before. */
    if (!put_entity(&out, 0x09c, (es->clientNum >= 0 && es->clientNum < 64) ?
            (uint32_t)es->clientNum : 0u) ||
        !put_entity(&out, 0x0a4, (uint32_t)es->iHeadIconTeam & 3u)) return 0;
    /* The owner C1's compass actually reads: es+0x80, eleven bits, the
     * parent's entity number, which C1's rocket spawn 0x5310ce writes for a
     * guidance-2 (predator) weapon and CODOL_ApplyRocketWeaponLock mirrors
     * into otherEntityNum. Measured live 2026-09-28: the compass update
     * copies it into the list entry's owner; +0x9c and +0xa4 are not read
     * there (docs/CODOL_C1_VIRTUALIZED_20260928.md). */
    if (es->otherEntityNum >= 0 && es->otherEntityNum < ENTITYNUM_WORLD &&
        !put_entity(&out, 0x080, (uint32_t)es->otherEntityNum)) return 0;
    *wire = out; return 1;
}
int CODOL_OverlayEngineItem(codol_entity_state_t *wire,const entityState_t *es)
{
    int weapon;
    unsigned model,packed;
    if(!wire || !es || wire->type!=ET_ITEM || es->eType!=ET_ITEM || es->index<=0) return 0;
    /* The native item index is weapon + 700*model, C1's own packing
     * (codol_weapon_slots.h), so it splits without ambiguity. Rejecting an
     * item here used to cost every nearby client its snapshots (see
     * CODOL_CollectServerEntitiesEmitted). */
    weapon=CODOL_WeaponToWire(CODOL_ItemIndexWeapon(es->index));
    model=CODOL_ItemIndexModel(es->index);
    if(weapon<=0 || weapon>=CODOL_ITEM_STRIDE) return 0;
    /* C1 43e94c..43e958 divides cent.nextState+98 by 700 and resolves the
     * remainder's world model at 43e619; 43e66b reads worldModel[0] and never
     * the quotient. The field is 11 bits wide, so a variant that does not fit
     * is dropped rather than wrapped into another weapon. */
    packed=(unsigned)weapon+CODOL_ITEM_STRIDE*model;
    if(packed>2047u) packed=(unsigned)weapon;
    return put_entity(wire,0x098,packed);
}
int CODOL_OverlayEngineTurret(codol_entity_state_t *wire,const entityState_t *es,unsigned model)
{
    codol_entity_state_t out; int weapon; uint32_t owner, flags, bytes;
    if(!wire || !es || es->eType!=ET_MG42 || wire->type!=(unsigned)ET_MG42 ||
       model>=2048 || (!!es->index!=!!model) ||
       es->otherEntityNum<0 || es->otherEntityNum>ENTITYNUM_NONE ||
       (unsigned)es->lerp.u.turret.lastBarrelRotChangeRate>65535 ||
       (unsigned)es->lerp.u.turret.lastHeatChangeLevel>65535 ||
       es->turretState.barrelSpinning>1 || es->turretState.overheated>1 ||
       es->turretState.heating>1 ||
       (weapon=CODOL_WeaponToWire((unsigned)es->weapon))<0) return 0;
    out=*wire;
    /* C1 G_SpawnTurret 0x57f2cb publishes its own "none" sentinel in the
     * owner field and setsentryowner 0x536a92 replaces it with an entity
     * number; the turret producer keeps the same value in s.otherEntityNum,
     * which the snapshot archives. */
    owner = es->otherEntityNum==ENTITYNUM_NONE ? CODOL_ENTITY_SENTINEL
                                               : (uint32_t)es->otherEntityNum;
    /* C1's turret-fired frame marker is eFlags 0x200: its shot path sets it,
     * the turret think clears it at 0x57dc9a and the heat update tests it at
     * 0x57b229. The retained turret code marks the same frame with eFlags
     * 0x40, and no other native eFlag has a measured CoDOL turret meaning, so
     * only this bit is translated. */
    flags = (es->lerp.eFlags & 0x40) ? 0x200u : 0u;
    /* Three direction bytes in one word, same order in both layouts:
     * spinning, overheated, heating (C1 es+0x74..0x76). */
    bytes = (uint32_t)es->turretState.barrelSpinning |
            ((uint32_t)es->turretState.overheated<<8) |
            ((uint32_t)es->turretState.heating<<16);
    /* Native 0x54..0x5c gun angles map to CoDOL 0x58..0x60 and the native
     * heat/spin words 0x60/0x64/0x68/0x6c map to 0x64/0x68/0x6c/0x70; C1 reads
     * them back in BG_GetTurretBarrelSpin 0x41dd80 and BG_GetTurretHeat
     * 0x41de50. The weapon selector is es+0xd4, which C1's spin update
     * 0x57b0f0, heat update 0x57b1f0, fire gate 0x57b050 and shot builder
     * 0x57acf0 all read; the model selector is the CoDOL +98 slot. */
    if(!entity_float(&out,0x058,es->lerp.u.turret.gunAngles[0]) ||
       !entity_float(&out,0x05c,es->lerp.u.turret.gunAngles[1]) ||
       !entity_float(&out,0x060,es->lerp.u.turret.gunAngles[2]) ||
       !put_entity(&out,0x064,(uint32_t)es->lerp.u.turret.lastBarrelRotChangeTime) ||
       !put_entity(&out,0x068,(uint32_t)es->lerp.u.turret.lastBarrelRotChangeRate) ||
       !put_entity(&out,0x06c,(uint32_t)es->lerp.u.turret.lastHeatChangeLevel) ||
       !put_entity(&out,0x070,(uint32_t)es->lerp.u.turret.lastHeatChangeTime) ||
       !put_entity(&out,0x074,bytes) ||
       !put_entity(&out,0x098,model) ||
       !put_entity(&out,0x0d4,(uint32_t)weapon) ||
       !put_entity(&out,0x080,owner) ||
       !put_entity(&out,0x008,flags)) return 0;
    *wire=out; return 1;
}
int CODOL_OverlayEngineVehicleIdentity(codol_entity_state_t *wire,const entityState_t *es)
{
    codol_entity_state_t out;
    unsigned identity;
    if(!wire || !es ||
       (es->eType!=ET_HELICOPTER && es->eType!=ET_VEHICLE) ||
       wire->type!=(unsigned)CODOL_EntityTypeToWire(es->eType) ||
       es->clientNum<0 || es->clientNum>=32 ||
       !CODOL_EntityStateVehicleIdentity(es,&identity) || identity>511 ||
       !(identity>>4)) return 0;
    out=*wire;
    /* C1 67a656/67a659 packs definition<<4 | instance, then 67a6bd writes
     * entity+58. 67a6df..67a6ff separately writes the optional spawning
     * client's ps.clientNum to entity+74 (zero when no owner was supplied).
     * Netfield tables12/14 assign these nine and five bits respectively.
     * Both native sources survive snapshot/archive copies; a rewind must
     * never reconstruct them from the current scr_vehicle or owner pointer. */
    if(!put_entity(&out,0x058,identity) ||
       !put_entity(&out,0x074,(unsigned)es->clientNum)) return 0;
    *wire=out; return 1;
}
int CODOL_OverlayEngineVehicleAssets(codol_entity_state_t *wire,const entityState_t *es,unsigned model)
{
    codol_entity_state_t out;
    unsigned i;
    int weapon;
    if(!wire || !es ||
       (es->eType!=ET_HELICOPTER && es->eType!=ET_VEHICLE) ||
       wire->type!=(unsigned)CODOL_EntityTypeToWire(es->eType) ||
       es->index<0 || es->index>=2048 || es->un2<0 || model>=2048 ||
       (!!es->un2!=!!model) ||
       (weapon=CODOL_WeaponToWire((unsigned)es->weapon))<0 || weapon>65535) return 0;
    out=*wire;
    /* Retained SpawnVehicle publishes the turret weapon at native+c4.
     * C1 67a5bb..67a5f5 resolves VehicleDef+194 and writes only WORD+d4;
     * do not replace its adjacent word with native weaponModel. */
    for(i=0;i<CODOL_ENTITY_FIELDS;++i)
        if(CODOL_EntityField(out.type,i)->offset==0x0d4) {
            out.field[i]=(out.field[i]&UINT32_C(0xffff0000))|(unsigned)weapon;
            break;
        }
    if(i==CODOL_ENTITY_FIELDS) return 0;
    /* Native G_DObjUpdate_90 publishes vehicle visual models in un2 (+d8),
     * not index (+88), which is reserved for the collision brush. C1's
     * corresponding 57121d..571227 writes WORD+e4 for types12/14; its
     * collision-template setup6748d5 writes the brush at+98. Preserve the
     * adjacent, independently owned upper word of the model field. */
    for(i=0;i<CODOL_ENTITY_FIELDS;++i)
        if(CODOL_EntityField(out.type,i)->offset==0x0e4) {
            out.field[i]=(out.field[i]&UINT32_C(0xffff0000))|model;
            break;
        }
    if(i==CODOL_ENTITY_FIELDS || !put_entity(&out,0x098,(unsigned)es->index)) return 0;
    *wire=out; return 1;
}
static unsigned char vehicle_definition_tree[32];
void CODOL_SetVehicleDefinitionAnimTree(unsigned definition_slot,unsigned client_tree)
{
    if(!definition_slot) { memset(vehicle_definition_tree,0,sizeof(vehicle_definition_tree)); return; }
    if(definition_slot<32 && client_tree<16) vehicle_definition_tree[definition_slot]=(unsigned char)client_tree;
}
int CODOL_OverlayEngineVehiclePose(codol_entity_state_t *wire,const entityState_t *es)
{
    codol_entity_state_t out;
    if(!wire || !es ||
       (es->eType!=ET_HELICOPTER && es->eType!=ET_VEHICLE) ||
       wire->type!=(unsigned)CODOL_EntityTypeToWire(es->eType)) return 0;
    out=*wire;
    /* C1 spawn 67a6ab..67a6ae binds vehicle+4 to entity+58.
     * Controller 67ac10 reads +8/+c into tag_body pitch/roll,
     * +18 into tag_turret yaw and +14 into tag_barrel pitch.
     * Steering update 678680 writes block+10. Client pose 67d080
     * independently interpolates these same five network values.
     * The retained materialTime between steerYaw and gunPitch is not
     * part of this mapping; copying the native union would misalign it. */
    if(!entity_float(&out,0x060,es->lerp.u.vehicle.bodyPitch) ||
       !entity_float(&out,0x064,es->lerp.u.vehicle.bodyRoll) ||
       !entity_float(&out,0x068,es->lerp.u.vehicle.steerYaw) ||
       !entity_float(&out,0x06c,es->lerp.u.vehicle.gunPitch) ||
       !entity_float(&out,0x070,es->lerp.u.vehicle.gunYaw) ||
       /* Retained G_VehEntHandler_Think publishes suspensionTravel*1000
        * into time2. C1 67b3a4..67b3b8 does the same from VehicleDef+160
        * into +7c; 67d703..67d73f uses the decoded travel to extend the
        * wheel trace along the negative body-up axis. It is distance in
        * fixed-point units, despite this field using a time delta codec. */
       !put_entity(&out,0x07c,(uint32_t)es->time2)) return 0;
    /* C1 0x443540 hands eType 12 and 14 the realm-0 animtree named by +094
     * when it builds the DObj (0x44372b), exactly as for script movers. A
     * vehicle whose wheels are server-animated (codol_vehicle_wheel_anim.c)
     * needs that tree for its animation commands to land. The id is chosen
     * by the captured definition slot, so an archived frame needs no live
     * entity; it is map-static and zero for every other vehicle. */
    {
        unsigned identity;
        if(CODOL_EntityStateVehicleIdentity(es,&identity) && (identity>>4)<32 &&
           vehicle_definition_tree[identity>>4] &&
           !put_entity(&out,0x094,vehicle_definition_tree[identity>>4])) return 0;
    }
    *wire=out; return 1;
}
int CODOL_OverlayEnginePlayerEntityFlags(codol_entity_state_t *wire,const entityState_t *es)
{
    unsigned i;
    if(!wire || !es || wire->type!=1 || es->eType!=ET_PLAYER) return 0;
    for(i=0;i<CODOL_ENTITY_FIELDS;++i) if(CODOL_EntityField(wire->type,i)->offset==0x008) {
        /* The CoDOL radar carriers must not reach C1 as themselves. C1's
         * compass actor update 0x433979..0x4339e8 reads these very bits on
         * every other player's es+8: 0x04000000 skips the actor, 0x08000000
         * shows it (actor flag 0x10, or 0x20 with 0x20000000), 0x10000000
         * sets 0x40/0x80. The team radar block rides 0x08000000 on each
         * jammed player, so a counter-UAV drew every jammed enemy on the
         * caller team's compass. Native 0x200000 is EF_TALK (Pmove, talk
         * button), which C1 measures as a radar jammer (0x45ba83); C1's
         * jammer bit is produced only from the CoDOL jammer carrier. */
        uint32_t native=(uint32_t)es->lerp.eFlags;
        wire->field[i]=(native&~((uint32_t)CODOL_PS_EF_RADAR_CARRIERS|UINT32_C(0x200000)))|
            ((native&CODOL_PS_EF_RADAR_JAMMER) ? UINT32_C(0x200000) : 0u);
        return 1;
    }
    return 0;
}
int CODOL_OverlayEnginePlayerEntityWeapons(codol_entity_state_t *wire,const entityState_t *es,unsigned primary_weapon)
{
    codol_entity_state_t out;
    int current,primary,held;
    if(!wire || !es || wire->type!=ET_PLAYER || es->eType!=ET_PLAYER ||
       (current=CODOL_WeaponToWire(es->weapon))<0 ||
       (primary=CODOL_WeaponToWire(primary_weapon))<0) return 0;
    /* C1 +60 (40d104..40d13d): the held "hold"-type offhand, captured with
     * the pair; 0 when none, and 0 rather than a failure when it has no wire
     * slot - it only selects a model. */
    held=CODOL_WeaponToWire(CODOL_EntityStateHeldOffhand(es));
    out=*wire;
    /* C1 BG_PlayerStateToEntityState: 40d154 writes current to word +d4;
     * 40d0fd writes current/primary-for-alt to word +d6 (inventory type 3).
     * The earlier reference helper's +80 weapon label is incorrect: 40d0bb
     * copies ps+1b0 there conditionally on eFlags instead. */
    if(!put_entity(&out,0x0d4,(uint32_t)current|((uint32_t)primary<<16)) ||
       !put_entity(&out,0x060,held>0 ? (uint32_t)held : 0)) return 0;
    *wire=out; return 1;
}
int CODOL_OverlayEnginePlayerEntityAnimations(codol_entity_state_t *wire,const entityState_t *es)
{
    codol_entity_state_t result;
    if(!wire || !es || wire->type!=ET_PLAYER || es->eType!=ET_PLAYER ||
       es->legsAnim<0 || es->legsAnim>2047 || es->torsoAnim<0 || es->torsoAnim>2047) return 0;
    result=*wire;
    /* C1 45b84c/45b858 copy es+d8/dc to clientAnim+9f4/9f8. The native
     * CoDOL BG producer already uses the target 1024-entry namespace and
     * 0x400 toggle; applying the old IW3 0x200 mask would corrupt index 512. */
    if(!put_entity(&result,0x0d8,(unsigned)es->legsAnim) ||
       !put_entity(&result,0x0dc,(unsigned)es->torsoAnim)) return 0;
    *wire=result; return 1;
}
/* The pose words C1's own BG_PlayerStateToEntityState puts on every player
 * entity, and that its corpse clone (0x51c827) copies verbatim. The server
 * published none of them, so every remote player was drawn without lean, with
 * legs that never turned toward the direction of travel, and flat when prone
 * on a slope; a corpse kept the same defaults.
 *   +58 leanf (float)      C1 0x40d070/0x40d076 <- ps+0x94
 *   +5c movementDir        C1 0x40d21c/0x40d222 <- ps+0xe8 (signed degrees)
 *       Consumers: lerp 0x442ca3 (player) / 0x44342a (player, corpse) write
 *       clientInfo+0x9e0 (lerpMoveDir, legs yaw in BG 0x406dc0) and
 *       clientInfo+0x9e4 (lerpLean) from +5c / +58.
 *   +68 waist pitch, +6c torso pitch (floats) C1 ClientEndFrame 0x50ce7c..
 *       0x50ce93 from the pmove prone pitches; CG_Player 0x45b864/0x45b86e
 *       and CG_Corpse 0x45bba4/0x45bbae load them into clientInfo+0x9fc/+0xa00.
 *   +88 groundEntityNum    C1 0x40d15b/0x40d16a <- ps+0xa8; the entity lerp
 *       0x443483 hands it to the mover adjustment 0x440120. Players only.
 *   +80 turret entity      C1 0x40d0a9..0x40d0bb <- ps+0x1b0 (viewlocked
 *       entity) while eFlags & 0xc00; players only.
 * The retained BG_PlayerStateToEntityState already fills the native words:
 * lerp.u.player.{leanf,movementDir} (_bg_misc.asm, es+0x54/0x58),
 * fTorsoPitch/fWaistPitch (float bits in es+0xdc/0xe0, zero unless prone),
 * groundEntityNum (es+0x7c) and, on a turret, otherEntityNum (es+0x74).
 * They are read from this captured state only. A value the field cannot hold
 * is published as the field's neutral value rather than refusing the entity:
 * these words are cosmetic, and a refused entity disappears. */
static uint32_t pose_float(int bits)
{
    float value;
    memcpy(&value,&bits,sizeof(value));
    return isfinite(value) && value>-360000.0f && value<360000.0f ? (uint32_t)bits : 0u;
}
int CODOL_OverlayEnginePlayerEntityPose(codol_entity_state_t *wire,const entityState_t *es)
{
    codol_entity_state_t out;
    int direction;
    uint32_t lean;
    if(!wire || !es || (es->eType!=ET_PLAYER && es->eType!=ET_PLAYER_CORPSE) ||
       wire->type!=(unsigned)es->eType) return 0;
    out=*wire;
    memcpy(&lean,&es->lerp.u.player.leanf,sizeof(lean));
    /* Player +5c is codec -76, corpse +5c is -8: both a signed byte. */
    direction=es->lerp.u.player.movementDir;
    if(direction<-128 || direction>127) direction=0;
    if(!put_entity(&out,0x058,pose_float((int)lean)) ||
       !put_entity(&out,0x05c,(uint32_t)direction) ||
       !put_entity(&out,0x068,pose_float(es->fWaistPitch)) ||
       !put_entity(&out,0x06c,pose_float(es->fTorsoPitch))) return 0;
    if(es->eType==ET_PLAYER) {
        if(es->groundEntityNum>=0 && es->groundEntityNum<=ENTITYNUM_NONE &&
           !put_entity(&out,0x088,(uint32_t)es->groundEntityNum)) return 0;
        if((es->lerp.eFlags & 0xc00) && es->otherEntityNum>=0 &&
           es->otherEntityNum<ENTITYNUM_WORLD &&
           !put_entity(&out,0x080,(uint32_t)es->otherEntityNum)) return 0;
    }
    /* Read-back of the pose words as they leave, on a change of stance
     * direction, ground or turret only (codol_debugTrace). */
    {
        static uint32_t last[64][3]; static int lines;
        unsigned n=(unsigned)es->number,k;
        uint32_t now[3];
        for(k=0;k<3;++k) now[k]=0;
        for(k=0;k<CODOL_ENTITY_FIELDS;++k) {
            unsigned o=CODOL_EntityField(out.type,k)->offset;
            if(o==0x05c) now[0]=out.field[k];
            else if(o==0x088) now[1]=out.field[k];
            else if(o==0x080) now[2]=out.field[k];
        }
        if(CODOL_TRACE_ON() && n<64 && lines<400 && memcmp(last[n],now,sizeof(now))) {
            float lean,waist,torso;
            memcpy(last[n],now,sizeof(now)); ++lines;
            memcpy(&lean,&es->lerp.u.player.leanf,4);
            memcpy(&waist,&es->fWaistPitch,4); memcpy(&torso,&es->fTorsoPitch,4);
            Com_Printf(CON_CHANNEL_SERVER,"CoDOL entity pose wire: entity %u type %u lean(58) %.2f"
                " moveDir(5c) %d waist(68) %.2f torso(6c) %.2f ground(88) %u turret(80) %u eFlags 0x%x\n",
                n,out.type,lean,(int)now[0],waist,torso,(unsigned)now[1],(unsigned)now[2],
                (unsigned)es->lerp.eFlags);
        }
    }
    *wire=out; return 1;
}
/* Hidden-part bits (hidePart/showPart). C1 keeps 256 of them in eight words at
 * entityState +ec..+108 (hidepart 0x5717xx: bit 0x80000000>>(bone&31) of
 * word bone>>5, the retained ScrCmd_hidepart's own order) and CG 0x4417b1..
 * 0x4417ec hands +ec straight to the DObj (0x636360 copies 32 bytes to
 * obj+0xa0) for every eType except item, player, corpse, actor and a script
 * model that carries a weapon. The retained entityState stores the first four
 * words in partBits; the rest of C1's range is published as visible. Only
 * the model entity types scripts hide parts on are published, since only
 * their bone numbering is the single model's own on both sides. */
int CODOL_OverlayEnginePartBits(codol_entity_state_t *wire,const entityState_t *es)
{
    codol_entity_state_t out;
    uint32_t bits[8];
    unsigned i;
    /* Compare against the wire type, not the native one: they differ for
     * every temp event entity (native ET_EVENTS+ev, C1 ET_EVENTS+its own
     * event number; EV_OBITUARY is 87 native, 128 on the wire). Comparing
     * the native number dropped every such event from every snapshot -
     * obituaries (the kill feed), melee/bullet-hit impacts, play-fx-on-tag,
     * earthquakes - since this overlay was added (d8e04ad8). */
    if(!wire || !es || CODOL_EntityTypeToWire(es->eType)!=(int)wire->type) return 0;
    if(es->eType!=ET_GENERAL && es->eType!=ET_SCRIPTMOVER) return 1;
    out=*wire;
    /* all 256 of C1's hide bits: words 0..3 are native partBits, 4..7 the
     * extension's hide_upper (bones 128..252) */
    CODOL_EntityStateHidePartBits(es,bits);
    for(i=0;i<8;++i)
        if(!put_entity(&out,0x0ec+4*i,bits[i])) return 0;
    *wire=out; return 1;
}
int CODOL_OverlayEngineCorpseIdentity(codol_entity_state_t *wire,const entityState_t *es)
{
    codol_entity_state_t out;
    unsigned i,ground;
    if(!wire || !es || wire->type!=2 || es->eType!=ET_PLAYER_CORPSE ||
       es->number<19 || es->number>26 || es->clientNum<0 || es->clientNum>=18 ||
       es->legsAnim<0 || es->legsAnim>2047 || es->torsoAnim<0 || es->torsoAnim>2047 ||
       es->groundEntityNum<0 || es->groundEntityNum>ENTITYNUM_NONE) return 0;
    out=*wire;
    /* C1 clone51c827 allocates eight entities starting at19;51c883 stores
     * the original player identity, and51c897 adds the dead/copy flags.
     * Reset46b901 uses that identity and bit80000 to copy the player's
     * appearance into this corpse's own client record. Read only the saved
     * entity state: the original player may already have respawned. */
    for(i=0;i<CODOL_ENTITY_FIELDS;++i) {
        if(CODOL_EntityField(out.type,i)->offset!=0x008) continue;
        /* A clone copies the player's flags, radar carriers included. */
        out.field[i]=(uint32_t)es->lerp.eFlags&~(uint32_t)CODOL_PS_EF_RADAR_CARRIERS;
        out.field[i]=(out.field[i]&~UINT32_C(0x80000))|
            ((uint32_t)es->lerp.eFlags&UINT32_C(0x80000));
        break;
    }
    if(i==CODOL_ENTITY_FIELDS) return 0;
    /* Native clone ground7c and C1 clone51caa5 ground88 both use the
     * 0x7ff NONE sentinel; WORLD is one below NONE. */
    ground=(unsigned)es->groundEntityNum;
    /* C1 clone51cb46..51cb58 preserves both animation words just as the
     * retained producer does. These are already CoDOL animation indices. */
    if(!put_entity(&out,0x09c,(unsigned)es->clientNum) ||
       !put_entity(&out,0x0d8,(unsigned)es->legsAnim) ||
       !put_entity(&out,0x0dc,(unsigned)es->torsoAnim) ||
       !put_entity(&out,0x088,ground)) return 0;
    *wire=out; return 1;
}
static int overlay_entity_visible(codol_entity_state_t *wire,const entityState_t *es,
                                  const uint32_t parameters[4],unsigned visibleSlots,int publish_link)
{
    codol_entity_state_t out;
    if(!wire || !es || !parameters ||
       CODOL_EntityTypeToWire(es->eType)!=(int)wire->type) return 0;
    out=*wire;
    if(es->eType==ET_PLAYER_CORPSE && !CODOL_OverlayEngineCorpseIdentity(&out,es)) return 0;
    if((es->eType==ET_PLAYER || es->eType==ET_PLAYER_CORPSE) &&
       !CODOL_OverlayEnginePlayerEntityPose(&out,es)) return 0;
    if(!CODOL_OverlayEnginePartBits(&out,es)) return 0;
    if(es->eType==ET_MISSILE) {
        if(!CODOL_OverlayEngineMissile(&out,es)) return 0;
    } else {
        if(es->eType==ET_ITEM && !CODOL_OverlayEngineItem(&out,es)) return 0;
        if(!CODOL_OverlayEngineTrajectories(&out,es)) return 0;
    }
    {
        unsigned info,i;float origin[3],angles[3];
        if(!CODOL_EntityStateLink(es,&info,origin,angles))return 0;
        /* A child whose parent this recipient's snapshot does not carry is
         * published unlinked: C1 0x4419a0 prints "parent ent #%d not in
         * snapshot" for every such frame and resolves no parent. The parent
         * number (low word) and its tag (bits 16-23, and the untagged flag
         * 2<<24) go; bit 24 describes this entity as a parent and stays. The
         * native link producer (G_GeneralLink) keeps the world pose in
         * trBase with TR_INTERPOLATE and zero deltas, so the unlinked child
         * still draws where the server places it. */
        if(!publish_link) info&=~(UINT32_C(0xffffff)|(UINT32_C(2)<<24));
        if(!put_entity(&out,0x0e8,info))return 0;
        /* C1 52d47b stores tag-local origin/angles in trajectory deltas.
         * 4404a0 resolves the parent (including predicted local player) and
         * its registered tag. Never reconstruct an archived link from live entities. */
        if(info&65535u)for(i=0;i<3;++i)
            if(!entity_float(&out,0x024+4*i,origin[i]) || !entity_float(&out,0x048+4*i,angles[i]))return 0;
    }
    /* alpha0022/entity_codec.py: +54 is model scale, read at 0x441532.
     * The retained entityState has no scale member; setModelScale keeps it
     * in a side table, normal size unless a script set one. */
    if(!entity_float(&out,0x054,CODOL_EntityModelScale(es->number))) return 0;
    if(es->eType==ET_ACTOR) {
        unsigned slot=(unsigned)es->lerp.u.actor.actorSlot;
        unsigned tree=(unsigned)es->lerp.u.actor.treeSelector;
        /* C1 42A69E reads state+58 as actor slot. 428BA6 reads +59
         * as the five-way actor tree selector. Never use player anim words. */
        if(slot>=32 || tree>=5 || !put_entity(&out,0x058,slot|(tree<<8))) return 0;
        /* Actor trajectories leave the server as TR_INTERPOLATE (C1 mode 1),
         * never TR_STATIONARY (mode 0). MEASURED 2026-09-21
         * (docs/CODOL_ZOMBIE_ANIM_SMOOTHNESS_20260921.md): every actor origin
         * producer ends in the retained G_SetOrigin (_g_utils_mp.asm:748),
         * which stores trBase and zeroes trType/trTime/trDuration/trDelta,
         * so a walking zombie was published 60 times a second as a
         * stationary entity. C1's entity lerp dispatch (0x443337) evaluates
         * mode 0 straight from the newest snapshot's trBase
         * (BG_EvaluateTrajectory 0x40ca40) and only interpolates between the
         * two snapshots it holds for mode 1 (0x443354 -> 0x442ac0); the
         * origin codec is integer on both arms (-83/-82/-81: 7-bit delta or
         * 16-bit wide arm, codol_delta.c position()), so a 15 u/s zombie
         * whose origin can only advance in whole units stepped visibly.
         * T5's MP actor does exactly this every frame after Actor_CallThink
         * (OpenBLOPS Game/Server/game_mp/actor_mp.cpp:1493 and :1504:
         * `s.lerp.pos.trType = isRagdoll ? 14 : 1`, same for apos). Only a
         * stationary trajectory is promoted: a ragdoll or physics trajectory
         * keeps its own mode. Applied at the wire so live and archived
         * (killcam) actor states agree without touching the producers. */
        if(es->lerp.pos.trType==TR_STATIONARY && !put_entity(&out,0x00c,1u)) return 0;
        if(es->lerp.apos.trType==TR_STATIONARY && !put_entity(&out,0x030,1u)) return 0;
    }
    /* C1 intensity setter547d91/getter547cec use entityState+5c.
     * Use this saved entityState, so archived lighting survives later edits.
     * Native intensity is union-relative+4, not C1's absolute offset. */
    if(es->eType==ET_PRIMARY_LIGHT) {
        const byte *color=es->lerp.u.primaryLight.colorAndExp;
        /* C1 getlightcolor555030 reads58..5b; exponent5554fc reads5b.
         * Pack saved bytes explicitly instead of reading an unaligned word. */
        uint32_t packedColor=(uint32_t)color[0]|((uint32_t)color[1]<<8)|
            ((uint32_t)color[2]<<16)|((uint32_t)color[3]<<24);
        /* C1 radius5550ec/5551f8 uses60; BSP index55511c uses98/11bits.
         * Both values come from this snapshot, never the current live light. */
        if(es->index<0 || es->index>=2048 ||
           !put_entity(&out,0x058,packedColor) ||
           !put_entity(&out,0x098,(unsigned)es->index) ||
           !entity_float(&out,0x05c,es->lerp.u.primaryLight.intensity) ||
           !entity_float(&out,0x060,es->lerp.u.primaryLight.radius) ||
           /* C1 setlightfov5554df/5554e6 stores outer/inner cosine words.
            * Retained SP_light initializes these in the native union too. */
           !entity_float(&out,0x064,es->lerp.u.primaryLight.cosHalfFovOuter) ||
           !entity_float(&out,0x068,es->lerp.u.primaryLight.cosHalfFovInner)) return 0;
    }
    if(es->eType==ET_PLAYER) {
        if(!CODOL_OverlayEnginePlayerEntityFlags(&out,es) ||
           !CODOL_OverlayEnginePlayerEntityAnimations(&out,es)) return 0;
        /* C1 field setter50e590 writes lookup result to a0;54fe91 returns
         * slot+1 and empty input returns0. Native headicon uses the same
         * one-based15-slot domain and is already saved by native deltas. */
        if(es->iHeadIcon<0 || es->iHeadIcon>15 ||
           !put_entity(&out,0x0a0,(unsigned)es->iHeadIcon)) return 0;
        /* +a4 is the team the head icon is shown to. CG 0x45aeca..0x45aedf
         * draws the icon for every viewer when it is 0, and otherwise only
         * for a viewer whose clientInfo team (+0x4c: 1 axis, 2 allies, 6
         * spectator) equals it or who spectates. It was never published,
         * so a team-restricted icon (the quick-message "talking" icon, the
         * friend icons) was drawn over the player for the enemy too. The
         * native headiconteam field uses the same 1/2 team numbers; the
         * wire field is two bits. */
        if(!put_entity(&out,0x0a4,(es->iHeadIconTeam>=0 && es->iHeadIconTeam<=3) ?
                (uint32_t)es->iHeadIconTeam : 0u)) return 0;
        /* C1 0x45bc70 uses +9c to select clientInfo; the entity number is
         * not a substitute. The measured netfield is six bits wide. */
        if(es->clientNum<0 || es->clientNum>=64 ||
           !put_entity(&out,0x09c,(uint32_t)es->clientNum)) return 0;
    }
    /* C1 carries the looping sound in the entityState, one byte, in every
     * eType table: producers 0x0054d760 / 0x00541320, transfer 0x0040d09d,
     * consumer 0x00443c74 -> 0x0043eba0. It is a state and not an event, so
     * every entity the frame serializes publishes it, live or archived. */
    /* entityState.solid, netfield +0xa8 (24 bits) in all 22 eType tables. The
     * client needs it for every trace it runs itself: CG_GetEntityBounds
     * 0x00485360 treats 0xffffff as an inline brush model and otherwise
     * UNPACKS this word into the entity's bounding box (half.x = half.y =
     * (solid & 0xff) - 1, mins.z = ((solid >> 8) & 0xff) - 1, maxs.z =
     * ((solid >> 16) & 0xff) - 32 - mins.z + 1), and 0x00485320 gives eType 1
     * (ET_PLAYER) the contents mask 0x2000000 and every other type 1. A zero
     * word decodes to an INVERTED box, so a client whose server never
     * publishes it cannot hit any player with a client-side trace: no
     * predicted collision, and no crosshair scan result either.
     *
     * The retained SV_LinkEntity packer (0x0054f153 in this build) already
     * produces C1's spelling for the two bytes that matter: byte0 =
     * clamp(maxs.x, 1, 255) and byte2 = clamp(maxs.z + 32, 1, 255) are exactly
     * what C1's own packer 0x005d88b5/0x005d88d2 writes. The middle byte is
     * the one place the retained IW3 code disagrees: it stores
     * clamp(1 - mins.z) where C1 stores clamp(mins.z + 1) (0x005d8865). They
     * agree for every box whose mins.z is 0 - every player and every corpse -
     * and for anything else C1 would decode the IW3 reading as a box floating
     * above the entity, so invert that byte back rather than ship it raw. */
    if(es->solid && es->solid!=SOLID_BMODEL) {
        uint32_t packed=(uint32_t)es->solid;
        int base=2-(int)((packed>>8)&0xffu);
        if(base<1) base=1;
        if(base>255) base=255;
        /* Best effort: dropping the entity would be worse than an eType whose
         * table somehow lacked the field, and every measured table carries it. */
        (void)put_entity(&out,0x0a8,
            (packed&0xffu)|((uint32_t)base<<8)|(packed&UINT32_C(0xff0000)));
    }
    if(!CODOL_OverlayEngineLoopSound(&out,es)) return 0;
    if(!CODOL_OverlayEngineEntityEventQueueVisible(&out,es,parameters,visibleSlots)) return 0;
    *wire=out; return 1;
}
int CODOL_OverlayEngineEntityVisible(codol_entity_state_t *wire,const entityState_t *es,
                                    const uint32_t parameters[4],unsigned visibleSlots)
{
    return overlay_entity_visible(wire,es,parameters,visibleSlots,1);
}
int CODOL_OverlayEngineEntityVisibleUnlinked(codol_entity_state_t *wire,const entityState_t *es,
                                            const uint32_t parameters[4],unsigned visibleSlots)
{
    return overlay_entity_visible(wire,es,parameters,visibleSlots,0);
}
int CODOL_OverlayEngineEntity(codol_entity_state_t *wire,const entityState_t *es,
                             const uint32_t parameters[4])
{
    return CODOL_OverlayEngineEntityVisible(wire,es,parameters,15u);
}
int CODOL_OverlayEnginePlayerEntity(codol_entity_state_t *wire,const entityState_t *es,
    unsigned primary_weapon,const uint32_t parameters[4])
{
    codol_entity_state_t result;
    if(!wire || !es || es->eType!=ET_PLAYER || wire->type!=ET_PLAYER) return 0;
    result=*wire;
    if(!CODOL_OverlayEngineEntity(&result,es,parameters) ||
       !CODOL_OverlayEnginePlayerEntityWeapons(&result,es,primary_weapon)) return 0;
    *wire=result; return 1;
}

/* C1 earthquake538a0d/19/16 and physics sphere54557e/58b/660.
 * Payload comes only from the captured entity union, including archive replay. */
int CODOL_OverlayEnginePhysicsEvent(codol_entity_state_t *wire,const entityState_t *es)
{
    codol_entity_state_t out;
    if(!wire || !es || CODOL_EntityTypeToWire(es->eType)!=(int)wire->type)return 0;
    out=*wire;
    if(es->eType==ET_EVENTS+EV_EARTHQUAKE) {
        const struct LerpEntityStateEarthquake *q=&es->lerp.u.earthquake;
        if(!isfinite(q->scale) || q->scale<=0 || !isfinite(q->radius) || q->radius<=0 || q->duration<=0)return 0;
        if(!entity_float(&out,0x058,q->scale) || !entity_float(&out,0x05c,q->radius) ||
           !put_entity(&out,0x060,(uint32_t)q->duration))return 0;
    } else if(es->eType==ET_EVENTS+EV_PHYS_EXPLOSION_SPHERE) {
        const struct LerpEntityStateExplosion *p=&es->lerp.u.explosion;
        if(!isfinite(p->innerRadius) || !isfinite(p->outerRadius) || !isfinite(p->magnitude) ||
           p->innerRadius<0 || p->outerRadius<p->innerRadius)return 0;
        if(!entity_float(&out,0x058,p->innerRadius) || !entity_float(&out,0x05c,p->outerRadius) ||
           !entity_float(&out,0x060,p->magnitude))return 0;
    } else return 0;
    if(!put_entity(&out,0x0ac,0))return 0;
    *wire=out;return 1;
}
