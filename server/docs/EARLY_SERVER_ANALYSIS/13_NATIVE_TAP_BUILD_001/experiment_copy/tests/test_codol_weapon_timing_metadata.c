/* Optional per-weapon timing metadata must degrade, never drop the server.
 *
 * Regression: the AC-130 was activated live, the player was handed
 * ac130_40mm_mp, and the very next line was
 *
 *   ERROR: CoDOL weapon reload perk metadata unavailable
 *   ----- Server Shutdown ----- Server crashed: ...
 *
 * weapon_frame_msec computes nothing but a timing MULTIPLIER, and all three of
 * its inputs are optional: IW4 treats the reload-perk field on a WeaponDef as
 * optional (absent means the perk does not apply) and the ability modifier
 * table is a tuning table. Killstreak-held weapons - the three AC-130 guns,
 * the chopper gunner minigun, the sentry and predator weapons - are precisely
 * the weapons with no reload metadata, because they never reload.
 *
 * This test drives CODOL_WeaponFrameMsec with each input missing in turn and
 * requires the unmodified duration back, exactly one warning per weapon per
 * cause, and a working modifier still applied on the normal path. The engine
 * dependencies are stubbed so the assertions are about this decision alone.
 */
#include "bg.h"
#include "codol_weapon_state.h"
#include "codol_playerstate_ext.h"
#include "codol_abilities.h"
#include "codol_assets.h"
#include "codol_weapon_input.h"
#include "codol_entitystate_ext.h"
#include "codol_weapon_native.h"
#include "xassets/weapondef.h"
#include <assert.h>
#include <stdarg.h>
#include <string.h>
#include <stdio.h>

/* ---- controllable stubs -------------------------------------------- */
static codol_ps_ext_t stub_ext;
static struct WeaponDef stub_def;
static int stub_inherits_ok, stub_inherits_value;
static int stub_table_ok;
static float stub_modifier;
static unsigned warnings;

const codol_ps_ext_t *CODOL_PlayerStateExtConst(const playerState_t *ps)
{ (void)ps; return &stub_ext; }
int BG_GetNumWeapons(void) { return 128; }
struct WeaponDef *BG_GetWeaponDef(int index) { (void)index; return &stub_def; }
int CODOL_GetNativeWeaponInheritsPerks(const struct WeaponDef *def,int *out)
{
    (void)def;
    if(!stub_inherits_ok) return 0;          /* no metadata: the AC-130 case */
    *out = stub_inherits_value; return 1;
}
int CODOL_LoadEngineStringTable(const char *name,const codol_engine_table_t **out)
{
    static const codol_engine_table_t *table = (const codol_engine_table_t *)1;
    (void)name;
    if(!stub_table_ok) return 0;
    *out = table; return 1;
}
int CODOL_GetActiveAbilityValue(const codol_client_abilities_t *a,
    const codol_engine_table_t *t,unsigned id,float *out)
{
    (void)a; (void)t; (void)id;
    if(!stub_table_ok) return 0;
    *out = stub_modifier; return 1;
}
void Com_PrintWarning(unsigned channel,const char *fmt,...)
{
    va_list args;
    (void)channel;
    ++warnings;
    fputs("  [warn] ",stderr);
    va_start(args,fmt); vfprintf(stderr,fmt,args); va_end(args);
}

/* Unreferenced by the paths under test, but named by the translation unit.
 * Signatures follow the real headers so nothing is silently mismatched. */
void __cdecl BG_AddPredictableEventToPlayerstate(const BGEvent e,const byte p,gclient_t *c)
{ (void)e; (void)p; (void)c; }
void CODOL_EntityStatePrimaryWeaponCaptured(entityState_t *es,unsigned primary,int resolved)
{ (void)es; (void)primary; (void)resolved; }
int CODOL_ExecutedWeaponInput(unsigned client,codol_weapon_input_t *out)
{ (void)client; (void)out; return 0; }
void CODOL_PlayerStateExtClearClientHand(unsigned client){ (void)client; }
void CODOL_PlayerStateExtClearClientOffhand(unsigned client){ (void)client; }
codol_ps_hand_t *CODOL_PlayerStateHandMutable(const playerState_t *ps){ (void)ps; return NULL; }
const codol_ps_hand_t *CODOL_PlayerStateHandRead(const playerState_t *ps){ (void)ps; return NULL; }
codol_ps_offhand_t *CODOL_PlayerStateOffhandMutable(const playerState_t *ps){ (void)ps; return NULL; }
const codol_ps_offhand_t *CODOL_PlayerStateOffhandRead(const playerState_t *ps){ (void)ps; return NULL; }
int CODOL_WeaponLockFireEvent(const playerState_t *ps,const struct WeaponDef *w)
{ (void)ps; (void)w; return 0; }
void CODOL_WeaponReloadClipFinished(playerState_t *ps){ (void)ps; }
int CODOL_WeaponReloadInfo(const playerState_t *ps,const struct WeaponDef *w,int empty,
    int *duration,int *add_time,int *fast)
{ (void)ps; (void)w; (void)empty; (void)duration; (void)add_time; (void)fast; return 0; }
void CODOL_WeaponReloadRemoved(playerState_t *ps,unsigned weapon){ (void)ps; (void)weapon; }
void CODOL_WeaponReloadSelected(playerState_t *ps,unsigned weapon){ (void)ps; (void)weapon; }
int Mantle_IsWeaponInactive(playerState_t *ps){ (void)ps; return 0; }
cvar_t *player_sustainAmmo;
/* The offhand and dive phases' asset queries. */
int CODOL_GetNativeWeaponOffhandCancel(const struct WeaponDef *def,int *out)
{ (void)def; (void)out; return 0; }
int CODOL_GetNativeWeaponUnlimitedAmmo(const struct WeaponDef *def,int *out)
{ (void)def; (void)out; return 0; }
int CODOL_GetNativeWeaponClass(const struct WeaponDef *def,unsigned *out)
{ (void)def; (void)out; return 0; }
int CODOL_GetNativeWeaponReloadData(const struct WeaponDef *def,int *dual_mag,
    codol_weapon_timing_extensions_t *timings)
{ (void)def; (void)dual_mag; (void)timings; return 0; }
void __cdecl CODOL_WeaponOffhandPhaseTime(playerState_t *ps){ (void)ps; }

/* ---- the test ------------------------------------------------------- */
#define ABILITY_RELOAD_PERK 0x40000000u   /* phases 7..11 */
#define ABILITY_BAND_LOW    0x200u        /* phases 1..4  */

static void arm(unsigned weapon,unsigned phase,uint32_t mask,playerState_t *ps)
{
    memset(ps,0,sizeof(*ps));
    ps->weapon=(int)weapon; ps->weaponstate=(int)phase;
    memset(&stub_ext,0,sizeof(stub_ext));
    stub_ext.abilities_known=1;
    stub_ext.abilities.masks[0]=mask;
    warnings=0;
}

int main(void)
{
    playerState_t ps;

    CODOL_ResetWeaponTimingReports();

    /* 1. The live crash: reload phase, reload perk active, weapon has no
     *    reload metadata at all. Must return the duration unchanged. */
    stub_inherits_ok=0; stub_table_ok=1; stub_modifier=0.5f;
    arm(61,7,ABILITY_RELOAD_PERK,&ps);
    assert(CODOL_WeaponFrameMsec(&ps,1000)==1000);
    assert(warnings==1);

    /* Reported once per weapon, not once per frame: this runs every weapon
     * frame and would otherwise flood the log. */
    { unsigned phase;
      for(phase=7;phase<=11;++phase) {
          ps.weaponstate=(int)phase;
          assert(CODOL_WeaponFrameMsec(&ps,1000)==1000);
      }
      assert(warnings==1); }

    /* A different weapon with the same gap still reports, so a second missing
     * definition is not hidden by the first. */
    arm(62,7,ABILITY_RELOAD_PERK,&ps);
    assert(CODOL_WeaponFrameMsec(&ps,1000)==1000);
    assert(warnings==1);

    /* 2. Metadata present and the perk does not apply to this weapon: no
     *    modifier, no warning. */
    stub_inherits_ok=1; stub_inherits_value=0;
    arm(63,7,ABILITY_RELOAD_PERK,&ps);
    assert(CODOL_WeaponFrameMsec(&ps,1000)==1000);
    assert(warnings==0);

    /* 3. The normal path still applies the modifier - the degradation above
     *    must not have turned the feature off. */
    stub_inherits_ok=1; stub_inherits_value=1; stub_table_ok=1; stub_modifier=0.5f;
    arm(64,7,ABILITY_RELOAD_PERK,&ps);
    assert(CODOL_WeaponFrameMsec(&ps,1000)==500);
    assert(warnings==0);

    /* 4. Ability table or row missing: unmodified duration, warned once. */
    stub_table_ok=0;
    arm(65,1,ABILITY_BAND_LOW,&ps);
    assert(CODOL_WeaponFrameMsec(&ps,800)==800);
    assert(warnings==1);
    assert(CODOL_WeaponFrameMsec(&ps,800)==800);
    assert(warnings==1);

    /* 5. A modifier that cannot be represented: unmodified duration, warned
     *    once, and never a garbage timing. */
    stub_table_ok=1; stub_modifier=1e30f;
    arm(66,1,ABILITY_BAND_LOW,&ps);
    assert(CODOL_WeaponFrameMsec(&ps,1000)==1000);
    assert(warnings==1);

    /* 6. No abilities published at all: untouched, silent. */
    arm(67,7,ABILITY_RELOAD_PERK,&ps);
    stub_ext.abilities_known=0; stub_inherits_ok=0;
    assert(CODOL_WeaponFrameMsec(&ps,1234)==1234);
    assert(warnings==0);

    /* 7. A zone change renumbers weapons, so the reset must re-arm the
     *    warning for a weapon index that already reported. */
    stub_inherits_ok=0; stub_table_ok=1;
    arm(61,7,ABILITY_RELOAD_PERK,&ps);
    assert(CODOL_WeaponFrameMsec(&ps,1000)==1000);
    assert(warnings==0);                     /* weapon 61 already reported */
    CODOL_ResetWeaponTimingReports();
    warnings=0;
    assert(CODOL_WeaponFrameMsec(&ps,1000)==1000);
    assert(warnings==1);

    puts("PASS: weapon timing degrades to unmodified duration on absent reload metadata, absent ability rows and unrepresentable modifiers, warns once per weapon per cause, and still applies a valid modifier");
    return 0;
}
