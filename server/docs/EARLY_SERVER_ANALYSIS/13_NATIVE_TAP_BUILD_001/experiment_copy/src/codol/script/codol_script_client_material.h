/* C1's per-player client materials: the SetClientMaterial method and their
 * publication into the playerState. SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * C1 method SetClientMaterial 0x0051ec30 (name in the method table recovered
 * from the shipped string list; error text 0x00c538e0 "SetClientMaterial() -
 * invalid <type> string <%s> for client %i"):
 *
 *   <player> SetClientMaterial( <type>, <material> )
 *
 *   - receiver: "not an entity" (0x00c52248) / "entity %i is not a player"
 *     (0x00c5222c), as the other player methods;
 *   - no <type> (or "") clears both words (0x0051edd7);
 *   - <type> is compared, case-insensitively (0x006283d0 with 0x7fffffff), to
 *     the two-entry table at 0x00cd9414: "killcam_you", "head_icon_self";
 *   - <material> missing or "" stores 0, otherwise G_MaterialIndex (0x00570290,
 *     relative to CS_MATERIALS, raising its own not-precached error);
 *   - the result goes straight into the playerState of ent->client:
 *     +0x53c + type*4 (0x0051edbe). No per-frame copy, no client-side half.
 *
 * Both words are measured C1 playerState netfields, ten bits each (indices
 * 235/236 of the table at 0x00c38ca8, codol_player_fields.inc). The client
 * reads ps+0x540 in the zombies player HUD 0x00460590: for the local player
 * the portrait is CS[4275 + ps+0x540] (0x00460652 -> 0x00453f40); when it is 0
 * the HUD keeps its default "hud_character_soldier" (0x00c4422c). Every other
 * player's portrait is that player's entity head icon, CS[6069 + es+0xa0]
 * (cent+0x184, 0x004606bd), which C1 does not draw over the player's head in
 * a "zm" gametype (0x0045aeb6 compares the gametype against "zm" and skips the
 * world head icon). */
#ifndef CODOL_SCRIPT_CLIENT_MATERIAL_H
#define CODOL_SCRIPT_CLIENT_MATERIAL_H
#include "codol_playerstate.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif

/* playerState wire offset of type 0 ("killcam_you"); type n is at +4n. */
#define CODOL_CLIENT_MATERIAL_FIELD 0x53c
/* Ten-bit fields; C1's reader accepts 1..0x3ff (0x00453f43). */
#define CODOL_CLIENT_MATERIAL_MAX 1023

/* Type name -> index in C1's table order, -1 for anything else. */
int CODOL_ClientMaterialType(const char *name);

/* Publish two already-resolved CoDOL material slots into ps+0x53c/0x540.
 * All-or-nothing; fails for a value the ten-bit fields cannot carry. */
int CODOL_OverlayPlayerClientMaterials(codol_player_fields_t *wire, const unsigned slots[2]);

#ifdef CODOL_SERVER
#include "scr_vm.h"
#include "player.h"
void CODOL_Scr_SetClientMaterial(scr_entref_t ref);
/* Read the materials the *captured* playerState carries and translate each
 * native index through the CoDOL material bank. Fails rather than publishing
 * an index that has no CoDOL slot. */
int CODOL_OverlayServerClientMaterials(codol_player_fields_t *wire, const playerState_t *ps);
#endif

#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
