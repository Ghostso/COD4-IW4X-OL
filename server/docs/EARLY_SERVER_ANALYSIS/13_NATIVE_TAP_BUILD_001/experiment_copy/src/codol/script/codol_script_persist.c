/* Script objects that outlive a round restart.
 *
 * Scr_ShutdownSystem clears every struct (Scr_FreeObjects) because IW3 kept
 * only primitives in game[] and pers[] across map_restart. CoDOL's scripts
 * follow IW4 and keep structs there (pers["killstreaks"][n], the _awards
 * stats), so the struct sweep spares what these roots still reach. */
#include "server.h"
#include "g_shared.h"
#include "codol_script_persist.h"

unsigned CODOL_ScriptPersistRoots(unsigned *roots, unsigned max)
{
    unsigned count=0;
    int i;
    if(!roots || !level.clients) return 0;
    for(i=0;i<level.maxclients && count<max;++i) {
        unsigned id=level.clients[i].sess.scriptPersId;
        if(id) roots[count++]=id;
    }
    return count;
}
