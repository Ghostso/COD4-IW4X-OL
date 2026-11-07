/* C1 hold-breath state: the server-side half of scope sway.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * What C1 draws sway from (C1.exe 1.1.1.13, static):
 *   - ps+0x24c holdBreathScale (float, netfield 34, format -88) and
 *     ps+0x250 holdBreathTimer (int, netfield 193, 16 bits) are produced by
 *     PM_UpdateHoldBreath 0x004188b0, called from PM_Weapon at 0x0041dc02
 *     right after the ADS lerp update. The client predicts the same function
 *     from every snapshot's playerState, so a server that never writes the
 *     two words re-bases the client's scale to 0 on every snapshot: the
 *     weapon sway multiplier saw-tooths between 0 and the client's lerp toward
 *     1.0 instead of holding the C1 values (1.0 normal, 0 held, up to 4.5
 *     during the gasp).
 *   - ps+0x344 bit 4 (PWF_HOLDING_BREATH) is consumed by the breath HUD hint
 *     CG_DrawBreathHint 0x45763a..0x4576df together with ps+0x250 == 0.
 *   - The weapon-side sway amplitudes are read by the client from its own
 *     WeaponDef; no dvar is involved: the breath timings are inlined
 *     constants in this build (4500 ms hold at 0x4188c5, +1000 ms gasp at
 *     0x418995, gasp scale 3.5 at 0xc84688, gasp lerp 6.0 at 0xc39ddc, hold
 *     lerp 1.0, fire delay -0.0 at 0xc84920), so there is nothing to
 *     replicate for it.
 *
 * Algorithm, 0x004188b0 (pm, pml):
 *   hold = 4500
 *   if ability 13 (ps+0x4d0 bit 18): hold -= (int)(value13 * -1000.0)
 *       if hold <= 0: flag off, scale = 1, timer = 0, return   (0x4188f7)
 *   if posFrac == 1 && BG_CanHoldBreath(ps) && cmd.buttons & 0x2000:
 *       if timer == 0: flag on                                (0x418945)
 *   else flag off                                             (0x41894e)
 *   timer += flag ? msec : -msec; timer = max(timer, 0)
 *   if flag && timer > hold: timer = hold + 1000, flag off     (0x418995)
 *   flag ? (target 0, rate 1) : (target timer/(hold+1000)*3.5 + 1, rate 6)
 *   goal  = 1 + (target - 1) * posFrac                         (0x418a08..13)
 *   scale = DiffTrack(goal, scale, rate, dt)                   (0x418a1e/23)
 *   if ability 26 (bit 5): scale = value26                     (0x418a51)
 * The goal anchor is the literal 1.0, NOT the running scale: at posFrac < 1 the
 * two forms converge to different values, which is what made the published
 * scale disagree with the client's own prediction on every partially-scoped
 * frame.
 * BG_CanHoldBreath 0x421f00: def(ps+0x33c)+0x694 (overlayReticle) != 0 &&
 *   posFrac != 0 && def+0x344 (class) != 11 && !ability 26.  The definition is
 *   the COMPOSED one, so the base image's +0x694 is replayed through each
 *   attachment's type-43 override entries (C1 0x421590) before the test.
 * Fire path 0x418810 (from 0x41bafb): same def gates, then clears the flag.
 *
 * The retained PM_Weapon still runs IW3's inlined copy (player_breath_* dvars,
 * gasp scale-1 anchored to 1.0, overlayReticle gate on the IW3 field that the
 * composed-weapon converter does not fill). It is not the C1 producer, so its
 * result is discarded: the three words are captured before PM_Weapon and
 * recomputed afterwards from that capture. */
#ifdef CODOL_SERVER
#include "codol_pmove_c1_breath.h"
#include "codol_playerstate_ext.h"
#include "codol_abilities.h"
#include "codol_assets.h"
#include "codol_weapon_compose.h"
#include "codol_weapon_native.h"
#include "bg.h"
#include "bg_public.h"
#include "player.h"
#include "q_shared.h"
#include "qcommon_io.h"
#include <math.h>
#include <string.h>

#define C1_BUTTON_BREATH 0x2000u
#define C1_BREATH_HOLD_MS 4500
#define C1_BREATH_GASP_MS 1000
#define C1_WEAPCLASS_MELEE 11u
#define C1_ABILITY_EXTRA_BREATH 13u
#define C1_ABILITY_BREATH_SCALE 26u
#define C1_WEAPONDEF_OVERLAY_RETICLE 0x694u
/* C1 CG_GetCrosshairColor 0x0043c4f6 gates the whole friend/foe crosshair
 * colouring on this byte of the held definition. Reported here so the live log
 * says what the composed weapons this server publishes actually carry. */
#define C1_WEAPONDEF_CROSSHAIR_GATE 0xbc3u
/* C1 PM_CanProne 0x412210 and PM_CanDive 0x408ed3 refuse while the held or
 * commanded definition carries this byte (the IW3 blocksProne role). The
 * retained WeaponDef field is not filled by the composed-weapon converter. */
#define C1_WEAPONDEF_BLOCKS_PRONE 0xbd9u
/* Per-index cache bound; the 700-wide CoDOL ownership fits. */
#define C1_BREATH_CACHE_WEAPONS 1024u

/* C1 0x618c10: move cur toward goal at rate/s over dt, snapping when within
 * 0.001 or when the step would overshoot. */
static float diff_track_c1(float goal,float cur,float rate,float dt)
{
    float diff=goal-cur, step=diff*rate*dt;
    if(fabsf(diff)<=0.001f) return goal;
    if(fabsf(step)>fabsf(diff)) return goal;
    return cur+step;
}

/* Keyed by a raw `const WeaponDef *`, so valid only while those definitions
 * live. File scope rather than function scope so the asset-category teardown
 * can drop them: it frees the composed weapon cores these pointers name, and a
 * recycled address in the next category would false-match and answer with the
 * previous category's scope flag. */
static const struct WeaponDef *cached_def[C1_BREATH_CACHE_WEAPONS];
static int cached_scope[C1_BREATH_CACHE_WEAPONS];
static unsigned char cached_blocks_prone[C1_BREATH_CACHE_WEAPONS];

void CODOL_ResetBreathScopeCache(void)
{
    memset(cached_def,0,sizeof cached_def);
    memset(cached_scope,0,sizeof cached_scope);
    memset(cached_blocks_prone,0,sizeof cached_blocks_prone);
}

/* def+0x694 of the C1 runtime definition. The retained WeaponDef has no
 * converted copy, so read the serialized base image the definition was built
 * from (type-28 blob is the runtime def; +0x694 sits well inside the 0xbfc
 * fixed part). A composed definition resolves through its base; attachments
 * that add a scope overlay are not visible here until the weapon core
 * captures +0x694 itself. Cached per weapon index for the definition pointer. */
static int weapon_has_scope_overlay(unsigned weapon,const struct WeaponDef *def)
{
    unsigned blocks_prone=0;
    const struct WeaponDef *base=NULL;
    codol_mounted_weapon_t mounted;
    int scope=0;
    uint32_t reticle=0;
    unsigned crosshair_gate=0x100u; /* 0x100 = image too small / absent */
    /* C1 sway parameters, for the zone-image vs live-runtime comparison in
     * docs/CODOL_IMPLEMENTATION_PASS.md 2026-09-16: BG_GetSwayParams 0x422fe0
     * and BG_GetAdsSteadySwayAngle 0x422e20 read +0x6ec/+0x6f0/+0x6f4/+0x6f8/
     * +0x6fc/+0x700/+0x714/+0x718 and select the override path on +0xbc8. */
    float sway[8]; unsigned ads_allowed=0x100u; unsigned s;
    for(s=0;s<8;++s) sway[s]=0.0f;
    if(!def) return 0;
    if(weapon<C1_BREATH_CACHE_WEAPONS && cached_def[weapon]==def) return cached_scope[weapon];
    if(CODOL_ComposedWeaponBaseDefinition(def,&base)!=1 || !base) base=def;
    if(base->szInternalName && base->szInternalName[0] &&
       CODOL_LoadMountedWeapon(base->szInternalName,&mounted)==1 &&
       mounted.asset.data && mounted.asset.size>=C1_WEAPONDEF_OVERLAY_RETICLE+4) {
        uint32_t word;
        memcpy(&word,mounted.asset.data+C1_WEAPONDEF_OVERLAY_RETICLE,4);
        scope=word!=0;
        reticle=word;
        if(mounted.asset.size>C1_WEAPONDEF_CROSSHAIR_GATE)
            crosshair_gate=mounted.asset.data[C1_WEAPONDEF_CROSSHAIR_GATE];
        /* +0x6ec..+0x700 is six contiguous floats; +0x714/+0x718 are NOT the
         * seventh and eighth of that run. Copying 32 bytes from +0x6ec printed
         * +0x704/+0x708 under the 714/718 labels, which is the whole of the
         * "the server's zone image disagrees with the client" finding in
         * docs/CODOL_IMPLEMENTATION_PASS.md 2026-09-16 (20:45) section 1. The
         * real +0x714/+0x718 agree with C1's live table on every weapon. */
        if(mounted.asset.size>=0x71cu) {
            memcpy(sway,mounted.asset.data+0x6ecu,6u*sizeof *sway);
            memcpy(sway+6,mounted.asset.data+0x714u,2u*sizeof *sway);
        }
        if(mounted.asset.size>0xbc8u) ads_allowed=mounted.asset.data[0xbc8u];
        if(mounted.asset.size>C1_WEAPONDEF_BLOCKS_PRONE)
            blocks_prone=mounted.asset.data[C1_WEAPONDEF_BLOCKS_PRONE];
    }
    /* C1 BG_BuildCustomWeaponDef 0x421590 applies every type-43 attachment's
     * {offset,type,value} override entries to the copied base image before the
     * client's BG_CanHoldBreath 0x421f00 reads def+0x694 out of it. Replay the
     * same entries here: a scope attachment on a base whose own image carries
     * zero there (every assault rifle) otherwise makes the server refuse a hold
     * the client grants, and the two predictions diverge every snapshot. */
    {
        const codol_composed_weapon_t *record=NULL;
        if(CODOL_ComposedWeaponRecord(def,&record)==1 && record) {
            unsigned a;
            for(a=0;a<record->count && a<CODOL_COMPOSED_ATTACHMENTS;++a) {
                const char *asset=NULL;
                codol_mounted_weapon_attachment_t att;
                unsigned e;
                if(!base->szInternalName || !base->szInternalName[0]) break;
                if(CODOL_ComposedAttachmentAssetName(base->szInternalName,record->items[a],
                                                     &asset)!=1 || !asset) continue;
                if(CODOL_LoadMountedWeaponAttachment(asset,&att)!=1) continue;
                for(e=0;e<att.count;++e) {
                    uint32_t off,val;
                    memcpy(&off,att.entries+12u*e,4);
                    if(off==C1_WEAPONDEF_BLOCKS_PRONE) {
                        memcpy(&val,att.entries+12u*e+8u,4);
                        blocks_prone=val&0xffu;
                    }
                    if(off==C1_WEAPONDEF_CROSSHAIR_GATE) {
                        memcpy(&val,att.entries+12u*e+8u,4);
                        crosshair_gate=val&0xffu;
                    }
                    if(off!=C1_WEAPONDEF_OVERLAY_RETICLE) continue;
                    memcpy(&val,att.entries+12u*e+8u,4);
                    reticle=val; scope=val!=0;
                }
                CODOL_FreeMountedWeaponAttachment(&att);
            }
        }
    }
    {   /* One line per weapon index on first resolution. The definition gate is
         * the one place a composed weapon can disagree with the client's own
         * definition and desynchronise the predicted breath state. */
        static int lines;
        if(CODOL_TRACE_VERBOSE() && lines<200) { ++lines;
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL breath def: weapon %u '%s' base '%s' overlayReticle(+0x694)=%u scope=%d crosshairGate(+0xbc3)=%u\n",
                weapon, def->szInternalName?def->szInternalName:"?",
                base->szInternalName?base->szInternalName:"?",
                (unsigned)reticle, scope, crosshair_gate);
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL breath def sway: weapon %u 6ec %.3f 6f0 %.3f 6f4 %.3f 6f8 %.3f 6fc %.3f 700 %.3f 714 %.3f 718 %.3f bc8 %u\n",
                weapon,sway[0],sway[1],sway[2],sway[3],sway[4],sway[5],sway[6],sway[7],ads_allowed);
        }
    }
    if(weapon<C1_BREATH_CACHE_WEAPONS) {
        cached_def[weapon]=def; cached_scope[weapon]=scope;
        cached_blocks_prone[weapon]=(unsigned char)(blocks_prone!=0);
    }
    return scope;
}

int CODOL_WeaponScopeOverlayC1(unsigned weapon)
{
    const struct WeaponDef *def=BG_GetWeaponDef((int)weapon);
    return def ? weapon_has_scope_overlay(weapon,def) : 0;
}

int CODOL_WeaponBlocksProneC1(unsigned weapon)
{
    const struct WeaponDef *def=BG_GetWeaponDef((int)weapon);
    if(!def || weapon>=C1_BREATH_CACHE_WEAPONS) return 0;
    (void)weapon_has_scope_overlay(weapon,def);
    return cached_def[weapon]==def && cached_blocks_prone[weapon];
}

static int ability_value(const playerState_t *ps,unsigned id,float *value)
{
    const codol_ps_ext_t *ext=CODOL_PlayerStateExtConst(ps);
    const codol_engine_table_t *table;
    if(!ext || !ext->abilities_known) return 0;
    if(!(ext->abilities.masks[id>>5]&(UINT32_C(0x80000000)>>(id&31)))) return 0;
    if(CODOL_LoadEngineStringTable("mp/coAbilityModifiersTable.csv",&table)!=1 ||
       CODOL_GetActiveAbilityValue(&ext->abilities,table,id,value)!=1) return 0;
    return 1;
}

/* C1 0x421f00 minus the ability-26 clause, shared with the fire path 0x418810
 * which tests only the definition and the ADS fraction. */
static int weapon_allows_breath(const playerState_t *ps)
{
    const struct WeaponDef *def=BG_GetWeaponDef(ps->weapon);
    unsigned cls=0;
    if(!def || !weapon_has_scope_overlay((unsigned)ps->weapon,def)) return 0;
    if(ps->fWeaponPosFrac==0.0f) return 0;
    if(CODOL_GetNativeWeaponClass(def,&cls)==1 && cls==C1_WEAPCLASS_MELEE) return 0;
    return 1;
}

int CODOL_CanHoldBreathC1(const playerState_t *ps)
{
    float unused;
    if(!ps || !weapon_allows_breath(ps)) return 0;
    return !ability_value(ps,C1_ABILITY_BREATH_SCALE,&unused);
}

void CODOL_HoldBreathSaveC1(const playerState_t *ps,codol_hold_breath_save_t *out)
{
    if(!ps || !out) return;
    out->scale=ps->holdBreathScale;
    out->timer=ps->holdBreathTimer;
    out->holding=(ps->weapFlags&CODOL_WEAP_HOLDING_BREATH)!=0;
    out->event_sequence=ps->eventSequence;
}

static int fired_this_command(const playerState_t *ps,int since)
{
    int s;
    for(s=since;s<ps->eventSequence;++s) {
        switch(ps->events[s&3]) {
        case EV_FIRE_WEAPON: case EV_FIRE_WEAPON_LASTSHOT: case EV_FIRE_WEAPON_MG42:
        case EV_FIRE_QUADBARREL_1: case EV_FIRE_QUADBARREL_2:
            return 1;
        default: break;
        }
    }
    return 0;
}

void CODOL_PM_UpdateHoldBreathC1(codol_pmove_c1_t *move,const codol_hold_breath_save_t *saved)
{
    playerState_t *ps;
    int hold=C1_BREATH_HOLD_MS, holding, msec;
    float value, target, rate, goal;
    if(!move || !move->ps) return;
    ps=move->ps;
    if(saved) {
        ps->holdBreathScale=saved->scale;
        ps->holdBreathTimer=saved->timer;
        if(saved->holding) ps->weapFlags|=CODOL_WEAP_HOLDING_BREATH;
        else ps->weapFlags&=~CODOL_WEAP_HOLDING_BREATH;
    }
    if(ability_value(ps,C1_ABILITY_EXTRA_BREATH,&value)) {
        hold-=(int)((double)value*-1000.0);
        if(hold<=0) {
            ps->weapFlags&=~CODOL_WEAP_HOLDING_BREATH;
            ps->holdBreathScale=1.0f;
            ps->holdBreathTimer=0;
            return;
        }
    }
    if(ps->fWeaponPosFrac==1.0f && CODOL_CanHoldBreathC1(ps) &&
       (move->cmd.buttons&C1_BUTTON_BREATH)) {
        if(ps->holdBreathTimer==0) ps->weapFlags|=CODOL_WEAP_HOLDING_BREATH;
    } else ps->weapFlags&=~CODOL_WEAP_HOLDING_BREATH;
    holding=(ps->weapFlags&CODOL_WEAP_HOLDING_BREATH)!=0;
    msec=move->local.msec;
    ps->holdBreathTimer+=holding ? msec : -msec;
    if(ps->holdBreathTimer<0) ps->holdBreathTimer=0;
    if(holding && ps->holdBreathTimer>hold) {
        ps->holdBreathTimer=hold+C1_BREATH_GASP_MS;
        ps->weapFlags&=~CODOL_WEAP_HOLDING_BREATH;
        holding=0;
    }
    if(holding) { target=0.0f; rate=1.0f; }
    else {
        target=(float)((double)((float)ps->holdBreathTimer/(float)(hold+C1_BREATH_GASP_MS))*3.5+1.0);
        rate=6.0f;
    }
    /* C1 0x418A08..0x418A13 blends the target against the CONSTANT 1.0, not
     * against the current scale: goal = 1 + (target-1)*adsFrac. Anchoring it
     * to the running scale (as this port first did) converges to `target`
     * instead of to the ADS-weighted target whenever adsFrac < 1, so every
     * partially-scoped frame published a value the client's own copy of
     * PM_UpdateHoldBreath did not reproduce and the sway snapped. */
    goal=1.0f+(target-1.0f)*ps->fWeaponPosFrac;
    ps->holdBreathScale=diff_track_c1(goal,ps->holdBreathScale,rate,move->local.frametime);
    if(ability_value(ps,C1_ABILITY_BREATH_SCALE,&value)) ps->holdBreathScale=value;
    /* 0x418810 from the fire request: a shot ends the hold. Its timer
     * adjustment multiplies by the inlined -0.0 fire delay, so only the flag
     * changes; the 4500 clamp cannot engage below hold+gasp either. */
    if(saved && fired_this_command(ps,saved->event_sequence) && weapon_allows_breath(ps))
        ps->weapFlags&=~CODOL_WEAP_HOLDING_BREATH;
    /* Live prediction-agreement trace: C1 runs this same function on the
     * client every frame from the last snapshot, so any server/client
     * disagreement in the gate or the integration shows up as snapping sway.
     * One line per 100 ms per client while the weapon is off the hip. */
    {
        static int idle_lines, hold_lines; static int last_ms[64];
        unsigned c=(unsigned)ps->clientNum;
        int active=(move->cmd.buttons&C1_BUTTON_BREATH)!=0 || ps->holdBreathTimer!=0 ||
                   (ps->weapFlags&CODOL_WEAP_HOLDING_BREATH)!=0;
        int *budget=active ? &hold_lines : &idle_lines;
        if(CODOL_TRACE_VERBOSE() && *budget<(active?1500:300) && c<64 &&
           ps->fWeaponPosFrac>0.0f &&
           (ps->commandTime-last_ms[c]>=100 || ps->commandTime<last_ms[c])) {
            last_ms[c]=ps->commandTime; ++*budget;
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL breath: c%u t%d w%u posFrac %.3f btn%d can%d hold%d timer %d scale %.4f msec %d ft %.4f\n",
                c,ps->commandTime,(unsigned)ps->weapon,ps->fWeaponPosFrac,
                (move->cmd.buttons&C1_BUTTON_BREATH)?1:0,CODOL_CanHoldBreathC1(ps),
                (ps->weapFlags&CODOL_WEAP_HOLDING_BREATH)?1:0,
                ps->holdBreathTimer,ps->holdBreathScale,
                move->local.msec,move->local.frametime);
        }
    }
}
#endif
