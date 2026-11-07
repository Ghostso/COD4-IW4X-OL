/* Script-owned weapon HUD icon overrides, and their publication into the
 * playerState. SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Two stages, because both references have two stages and the difference is
 * observable:
 *
 *   1. a per-client array the script owns. IW4 keeps it at client+0x3264
 *      (setter 0x005f56d0 stores at client+0x3264+slot*4, getter 0x005f57c0
 *      reads the same word through ent->client at 0x005f5857); C1 keeps it at
 *      client+0x35ac (0x00549570, 0x0054973f). Neither getter reads a
 *      playerState.
 *   2. a copy of that array inside the client's own playerState, made once per
 *      frame. IW4 0x005d80bc copies client+0x3264..0x3278 into
 *      ps+0x470..0x484, in the same tail that copies the radar flags from
 *      client+0x3258..0x3260 into ps+0x1a8..0x1b0, immediately before the
 *      playerState is transferred into the entity state.
 *
 * Collapsing the two into one store would be wrong here and not only in
 * theory: SpectatorClientEndFrame copies the followed player's archived
 * playerState over the follower's (_g_active_mp.asm, the 0x2f64 memcpy) and
 * applies the followed extension with it, so a follower whose script state
 * lived in the playerState would lose its own overrides and read the followed
 * player's. In both references the copy covers the playerState only, and the
 * follower's own array survives untouched.
 *
 * Stage 2 runs on the playing path only. Retained ClientEndFrame dispatches on
 * client+0x2f64: sessionState 2 calls SpectatorClientEndFrame and returns
 * through the shared tail, sessionState 3 is intermission, and the playing path
 * converges at ClientEndFrame_420 - the last client-to-playerState store before
 * G_UpdateEntityStateFromPlayerState, which is where IW4 publishes. Publishing
 * there means a follower publishes nothing over the icons the follow copy just
 * brought it, which is how the follower sees the followed player's HUD.
 *
 * Lifetime, from this tree's own spawn and connect paths, matching where the
 * references' gclient memory is cleared:
 *   ClientSpawn         memset(client, 0, sizeof(gclient_s)) - every spawn
 *   connect/disconnect  CODOL_ResetClientInput - a fresh or leaving slot
 *   map/game reset      CODOL_ResetGameInput
 * Following and unfollowing clear nothing: neither respawns, and neither
 * reference's copy reaches the array.
 */
#ifndef CODOL_HUD_ICON_OVERRIDES_H
#define CODOL_HUD_ICON_OVERRIDES_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

/* C1's slot table (0x00cd3958) has eight entries; the vocabulary and order
 * live in codol_script_hud_notifications.h, which asserts the counts agree. */
#define CODOL_HUD_ICON_CLIENT_SLOTS 8

/* Stage 1. The value is a native material configstring index relative to
 * CS_MATERIALS, 0 meaning "no override" - the value both engines' setters
 * store for scr_const.none. Set fails for an out-of-range client, slot or
 * index rather than recording something the publication cannot carry; Get
 * answers 0 for anything out of range, which is "no override". */
int CODOL_SetClientHudIconOverride(unsigned client, unsigned slot, unsigned material);
unsigned CODOL_GetClientHudIconOverride(unsigned client, unsigned slot);

/* Stage 2, called from the retained ClientEndFrame playing path with the
 * client number, at the point IW4 publishes. Copies the whole array into that
 * client's live playerState storage. Does nothing for an out-of-range client
 * or a playerState that carries no extension. */
void CODOL_PublishClientHudIconOverrides(unsigned client);

/* The clears, at the three sites above. */
void CODOL_ResetClientHudIconOverrides(unsigned client);
void CODOL_ResetAllHudIconOverrides(void);

#ifdef __cplusplus
}
#endif
#endif
