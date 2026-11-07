#include "codol_weapon_lock.h"
#include <assert.h>
#include <string.h>
#include <math.h>
#include <stdio.h>
int main(void)
{
    codol_weapon_lock_t s,before;float point[]={1,2,3},offset[]={100,0,-32},bad[]={NAN,0,0};
    CODOL_ResetWeaponLock(&s);assert(!s.flags && s.entity==2047);
    assert(CODOL_SetWeaponLockWarning(&s,0x10,1));
    assert(CODOL_SetWeaponLockWarning(&s,0x20,1));
    assert(CODOL_SetWeaponLock(&s,17,NULL,0,NULL,0) && s.flags==0x31 && s.entity==17);
    assert(CODOL_SetWeaponLock(&s,17,NULL,1,offset,0) && s.flags==0x3b);
    assert(!memcmp(s.missile_offset,offset,sizeof(offset)));
    assert(CODOL_SetWeaponLock(&s,0,point,1,NULL,1) && s.flags==0x7f && s.entity==17);
    assert(!memcmp(s.position,point,sizeof(point)) && !s.missile_offset[0] && !s.missile_offset[2]);
    CODOL_FreeWeaponLock(&s);assert(s.flags==0x70 && s.entity==2047 && s.position[2]==3);
    assert(CODOL_SetWeaponLock(&s,18,NULL,0,NULL,0) && s.flags==0x31 && s.entity==18);
    assert(CODOL_SetWeaponLockWarning(&s,0x10,0) && s.flags==0x21);
    before=s;
    assert(!CODOL_SetWeaponLock(&s,2047,NULL,1,NULL,0));
    assert(!CODOL_SetWeaponLock(&s,0,bad,0,NULL,0));
    assert(!CODOL_SetWeaponLock(&s,18,NULL,1,bad,0));
    assert(!CODOL_SetWeaponLockWarning(&s,2,0));
    assert(!memcmp(&before,&s,sizeof(s)));
    { codol_player_fields_t wire,prior;unsigned found=0;
      memset(&wire,0xa5,sizeof(wire));prior=wire;
      assert(CODOL_OverlayWeaponLock(&wire,&s));
      for(unsigned i=0;i<CODOL_PLAYER_FIELDS;++i) {
          unsigned o=CODOL_PlayerField(i)->offset;
          if(o==0x48c){assert(wire.field[i]==0x21);++found;}
          else if(o==0x490){assert(wire.field[i]==18);++found;}
          else if(o>=0x494 && o<=0x49c && !(o&3)) {
              float value;memcpy(&value,&wire.field[i],4);assert(value==point[(o-0x494)/4]);++found;
          } else assert(wire.field[i]==prior.field[i]);
      }
      assert(found==5);prior=wire;s.flags=128;
      assert(!CODOL_OverlayWeaponLock(&wire,&s) && !memcmp(&wire,&prior,sizeof(wire)));
    }
    puts("PASS: weapon lock entity/position transitions, mode and warning preservation, missile offsets and atomic errors");
}
