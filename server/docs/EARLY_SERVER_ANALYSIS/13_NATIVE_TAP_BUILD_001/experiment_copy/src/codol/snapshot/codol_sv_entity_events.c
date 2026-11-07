#ifdef CODOL_SERVER
/* Entity event-generation resets.
 *
 * These live apart from codol_sv_entities.c on purpose. Clearing a slot's
 * event history has to reach every subsystem that keeps per-entity state -
 * vehicles, model animation, missiles, glass - so this file drags in most of
 * the server. The snapshot collectors next door depend on none of that, and
 * keeping them in their own translation unit is what lets them be linked
 * against on their own by tests and tools. */
#include "server.h"
#include "codol_sv_entities.h"
#include "codol_playerstate_ext.h"
#include "codol_entitystate_ext.h"
#include "codol_remote_missile.h"
#include "codol_weapon_lock.h"
#include "codol_model_animation.h"
#include "codol_vehicle_spawner.h"
#include "codol_script_combat_builtins.h"
#include "codol_glass_world.h"
#include "codol_bomb.h"
#include "codol_player_worldweapon.h"
#include "codol_knife_attachment.h"
#include "codol_rc_spawn_influence.h"

void CODOL_ResetEntityEventGeneration(unsigned number)
{
    CODOL_ResetRCSpawnInfluencer(number);
    CODOL_ResetKnifeAttachment(number);
    CODOL_ResetPlayerWorldWeaponEntity(number);
    CODOL_ResetBombState(number);
    CODOL_ResetVehicleSpawner(number);
    CODOL_ResetEntityModelAnimation(number);
    CODOL_ResetMissilePosition(number);
    CODOL_ResetMissileRemoteState(number);
    /* A reused entity slot starts a new event history; captured snapshots and
     * archived frames keep the epoch they were taken with. A player entity
     * going away takes its event epochs with it; the retained counter is
     * zeroed by the gclient memset on the next spawn. */
    CODOL_ResetEntityEventEpoch(number);
}

void CODOL_ResetEntityEventGenerations(void)
{
    CODOL_ResetRCSpawnInfluencers();
    CODOL_ResetKnifeAttachments();
    CODOL_ResetPlayerWorldWeapons();
    CODOL_ResetBombStates();
    CODOL_ResetVehicleSpawners();
    CODOL_ResetMissilePositions();
    CODOL_ResetPhysicsLaunches();
    CODOL_GlassWorldReset();
    CODOL_ResetMissileRemoteStates();
    CODOL_ResetEntityEventEpochs();
    /* A teardown, unlike a slot recycle: the ring and the archive are
     * about to be rebuilt, so their captured histories go too. */
    CODOL_EntityStateExtClearAll();
}
#endif
