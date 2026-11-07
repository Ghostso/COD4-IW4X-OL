#include "codol_profile.h"
#include "codol_stats.h"
#include <stdlib.h>
#include <string.h>
/* data is what was attached; session is the copy script edits are made on, so
 * that every reader observes them without altering the attached bytes. */
static struct {uint8_t *data,*session;uint64_t uid;} clients[32];
int CODOL_AttachClientSecureProfile(unsigned client,uint64_t uid,const uint8_t *profile,size_t size,
    const codol_structured_schema_t *schema)
{
    const codol_structured_definition_t *def;const uint8_t *record;size_t capacity;uint8_t *copy;
    if(client>=32 || !uid || !CODOL_ProfileRecord(profile,size,schema,&def,&record,&capacity))return 0;
    copy=malloc(CODOL_STATS_SIZE);if(!copy)return 0;
    memcpy(copy,profile,CODOL_STATS_SIZE);free(clients[client].data);
    free(clients[client].session);clients[client].session=NULL;
    clients[client].data=copy;clients[client].uid=uid;return 1;
}
const uint8_t *CODOL_ClientSecureProfileAttached(unsigned client,uint64_t *uid)
{
    if(client>=32 || !clients[client].data)return NULL;
    if(uid)*uid=clients[client].uid;return clients[client].data;
}
const uint8_t *CODOL_ClientSecureProfile(unsigned client,uint64_t *uid)
{
    if(client>=32 || !clients[client].data)return NULL;
    if(uid)*uid=clients[client].uid;
    return clients[client].session ? clients[client].session : clients[client].data;
}
uint8_t *CODOL_ClientSecureProfileWritable(unsigned client)
{
    uint8_t *copy;
    if(client>=32 || !clients[client].data)return NULL;
    if(clients[client].session)return clients[client].session;
    copy=malloc(CODOL_STATS_SIZE);if(!copy)return NULL;
    memcpy(copy,clients[client].data,CODOL_STATS_SIZE);
    clients[client].session=copy;return copy;
}
void CODOL_DetachClientSecureProfile(unsigned client)
{if(client<32){free(clients[client].data);free(clients[client].session);
    memset(clients+client,0,sizeof(clients[client]));}}
void CODOL_ResetClientSecureProfiles(void)
{for(unsigned i=0;i<32;++i)CODOL_DetachClientSecureProfile(i);}
/* See CODOL_CarryClientSecureProfile in codol_profile.h. */
static struct {uint8_t *data;uint64_t uid;} carried[32];
void CODOL_DropCarriedSecureProfile(unsigned client)
{if(client<32){free(carried[client].data);memset(carried+client,0,sizeof(carried[client]));}}
void CODOL_CarryClientSecureProfile(unsigned client)
{
    const uint8_t *view;uint8_t *copy;
    if(client>=32)return;
    CODOL_DropCarriedSecureProfile(client);
    view=clients[client].session ? clients[client].session : clients[client].data;
    if(!view || !clients[client].uid)return;
    copy=malloc(CODOL_STATS_SIZE);if(!copy)return;
    memcpy(copy,view,CODOL_STATS_SIZE);
    carried[client].data=copy;carried[client].uid=clients[client].uid;
}
int CODOL_TakeCarriedSecureProfile(unsigned client,uint64_t uid,uint8_t *out,size_t capacity)
{
    int ok;
    if(client>=32 || !carried[client].data)return 0;
    ok=uid && carried[client].uid==uid && out && capacity>=CODOL_STATS_SIZE;
    if(ok)memcpy(out,carried[client].data,CODOL_STATS_SIZE);
    CODOL_DropCarriedSecureProfile(client);
    return ok;
}
