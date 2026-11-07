#ifndef CODOL_HIDE_PARTS_H
#define CODOL_HIDE_PARTS_H
/* Eight-word hide-part masks for 253-bone DObjs.
 *
 * C1's DObj hides parts with eight 32-bit words (0x4417e6); the retained
 * entityState carries four (entityState_t.partBits, bones 0-127). Words 4..7
 * (bones 128-252, which only CoDOL outfits have) live in the entityState
 * extension (codol_entitystate_ext.h), so they are copied into snapshots and
 * archives with the state. hidepart, showpart, showallparts, G_DObjUpdate and
 * clonePlayer go through these functions so the server DObj always receives
 * the whole mask. */
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

struct gentity_s;
struct DObj_s;

void CODOL_GetEntityHidePartBits(const struct gentity_s *ent, uint32_t bits[8]);
void CODOL_StoreEntityHidePartBits(struct gentity_s *ent, const uint32_t bits[8]);
/* hidepart / showpart: bone is a DObj bone index; indices past the DObj's
 * bone range (0xfe/0xff lookup failures) change nothing. */
void CODOL_SetEntityPartHidden(struct gentity_s *ent, struct DObj_s *obj, unsigned int bone, int hidden);
void CODOL_ShowAllEntityParts(struct gentity_s *ent, struct DObj_s *obj);
/* G_DObjUpdate: a new DObj takes the entity's whole mask. */
void CODOL_DObjSetEntityHidePartBits(struct DObj_s *obj, const struct gentity_s *ent);
/* G_CreateDObj (bgs->CreateDObj, the player animation path): the rebuilt
 * DObj of entity `handle` takes that entity's whole mask. */
void CODOL_DObjSetEntityNumHidePartBits(struct DObj_s *obj, int handle);
/* clonePlayer copies the retained four words itself; this adds the rest. */
void CODOL_CopyEntityHidePartBits(struct gentity_s *to, const struct gentity_s *from);

#ifdef __cplusplus
}
#endif
#endif
