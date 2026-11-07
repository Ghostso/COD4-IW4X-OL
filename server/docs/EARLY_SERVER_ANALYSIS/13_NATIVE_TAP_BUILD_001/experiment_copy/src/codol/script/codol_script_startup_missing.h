/* Missing player builtins reached by the MP script closure that a match
 * compiles. Both members are player-receiver methods called from scripts the
 * gametypes always compile:
 *
 *   playerhide                  maps/mp/gametypes/_playerlogic.gsc:920 (the
 *                               intermission spawn) and _damage.gsc:685 (the
 *                               faux-death path, after clonePlayer).
 *   worldpointinreticle_circle  maps/mp/_javelin.gsc and maps/mp/_stinger.gsc
 *                               lock-target selection (6 reachable calls).
 *
 * Evidence
 *   playerhide: C1 0x54de50 resolves the script entity through 0x534a10,
 *   requires the client pointer (C1 gentity +0x17c), raises the C1 string at
 *   0xc58f78 ("Must be called on a player.") when it is null, ORs the C1
 *   playerState flags word (+0xec, the same offset the CoDOL player field
 *   table publishes) with 0x10, then clears the entityShared contents field
 *   (C1 +0x130). IW4 0x5f6de0 is the same function against its own layout:
 *   client at +0x158, ps.eFlags at +0xb0 with bit 0x20, contents at +0x11c
 *   (that contents offset is the one already measured for this tree's
 *   setcontents/makeusable draft, src/codol_script_missing_next.h). Neither
 *   build checks the willNeverChange marker and neither relinks the entity.
 *
 *   worldpointinreticle_circle: IW4 method table 0x0073d75c, handler
 *   0x005f5910, projection helper 0x00502dc0, dot-product helper 0x00409f00.
 *   Decoded from those functions rather than from alpha0022's
 *   builtin_surface.py `_inreticle`, whose "horizontal/vertical half-angle
 *   ellipse" reading does not match the code. Measured: the receiver must be a
 *   player (object error va("entity %i is not a player"), IW4 0x72d454); the
 *   arguments are a vector, a full field of view in degrees and a radius, with
 *   no argument count check; the point is transformed into the view axis, must
 *   be strictly in front, and is projected into 640x480 virtual screen pixels
 *   with -320.0 (0x72d790), -240.0 (0x714f20), the 0.75 aspect (0x6e2a80) and
 *   tan(fov * deg2rad * 0.5); the result is x*x + y*y < radius*radius, strict,
 *   so exact equality returns false. IW4's origin wrapper4b6d00 uses link
 *   flags bit4 and parent18c, written by PlayerLinkWeaponViewToDelta. Native
 *   CODOL_PLAYERLINK_WEAPONVIEW/linkEntNum provides this tag_player branch.
 *   Float stores follow the measured projection; libm/runtime parity is untested.
 */
#ifndef CODOL_SCRIPT_STARTUP_MISSING_H
#define CODOL_SCRIPT_STARTUP_MISSING_H
#ifdef CODOL_SERVER
#include "scr_vm.h"
struct playerState_s;

/* The authoritative player state uses C1's hidden bit directly. Generic
 * retained entities still use their own ScrCmd_Hide flag independently. */
#define CODOL_PS_EF_HIDDEN 0x00000010
#define CODOL_WIRE_EF_HIDDEN 0x00000010u

/* self PlayerHide()
 * Receiver: connected player entity. No arguments, no return value.
 * Marks the player hidden and clears its collision contents. */
void CODOL_Scr_PlayerHide(scr_entref_t entref);

/* self WorldPointInReticle_Circle( <point>, <fov degrees>, <radius> )
 * Receiver: player entity. Returns a boolean: is the world point in front of
 * the view and inside a circle of <radius> 640x480 virtual pixels around the
 * screen centre. */
void CODOL_Scr_WorldPointInReticleCircle(scr_entref_t entref);

/* Shared by the implementation and by the wire codec patch this worker hands
 * to the parent: is this player's state marked hidden? */
#ifdef __cplusplus
extern "C" {
#endif
int CODOL_PlayerStateHidden(const struct playerState_s *ps);
#ifdef __cplusplus
}
#endif

#endif
#endif
