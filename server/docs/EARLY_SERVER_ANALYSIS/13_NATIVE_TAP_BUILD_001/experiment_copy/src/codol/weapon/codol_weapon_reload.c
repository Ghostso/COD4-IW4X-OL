/* Native C1 dual-magazine reload phases. No client-side patches. */
#ifdef CODOL_SERVER
#include "codol_weapon_bits.h"
#include "codol_weapon_reload.h"
#include "codol_weapon_native.h"
#include "codol_playerstate_ext.h"
#include "bg_public.h"
#include "bg.h"
#include "qcommon_io.h"

/* Transition-only evidence for the reported missing alternate reload. Bounded
 * per process; never runs from the per-frame snapshot or weapon clock loops. */
static unsigned reload_trace_count;
static void trace_reload(const playerState_t *ps,const char *transition,
    int before,int after,int duration,int add_time)
{
    const struct WeaponDef *def;
    const codol_ps_hand_t *hand;
    unsigned raw,wire_animation=0;
    if(reload_trace_count>=48 || !ps)return;
    ++reload_trace_count;
    def=ps->weapon && ps->weapon<CODOL_WEAPON_SLOTS ? BG_GetWeaponDef(ps->weapon) : NULL;
    hand=CODOL_PlayerStateHandRead(ps);
    raw=(unsigned)ps->weapAnim;
    if((raw&31u)==13)wire_animation=hand->primary_reload_fast ? 14 : 13;
    else if((raw&31u)==14)wire_animation=hand->primary_reload_fast ? 16 : 15;
    if(wire_animation && (raw&0x200u))wire_animation|=0x400u;
    Com_DPrintf(CON_CHANNEL_SERVER,
        "CoDOL dualmag %s: client %d weapon %u quick %d -> %d state %d anim %u expectedC1Anim %u phaseQuick %u time %d add %d clip %d\n",
        transition,ps->clientNum,ps->weapon,before,after,ps->weaponstate,
        raw,wire_animation,(unsigned)hand->primary_reload_fast,
        duration,add_time,def ? ps->ammoclip[def->iClipIndex] : -1);
}

static void event(playerState_t *ps,BGEvent id)
{ BG_AddPredictableEventToPlayerstate(id,0,(gclient_t *)ps); }
static const struct WeaponDef *definition(const playerState_t *ps)
{ return ps && ps->weapon && ps->weapon<CODOL_WEAPON_SLOTS ? BG_GetWeaponDef(ps->weapon) : NULL; }
static int dual_mag(const struct WeaponDef *def)
{
    codol_weapon_timing_extensions_t timings; int enabled=0;
    return def && CODOL_GetNativeWeaponReloadData(def,&enabled,&timings) && enabled;
}
static int quick(const playerState_t *ps)
{
    const codol_ps_hand_t *hand=CODOL_PlayerStateHandRead(ps);
    return ps->weapon<CODOL_PS_EXT_WEAPON_BITS && !!(hand->fast_mag[ps->weapon>>5] & (1u<<(ps->weapon&31)));
}
static int slot_named(const struct WeaponDef *def,unsigned slot)
{
    const char *name=NULL;
    return CODOL_GetNativeWeaponAnimationName(def,slot,&name) && name && *name;
}
/* Whether the client can show the quick branch of this reload phase.
 *
 * C1 selects the quick branch from inventory byte2 and def+0xbc7 alone
 * (0x419347..0x419354) and starts wire animation 14/16 through 0x418080;
 * it never consults the names. The viewmodel then maps wire 13/14/15/16 to
 * name slots 9/10/11/12 (0x47be58 entries -> 0x47ad10(9..12), i.e. source
 * +0xa0/+0xa4/+0xa8/+0xac) and registers an EMPTY slot as the idle animation
 * (0x47c0d6..0x47c0df). The shipped patch_common_gametype_mp seeds the quick
 * slots of m4a1tech_mp but leaves m4a1techevent_mp's +0xa4/+0xac empty (so
 * does ui_viewer_mp's copy), and the patched dualmags_m4tech entries are
 * "[r] reload ..." replacements that leave an empty source empty; so every
 * quick reload of that composed weapon shows idle on C1 itself. The composed
 * core retains the same post-override names the client builds.
 * Akimbo hands use the two dual banks (+0x13c/+0x1fc). */
static int quick_animation_shown(const struct WeaponDef *def,int empty)
{
    unsigned quick=empty ? 12u : 10u,normal=empty ? 11u : 9u,bank;
    int dual_wield=0,shown=1;
    if(!CODOL_GetNativeWeaponDualWield(def,&dual_wield))dual_wield=0;
    for(bank=dual_wield ? 48u : 0u;bank<(dual_wield ? 144u : 48u);bank+=48u)
        if(!slot_named(def,bank+quick) && slot_named(def,bank+normal))shown=0;
    return shown;
}
/* A dual magazine whose quick reload the client can actually show.
 *
 * The next-magazine bit is the ONLY input C1 uses to pick the quick branch,
 * and the server publishes it (inventory flag4, codol_engine_state.c). For a
 * weapon whose quick animation slots are empty the quick magazine is never
 * armed, so the client predicts the normal branch (wire 13/15, its real
 * dual-mag reload animation, stock duration +0x5c8/+0x5d4) and the server
 * runs exactly the same phase. The previous adaptation kept the quick
 * duration under the normal animation: the client first predicted wire 14/16
 * (idle), then snapped to the normal animation, which was cut short because
 * C1 paces it to the normal duration. The quick-reload speed of such a
 * weapon is given up: C1's own data has no animation for it. */
static int quick_usable(const struct WeaponDef *def)
{
    return dual_mag(def) && quick_animation_shown(def,0) && quick_animation_shown(def,1);
}
void CODOL_WeaponReloadSelected(playerState_t *ps,unsigned weapon)
{
    codol_ps_hand_t *hand=CODOL_PlayerStateHandMutable(ps); unsigned bit;
    int before,enabled;
    if(!hand || !weapon || weapon>=CODOL_PS_EXT_WEAPON_BITS)return;
    bit=1u<<(weapon&31);
    before=!!(hand->fast_mag[weapon>>5]&bit);
    enabled=quick_usable(BG_GetWeaponDef(weapon));
    /* C1 FinishWeaponChange419dc4..419ded initializes byte2 from def+bc7
     * on every raise. A fresh selection starts on the quick magazine, unless
     * the client has no quick animation to show (quick_usable). */
    if(enabled)hand->fast_mag[weapon>>5]|=bit;
    else hand->fast_mag[weapon>>5]&=~bit;
    hand->primary_reload_fast=0;
    if(enabled)trace_reload(ps,"select",before,1,ps->weaponTime,ps->weaponDelay);
}
void CODOL_WeaponReloadRemoved(playerState_t *ps,unsigned weapon)
{
    codol_ps_hand_t *hand=CODOL_PlayerStateHandMutable(ps);
    if(hand && weapon<CODOL_PS_EXT_WEAPON_BITS)hand->fast_mag[weapon>>5]&=~(1u<<(weapon&31));
}
void CODOL_WeaponReloadClipFinished(playerState_t *ps)
{
    codol_ps_hand_t *hand;
    int before;
    if(!quick_usable(definition(ps)) || !(hand=CODOL_PlayerStateHandMutable(ps)))return;
    /* C1 PM_ReloadClip41e5e2..41e62e toggles after the transfer attempt,
     * including a zero-round attempt. Cancellation before it leaves it alone. */
    before=quick(ps);
    if(ps->weapon>=CODOL_PS_EXT_WEAPON_BITS)return;   /* no dual-mag bit above the bundle */
    hand->fast_mag[ps->weapon>>5]^=1u<<(ps->weapon&31);
    trace_reload(ps,"transfer",before,!before,ps->weaponTime,ps->weaponDelay);
}
int CODOL_WeaponReloadInfo(const playerState_t *ps,const struct WeaponDef *def,int empty,
    int *duration,int *add_time,int *fast)
{
    codol_weapon_timing_extensions_t timings; int enabled;
    if(!ps || !def || !duration || !add_time || !fast ||
       !CODOL_GetNativeWeaponReloadData(def,&enabled,&timings))return 0;
    *fast=enabled && quick(ps);
    *duration=empty ? (*fast ? timings.reload_empty_variant : def->iReloadEmptyTime) :
        (*fast ? timings.reload_variant : def->iReloadTime);
    *add_time=empty ? (*fast ? timings.reload_empty_add_variant : timings.reload_empty_add) :
        (*fast ? timings.reload_add_variant : def->iReloadAddTime);
    /* C1 4191c8..41925a: zero or overlong add time means end of animation. */
    if(!*add_time || *add_time>=*duration)*add_time=*duration;
    return 1;
}
static int reload_add(const playerState_t *ps,const struct WeaponDef *def,int *duration,int *fast)
{
    int add;
    if(ps->weaponstate==9 || ps->weaponstate==10) {
        *duration=def->iReloadStartTime; *fast=0;
        add=def->iReloadStartAddTime;
        return add && add>*duration ? *duration : add;
    }
    if(!CODOL_WeaponReloadInfo(ps,def,!ps->ammoclip[def->iClipIndex] && !def->weapType,
        duration,&add,fast))return 0;
    return add;
}
int CODOL_FastMagSetReloadingState(playerState_t *ps)
{
    const struct WeaponDef *def=definition(ps);
    codol_ps_hand_t *hand=CODOL_PlayerStateHandMutable(ps);
    int empty,time,add,fast;
    if(hand)hand->primary_reload_fast=0;
    if(!dual_mag(def))return 0;
    empty=!ps->ammoclip[def->iClipIndex] && !def->weapType;
    if(!CODOL_WeaponReloadInfo(ps,def,empty,&time,&add,&fast))return 0;
    /* The captured phase is what the C1 publisher turns into wire 14/16. */
    if(hand)hand->primary_reload_fast=(unsigned char)fast;
    /* Native weapAnim keeps its native animation IDs; the C1 publisher uses
     * the captured branch above to emit C1 quick IDs14/16 for this phase. */
    /* C1 0x418080 writes the animation below PM_DEAD (8), last stand too. */
    if(ps->pm_type<8)ps->weapAnim=((~ps->weapAnim)&0x200)|(empty ? 14 : 13);
    ps->weaponTime=time;
    event(ps,empty ? EV_RELOAD_FROM_EMPTY : EV_RELOAD);
    ps->weaponstate=ps->weaponstate==10 ? 8 : 7;
    if(def->bBoltAction && CODOL_WeaponBitsRechamberTest(ps,ps->weapon)) {
        if(!add)add=time;
        if(def->iRechamberBoltTime<add)add=def->iRechamberBoltTime;
        if(!add)add=1;
    }
    if(add)ps->weaponDelay=add;
    trace_reload(ps,empty ? "start-empty" : "start",fast,fast,time,add);
    return 1;
}
int CODOL_FastMagReloadClip(playerState_t *ps)
{
    const struct WeaponDef *def=definition(ps); int add,cap,start;
    if(!dual_mag(def))return 0;
    start=ps->weaponstate==9 || ps->weaponstate==10;
    if(start && !def->iReloadStartAdd)return 1;
    add=def->iClipSize-ps->ammoclip[def->iClipIndex];
    if(add>ps->ammo[def->iAmmoIndex])add=ps->ammo[def->iAmmoIndex];
    cap=start ? def->iReloadStartAdd : def->iReloadAmmoAdd;
    if(cap && cap<def->iClipSize && add>cap)add=cap;
    if(add) {
        ps->ammoclip[def->iClipIndex]+=add;
        ps->ammo[def->iAmmoIndex]-=add;
        event(ps,EV_RELOAD_ADDAMMO);
    }
    CODOL_WeaponReloadClipFinished(ps);
    return 1;
}
int CODOL_FastMagReloadDelayedAction(playerState_t *ps)
{
    const struct WeaponDef *def=definition(ps); int add,time,fast,bolt;
    if(!dual_mag(def))return 0;
    if(def->bBoltAction && CODOL_WeaponBitsRechamberTest(ps,ps->weapon)) {
        CODOL_WeaponBitsRechamberSet(ps,ps->weapon,0);
        event(ps,EV_EJECT_BRASS);
        if((ps->weaponstate==9 || ps->weaponstate==10) && !def->iReloadStartAddTime)return 1;
        if(ps->weaponTime) {
            add=reload_add(ps,def,&time,&fast);
            bolt=def->iRechamberBoltTime<add ? def->iRechamberBoltTime : 1;
            add-=bolt;
            if(add>=1) { ps->weaponDelay=add; return 1; }
        }
    }
    return CODOL_FastMagReloadClip(ps);
}
#endif
