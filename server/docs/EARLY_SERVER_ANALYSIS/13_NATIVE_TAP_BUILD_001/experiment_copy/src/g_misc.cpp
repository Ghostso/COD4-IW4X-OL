#include "q_shared.h"
#include "g_shared.h"
#ifdef CODOL_SERVER
#include "codol_script_turret_target.h"
#include "codol_sentient.h"
#endif

#define MAX_TURRETS 32



extern turretInfo_s turretInfo[MAX_TURRETS];

extern "C"{

void G_InitTurrets()
{
  int i;

  for(i = 0; i < MAX_TURRETS; ++i){
    turretInfo[i].inuse = 0;
  }
#ifdef CODOL_SERVER
  /* EntHandle::Init has already reset its registry at level init. */
  CODOL_TurretTarget_ResetAll();
  /* The sentient registry is the turret acquisition's candidate set and holds
   * EntHandles of its own, so it is cleared on the same level-init edge. */
  CODOL_Sentient_ResetAll();
#endif
}

int G_TurretCalcFireTime()
{
    return 1000 / level.framerate;
}


}
