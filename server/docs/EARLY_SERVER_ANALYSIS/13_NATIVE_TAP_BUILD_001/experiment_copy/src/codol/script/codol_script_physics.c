#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "server.h"

void CODOL_Scr_PhysicsLaunchClient(scr_entref_t reference)
{
    unsigned number=reference.entnum;
    if(reference.classnum || number>=ENTITYNUM_WORLD || !g_entities[number].r.inuse) {
        Scr_ObjectError("physicslaunchclient requires a live entity"); return;
    }
    /* IW4 method 407eb0 calls SetupPhysicsLaunch, clears contents/physicsObject,
     * then SV_LinkEntity (4e0880). Retained PhysicsLaunch performs the same
     * setup with IW3's native trajectory enum. Its vectors are linear/angular
     * deltas, not a point/force pair. Preserve its argument and class checks. */
    ScriptEntCmd_PhysicsLaunch(reference);
    SV_LinkEntity(g_entities+number);
}
#endif
