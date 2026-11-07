#include "codol_sv_state.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    CODOL_ResetServerConfigstrings();
    assert(!CODOL_ServerMapIdentityMatches("mp_killhouse_sh","mp"));
    assert(!CODOL_SetServerMapIdentity("../mp_killhouse_sh","mp"));
    assert(!CODOL_SetServerMapIdentity("mp_killhouse_sh;quit","mp"));
    assert(!CODOL_SetServerMapIdentity("MP_KILLHOUSE_SH","mp"));
    assert(!CODOL_SetServerMapIdentity("mp_killhouse_sh","tdm"));
    assert(CODOL_SetServerMapIdentity("mp_killhouse_sh","mp"));
    assert(CODOL_SetServerMapIdentity("mp_killhouse_sh","mp"));
    assert(!CODOL_SetServerMapIdentity("mp_cargoship_sh","mp"));
    assert(CODOL_SetServerInheritedConfigstrings("mp",0,NULL));
    assert(CODOL_ServerMapIdentityMatches("mp_killhouse_sh","mp"));
    assert(!CODOL_ServerMapIdentityMatches("mp_cargoship_sh","mp"));
    assert(!CODOL_ServerMapIdentityMatches("mp_killhouse_sh","coop"));
    CODOL_ResetServerConfigstrings();
    assert(CODOL_SetServerMapIdentity("mp_cargoship_sh","mp"));
    assert(CODOL_SetServerInheritedConfigstrings("mp",0,NULL));
    assert(CODOL_ServerMapIdentityMatches("mp_cargoship_sh","mp"));
    puts("PASS: mounted map/configstring identity is atomic and map-scoped");
    return 0;
}
