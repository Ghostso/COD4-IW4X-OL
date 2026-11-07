/* C1 SetClientMaterial and the publication of its two playerState words.
 * See codol_script_client_material.h for the C1 provenance.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include <string.h>
#include <stdio.h>
#include "codol_script_client_material.h"

/* C1 0x00cd9414, in table order; the index is the playerState word. */
static const char *const client_material_types[2] = { "killcam_you", "head_icon_self" };

int CODOL_ClientMaterialType(const char *name)
{
    unsigned i;
    if (!name) return -1;
    for (i = 0; i < 2; ++i) {
        const char *a = name, *b = client_material_types[i];
        /* C1 compares with its case-insensitive stricmp (0x006283d0). */
        while (*a && *b) {
            char x = *a, y = *b;
            if (x >= 'A' && x <= 'Z') x = (char)(x - 'A' + 'a');
            if (y >= 'A' && y <= 'Z') y = (char)(y - 'A' + 'a');
            if (x != y) break;
            ++a; ++b;
        }
        if (!*a && !*b) return (int)i;
    }
    return -1;
}

static int put_player(codol_player_fields_t *out, unsigned offset, uint32_t value)
{
    unsigned i;
    const codol_player_field_t *field;
    for (i = 0; i < CODOL_PLAYER_FIELDS; ++i) {
        field = CODOL_PlayerField(i);
        if (!field) return 0;
        if (field->offset == offset) { out->field[i] = value; return 1; }
    }
    return 0;
}

int CODOL_OverlayPlayerClientMaterials(codol_player_fields_t *wire, const unsigned slots[2])
{
    codol_player_fields_t out;
    unsigned i;
    if (!wire || !slots) return 0;
    out = *wire;
    for (i = 0; i < 2; ++i) {
        if (slots[i] > CODOL_CLIENT_MATERIAL_MAX) return 0;
        if (!put_player(&out, CODOL_CLIENT_MATERIAL_FIELD + 4u * i, slots[i])) return 0;
    }
    *wire = out;
    return 1;
}

#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "server.h"
#include "codol_playerstate_ext.h"
#include "codol_assets.h"
#include "qcommon_io.h"

/* Retained G_MaterialIndex (_g_utils_mp.asm): native index relative to
 * CS_MATERIALS, 0 for "", the engine's own "not precached" script error when
 * allocation is closed - the contract C1 0x00570290 has. It copies the name
 * unbounded into a 0x48-byte frame buffer; C1 bounds its copy at 0x40
 * (0x0051ed18), so the name is bounded here before the call. */
extern int G_MaterialIndex(const char *name);
#define CODOL_CLIENT_MATERIAL_NAME_MAX 0x40

_Static_assert(CODOL_PS_CLIENT_MATERIAL_SLOTS == 2,
    "the playerState extension must hold both C1 client material words");

void CODOL_Scr_SetClientMaterial(scr_entref_t ref)
{
    gentity_t *ent;
    codol_ps_ext_t *ext;
    const char *type = NULL, *material = NULL;
    unsigned params;
    int slot, native = 0;
    if (ref.classnum || ref.entnum >= MAX_GENTITIES) {
        Scr_ObjectError("not an entity"); return;
    }
    ent = &g_entities[ref.entnum];
    if (!ent->client) {
        Scr_ObjectError(va("entity %i is not a player", ref.entnum)); return;
    }
    ext = CODOL_PlayerStateExt(&ent->client->ps);
    if (!ext) { Scr_Error("player client material storage is unavailable"); return; }
    params = Scr_GetNumParam();
    if (params >= 1) type = Scr_GetString(0);
    if (params >= 2) material = Scr_GetString(1);
    /* C1 0x0051ecf2..0x0051ecfe: no type, or an empty one, clears both. */
    if (!type || !*type) {
        memset(ext->client_material, 0, sizeof(ext->client_material));
        return;
    }
    if (material && *material) {
        if (strlen(material) >= CODOL_CLIENT_MATERIAL_NAME_MAX) {
            Scr_ParamError(1, "client material name is too long"); return;
        }
        native = G_MaterialIndex(material);
        if (native < 0 || native >= MAX_MATERIALS) {
            Scr_ParamError(1, va("\"%s\" could not be registered as a client material", material));
            return;
        }
    }
    slot = CODOL_ClientMaterialType(type);
    if (slot < 0) {
        Scr_Error(va("SetClientMaterial() - invalid <type> string <%s> for client %i", type, ref.entnum));
        return;
    }
    ext->client_material[slot] = (uint16_t)native;
}

int CODOL_OverlayServerClientMaterials(codol_player_fields_t *wire, const playerState_t *ps)
{
    const codol_ps_ext_t *ext;
    unsigned slots[2], i;
    if (!wire || !ps) return 0;
    /* The captured state's own words: a follower or an archived frame
     * publishes what that state carried, as C1's in-playerState store does. */
    ext = CODOL_PlayerStateExtConst(ps);
    if (!ext) return 0;
    for (i = 0; i < 2; ++i) {
        int mapped;
        if (!ext->client_material[i]) { slots[i] = 0; continue; }
        /* G_MaterialIndex publishes the configstring, and the CoDOL bank maps
         * it before snapshots are built; an unmapped index means the bank is
         * exhausted. Fail the frame rather than draw another material. */
        mapped = CODOL_ServerMaterialToWire(ext->client_material[i]);
        if (mapped <= 0 || mapped > CODOL_CLIENT_MATERIAL_MAX) return 0;
        slots[i] = (unsigned)mapped;
    }
    return CODOL_OverlayPlayerClientMaterials(wire, slots);
}
#endif
