#include "q_shared.h"
#include "q_shared.h"
#include "g_shared.h"
#include "server.h"
#include "server_public.h"
#include "cscr_stringlist.h"
#ifdef CODOL_SERVER
#include "bg_public.h"
#include "xassets/weapondef.h"
#include "codol_usercmd.h"
#include "codol_weapon_bits.h"
#endif


extern unsigned int bg_lastParsedWeaponIndex;

#ifdef CODOL_SERVER
void __cdecl CODOL_DebugWeaponGrant(playerState_t *ps, int weapon, unsigned variant, int result)
{
  if(!CODOL_TRACE_ON()) return;
  const struct WeaponDef *def = weapon >= 0 && weapon < BG_GetNumWeapons() ? BG_GetWeaponDef(weapon) : NULL;
  const unsigned owned = ps && weapon >= 0 ? (unsigned)CODOL_WeaponBitsOwned(ps, (unsigned)weapon) : 0u;
  const int wire = weapon >= 0 ? CODOL_WeaponToWire((unsigned)weapon) : -1;
  Com_Printf(CON_CHANNEL_PLAYERWEAP,
    "CoDOL giveweapon: name %s engine %d wire %d variant %u result %d owned %u current %u inventory %d gunmodel %p\n",
    def && def->szInternalName ? def->szInternalName : "<null>", weapon, wire,
    variant, result, owned, ps ? ps->weapon : 0u,
    def ? (int)def->inventoryType : -1,
    def && variant < 16 ? (void *)def->gunXModel[variant] : NULL);
}
/* After G_InitializeAmmo in PlayerCmd_giveWeapon: which pooled ammo/clip slot
 * the definition resolved to and what landed there. */
void __cdecl CODOL_DebugWeaponAmmo(gentity_t *ent, int weapon)
{
  if(!CODOL_TRACE_ON()) return;
  const struct WeaponDef *def = weapon >= 0 && weapon < BG_GetNumWeapons() ? BG_GetWeaponDef(weapon) : NULL;
  const playerState_t *ps = ent && ent->client ? &ent->client->ps : NULL;
  if (!def || !ps) return;
  Com_Printf(CON_CHANNEL_PLAYERWEAP,
    "CoDOL giveammo: name %s engine %d ammo %s idx %d clip %s idx %d size %d start %d -> clip %d reserve %d\n",
    def->szInternalName ? def->szInternalName : "<null>", weapon,
    def->szAmmoName ? def->szAmmoName : "", def->iAmmoIndex,
    def->szClipName ? def->szClipName : "", def->iClipIndex, def->iClipSize, def->iStartAmmo,
    def->iClipIndex >= 0 && def->iClipIndex < 128 ? ps->ammoclip[def->iClipIndex] : -1,
    def->iAmmoIndex >= 0 && def->iAmmoIndex < 128 ? ps->ammo[def->iAmmoIndex] : -1);
}
#endif

struct AntilagClientStore
{
  vec3_t realClientPositions[MAX_CLIENTS];
  bool clientMoved[MAX_CLIENTS];
};


void __cdecl G_AntiLagRewindClientPos(int gameTime, struct AntilagClientStore *antilagStore)
{
  int client;
  vec3_t clientPositions[MAX_CLIENTS];
  vec3_t clientAngles[MAX_CLIENTS];
  bool success[MAX_CLIENTS];

  if ( g_antilag->boolean == qfalse)
  {
    return;
  }
  assert(antilagStore != NULL);

  memset(antilagStore, 0, sizeof(*antilagStore));

  assert(gameTime > 0);
  if ( level.time - gameTime > 400 )
  {
    gameTime = level.time - 400;
  }
  if ( level.time - gameTime > 1000 / level.framerate )
  {
    memset(success, 0, sizeof(success));
    if ( SV_GetClientPositionsAtTime(gameTime, clientPositions, clientAngles, success) )
    {
      for ( client = 0; client < level.maxclients; ++client )
      {
        if ( !success[client] || level.clients[client].sess.connected != CON_CONNECTED || level.clients[client].sess.sessionState )
        {
          antilagStore->clientMoved[client] = false;
        }
        else
        {
          assert(!IS_NAN(clientPositions[client][0]) && !IS_NAN(clientPositions[client][1]) && !IS_NAN(clientPositions[client][2]));
          assert(!IS_NAN(clientAngles[client][0]) && !IS_NAN(clientAngles[client][1]) && !IS_NAN(clientAngles[client][2]));

          VectorCopy(g_entities[client].r.currentOrigin, antilagStore->realClientPositions[client]);
/*
          VectorCopy(g_entities[client].r.currentAngles, antilagStore->realClientAngles[client]);
*/
	  assertx(!IS_NAN( antilagStore->realClientPositions[client][0]) &&
		!IS_NAN(antilagStore->realClientPositions[client][1]) &&
		!IS_NAN(antilagStore->realClientPositions[client][2]), 
		"client %i's origin is invalid - (%f, %f, %f)", client,
                antilagStore->realClientPositions[client][0],
                antilagStore->realClientPositions[client][1],
                antilagStore->realClientPositions[client][2]);
/*
	  assertx(!IS_NAN( antilagStore->realClientAngles[client][0]) &&
		!IS_NAN(antilagStore->realClientAngles[client][1]) &&
		!IS_NAN(antilagStore->realClientAngles[client][2]), 
                "client %i's angles are invalid - (%f, %f, %f)", client,
                antilagStore->realClientAngles[client][0],
                antilagStore->realClientAngles[client][1],
                antilagStore->realClientAngles[client][2]);
*/

	//Unlink not in Blackops...
          SV_UnlinkEntity(&g_entities[client]);

          VectorCopy(clientPositions[client], g_entities[client].r.currentOrigin);
//          VectorCopy(clientAngles[client], g_entities[client].r.currentAngles);

          SV_LinkEntity(&g_entities[client]);
          antilagStore->clientMoved[client] = true;
        }
      }
    }
  }
}

void __cdecl G_AntiLag_RestoreClientPos(struct AntilagClientStore *antilagStore)
{
  int client;

  if ( g_antilag->boolean == qfalse)
  {
    return;
  }

  assert(antilagStore != NULL);

  for ( client = 0; client < level.maxclients; ++client )
  {
    if ( antilagStore->clientMoved[client] )
    {
      assertx(!IS_NAN(antilagStore->realClientPositions[client][0]) &&
                !IS_NAN(antilagStore->realClientPositions[client][1]) &&
                 !IS_NAN(antilagStore->realClientPositions[client][2]),
                "client %i's origin is invalid - (%f, %f, %f)", client,
               antilagStore->realClientPositions[client][0],
               antilagStore->realClientPositions[client][1],
               antilagStore->realClientPositions[client][2]);
/*
      assertx(!IS_NAN(antilagStore->realClientAngles[client][0]) && 
		!IS_NAN(antilagStore->realClientAngles[client][1]) &&
		!IS_NAN(antilagStore->realClientAngles[client][2]),
		"client %i's angles are invalid - (%f, %f, %f)", client,
               antilagStore->realClientAngles[client][0],
               antilagStore->realClientAngles[client][1],
               antilagStore->realClientAngles[client][2]);
*/

	//Unlink not in Blackops...
      SV_UnlinkEntity(&g_entities[client]);

      VectorCopy(antilagStore->realClientPositions[client], g_entities[client].r.currentOrigin);
//      VectorCopy(antilagStore->realClientAngles[client], g_entities[client].r.currentAngles);

      SV_LinkEntity(&g_entities[client]);
      antilagStore->clientMoved[client] = false;

    }
  }
}


void __cdecl G_SetupWeaponDef()
{
  Com_DPrintf(CON_CHANNEL_PLAYERWEAP, "----------------------\n");
  Com_DPrintf(CON_CHANNEL_PLAYERWEAP, "Game: G_SetupWeaponDef\n");
  if ( bg_lastParsedWeaponIndex == 0)
  {
    Com_SetWeaponInfoMemory(1);
    ClearRegisteredItems();
    BG_ClearWeaponDef();

//    SL_SetScriptCompile(true); //Scriptstring Glitch workaround

    G_GetWeaponIndexForName("defaultweapon_mp");
  //Not in CoD4  BG_LoadWeaponTable("_mp", G_RegisterWeapon);
//    SL_SetScriptCompile(false); //Scriptstring Glitch workaround
  }
  Com_DPrintf(CON_CHANNEL_PLAYERWEAP, "----------------------\n");
}


