/* Native duplicate of a spawner's dynamic VM fields, matching T5
 * G_DuplicateScriptFields -> Scr_CopyEntityNum. Arrays have value semantics;
 * entity/struct references retain identity. No VM operand stack mutation.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
extern "C" {
#include "entity.h"
#include "cscr_variable.h"
#include "scr_vm.h"
}
// Existing native implementation is C++ with this retained calling convention.
extern "C" void __regparm2 CopyArray(unsigned int parentId, unsigned int newParentId);
extern "C" int CODOL_ActorCopySpawnerScriptFields(gentity_s *destination,
                                                  const gentity_s *source)
{
    if(!destination || !source || destination==source || !destination->r.inuse ||
       !source->r.inuse || destination->client || source->s.eType!=ET_ACTOR_SPAWNER)return 0;
    unsigned from=Scr_GetEntityId(source->s.number,0);
    unsigned to=Scr_GetEntityId(destination->s.number,0);
    // Only a newly allocated destination is valid. Do not partially merge
    // copied fields into an actor whose scripts have already started.
    if(FindFirstSibling(to))return 0;
    for(unsigned id=FindFirstSibling(from);id;id=FindNextSibling(id)) {
        unsigned name=GetVariableName(id);
        VariableValue value=Scr_EvalVariable(id); // acquires one owning ref
        if(value.type==VAR_POINTER && Scr_GetObjectType(value.u.pointerValue)==VAR_ARRAY) {
            unsigned array=Scr_AllocArray();
            CopyArray(value.u.pointerValue,array);
            RemoveRefToValue(value.type,value.u);
            value.u.pointerValue=array;
        }
        // SetVariableValue consumes the acquired/new reference; no extra
        // RemoveRef here. Strings, vectors and entity references remain valid.
        SetVariableValue(GetVariable(to,name),&value);
    }
    return 1;
}
#endif
