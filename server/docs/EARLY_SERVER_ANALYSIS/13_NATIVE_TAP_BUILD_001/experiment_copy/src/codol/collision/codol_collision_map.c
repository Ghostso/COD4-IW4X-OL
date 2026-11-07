#include "codol_collision.h"
#include <string.h>

void CODOL_FreeCollisionMap(codol_collision_map_t *map)
{
    if (!map) return;
    CODOL_FreeCollisionMaterials(&map->materials);
    CODOL_FreeCollisionBrushes(&map->brushes);
    CODOL_FreeCollisionTerrain(&map->terrain);
    CODOL_FreeCollisionLeaves(&map->leaves);
    CODOL_FreeCollisionBrushTree(&map->brush_tree);
    CODOL_FreeMapEntities(&map->entities);
    CODOL_FreeCollisionStaticModels(&map->static_models);
    memset(map,0,sizeof(*map));
}
int CODOL_ReadCollisionMap(const codol_asset_t *collision,const codol_asset_t *world,
                           codol_collision_name_resolver_t resolver,void *context,
                           codol_collision_map_t *out)
{
    return CODOL_ReadCollisionMapResolved(collision,world,resolver,NULL,context,out);
}
int CODOL_ReadCollisionMapResolved(const codol_asset_t *collision,const codol_asset_t *world,
                           codol_collision_name_resolver_t resolver,
                           codol_collision_model_resolver_t model_resolver,void *context,
                           codol_collision_map_t *out)
{
    codol_collision_map_t map={0};
    codol_collision_layout_t layout;
    if (!out || !CODOL_ReadCollisionLayout(collision,&layout)) return 0;
    /* C1's loader matches the IW4 clipMap layout through dynEntCollList.
     * The following uint32 at 0xcc is checksum in IW4x's declaration.
     * Preserve the archive value; do not substitute the configstring CRC. */
    map.checksum=(uint32_t)collision->data[204]|(uint32_t)collision->data[205]<<8|
        (uint32_t)collision->data[206]<<16|(uint32_t)collision->data[207]<<24;
    map.static_model_count=layout.sections[CODOL_COLL_STATIC_MODELS].count;
    if (!CODOL_ReadCollisionStaticModels(collision,model_resolver,context,&map.static_models) ||
        !CODOL_ReadWorldBrushes(collision,world,&map.brushes) ||
        !CODOL_ReadCollisionTerrain(collision,&map.terrain) ||
        !CODOL_ReadCollisionLeaves(collision,&map.leaves) ||
        !CODOL_ReadCollisionBrushTree(collision,&map.brush_tree) ||
        !CODOL_ReadCollisionMaterials(collision,resolver,context,&map.materials) ||
        !CODOL_ReadCollisionMapEntities(collision,&map.entities)) {
        CODOL_FreeCollisionMap(&map); return 0;
    }
    CODOL_FreeCollisionMap(out); *out=map; return 1;
}
