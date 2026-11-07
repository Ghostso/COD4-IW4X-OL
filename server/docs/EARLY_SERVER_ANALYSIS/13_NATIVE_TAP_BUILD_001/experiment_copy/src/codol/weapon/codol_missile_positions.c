#include "codol_weapon_lock.h"
#include <string.h>
unsigned char codol_missile_position_active[ENTITYNUM_WORLD];
unsigned char codol_missile_lock_active[ENTITYNUM_WORLD];
float codol_missile_positions[ENTITYNUM_WORLD][3];
void CODOL_ResetMissilePosition(unsigned entity)
{
    if(entity>=ENTITYNUM_WORLD)return;
    codol_missile_position_active[entity]=0;
    codol_missile_lock_active[entity]=0;
    memset(codol_missile_positions[entity],0,sizeof(codol_missile_positions[entity]));
}
void CODOL_ResetMissilePositions(void)
{
    memset(codol_missile_lock_active,0,sizeof(codol_missile_lock_active));
    memset(codol_missile_position_active,0,sizeof(codol_missile_position_active));
    memset(codol_missile_positions,0,sizeof(codol_missile_positions));
}
void CODOL_SetMissileEntityTarget(unsigned entity,int locked)
{
    CODOL_ResetMissilePosition(entity);
    if(entity<ENTITYNUM_WORLD) codol_missile_lock_active[entity]=locked ? 1 : 0;
}
