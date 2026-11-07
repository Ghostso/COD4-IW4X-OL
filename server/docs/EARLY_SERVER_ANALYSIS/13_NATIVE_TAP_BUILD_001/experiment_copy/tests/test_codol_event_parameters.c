#include "codol_events.h"
#include "bg.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    uint32_t value=99,events[4]={EV_NONE,EV_STANCE_FORCE_STAND,EV_STANCE_FORCE_CROUCH,EV_STANCE_FORCE_PRONE};
    uint32_t parameters[4]={UINT32_MAX,0,2,3},out[4]={9,8,7,6},saved[4];
    unsigned event,reason;
    {
        static const unsigned native[]={EV_RELOAD,EV_RELOAD_FROM_EMPTY,EV_RELOAD_START,EV_RECHAMBER_WEAPON,
            EV_FIRE_WEAPON,EV_FIRE_WEAPON_LASTSHOT};
        static const unsigned wire[]={18,19,20,34,30,31};
        uint32_t zero[4]={0},queue[4];
        for(event=0;event<6;++event) {
            assert(CODOL_EventToWire(native[event])==(int)wire[event]);
            value=99;
            assert(CODOL_EventParameterToWire(native[event],0,&value)==1 && !value);
            value=99;
            assert(CODOL_EventParameterToWire(native[event],1,&value)==-1 && value==99);
            assert(CODOL_EventParameterToWire(native[event],UINT32_MAX,&value)==-1 && value==99);
            if(event<4) queue[event]=native[event];
        }
        assert(CODOL_ResolveEventParameters(queue,zero,out));
        assert(!out[0] && !out[1] && !out[2] && !out[3]);
        memcpy(saved,out,sizeof(out)); zero[3]=1;
        assert(!CODOL_ResolveEventParameters(queue,zero,out) && !memcmp(out,saved,sizeof(out)));
        queue[0]=EV_FIRE_WEAPON; queue[1]=EV_FIRE_WEAPON_LASTSHOT; zero[3]=0;
        assert(CODOL_ResolveEventParameters(queue,zero,out));
        assert(!out[0] && !out[1]);
    }
    for(event=EV_STANCE_FORCE_STAND;event<=EV_STANCE_FORCE_PRONE;++event) {
        for(reason=0;reason<=3;++reason) {
            assert(CODOL_EventParameterToWire(event,reason,&value)==1 && value==reason);
            assert(CODOL_EventToWire(event)==(int)event);
        }
        value=99; assert(CODOL_EventParameterToWire(event,4,&value)==-1 && value==99);
        assert(CODOL_EventParameterToWire(event,UINT32_MAX,&value)==-1 && value==99);
    }
    assert(CODOL_EventParameterToWire(EV_NONE,UINT32_MAX,&value)==1 && !value);
    /* Sound alias carries the registered bank index: 1..255 is the whole
     * space and zero means no sound. */
    value=99; assert(CODOL_EventParameterToWire(EV_SOUND_ALIAS,3,&value)==1 && value==3);
    value=99; assert(CODOL_EventParameterToWire(EV_SOUND_ALIAS,0,&value)==-1 && value==99);
    value=99; assert(CODOL_EventParameterToWire(EV_SOUND_ALIAS,256,&value)==-1 && value==99);
    assert(CODOL_EventParameterToWire(UINT32_MAX,0,&value)==0 && value==99);
    assert(CODOL_EventParameterToWire(EV_NONE,0,NULL)==-1);
    assert(CODOL_ResolveEventParameters(events,parameters,out));
    assert(!out[0] && !out[1] && out[2]==2 && out[3]==3);
    /* An event with no wire translation at all fails the whole queue. */
    memcpy(saved,out,sizeof(out)); events[3]=UINT32_MAX;
    assert(!CODOL_ResolveEventParameters(events,parameters,out) && !memcmp(out,saved,sizeof(out)));
    events[3]=EV_STANCE_FORCE_PRONE; parameters[3]=4;
    assert(!CODOL_ResolveEventParameters(events,parameters,out) && !memcmp(out,saved,sizeof(out)));
    assert(!CODOL_ResolveEventParameters(NULL,parameters,out));
    assert(!CODOL_ResolveEventParameters(events,NULL,out));
    assert(!CODOL_ResolveEventParameters(events,parameters,NULL));
    parameters[3]=1;
    assert(CODOL_ResolveEventParameters(events,parameters,parameters));
    assert(!parameters[0] && parameters[3]==1);
    puts("PASS: stance event reason translation, unsupported event rejection and atomic queue resolution");
}
