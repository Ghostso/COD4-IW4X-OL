#include "codol_configstrings.h"
#include "codol_sv_state.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    codol_configstrings_t inherited={0},overrides={0};
    char white[]="white";
    const char *cells[]={"4276",white,"681","MP_VICTORY","2","cod"};
    const char *bad[]={"6519","bad"}; unsigned i,count; size_t bytes; const char *saved;
    assert(CODOL_ImportConstantConfigstrings(&inherited,3,cells));
    white[0]='X'; assert(!strcmp(inherited.values[4276],"white"));
    assert(CODOL_RegisterHudMaterial(&overrides,&inherited,"white")==1 && !overrides.count);
    assert(CODOL_RegisterLocalizedString(&overrides,&inherited,"MP_VICTORY")==1 && !overrides.count);
    assert(CODOL_RegisterHudMaterial(&overrides,&inherited,"damage_feedback")==2 && overrides.count==1);
    assert(CODOL_RegisterHudMaterial(&overrides,&inherited,"damage_feedback")==2 && overrides.count==1);
    assert(CODOL_RegisterLocalizedString(&overrides,&inherited,"Hello player")==2 && overrides.count==2);
    assert(CODOL_RegisterHudMaterial(&overrides,&inherited,"")==0);
    assert(CODOL_RegisterHudMaterial(&overrides,&inherited,"bad name")==-1);
    assert(CODOL_RegisterHudMaterial(&inherited,&inherited,"new")==-1);
    assert(CODOL_SetConfigstring(&overrides,4276,""));
    /* Clearing a constant does not make its slot safe to repurpose. */
    assert(CODOL_RegisterHudMaterial(&overrides,&inherited,"replacement")==3);
    saved=inherited.values[4276]; count=inherited.count; bytes=inherited.bytes;
    assert(!CODOL_ImportConstantConfigstrings(&inherited,1,bad));
    bad[0]="-1"; assert(!CODOL_ImportConstantConfigstrings(&inherited,1,bad));
    bad[0]="999999999999999999999"; assert(!CODOL_ImportConstantConfigstrings(&inherited,1,bad));
    bad[0]="12x"; assert(!CODOL_ImportConstantConfigstrings(&inherited,1,bad));
    { const char *duplicate[]={"2","a","02","b"};
      assert(!CODOL_ImportConstantConfigstrings(&inherited,2,duplicate)); }
    assert(inherited.values[4276]==saved && inherited.count==count && inherited.bytes==bytes);
    for(i=1;i<CODOL_HUD_MATERIAL_SLOTS;++i) assert(CODOL_SetConfigstring(&inherited,CODOL_CS_MATERIALS+i,"occupied"));
    count=overrides.count; bytes=overrides.bytes;
    assert(CODOL_RegisterHudMaterial(&overrides,&inherited,"no room")==-1);
    assert(CODOL_RegisterHudMaterial(&overrides,&inherited,"no_room")==-1 && overrides.count==count && overrides.bytes==bytes);
    assert(CODOL_ImportConstantConfigstrings(&inherited,0,NULL) && !inherited.count && !inherited.bytes);
    CODOL_ClearConfigstrings(&overrides); CODOL_ClearConfigstrings(&inherited);
    CODOL_ResetServerConfigstrings();
    assert(!CODOL_ServerInheritedConfigstrings());
    assert(!CODOL_SetServerInheritedConfigstrings("invalid",0,NULL));
    assert(!CODOL_SetServerInheritedConfigstrings("mp",1,bad) && !CODOL_ServerInheritedConfigstrings());
    assert(CODOL_SetServerInheritedConfigstrings("mp",3,cells));
    assert(CODOL_ServerInheritedConfigstrings()->count==3);
    assert(!CODOL_SetServerInheritedConfigstrings("coop",0,NULL));
    assert(!CODOL_SetServerInheritedConfigstrings("mp",0,NULL));
    assert(CODOL_SetConfigstring(CODOL_ServerConfigstrings(),4277,"custom"));
    CODOL_ResetServerConfigstrings();
    assert(!CODOL_ServerInheritedConfigstrings() && !CODOL_ServerConfigstrings()->count);
    assert(CODOL_SetServerInheritedConfigstrings("coop",0,NULL));
    assert(CODOL_ServerInheritedConfigstrings() && !CODOL_ServerInheritedConfigstrings()->count);
    CODOL_ResetServerConfigstrings();
    puts("PASS: inherited configstring import, reuse, reservation and atomic failure"); return 0;
}
