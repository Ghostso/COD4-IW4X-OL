#include "g_public_mp.h"
#include "q_shared.h"
#include "qcommon.h"
#include "g_shared.h"
#include "scr_vm.h"
#include "server_public.h"
#include "plugin_handler.h"
#ifdef CODOL_SERVER
#include "codol_script_usehint.h"
#include "codol_radar_input.h"
#include "codol_script_startup_extra.h"
#include "codol_sentient.h"
#include "codol_script_playeruse.h"
extern "C" {
#include "codol_weapon_lock.h"
#include "codol_script_combat_builtins.h"
#include "codol_weapon_input.h"
#include "codol_weapon_state.h"
#include "codol_sprint_state.h"
#include "codol_playerstate_ext.h"
#include "codol_recoil_state.h"
#include "codol_hud_icon_overrides.h"
#include "codol_action_slots.h"
#include "codol_script_vision.h"
void CODOL_ResetActionSlots(unsigned client);
}
#endif

void __cdecl ClientClearFields(gclient_s *client)
{
    client->useHoldEntity.setEnt(0);
}

void ClearAllSpectators(struct gentity_s* ent)
{
	int i;
	struct gentity_s* followers;

	for(i = 0, followers = level.gentities; i < level.maxclients; i++, followers++)//let refollow all spectors me who have prior followed me
	{
		if(followers->client && followers->client->lastFollowedClient == ent->s.number)
			Cmd_FollowClient_f(followers, ent->s.number);
	}
}

#ifdef CODOL_SERVER
#include "codol_knife_attachment.h"
#endif
extern "C" void __cdecl ClientSpawn(gentity_s *ent, const float *spawn_origin, const float *spawn_angles)
{
  gclient_s *client;
  vec3_t clean_spawn_angles;
  int index;
  int iFlags;
  int savedSpawnCount;
  int savedServerTime;
  clientSession_t savedSess;

  index = ent - g_entities;
  client = ent->client;

  assertx(index < level.maxclients ,"index doesn't index level.maxclients\n\t%i not in [0, %i)", index, level.maxclients);
  assert(ent->client == &level.clients[index]);
  assert(ent->r.inuse);
#ifdef CODOL_SERVER
  CODOL_KnifePlayerSpawning(ent);
#endif

  if ( client->ps.otherFlags & POF_PLAYER )
  {
    if ( client->ps.eFlags & PLAYER_EFLAG_TURRET_MASK )
    {
      assert(client->ps.clientNum == ent->s.number);
      assert(client->ps.viewlocked_entNum != ENTITYNUM_NONE);
      assert(level.gentities[client->ps.viewlocked_entNum].r.ownerNum.entnum() == index);

      gentity_s *turretent = &level.gentities[client->ps.viewlocked_entNum];
      if(turretent->r.ownerNum.ent()->client)
      {
        G_ClientStopUsingTurret(turretent);
      }
    }
  }
  G_EntUnlink(ent);
  if ( ent->r.linked )
  {
    SV_UnlinkEntity(ent);
  }
  ent->s.groundEntityNum = ENTITYNUM_NONE;
  Scr_SetString(&ent->classname, scr_const.player);
  ent->clipmask = 0x2810011;
  ent->r.svFlags |= 1u;
  ent->takedamage = 0;
  G_SetClientContents(ent);
  ent->handler = 11;
  /*
  Blackops
  ent->handler = 14;
  */
  ent->flags = 4096;
  
  VectorCopy(playerMins, ent->r.mins);
  VectorCopy(playerMaxs, ent->r.maxs);

  iFlags = client->ps.eFlags & 0x100002;
  
  memcpy(&savedSess, &client->sess, sizeof(savedSess));
  
  savedSpawnCount = client->ps.stats[4];
  savedServerTime = client->lastServerTime;
  
  ClientClearFields(client);
#ifdef CODOL_SERVER
  CODOL_PlayerLinkResetClient(index);
#endif

  memset(client, 0, sizeof(gclient_s));
#ifdef CODOL_SERVER
  CODOL_ResetClientWeaponLock((unsigned)index);
  CODOL_ResetPlayerShieldState((unsigned)index);
  CODOL_ResetClientRadarInput((unsigned)index);
  CODOL_ResetClientWeaponState((unsigned)index);
  CODOL_ResetActionSlots((unsigned)index);
  /* T5 clears its sprint duration/cooldown with the playerState memset in
   * G_ClientSpawn; scripts reapply them per spawn. */
  CODOL_ResetSprintOverrides((unsigned)index);
  /* The scale is stored outside ps; mirror the native spawn memset here. */
  CODOL_ResetPlayerRecoilScale((unsigned)index);
  CODOL_PlayerStateExtClearClientStun((unsigned)index);
  /* ClientSpawn just zeroed ps->eventSequence; the epoch that counts past its
   * 8-bit wrap is zeroed with it. */
  CODOL_PlayerStateExtClearClientEvents((unsigned)index);
  /* ClientSpawn just zeroed the playerState; C1's ps+0x1f4 loop sound goes
   * with it, and only the live state is silenced. */
  CODOL_PlayerStateExtClearClientLoopSound((unsigned)index);
  /* IW4 and C1 keep both halves of the weapon HUD icon overrides in the gclient
   * this memset just zeroed - the script-owned array (IW4 client+0x3264, C1
   * client+0x35ac) and, inside the playerState, the copy ClientEndFrame
   * publishes into it - so a respawning player draws its own weapon icons again
   * until a script overrides them. Only the live state is cleared; captured and
   * archived states keep the icons they were taken with. */
  CODOL_ResetClientHudIconOverrides((unsigned)index);
  CODOL_PlayerStateExtClearClientHudIcons((unsigned)index);
  /* The memset above used to zero ps.weapons/weaponold/weaponrechamber/
   * weaponmodels in place; they live in the extension now, so zero them
   * there. Live state only. */
  CODOL_PlayerStateExtClearClientInventory((unsigned)index);
  CODOL_ResetClientActionSlotState((unsigned)index);
  CODOL_ResetClientKillstreakHud((unsigned)index);
  CODOL_PlayerStateExtClearClientAbilities((unsigned)index);
  CODOL_PlayerStateExtClearClientPerks((unsigned)index);
  CODOL_PlayerStateExtClearClientLinks((unsigned)index);
  CODOL_PlayerStateExtClearClientUseHint((unsigned)index);
  CODOL_PlayerStateExtClearClientPoison((unsigned)index);
  CODOL_ForceUseHint_ResetClient(index);
  /* The disablePlayerUse bits are NOT cleared here. IW4 keeps them at
   * client+0x327c, inside clientSession_t (0x311c..0x3394), which ClientSpawn
   * saves before its gclient memset and copies back (0x47da4f / 0x47da9a), so
   * they outlive a respawn: a teammate kept off a placed sentry stayed kept
   * off after he died. Only a new connection (CODOL_ResetClientInput) and the
   * target's own free (CODOL_PlayerUseClearTarget) clear them. */
  /* Clear the native vision record with the rest of this gclient. This does
   * not send a client transition. C1 stores these values in gclient too,
   * but its exact respawn preservation policy still needs confirmation. */
  CODOL_ResetPlayerVisionSets((unsigned)index);
#endif
  
  memcpy(&client->sess, &savedSess, sizeof(client->sess));

#ifdef CODOL_SERVER
  /* C1 owns these bits in playerState::otherFlags.  The retained spawn
   * memset used to leave POF_PLAYER clear forever because IW3 established
   * its old bit elsewhere.  BG_PlayerStateToEntityState now consumes the C1
   * bit directly, so establish it from the authoritative session state. */
  if (client->sess.sessionState == SESS_STATE_PLAYING ||
      client->sess.sessionState == SESS_STATE_DEAD)
    client->ps.otherFlags |= POF_PLAYER;
#endif
  
  client->lastServerTime = savedServerTime;
  client->spectatorClient = -1;
  client->ps.stats[4] = savedSpawnCount + 1;
  client->ps.stats[2] = client->sess.maxHealth;
  client->ps.eFlags = iFlags;
  client->sess.cs.clientIndex = index;
  client->sess.cs.attachedVehEntNum = ENTITYNUM_NONE;
  client->ps.clientNum = index;
  client->ps.viewlocked_entNum = ENTITYNUM_NONE;
#ifdef CODOL_SERVER
  /* C1 reads the killcam entity selector out of the snapshot playerstate at
     +0xa54 the moment its killcam latch turns on (0x0046c09e) and recognises
     ONLY 2047 as "no entity": 0x0046c0b8 compares against 0x7ff and takes the
     clearing arm at 0x0046c0bc (cg+0xc8b70 = 0, cg+0xc8b6c = 0x7ff).  Any
     other value falls through to 0x0046c0d1, is multiplied by the 0x228
     centity stride at 0x0046c0eb and becomes the killcam camera's attachment.
     The only native writer of ps.killCamEntity is SpectatorClientEndFrame's
     forced-follow arm (_g_active_mp.asm, sess.killCamEntity -1 -> 2047 into
     the archived copy at stack ps+0x8a0); every other path publishes whatever
     the spawn memset left, i.e. 0 - a valid entity number meaning client 0.
     Establish ENTITYNUM_NONE here, beside viewlocked_entNum, so "no killcam
     entity" is what the wire carries by default.  codol_engine_state.c
     publishes this field verbatim at wire offset 0xa54. */
  client->ps.killCamEntity = ENTITYNUM_NONE;
#endif

  assertx((int)(client - level.clients) < level.maxclients ,"client - level.clients doesn't index level.maxclients\n\t%i not in [0, %i)", client - level.clients, level.maxclients);

  SV_GetUsercmd(client - level.clients, &client->sess.cmd);
  client->ps.eFlags ^= 2u;
  client->ps.viewHeightTarget = 60;
  client->ps.viewHeightCurrent = 60.0;
  client->ps.viewHeightLerpTime = 0;
  client->ps.dofNearBlur = 6.0;
  client->ps.dofFarBlur = 1.8;
  client->ps.spreadOverride = 0;
  client->ps.spreadOverrideState = 0;
  client->ps.throwBackGrenadeTimeLeft = 0;
  client->ps.throwBackGrenadeOwner = ENTITYNUM_NONE;
/*
    BLACKOPS
  for ( i = 0; i < 15; ++i )
  {
    BG_PlayerSetWeaponQuickReload(&client->ps, client->ps.heldWeapons[i].weapon, 1);
  }
  if ( BG_GetWeaponDef(client->ps.weapon)->bDualWield )
  {
    PM_StartWeaponAnim(&client->ps, 1, 1);
  }
  PM_StartWeaponAnim(&client->ps, 1, 0);
*/
  G_SetOrigin(ent, spawn_origin);
  
  VectorCopy(spawn_origin, client->ps.origin);

  client->ps.pm_flags |= 0x400u;
  client->ps.gravity = (int)g_gravity->value;

  clean_spawn_angles[0] = spawn_angles[0];
  clean_spawn_angles[1] = spawn_angles[1];
  clean_spawn_angles[2] = 0.0;
  
  SetClientViewAngle(ent, clean_spawn_angles);
  client->inactivityTime = level.time + 1000 * g_inactivity->integer;
  
  client->buttons = client->sess.cmd.buttons;
  level.clientIsSpawning = 1;
#ifdef CODOL_SERVER
  Com_DPrintf(CON_CHANNEL_SERVER,"CoDOL spawn: client %d session %d origin (%.0f %.0f %.0f) angles (%.0f %.0f %.0f)\n",index,(int)client->sess.sessionState,spawn_origin[0],spawn_origin[1],spawn_origin[2],spawn_angles[0],spawn_angles[1],spawn_angles[2]);
#endif
  client->lastSpawnTime = level.time;
#ifdef CODOL_SERVER
  /* C1 ClientSpawn tail 0x50f975..0x50f9ad: after PMF_RESPAWNED, client+0x70
   * and ps+0x333c both take level.time. Published as netfield 98 (TIME). */
  if(CODOL_PlayerStateSpawnTimeSet(&client->ps, level.time))
    Com_Printf(CON_CHANNEL_SERVER,"CoDOL ps: client %d spawnTime %d\n",index,level.time);
#endif
  client->sess.cmd.serverTime = level.time;
  client->ps.commandTime = level.time - 100;
  ClientEndFrame(ent);
#ifdef CODOL_SERVER
  codol_weapon_input_scope_t savedWeaponInput;
  CODOL_BeginSyntheticWeaponInput((unsigned)index, &savedWeaponInput);
#endif
  ClientThink_real(ent, &client->sess.cmd);
#ifdef CODOL_SERVER
  CODOL_EndSyntheticWeaponInput((unsigned)index, &savedWeaponInput);
#endif
  level.clientIsSpawning = 0;
  BG_PlayerStateToEntityState(&client->ps, &ent->s, 1, 1);



  //IW4OL garbage
  client->lastFollowedClient = -1; //remove the last followed player number if we self have respawned

  ClearAllSpectators(ent);
#ifdef CODOL_SERVER
  /* The client is a sentient for as long as it is in the game: C1's turret
   * acquisition and its friendly blocker both read the registry, never the
   * client list. Re-spawning refreshes the record's team and origin; C1 keeps
   * the record across a death and filters on health instead (0x57ce30). */
  CODOL_Sentient_ClientSpawned(ent);
#endif

	PHandler_Event(PLUGINS_ONCLIENTSPAWN, ent);




	if(ent->client->sess.sessionState == SESS_STATE_PLAYING)
	{
    SV_GameSetUndercoverState(index, false);
	}

}

const char *__cdecl CS_DisplayName(clientState_t *cs, int type)
{
  const char* clan = SV_GetPlayerClan(cs->clientIndex);
  const char* name = SV_GetPlayerName(cs->clientIndex);
  
  if(name && clan)
  {
    return Com_DisplayName(name, clan, type);
  }
  return "";
}

extern "C" __cdecl const char* G_GetPlayerId(struct gentity_s* ent)
{
    char id[33];

    if(ent->client == NULL)
    {
	return "";
    }
/*
    uint64_t xuid = SV_GetPlayerXuid(ent->client.ps.clientNum);

    return va("%llu", xuid);
*/

    SV_GetGuid(ent->client->ps.clientNum, id, sizeof(id));

    return va("%s", id);

}

void CS_SetPlayerName(clientState_t *cs, const char* name)
{
  SV_UpdatePlayernameById(cs->clientIndex ,name);
}

extern "C" __cdecl void ClientEndFrame_TurretThink_Stub(gentity_s* ent)
{
  gclient_s* client = ent->client;
	release_assert(client->ps.clientNum == ent->s.number);
	release_assert(client->ps.viewlocked_entNum != ENTITYNUM_NONE);
	release_assertx(level.gentities[client->ps.viewlocked_entNum].r.ownerNum.isDefined() && (level.gentities[client->ps.viewlocked_entNum].r.ownerNum.ent() == ent), "viewlocked_entNum is %i, ownerNum is %i, ent->s.number is %i", client->ps.viewlocked_entNum, level.gentities[client->ps.viewlocked_entNum].r.ownerNum,ent->s.number);
	turret_think_client(&level.gentities[client->ps.viewlocked_entNum]);
}
