#ifdef CODOL_SERVER
#include "codol_playerstate_ext.h"
/* The whole-game input reset.
 *
 * It lives apart from codol_game.c because it has to reach subsystems in the
 * player, script and vehicle areas. codol_game.c owns the input state itself
 * and must stay linkable on its own, so it exposes CODOL_ResetGameInputCore
 * and this file adds the rest on top. */
#include "server.h"
#include "codol_game.h"
#include "codol_spectate_defaults.h"
#include "codol_weapon_input.h"
#include "codol_script_usehint.h"
#include "codol_clientstate_ext.h"
#include "codol_scoreboard_stats.h"
#include "codol_weapon_state.h"
#include "codol_item_ammo.h"
#include "codol_script_vision.h"
#include "codol_script_playeruse.h"
#include "codol_script_player_builtins.h"
#include "codol_script_vehicle_builtins.h"
#include "codol_hud_icon_overrides.h"
#include "codol_player_appearance.h"

void CODOL_ResetGameInput(void)
{
    unsigned client;
    CODOL_ResetGameInputCore();
    for(client=0;client<MAX_CLIENTS;++client) CODOL_ResetWeaponInput(client);
    CODOL_ResetWeaponStates();
    CODOL_ResetWeaponWireIndexReports();
    CODOL_ResetAllScoreStats();
    CODOL_ResetAllSpectateDefaults();
    CODOL_ClearCapturedClientAbilities();
    CODOL_ResetClientCharacters();
    CODOL_ForceUseHint_ResetAll();
    CODOL_PlayerUseResetAll();
    CODOL_ResetAllPlayerVisionSets();
    CODOL_ResetPlayerBuiltinsAll();
    CODOL_PlayerRemoteView_ResetAll();
    CODOL_VehicleTurretControl_Reset();
    CODOL_TurretMinimap_ResetAll();
    CODOL_ResetAllHudIconOverrides();
}
void CODOL_ResetClientInput(unsigned client)
{
    CODOL_PlayerStateExtClearClientPoison(client);
    CODOL_ResetClientInputCore(client);
    CODOL_ResetWeaponInput(client);
    CODOL_ResetScoreStats(client);
    CODOL_ResetSpectateDefaults(client);
    CODOL_ResetClientWeaponState(client);
    CODOL_ClearPublishedClientAbilities(client);
    CODOL_ClearClientCharacter(client);
    CODOL_ForceUseHint_ResetClient((int)client);
    CODOL_PlayerUseResetClient((int)client);
    /* A connecting or leaving slot drops the per-player vision records with the
     * rest of the client input state, so a reused slot cannot inherit them. */
    CODOL_ResetPlayerVisionSets(client);
    CODOL_ResetPlayerBuiltinsClient(client);
    CODOL_PlayerRemoteView_ResetClient((int)client);
    CODOL_VehicleTurretControl_ClientLeft((int)client);
    /* A fresh or leaving client slot: both halves of the weapon HUD icon
     * overrides go, the script-owned array and the copy last published into the
     * live playerState. In IW4 and C1 both halves are gclient memory that a new
     * connection starts zeroed. Captured and archived states keep theirs. */
    CODOL_ResetClientHudIconOverrides(client);
}
#endif
