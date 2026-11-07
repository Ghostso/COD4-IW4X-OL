#include "codol_sv_frame.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
/* The engine-state translator owns this in the server; the harness stubs the
  * translator out, so it supplies the diagnostic slot the capture writes. */
const char *codol_player_failure;
static codol_hud_state_t produced;
static int accepted=1;
int CODOL_CollectServerHud(codol_hud_state_t *out,const hudElemState_t *source)
{
    assert(source); *out=produced; return accepted;
}
int main(void)
{
    hudElemState_t source={0}; codol_hud_state_t out,before;
    produced.count[0]=1; produced.elements[0][0].field[0]=123;
    assert(CODOL_CaptureClientSnapshotHud(0,42,&source));
    produced.elements[0][0].field[0]=456;
    assert(CODOL_CaptureClientSnapshotHud(1,42,&source));
    assert(CODOL_CopyClientSnapshotHud(0,42,&out) && out.elements[0][0].field[0]==123);
    before=out;
    assert(!CODOL_CopyClientSnapshotHud(0,41,&out) && !memcmp(&out,&before,sizeof(out)));
    assert(CODOL_CaptureClientSnapshotHud(0,43,&source));
    assert(!CODOL_CopyClientSnapshotHud(0,42,&out));
    assert(CODOL_CopyClientSnapshotHud(0,43,&out) && out.elements[0][0].field[0]==456);
    accepted=0; assert(!CODOL_CaptureClientSnapshotHud(0,44,&source));
    assert(!CODOL_CopyClientSnapshotHud(0,43,&out) && !CODOL_CopyClientSnapshotHud(0,44,&out));
    assert(CODOL_CopyClientSnapshotHud(1,42,&out));
    CODOL_InvalidateClientSnapshotHud(1); assert(!CODOL_CopyClientSnapshotHud(1,42,&out));
    accepted=1; assert(CODOL_CaptureClientSnapshotHud(1,45,&source));
    assert(!CODOL_CaptureClientSnapshotHud(1,46,NULL) && !CODOL_CopyClientSnapshotHud(1,45,&out));
    assert(!CODOL_CaptureClientSnapshotHud(MAX_CLIENTS,1,&source));
    assert(!CODOL_CopyClientSnapshotHud(MAX_CLIENTS,1,&out));
    assert(!CODOL_CopyClientSnapshotHud(0,44,NULL));
    CODOL_ClearClientSnapshotHud(0); CODOL_ClearClientSnapshotHud(1); CODOL_ClearClientSnapshotHud(MAX_CLIENTS);
    puts("PASS: per-client HUD capture ownership, sequence identity, invalidation, failed replacement and teardown");
}
