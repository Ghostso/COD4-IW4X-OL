/* Pure translation of captured player link state. */
#include "codol_player_links_wire.h"
#include "qcommon_io.h"

static int link_put(codol_player_fields_t *wire, unsigned offset, uint32_t value)
{
    unsigned i;

    for(i = 0; i < CODOL_PLAYER_FIELDS; ++i) {
        const codol_player_field_t *field = CODOL_PlayerField(i);

        if(field && field->offset == offset) { wire->field[i] = value; return 1; }
    }
    return 0;
}

static int link_get(const codol_player_fields_t *wire, unsigned offset, uint32_t *out)
{
    unsigned i;

    for(i = 0; i < CODOL_PLAYER_FIELDS; ++i) {
        const codol_player_field_t *field = CODOL_PlayerField(i);

        if(field && field->offset == offset) { *out = wire->field[i]; return 1; }
    }
    return 0;
}

int CODOL_OverlayPlayerLinks(codol_player_fields_t *wire, const codol_ps_links_t *link)
{
    codol_player_fields_t out;
    uint32_t pmFlags, otherFlags, linkFlags;

    if(!wire || !CODOL_PlayerLinksValid(link)) return 0;
    /* Entity lifetime was resolved when this state was captured. A live entity
     * lookup here would erase an archived link after the target is freed, or
     * make that old link refer to a new occupant of the same slot. */
    out = *wire;
    if(!link_get(&out, 0x00c, &pmFlags) || !link_get(&out, 0x010, &otherFlags) ||
       !link_get(&out, 0x014, &linkFlags)) return 0;

    /* C1 0x548480 / 0x54856f. */
    pmFlags &= ~UINT32_C(0x80000);
    if(link->controlsEntNum != ENTITYNUM_NONE) pmFlags |= UINT32_C(0x80000);

    /* C1 0x54824e / 0x5482a5. */
    otherFlags = (otherFlags & ~UINT32_C(0x82)) | link->cameraFlags;

    /* C1 0x53b559 sets bit 1 for linked offset; 0x53ad9e sets bit 2
     * for weapon-view delta in this same three-bit field. */
    /* C1 0x53b37a / 0x53bad6 set bit 0x1 (PLF_ANGLES_LOCKED) for the
     * absolute and blend links; PM_UpdateViewAngles 0x4141b8 reads it back. */
    linkFlags &= ~UINT32_C(0x7);
    if(link->anglesLocked) linkFlags |= 0x1;
    if(link->offsetEnabled) linkFlags |= 0x2;
    if(link->mode == 2) linkFlags |= 0x4;

    if(!link_put(&out, 0x00c, pmFlags) || !link_put(&out, 0x010, otherFlags) ||
       !link_put(&out, 0x014, linkFlags)) return 0;

    /* C1 53ad7a..53ad98 copies ps.viewangles into these three angle
     * netfields when establishing the weapon-view link. */
    if(!link_put(&out, 0x1e0, link->weaponViewAngleBits[0]) ||
       !link_put(&out, 0x1e4, link->weaponViewAngleBits[1]) ||
       !link_put(&out, 0x1e8, link->weaponViewAngleBits[2])) return 0;

    /* C1 CG_OffsetFirstPersonView 0x4711aa skips the normal eye-height add
     * whenever this is not ENTITYNUM_NONE. Only weapon-view linking owns it. */
    if(!link_put(&out, 0x1ec, link->linkWeaponEntNum)) return 0;

    /* C1 575fad..575fc5 publishes the calculated reference at ps+1d4;
     * 575fe9..575ffd initializes it to zero for the relative-link case. */
    if(!link_put(&out, 0x1d4, link->linkAngleBits[0]) ||
       !link_put(&out, 0x1d8, link->linkAngleBits[1]) ||
       !link_put(&out, 0x1dc, link->linkAngleBits[2])) return 0;

    /* C1 unlink leaves these fields behind. Publish the captured values even
     * when inactive, instead of depending on a previous recipient's baseline. */
    if(!link_put(&out, 0x054, link->cameraEntNum) ||
       !link_put(&out, 0x058, link->cameraTagIndex)) return 0;
    /* C1 0x548492 / 0x548577: the controls field is explicitly reset to 0x7ff. */
    if(link->controlsEntNum != ENTITYNUM_NONE) {
        if(link->controlsEntNum < 0 || link->controlsEntNum >= 2047u) return 0;
        if(!link_put(&out, 0x05c, (uint32_t)link->controlsEntNum)) return 0;
    } else if(!link_put(&out, 0x05c, 2047u)) {
        return 0;
    }

    *wire = out;
    return 1;
}

int CODOL_OverlayEnginePlayerLinks(codol_player_fields_t *wire, const playerState_t *ps)
{
    const codol_ps_ext_t *ext;
    if(!wire || !ps) return 0;
    ext = CODOL_PlayerStateExtConst(ps);
    if(!ext || !ext->links_known) return 0;
    if(!CODOL_OverlayPlayerLinks(wire, &ext->links)) return 0;
    {
        static uint32_t last[64]; static int lines;
        unsigned c=(unsigned)ps->clientNum;
        uint32_t key=0x80000000u|ext->links.mode|(ext->links.offsetEnabled<<2)|(ext->links.anglesLocked<<3);
        if(CODOL_TRACE_VERBOSE() && c<64 && lines<400 && key!=last[c]) {
            last[c]=key; ++lines;
            Com_Printf(CON_CHANNEL_SERVER,"CoDOL ps: client %u linkFlags 0x%x mode %u locked %u\n",
                c,(ext->links.anglesLocked?1u:0u)|(ext->links.offsetEnabled?2u:0u)|(ext->links.mode==2?4u:0u),
                (unsigned)ext->links.mode,(unsigned)ext->links.anglesLocked);
        }
    }
    return 1;
}
