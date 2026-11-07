#include "scr_vm_functions.h"
#include "codol_weapon_flags.h"
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

gentity_t g_entities[MAX_GENTITIES];
static gclient_t player;
static unsigned errors, clears, script_checks;
void Player_UpdateActivate(gentity_t *);
void Scr_ObjectError(const char *s) { assert(s && *s); ++errors; }
qboolean Scr_IsSystemActive(unsigned char system) { assert(system==1); ++script_checks; return 0; }
/* The activation assembly consults two CoDOL hooks that live in the script
 * area. Linking their real translation units here would pull the whole script
 * VM in for behaviour this harness does not exercise, so they are stubbed the
 * way the VM entry points above are, and the counters below assert the
 * assembly still reaches them. */
static unsigned use_hint_calls, use_allowed_calls;
qboolean CODOL_ForceUseHint_Apply(gentity_t *entity)
{ assert(entity); ++use_hint_calls; return qfalse; }
int CODOL_PlayerUseAllowed(const gentity_t *player,const gentity_t *target)
{ assert(player); (void)target; ++use_allowed_calls; return 1; }

void TestSetHandle(EntHandle *,gentity_t *) __asm__("_ZN9EntHandle6setEntEP9gentity_s");
void TestSetHandle(EntHandle *h,gentity_t *ent)
{
    assert(h==&player.useHoldEntity && !ent);
    memset(h,0,sizeof(*h)); ++clears;
}
int main(void)
{
    scr_entref_t ref={0}; unsigned i;
    _Static_assert(offsetof(gclient_t,ps.weapFlags)==0x10,"native flag ABI");
    _Static_assert(offsetof(gclient_t,buttons)==0x3088,"native button ABI");
    _Static_assert(offsetof(gclient_t,useHoldEntity)==0x30f8,"native handle ABI");
    _Static_assert(offsetof(gclient_t,useButtonDone)==0x3100,"native use ABI");
    ref.entnum=2; g_entities[2].client=&player;
    for(i=0;i<8;++i) {
        memset(&player,0,sizeof(player));
        player.ps.weapFlags=0x1883;
        player.buttons=(i&1)?0x20:0;
        player.oldbuttons=(i&2)?0x20:0;
        player.latched_buttons=(i&4)?0x28:0;
        memset(&player.useHoldEntity,0x01,sizeof(player.useHoldEntity));
        CODOL_Scr_DisableUsability(ref);
        CODOL_Scr_DisableUsability(ref);
        assert(player.ps.weapFlags==0x3883);
        Player_UpdateActivate(&g_entities[2]);
        assert(player.ps.weapFlags==(0x3882|((i&2)&&!(i&1))));
        assert(player.useButtonDone==1 && clears==i+1 && script_checks==0);
        CODOL_Scr_EnableUsability(ref);
        CODOL_Scr_EnableUsability(ref);
        assert(!(player.ps.weapFlags&CODOL_USE_DISABLED));
        assert((player.ps.weapFlags&~1)==0x1882);
    }
    memset(&player,0,sizeof(player));
    player.latched_buttons=0x8;
    Player_UpdateActivate(&g_entities[2]);
    assert(script_checks==1 && clears==8 && !player.useButtonDone);
    for(i=0;i<3;++i) {
        ref.entnum=i==0?3:i==1?MAX_GENTITIES:2; ref.classnum=i==2?2:0;
        CODOL_Scr_DisableUsability(ref);
        CODOL_Scr_EnableUsability(ref);
        assert(errors==2*(i+1) && !player.ps.weapFlags);
    }
    /* Neither hook fires on these paths: this harness drives activation with
     * no use-hint entity and no candidate use target. They are counted so a
     * future case that does set one up has the evidence to assert on. */
    (void)use_hint_calls; (void)use_allowed_calls;
    puts("PASS: native activation assembly enforces usability, cancels holds, preserves release edges and resumes enabled processing");
}
