/* Eight-word hide-part masks for 253-bone DObjs; see codol_hide_parts.h. */
#include "q_shared.h"
#include "entity.h"
#include "g_shared.h"
#include "dobj.h"
#include "codol_entitystate_ext.h"
#include "codol_hide_parts.h"
#include <string.h>

void __cdecl DObjSetHidePartBits(DObj *obj, const unsigned int *partBits);

void CODOL_GetEntityHidePartBits(const struct gentity_s *ent, uint32_t bits[8])
{
    CODOL_EntityStateHidePartBits(ent ? &ent->s : NULL, bits);
}

void CODOL_StoreEntityHidePartBits(struct gentity_s *ent, const uint32_t bits[8])
{
    if (ent)
        CODOL_EntityStateSetHidePartBits(&ent->s, bits);
}

void CODOL_SetEntityPartHidden(struct gentity_s *ent, struct DObj_s *obj, unsigned int bone, int hidden)
{
    uint32_t bits[DOBJ_PART_BIT_WORDS];
    CODOL_GetEntityHidePartBits(ent, bits);
    if (obj && bone < obj->numBones) {
        uint32_t bit = 0x80000000u >> (bone & 31);
        if (hidden)
            bits[bone >> 5] |= bit;
        else
            bits[bone >> 5] &= ~bit;
    }
    if (obj)
        DObjSetHidePartBits(obj, bits);
    CODOL_StoreEntityHidePartBits(ent, bits);
}

void CODOL_ShowAllEntityParts(struct gentity_s *ent, struct DObj_s *obj)
{
    uint32_t bits[DOBJ_PART_BIT_WORDS] = {0};
    if (obj)
        DObjSetHidePartBits(obj, bits);
    CODOL_StoreEntityHidePartBits(ent, bits);
}

void CODOL_DObjSetEntityHidePartBits(struct DObj_s *obj, const struct gentity_s *ent)
{
    uint32_t bits[DOBJ_PART_BIT_WORDS];
    if (!obj)
        return;
    CODOL_GetEntityHidePartBits(ent, bits);
    DObjSetHidePartBits(obj, bits);
}

void CODOL_DObjSetEntityNumHidePartBits(struct DObj_s *obj, int handle)
{
    if (handle < 0 || handle >= MAX_GENTITIES)
        return;
    CODOL_DObjSetEntityHidePartBits(obj, &g_entities[handle]);
}

void CODOL_CopyEntityHidePartBits(struct gentity_s *to, const struct gentity_s *from)
{
    uint32_t bits[DOBJ_PART_BIT_WORDS];
    CODOL_GetEntityHidePartBits(from, bits);
    CODOL_StoreEntityHidePartBits(to, bits);
}
