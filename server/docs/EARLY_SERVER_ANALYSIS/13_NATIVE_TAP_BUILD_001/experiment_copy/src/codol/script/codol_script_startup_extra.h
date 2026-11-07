/*
 * Native player view / camera / controls linking for the CoDOL script startup
 * pass. See src/codol_script_startup_extra.c for the reference evidence.
 */
#ifndef __CODOL_SCRIPT_STARTUP_EXTRA_H__
#define __CODOL_SCRIPT_STARTUP_EXTRA_H__

#ifdef CODOL_SERVER

#include "q_shared.h"
#include "scr_vm.h"
#include "codol_playerstate.h"
#include "codol_player_links.h"

#ifdef __cplusplus
extern "C" {
#endif

struct gentity_s;
struct playerState_s;

typedef enum
{
    CODOL_PLAYERLINK_NONE = 0,
    /* playerLinkTo: the player rides the link. */
    CODOL_PLAYERLINK_VIEW = 1,
    /* playerLinkWeaponViewToDelta: the player rides the link and keeps the
     * origin it had, and only the weapon view follows the delta. */
    CODOL_PLAYERLINK_WEAPONVIEW = 2
} codolPlayerLinkMode_t;

/* IW4 clamps every arc into [0,180] against the constant at 0x6fe380. */
#define CODOL_PLAYERLINK_MAX_ARC 180.0f

/* C1 0x5484c0 writes 0x7ff into the controls-link entity field when it clears
 * it, and every entity-number field in C1's playerState table is 11 bits. The
 * engine's ENTITYNUM_NONE is the same 2047 now that GENTITYNUM_BITS is 11. */
#define CODOL_WIRE_ENTITYNUM_NONE 0x7ff

typedef struct
{
    codolPlayerLinkMode_t mode;
    int linkEntNum;             /* ENTITYNUM_NONE when not linked */
    qboolean offsetEnabled;
    float rightArc;
    float leftArc;
    float topArc;
    float bottomArc;

    /* Parameter 2. IW4 gclient+0x3410 (5ef5cb..5ef5f4), C1 1.1.1.13
     * gclient+0x3768 (53ae2b..53ae55). The fraction of the link frame's
     * per-frame rotation that is carried into the player's view: IW4 5fdd43
     * feeds it to the quaternion lerp at 0x49fc30 from identity to the relative
     * frame rotation. That rotation is composed onto the player's view, and
     * 5fddf9 adds the resulting angle difference to viewangles/delta_angles.
     * An absent parameter is
     * zero (IW4 5ef5dc fldz, C1 53ae46), i.e. the view does not turn with the
     * link at all; `maps/mp/killstreaks/_ac130.gsc:865` passes 1.0. */
    float viewRotationFraction;

    /* Parameter 7 of playerLinkTo. IW4 gclient+0x340e (5ef5c1), C1
     * gclient+0x3766 (53ae25). IW4's origin update at 5fe00c takes the
     * step-and-slide collision branch when set and the plain interpolation branch
     * (5fe138) when it is clear. playerLinkWeaponViewToDelta always clears it
     * (5ef56a / C1 53adcb). */
    qboolean collideWhileLinked;

    /* IW4 gclient+0x340f, C1 gclient+0x3767. playerLinkTo sets it
     * unconditionally (5ef5a5 / C1 53ae05); playerLinkWeaponViewToDelta sets it
     * from parameter 7 (5ef564 / C1 53adc1). It selects how the angles the view
     * clamp is expressed against are maintained: IW4 5fde84 re-reads them from
     * the link frame every frame when set, and 5fdea9 rotates the previous ones
     * by this frame's link delta when clear. IW4 4fdb80 uses the same byte at
     * link time to initialize the reference from the tag frame when set,
     * or from zero when clear. Clamp initialization still uses world angles. */
    qboolean viewLinkAbsolute;

    /* C1 ps+0x14 bit 1 / IW4 PLF_ANGLES_LOCKED. playerLinkToAbsolute
     * (C1 0x53b2e0: viewRotationFraction 1.0, or [ps+0x14],1, and ~4) and
     * playerLinkToBlend (0x53ba40, same stores after the blend timers) set
     * it; unlink clears it (0x53a8fa). PM_UpdateViewAngles 0x4141b8 treats a
     * locked NORMAL_LINKED/DEAD_LINKED view as driven by the link frame and
     * skips the usercmd pitch clamp (0x414209..0x414216). */
    qboolean anglesLocked;

    /* IW4 gclient+0x174..0x17c, C1 gclient+0x1d4..0x1dc: the link view
     * reference. Distinct from the world-frame angles supplied to the clamp
     * writer (IW4 5fdbca..5fdbdb). */
    float linkAngles[3];
    /* The link orientation seen last frame, IW4 gclient+0x33fc (x,y,z,w), with
     * its "already have one" byte at gclient+0x340c: IW4 5fdd5f writes the
     * identity rotation and sets the byte on the first frame, so the first frame
     * contributes no rotation. */
    float lastFrameQuat[4];
    qboolean haveLastFrameQuat;

    /* The clamp this link asks for, in world angles: index 0 pitch, index 1 yaw,
     * base the centre of the permitted interval and range its half width, with
     * 180 or more meaning unrestricted. Recomputed every frame from the parent
     * tag's world angles and the arcs. clampActive is false for unrestricted arcs.
     * This is deliberately NOT written into ps.viewAngleClampBase/Range: the
     * retained PM only reads that pair behind the turret eFlags gate, and those
     * flags have other consumers. See the report for the proposed consumer. */
    qboolean clampActive;
    float clampBase[2];
    float clampRange[2];

    /* IW4 gclient+0x180..0x188 (5ef518), C1 gclient+0x1e0..0x1e8 (53ad7a): the
     * player's own viewangles captured when playerLinkWeaponViewToDelta linked
     * them, which is the delta the weapon view is expressed against. */
    float weaponViewAngles[3];

    int cameraEntNum;           /* Retained when cameraFlags active bit clears. */
    int cameraTagIndex;         /* 1..CODOL_TAG_SLOTS-1, 0 when none */
    uint32_t cameraFlags;       /* C1 otherFlags masks 2 and 0x80. */

    int controlsEntNum;         /* ENTITYNUM_NONE when controls are not linked */
} codolPlayerLink_t;

void CODOL_PlayerLinkResetAll(void);
/* Releases only the player link. The camera and the controls links are separate
 * script-owned states with their own unlink methods and are not touched. */
void CODOL_PlayerLinkReset(int clientNum);
/* Releases every link a client owns: used for spawn, disconnect and map reset. */
void CODOL_PlayerLinkResetClient(int clientNum);
void CODOL_PlayerLinkEntityFreed(const struct gentity_s *freed);
/* Advances linked view after the tag parent runs, inside G_RunClient before
 * linked origin publication. Does not move the player. */
void CODOL_PlayerLinkRunFrame(struct gentity_s *ent);

/* True while the player holds a weapon-view link, which must not have its origin
 * driven by the retained tag attachment (IW4 4b3f72 skips the origin update for
 * exactly this flag). The retained G_RunClient has no such test, so this is the
 * predicate its proposed integration hunk calls. */
qboolean CODOL_PlayerLinkSuppressesFixedLink(const struct gentity_s *ent);

/* IW4 G_GetPlayerViewOrigin 0x4b6d00: the weapon-view link's tag_player, the
 * origin a playerLinkWeaponViewToDelta player (the AC-130 gunner) sees and
 * fires from. Returns 0 when ps holds no such link; the retained
 * G_GetPlayerViewOrigin then keeps its turret/eye origin. */
int CODOL_PlayerWeaponViewOrigin(const struct playerState_s *ps, float *origin);

/* The clamp a link asks for, or qfalse when it asks for none. Consumer-facing:
 * the movement code applies it, this module only produces it. */
qboolean CODOL_PlayerLinkViewClamp(int clientNum, float base[2], float range[2]);
/* Movement consumer: only the owning live playerState may read the script
 * record. previousYaw is the yaw before command angles were applied. */
void CODOL_PlayerLinkClampView(struct playerState_s *ps, float previousYaw);
/* Playing-frame capture only; never invoked after spectator follow copies. */
void CODOL_CaptureClientPlayerLinks(unsigned clientNum);

qboolean CODOL_PlayerIsLinked(int clientNum);
const codolPlayerLink_t *CODOL_PlayerLinkState(int clientNum);
/* Remote vehicle body-angle capture. Reject conflicting live link ownership. */
int CODOL_PlayerLinkSetRemoteAngles(unsigned clientNum,const float angles[3]);
/* Live C1 ps+0x014 linkFlags producer. Bit 1 is linked-offset and bit 2 is
 * weapon-view delta. Movement consumes this value directly; otherFlags is the
 * separate C1 field at ps+0x010. */
unsigned CODOL_PlayerLinkFlags(int clientNum);
struct gentity_s *CODOL_PlayerControlsLinkedEntity(int clientNum);
struct gentity_s *CODOL_PlayerCameraLinkedEntity(int clientNum, int *tagIndex);
/* Reverse lookup for consumers that own a controlled entity: returns the client
 * number steering it, or -1. */
int CODOL_EntityControllingPlayer(int entNum);

/* Pure translation of the record captured with this playerState. The caller
 * must supply that captured value, never a live client-number lookup for a
 * delayed snapshot. Capture and archive plumbing carry this record with the
 * playerState; movement and controls consumers remain under implementation. */
int CODOL_OverlayPlayerLinks(codol_player_fields_t *wire,
                            const codol_ps_links_t *captured);

void CODOL_PlayerCmd_PlayerLinkTo(scr_entref_t entref);
void CODOL_PlayerCmd_PlayerLinkToDelta(scr_entref_t entref);
void CODOL_PlayerCmd_PlayerLinkToAbsolute(scr_entref_t entref);
void CODOL_PlayerCmd_PlayerLinkWeaponViewToDelta(scr_entref_t entref);
void CODOL_PlayerCmd_PlayerLinkedOffsetEnable(scr_entref_t entref);
void CODOL_PlayerCmd_PlayerLinkedOffsetDisable(scr_entref_t entref);
void CODOL_PlayerCmd_CameraLinkTo(scr_entref_t entref);
void CODOL_PlayerCmd_CameraUnlink(scr_entref_t entref);
void CODOL_PlayerCmd_ControlsLinkTo(scr_entref_t entref);
void CODOL_PlayerCmd_ControlsUnlink(scr_entref_t entref);

/* Extension point for the retained "unlink" method: returns qtrue when the
 * receiver was a linked player and the player link was released. */
qboolean CODOL_PlayerLinkUnlinkReceiver(scr_entref_t entref);

/* Bulk registration remains deferred: linked collision and the remaining
 * reference behavior are unfinished. Camera and controls methods have
 * individual registry entries in scr_vm_main.c. */
void CODOL_ScriptStartupExtra_Register(void);

#ifdef __cplusplus
}
#endif

#endif /* CODOL_SERVER */
#endif /* __CODOL_SCRIPT_STARTUP_EXTRA_H__ */
