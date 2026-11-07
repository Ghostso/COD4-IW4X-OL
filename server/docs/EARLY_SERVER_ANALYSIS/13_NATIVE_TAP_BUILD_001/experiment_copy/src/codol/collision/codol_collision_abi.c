/* Keep the portable converter's output compatible with retained IW3 terrain
 * routines. Installation waits for the complete clipMap and dependencies. */
#include "cm_local.h"
#include "dobj.h"
#include "codol_collision.h"
#include "codol_xmodel.h"
#include <stddef.h>

#define SAME_SIZE(a,b) _Static_assert(sizeof(a)==sizeof(b), "collision size mismatch")
#define SAME_FIELD(a,b,x,y) _Static_assert(offsetof(a,x)==offsetof(b,y), "collision field mismatch")
SAME_SIZE(codol_xmodel_bone_info_t, XBoneInfo_t);
SAME_FIELD(codol_xmodel_bone_info_t, XBoneInfo_t, bounds, bounds);
SAME_FIELD(codol_xmodel_bone_info_t, XBoneInfo_t, offset, offset);
SAME_FIELD(codol_xmodel_bone_info_t, XBoneInfo_t, radiusSquared, radiusSquared);
SAME_SIZE(codol_collision_border_t, CollisionBorder_t);
SAME_FIELD(codol_collision_border_t, CollisionBorder_t, distEq, distEq);
SAME_FIELD(codol_collision_border_t, CollisionBorder_t, zBase, zBase);
SAME_FIELD(codol_collision_border_t, CollisionBorder_t, zSlope, zSlope);
SAME_FIELD(codol_collision_border_t, CollisionBorder_t, start, start);
SAME_FIELD(codol_collision_border_t, CollisionBorder_t, length, length);
SAME_SIZE(codol_collision_partition_t, CollisionPartition_t);
_Static_assert(_Generic(((CollisionPartition_t *)0)->triCount, unsigned char: 1, default: 0),
               "terrain triangle count must preserve values above 127");
_Static_assert(_Generic(((CollisionPartition_t *)0)->borderCount, unsigned char: 1, default: 0),
               "terrain border count must be unsigned");
SAME_FIELD(codol_collision_partition_t, CollisionPartition_t, triCount, triCount);
SAME_FIELD(codol_collision_partition_t, CollisionPartition_t, borderCount, borderCount);
SAME_FIELD(codol_collision_partition_t, CollisionPartition_t, firstTri, firstTri);
SAME_FIELD(codol_collision_partition_t, CollisionPartition_t, borders, borders);
SAME_SIZE(codol_collision_aabb_t, CollisionAabbTree_t);
SAME_FIELD(codol_collision_aabb_t, CollisionAabbTree_t, origin, origin);
SAME_FIELD(codol_collision_aabb_t, CollisionAabbTree_t, halfSize, halfSize);
SAME_FIELD(codol_collision_aabb_t, CollisionAabbTree_t, materialIndex, materialIndex);
SAME_FIELD(codol_collision_aabb_t, CollisionAabbTree_t, childCount, childCount);
SAME_FIELD(codol_collision_aabb_t, CollisionAabbTree_t, index, u);
SAME_SIZE(codol_collision_plane_t, cplane_t);
SAME_FIELD(codol_collision_plane_t, cplane_t, normal, normal);
SAME_FIELD(codol_collision_plane_t, cplane_t, dist, dist);
SAME_FIELD(codol_collision_plane_t, cplane_t, type, type);
SAME_FIELD(codol_collision_plane_t, cplane_t, signbits, signbits);
SAME_SIZE(codol_collision_side_t, cbrushside_t);
SAME_FIELD(codol_collision_side_t, cbrushside_t, plane, plane);
SAME_FIELD(codol_collision_side_t, cbrushside_t, materialNum, materialNum);
SAME_FIELD(codol_collision_side_t, cbrushside_t, firstAdjacentSideOffset, firstAdjacentSideOffset);
SAME_FIELD(codol_collision_side_t, cbrushside_t, edgeCount, edgeCount);
SAME_SIZE(codol_collision_brush_t, cbrush_t);
#ifdef CODOL_SERVER
SAME_FIELD(codol_collision_brush_t,cbrush_t,glassPieceIndex,glassPieceIndex);
_Static_assert(sizeof(cbrush_t)==80 && offsetof(cbrush_t,glassPieceIndex)==70,
    "glass tail field must preserve retained brush stride and assembly offset");
#endif
SAME_FIELD(codol_collision_brush_t, cbrush_t, mins, mins);
SAME_FIELD(codol_collision_brush_t, cbrush_t, maxs, maxs);
SAME_FIELD(codol_collision_brush_t, cbrush_t, contents, contents);
SAME_FIELD(codol_collision_brush_t, cbrush_t, numsides, numsides);
SAME_FIELD(codol_collision_brush_t, cbrush_t, sides, sides);
SAME_FIELD(codol_collision_brush_t, cbrush_t, axialMaterialNum, axialMaterialNum);
SAME_FIELD(codol_collision_brush_t, cbrush_t, baseAdjacentSide, baseAdjacentSide);
SAME_FIELD(codol_collision_brush_t, cbrush_t, firstAdjacentSideOffsets, firstAdjacentSideOffsets);
SAME_FIELD(codol_collision_brush_t, cbrush_t, edgeCount, edgeCount);
SAME_SIZE(codol_collision_material_t, dmaterial_t);
SAME_FIELD(codol_collision_material_t, dmaterial_t, material, material);
SAME_FIELD(codol_collision_material_t, dmaterial_t, surfaceFlags, surfaceFlags);
SAME_FIELD(codol_collision_material_t, dmaterial_t, contentFlags, contentFlags);
SAME_SIZE(codol_collision_node_t, cNode_t);
SAME_FIELD(codol_collision_node_t, cNode_t, plane, plane);
SAME_FIELD(codol_collision_node_t, cNode_t, children, children);
SAME_SIZE(codol_collision_leaf_t, cLeaf_t);
SAME_FIELD(codol_collision_leaf_t, cLeaf_t, firstCollAabbIndex, firstCollAabbIndex);
SAME_FIELD(codol_collision_leaf_t, cLeaf_t, collAabbCount, collAabbCount);
SAME_FIELD(codol_collision_leaf_t, cLeaf_t, brushContents, brushContents);
SAME_FIELD(codol_collision_leaf_t, cLeaf_t, terrainContents, terrainContents);
SAME_FIELD(codol_collision_leaf_t, cLeaf_t, mins, mins);
SAME_FIELD(codol_collision_leaf_t, cLeaf_t, maxs, maxs);
SAME_FIELD(codol_collision_leaf_t, cLeaf_t, leafBrushNode, leafBrushNode);
SAME_FIELD(codol_collision_leaf_t, cLeaf_t, cluster, cluster);
SAME_SIZE(codol_collision_submodel_t, cmodel_t);
SAME_FIELD(codol_collision_submodel_t, cmodel_t, mins, mins);
SAME_FIELD(codol_collision_submodel_t, cmodel_t, maxs, maxs);
SAME_FIELD(codol_collision_submodel_t, cmodel_t, radius, radius);
SAME_FIELD(codol_collision_submodel_t, cmodel_t, leaf, leaf);
SAME_SIZE(codol_collision_brush_node_t, cLeafBrushNode_t);
SAME_FIELD(codol_collision_brush_node_t, cLeafBrushNode_t, axis, axis);
SAME_FIELD(codol_collision_brush_node_t, cLeafBrushNode_t, leafBrushCount, leafBrushCount);
SAME_FIELD(codol_collision_brush_node_t, cLeafBrushNode_t, contents, contents);
SAME_FIELD(codol_collision_brush_node_t, cLeafBrushNode_t, data, data);
SAME_SIZE(codol_collision_static_model_t, cStaticModel_t);
SAME_FIELD(codol_collision_static_model_t, cStaticModel_t, writable, writable);
SAME_FIELD(codol_collision_static_model_t, cStaticModel_t, xmodel, xmodel);
SAME_FIELD(codol_collision_static_model_t, cStaticModel_t, origin, origin);
SAME_FIELD(codol_collision_static_model_t, cStaticModel_t, invScaledAxis, invScaledAxis);
SAME_FIELD(codol_collision_static_model_t, cStaticModel_t, absmin, absmin);
SAME_FIELD(codol_collision_static_model_t, cStaticModel_t, absmax, absmax);
