#ifndef CODOL_POSE_BUDGET_H
#define CODOL_POSE_BUDGET_H
/* Server-pose copies of CoDOL character parts.
 *
 * The server DObj holds DOBJ_MAX_BONES (253) bones, as C1's does, so a stock
 * CoDOL outfit (168-191 bones) is posed whole and this copy is not used. It
 * remains the guard for an outfit past 253 bones: when a part the server
 * needs for gameplay (jacket, hands, head) does not fit whole, the server
 * poses a copy that keeps only what gameplay reads from it:
 *   - every root bone,
 *   - every tag_ bone (weapon, eye and stow tags),
 *   - every bone with a hit volume (XBoneInfo radiusSquared > 0), which is
 *     all DObjTraceline can hit,
 *   - every ancestor of a kept bone, so each kept bone's world transform is
 *     exactly the one the full model would give it.
 * The client still draws the complete part; only the server pose is reduced. */
#include "xassets/xmodel.h"

#ifdef __cplusplus
extern "C" {
#endif

/* bone_name maps a bone-name handle to its text (SL_ConvertToString on the
 * server). Returns a new model, or NULL when nothing can be dropped, the
 * source is malformed or allocation fails. Surfaces, LODs and materials stay
 * shared with the source (the server never skins a DObj); collision surfaces
 * are dropped because they name bones by source index. */
XModel *CODOL_BuildGameplayPoseModel(const XModel *source,const char *(*bone_name)(unsigned handle));
void CODOL_FreeGameplayPoseModel(XModel *model);

#ifdef __cplusplus
}
#endif
#endif
