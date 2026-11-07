#include "codol_weapon_lock.h"
#include "codol_game.h"
#include "qcommon_io.h"
#include "codol_action_slots.h"
#include "codol_clientstate_ext.h"
#include "codol_hud_icon_overrides.h"
#include "codol_item_ammo.h"
#include "codol_killstreak_hud.h"
#include "codol_lookat.h"
#include "codol_perk_runtime.h"
#include "codol_perks.h"
#include "codol_player_appearance.h"
#include "codol_pmove_c1.h"
#include "codol_radar_types.h"
#include "codol_scoreboard_stats.h"
#include "codol_script_player_builtins.h"
#include "codol_script_playeruse.h"
#include "codol_script_usehint.h"
#include "codol_script_vehicle_builtins.h"
#include "codol_script_vision.h"
#include "codol_spectate_defaults.h"
#include "codol_weapon_input.h"
#include "codol_weapon_state.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
/* This harness only uses the client-indexed live slots, so it binds no
 * playerState storage; the definitions keep the resolver linkable without
 * dragging in the server globals. */
const void *CODOL_PlayerStateExtLiveBase(unsigned *count){if(count)*count=0;return NULL;}
const void *CODOL_PlayerStateExtSnapshotBase(unsigned *count){if(count)*count=0;return NULL;}
const void *CODOL_PlayerStateExtArchiveBase(unsigned *count){if(count)*count=0;return NULL;}
/* codol_playerstate_ext.c reports untracked storage through this hook. */
void Com_PrintWarning(conChannel_t channel,const char *fmt,...){(void)channel;(void)fmt;}
/* The fixture links the production aggregate reset and its core. These
 * adapters are the unrelated reset owners; they have no access to the lock
 * under test. Header imports above keep their signatures compiler-checked. */
#define RESET_CLIENT(fn) void fn(unsigned client) { (void)client; }
#define RESET_SLOT(fn) void fn(int slot) { (void)slot; }
#define RESET_ALL(fn) void fn(void) {}
RESET_CLIENT(CODOL_ResetPerkRuntime)
void CODOL_ClearPerks(codol_perk_state_t *perks) { if(perks) memset(perks, 0, sizeof(*perks)); }
RESET_CLIENT(CODOL_ResetClientActionSlotState)
RESET_CLIENT(CODOL_ResetClientKillstreakHud)
RESET_CLIENT(CODOL_ResetLookAtClientState)
RESET_CLIENT(CODOL_PmoveC1ResetClient)
RESET_ALL(CODOL_PmoveC1ResetAll)
RESET_CLIENT(CODOL_ResetWeaponInput)
RESET_ALL(CODOL_ResetWeaponStates)
RESET_ALL(CODOL_ResetWeaponWireIndexReports)
RESET_ALL(CODOL_ResetAllScoreStats)
RESET_ALL(CODOL_ResetAllSpectateDefaults)
RESET_ALL(CODOL_ClearCapturedClientAbilities)
RESET_ALL(CODOL_ResetClientCharacters)
RESET_ALL(CODOL_ForceUseHint_ResetAll)
RESET_ALL(CODOL_PlayerUseResetAll)
RESET_ALL(CODOL_ResetAllPlayerVisionSets)
RESET_ALL(CODOL_ResetPlayerBuiltinsAll)
RESET_ALL(CODOL_PlayerRemoteView_ResetAll)
RESET_ALL(CODOL_VehicleTurretControl_Reset)
RESET_ALL(CODOL_TurretMinimap_ResetAll)
RESET_ALL(CODOL_ResetAllHudIconOverrides)
RESET_CLIENT(CODOL_ResetScoreStats)
RESET_CLIENT(CODOL_ResetSpectateDefaults)
RESET_CLIENT(CODOL_ResetClientWeaponState)
RESET_CLIENT(CODOL_ClearPublishedClientAbilities)
RESET_CLIENT(CODOL_ClearClientCharacter)
RESET_SLOT(CODOL_ForceUseHint_ResetClient)
RESET_SLOT(CODOL_PlayerUseResetClient)
RESET_CLIENT(CODOL_ResetPlayerVisionSets)
RESET_CLIENT(CODOL_ResetPlayerBuiltinsClient)
RESET_SLOT(CODOL_PlayerRemoteView_ResetClient)
RESET_SLOT(CODOL_VehicleTurretControl_ClientLeft)
RESET_CLIENT(CODOL_ResetClientHudIconOverrides)
RESET_CLIENT(CODOL_ResetClientRadarTypes)
RESET_ALL(CODOL_ResetAllRadarTypes)
#undef RESET_CLIENT
#undef RESET_SLOT
#undef RESET_ALL
int main(void)
{
    codol_weapon_lock_t *first=CODOL_ClientWeaponLock(0),*last=CODOL_ClientWeaponLock(31);
    assert(first && last && first!=last && first->entity==2047 && last->entity==2047);
    assert(!CODOL_ClientWeaponLock(32));
    assert(CODOL_SetWeaponLock(first,10,NULL,1,NULL,0));
    assert(CODOL_SetWeaponLock(last,11,NULL,1,NULL,1));
    CODOL_ResetClientInput(0);
    assert(!first->flags && first->entity==2047 && last->entity==11 && last->flags==7);
    CODOL_ResetGameInput();
    for(unsigned i=0;i<32;++i) {
        codol_weapon_lock_t *s=CODOL_ClientWeaponLock(i);
        assert(s && !s->flags && s->entity==2047);
    }
    puts("PASS: native client input reset and map reset clear independent weapon locks");
}
