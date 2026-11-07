/* CoDOL weapon HUD icon overrides and HUD splash notifications.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Two unrelated HUD notifications share this file because they share nothing
 * with the rest of the HUD: neither is a hudelem, and both are addressed to one
 * player.
 *
 * Weapon HUD icon overrides
 * -------------------------
 * A player can replace the material the client draws for one of its weapon
 * icon slots. IW4 and C1 model it identically: the value is a *material
 * configstring index*, kept per player, published inside the playerState, and
 * resolved back to a material name by the getter.
 *
 *   IW4 setweaponhudiconoverride 0x005f56d0
 *       slot name -> index into a six-entry scr_const table at 0x0079a16c
 *       ("primaryoffhand", "secondaryoffhand", "actionslot1".."actionslot4");
 *       an unknown name is Scr_ParamError(0, "\"%s\" is not a valid weapon hud
 *       icon type to override"). The material argument is scr_const.none -> 0,
 *       otherwise G_MaterialIndex(name) (0x004a93a0). Stored at
 *       client+0x3264+slot*4.
 *   IW4 getweaponhudiconoverride 0x005f57c0
 *       reads the same word; 0 returns scr_const.none, anything else returns
 *       the configstring at (value + 0x9b5), IW4's material base.
 *   IW4 0x005d80bc  publishes client+0x3264..0x3278 into ps+0x470..0x484, in
 *       the same function that publishes the radar flags from
 *       client+0x3258..0x3260 into ps+0x1a8..0x1b0. The array is therefore
 *       playerState state in IW4, and every archive/spectator/snapshot copy
 *       carries it.
 *
 * C1 has the same pair with two more slots:
 *
 *   C1 setter 0x00549300, getter 0x00549580, slot table 0x00cd3958 with eight
 *      entries (scr_const 0x024ee0fc..0x024ee10a, initialised at 0x00577ae0):
 *      primaryoffhand, secondaryoffhand, tertiaryoffhand, actionslot1..5.
 *      Same "not an entity" / "entity %i is not a player" / invalid-type
 *      errors, same scr_const.none -> 0, same G_MaterialIndex (0x00570290,
 *      relative slots 1..0x3ff over configstring base 0x10b3 = 4275 =
 *      CODOL_CS_MATERIALS), stored at client+0x35ac+slot*4.
 *   C1 client consumer: UI expression "actionslothudiconoverride" (opcode 212,
 *      handler 0x005e6063 -> 0x005e41b0) reads
 *      ps[0x574 + slot*4] for slots 1..5 and converts it with the configstring
 *      string table pre-offset by the material base (0x06d113fc =
 *      0x06d0d130 + 0x10b3 dwords); 0 or out of 1..0x3ff draws nothing.
 *
 * The eight slots are exactly the eight consecutive 10-bit playerState fields
 * the measured C1 table carries at 0x56c, 0x570, 0x574, 0x578, 0x57c, 0x580,
 * 0x584 and 0x588 (codol_player_fields.inc): base 0x56c, slot n at 0x56c+4n,
 * so the UI's 0x574+slot*4 for slots 1..5 is actionslot1..actionslot5, and
 * 10 bits is the 1..0x3ff domain both ends use.
 *
 * HUD splash
 * ----------
 * A splash is a row of mp/splashTable.csv shown in one of five client slots for
 * a duration. Neither engine sends a material or any text: the client owns the
 * table and looks the row up itself.
 *
 *   IW4 showhudsplash 0x005df430  name, slot (0..4), optional duration;
 *       row = StringTable_LookupRowNumForValue(mp/splashTable.csv, 0, name);
 *       SV_GameSendServerCommand(ent->s.number, 0, va("%c %i %i %i", 'A',
 *       slot, row, duration)).
 *   C1  showhudsplash 0x0051e530  the same, with 'w' (0x77) instead of 'A'.
 *   C1  client CG_ServerCommand 0x00469320 switches on the first character of
 *       argv(0); 'w' -> 0x00469e0e -> CG_ShowSplash(localClient, atoi(argv(1)),
 *       atoi(argv(2)), atoi(argv(3))) at 0x00469140, which re-validates
 *       0 <= slot <= 4, reads the row's column 4 for the default duration and
 *       stores {row, startTime, ?, duration} at cg+0x174384+slot*16.
 */
#ifndef CODOL_SCRIPT_HUD_NOTIFICATIONS_H
#define CODOL_SCRIPT_HUD_NOTIFICATIONS_H
#include "player.h"
#include "codol_playerstate.h"
#include "codol_hud_icon_overrides.h"
#ifdef __cplusplus
extern "C" {
#endif

/* C1's slot table has eight entries; IW4's first six are the same names in the
 * same order, without tertiaryoffhand and actionslot5. The client indexes the
 * playerState array with this number, so the order is the wire contract.
 *
 * The script store this vocabulary names is codol_hud_icon_overrides.h: a
 * per-client array, as in both references. This file owns what the slots mean
 * and the three methods; that file owns the store and its publication. */
#define CODOL_HUD_ICON_OVERRIDE_SLOTS CODOL_HUD_ICON_CLIENT_SLOTS
/* playerState wire offset of slot 0; slot n is at BASE + 4*n. */
#define CODOL_HUD_ICON_OVERRIDE_FIELD 0x56c
/* Ten bits, and C1's own consumer rejects anything above 0x3ff. */
#define CODOL_HUD_ICON_OVERRIDE_MAX 1023
/* C1 CG_ShowSplash and both server builtins bound the slot the same way. */
#define CODOL_HUD_SPLASH_SLOTS 5
/* The table both ends look the row up in, and the column the key lives in. */
#define CODOL_HUD_SPLASH_TABLE "mp/splashTable.csv"
#define CODOL_HUD_SPLASH_KEY_COLUMN 0
/* The reliable command C1's client dispatches to CG_ShowSplash. */
#define CODOL_HUD_SPLASH_COMMAND 'w'

/* Slot name <-> index, in C1's table order. Unknown names give -1; the caller
 * raises the engines' own parameter error, because only it knows the argument
 * position. NULL for an out-of-range index. */
int CODOL_WeaponHudIconOverrideSlot(const char *name);
const char *CODOL_WeaponHudIconOverrideSlotName(unsigned slot);

/* Publish eight already-resolved CoDOL material slots into the playerState
 * fields at 0x56c..0x588. Values are wire slots, not native configstring
 * indices, and must fit the ten bits the fields carry. All eight commit
 * together or the wire state is left byte-for-byte unchanged. */
int CODOL_OverlayPlayerWeaponHudIcons(codol_player_fields_t *wire,
    const unsigned slots[CODOL_HUD_ICON_OVERRIDE_SLOTS]);

#ifdef CODOL_SERVER
/* Read the overrides a *captured* playerState carries - the copy the producer
 * published into it, which an archived or spectator-followed state carries
 * exactly as it was taken - translate each native material index through the
 * CoDOL material bank and publish them into the wire fields. Never consults the
 * script store or a live client. Fails if a captured material has no CoDOL
 * slot, rather than publishing a different material or dropping the override. */
int CODOL_OverlayServerWeaponHudIcons(codol_player_fields_t *wire, const playerState_t *ps);

/* The row lookup both engines perform: mp/splashTable.csv, column 0, backwards,
 * case-insensitive, so a later duplicate wins. -1 when the table is missing or
 * the name is not in it. */
int CODOL_HudSplashRowNum(const char *name);

/* ACTION_SLOT_HELP. C1's key-binding substitution 0x603e50 resolves the
 * token [{ACTION_SLOT_HELP}] - the key in every MP_EARNED_* killstreak splash
 * description - to "+actionslot %d" with the local player's clientInfo byte
 * +0x5c plus one (0x603db8..0x603dde). That byte is clientState +0x010 (three
 * bits, copied at 0x46c95e), so a client whose field stays 0 is always told
 * "+actionslot 1" (key 8 in default_mp_controls.cfg) whatever slot the reward
 * went into. The store holds the 1-based action slot the script last named
 * for each client; 0 means none published (wire 0 = slot 1, the C1 default). */
unsigned CODOL_ClientActionSlotHelp(unsigned client);
#endif

#ifdef __cplusplus
}
#endif
#endif
