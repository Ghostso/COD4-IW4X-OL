/* Captured native link state; no VM, entity pointers or live lookups. */
#ifndef CODOL_PLAYER_LINKS_H
#define CODOL_PLAYER_LINKS_H
#include <stdint.h>
#pragma pack(push, 8)
typedef struct {
    uint32_t mode;
    uint32_t offsetEnabled;
    /* C1 ps+0x14 bit 1 (IW4 PLF_ANGLES_LOCKED): set by the absolute /
     * blend link methods (0x53b37a, 0x53bad6), cleared on unlink (0x53a8fa). */
    uint32_t anglesLocked;
    /* C1 ps+0x1ec. ENTITYNUM_NONE unless mode is weapon-view. */
    uint32_t linkWeaponEntNum;
    uint32_t cameraEntNum;
    uint32_t cameraTagIndex;
    uint32_t controlsEntNum;
    uint32_t cameraFlags; /* C1 otherFlags: active2, retained-on-unlink80. */
    /* Float words captured at weapon-view link time (C1 ps+1e0..1e8).
     * Keep them with the snapshot, not in a live-client lookup at encoding. */
    uint32_t weaponViewAngleBits[3];
    /* Updated link reference, separate from the weapon-view initial angles. */
    uint32_t linkAngleBits[3];
} codol_ps_links_t;

/* Native and C1 share ENTITYNUM_NONE 2047; publication writes it unchanged.
 * Tag indices address the 64-entry configstring tag bank. */
static inline int CODOL_PlayerLinksValid(const codol_ps_links_t *value)
{
    return value && value->mode <= 2 && value->offsetEnabled <= 1 && value->anglesLocked <= 1 &&
        (value->mode != 0 || !value->anglesLocked) &&
        value->linkWeaponEntNum <= ENTITYNUM_NONE &&
        (value->mode == 2 || value->linkWeaponEntNum == ENTITYNUM_NONE) &&
        value->cameraEntNum <= ENTITYNUM_NONE && value->controlsEntNum <= ENTITYNUM_NONE &&
        value->cameraTagIndex < 64 && !(value->cameraFlags & ~UINT32_C(0x82)) &&
        (value->weaponViewAngleBits[0] & UINT32_C(0x7f800000)) != UINT32_C(0x7f800000) &&
        (value->weaponViewAngleBits[1] & UINT32_C(0x7f800000)) != UINT32_C(0x7f800000) &&
        (value->weaponViewAngleBits[2] & UINT32_C(0x7f800000)) != UINT32_C(0x7f800000) &&
        (value->linkAngleBits[0] & UINT32_C(0x7f800000)) != UINT32_C(0x7f800000) &&
        (value->linkAngleBits[1] & UINT32_C(0x7f800000)) != UINT32_C(0x7f800000) &&
        (value->linkAngleBits[2] & UINT32_C(0x7f800000)) != UINT32_C(0x7f800000);
}
#pragma pack(pop)
#endif
