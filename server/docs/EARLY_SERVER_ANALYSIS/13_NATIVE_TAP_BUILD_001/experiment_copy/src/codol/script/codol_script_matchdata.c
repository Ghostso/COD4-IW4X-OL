#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "codol_matchdata.h"
#include "codol_matchdata_server.h"
#include "codol_match_report.h"
#include "filesystem.h"
#include "qcommon_io.h"
#include <stdio.h>
#include <string.h>
/* A path cannot consume more values than the VM argument stack. Derive its
 * storage from that actual capacity, rather than imposing a schema depth of
 * 32. Automatic storage is also released by the VM's script-error unwind. */
#define CODOL_MATCHDATA_MAX_PATH \
    (sizeof(((scrVmPub_t *)0)->stack)/sizeof(((scrVmPub_t *)0)->stack[0]))
void CODOL_Scr_SendClientMatchData(void)
{
    int slot;
    for(slot=0;slot<level.maxclients && slot<MAX_CLIENTS;++slot)
        if(g_entities[slot].client && g_entities[slot].client->sess.connected==CON_CONNECTED)
            CODOL_RequestClientMatchData((unsigned)slot);
    /* IW4's _gamelogic::processLobbyData ends every match here, after the
     * awards and scoreboards are assembled and while every player is still
     * connected with its session profile attached. sendMatchData() next to it
     * is gated on matchMakingGame(), so this is the one end-of-match signal the
     * vendor scripts always reach. Report the match's XP to the lobby from it,
     * rather than inventing a second native notion of "game over". */
    CODOL_WriteMatchReport("gameended");
}
void CODOL_Scr_SetClientMatchDataDef(void)
{
    if(Scr_GetNumParam()!=1) {Scr_Error("setClientMatchDataDef requires one asset name");return;}
    if(!CODOL_SelectClientMatchData(Scr_GetString(0)))
        Scr_Error("setClientMatchDataDef: unavailable/invalid schema or definition already selected");
}
void CODOL_Scr_GetClientMatchDataDef(void)
{
    codol_client_matchdata_t *m=CODOL_ClientMatchData();
    if(Scr_GetNumParam()) {Scr_Error("getClientMatchDataDef takes no arguments");return;}
    Scr_AddString(m ? m->name : "");
}
static codol_client_matchdata_t *lookup(int count,codol_structured_path_t *path,
    codol_structured_field_t *field)
{
    codol_client_matchdata_t *m=CODOL_ClientMatchData();int i;
    if(!m) {Scr_Error("client match data definition is not selected");return NULL;}
    if(count<0 || (unsigned)count>CODOL_MATCHDATA_MAX_PATH) {
        Scr_Error("client match data path exceeds the VM argument capacity");return NULL;
    }
    for(i=0;i<count;++i) {
        unsigned type=Scr_GetType(i);
        if(type==VAR_INTEGER)path[i]=(codol_structured_path_t){NULL,Scr_GetInt(i)};
        else if(type==VAR_STRING)path[i]=(codol_structured_path_t){Scr_GetString(i),0};
        else {Scr_Error("client match data path requires field names or integer indices");return NULL;}
    }
    if(!CODOL_ResolveStructuredField(m->schema.definitions,path,(size_t)count,field)) {
        Scr_Error("invalid client match data field path");return NULL;
    }
    return m;
}
void CODOL_Scr_SetClientMatchData(void)
{
    codol_structured_path_t path[CODOL_MATCHDATA_MAX_PATH];codol_structured_field_t f;
    int count=Scr_GetNumParam()-1,ok;uint32_t value;float number;
    codol_client_matchdata_t *m=lookup(count,path,&f);
    if(!m)return;
    if(f.type.kind==3 || f.type.kind==4) {
        const char *text=Scr_GetString(count);
        ok=CODOL_StructuredWriteText(m->schema.definitions,path,count,m->record,sizeof(m->record),text);
        if(!ok && f.type.kind==4) {
            /* Adaptation: the IW4 gametype writes its own names (character
             * sets as factions, IW4 killstreak/weapon refs) into enum fields
             * whose CoDOL member lists differ. IW4 would error; here the
             * write is skipped and reported once per value in developer mode
             * so the match end is not cut short by lobby bookkeeping. */
            static char reported[16][48]; static unsigned reported_count; unsigned i; int seen=0;
            const codol_structured_enum_t *e=m->schema.definitions->enums+f.type.index;
            for(i=0;i<reported_count;++i) if(!strcmp(reported[i],text ? text : "")) { seen=1; break; }
            if(!seen && reported_count<16) {
                char members[512]; size_t used=0; members[0]=0;
                Q_strncpyz(reported[reported_count++],text ? text : "",48);
                for(i=0;e && i<e->count && e->members && used<sizeof(members)-1;++i)
                    used+=(size_t)snprintf(members+used,sizeof(members)-used,"%s%s",i ? "," : "",e->members[i].name ? e->members[i].name : "?");
                Com_DPrintf(CON_CHANNEL_SERVER,"CoDOL setClientMatchData: \"%s\" is not a member of the enum for %s (members: %s); skipped\n",
                    text ? text : "",path[0].name ? path[0].name : "?",members);
            }
            return;
        }
    }
    else {
        if(f.type.kind==8) {number=Scr_GetFloat(count);memcpy(&value,&number,4);}
        else {value=(uint32_t)Scr_GetInt(count);if(f.type.kind==2)value=value!=0;}
        ok=CODOL_StructuredWriteScalar(&m->schema.definitions->layout,f.type.kind,
            f.logical_index,m->record,sizeof(m->record),value);
    }
    if(!ok)Scr_Error("invalid client match data value");
}
void CODOL_Scr_GetClientMatchData(void)
{
    codol_structured_path_t path[CODOL_MATCHDATA_MAX_PATH];codol_structured_field_t f;
    int count=Scr_GetNumParam();uint32_t value;float number;const char *text;
    codol_client_matchdata_t *m=lookup(count,path,&f);
    if(!m)return;
    if(f.type.kind==3 || f.type.kind==4) {
        if(!CODOL_StructuredReadText(m->schema.definitions,path,count,m->record,sizeof(m->record),&text)) {
            Scr_Error("invalid stored client match data text");return;
        }
        Scr_AddString(text);return;
    }
    if(!CODOL_StructuredReadScalar(&m->schema.definitions->layout,f.type.kind,
        f.logical_index,m->record,sizeof(m->record),&value)) {
        Scr_Error("invalid stored client match data scalar");return;
    }
    if(f.type.kind==8) {memcpy(&number,&value,4);Scr_AddFloat(number);}
    else if(f.type.kind==9)Scr_AddInt(value&0x8000 ? (int)value-65536 : (int)value);
    else {int32_t integer;memcpy(&integer,&value,4);Scr_AddInt(integer);}
}
/* Server match record (setMatchDataDef/setMatchData/getMatchData/
 * clearMatchData/sendMatchData). C1 keeps it apart from the client record. */
static const char *no_definition="No match data def defined";
/* C1's traversal (0x551760) consumes parameters until the type is scalar. */
static int server_path(const codol_structured_definition_t *d,int limit,
    codol_structured_path_t *path,codol_structured_field_t *out,int *length)
{
    int k;
    /* C1 0x55178e checks for a scalar before consuming any parameter.
     * A scalar root therefore has a zero-component path. */
    if(CODOL_ResolveStructuredField(d,NULL,0,out)) {*length=0;return 1;}
    if(limit<0 || (unsigned)limit>CODOL_MATCHDATA_MAX_PATH)return 0;
    for(k=1;k<=limit;++k) {
        unsigned type=Scr_GetType((unsigned)(k-1));
        if(type==VAR_INTEGER)path[k-1]=(codol_structured_path_t){NULL,Scr_GetInt((unsigned)(k-1))};
        else if(type==VAR_STRING)path[k-1]=(codol_structured_path_t){Scr_GetString((unsigned)(k-1)),0};
        else return 0;
        if(CODOL_ResolveStructuredField(d,path,(size_t)k,out)) {*length=k;return 1;}
    }
    return 0;
}
/* C1 reports value failures as `"%s: \"%s\" %s"` with the message table at
 * 0xccfcec (0x5534b6). Non-string values are rendered by their script type. */
static void server_value_error(const char *caller,unsigned index,const char *reason)
{
    char text[256];unsigned type=Scr_GetType(index);
    if(type==VAR_STRING)snprintf(text,sizeof(text),"%s: \"%s\" %s",caller,Scr_GetString(index),reason);
    else if(type==VAR_FLOAT)snprintf(text,sizeof(text),"%s: \"%f\" %s",caller,(double)Scr_GetFloat(index),reason);
    else if(type==VAR_INTEGER)snprintf(text,sizeof(text),"%s: \"%d\" %s",caller,Scr_GetInt(index),reason);
    else snprintf(text,sizeof(text),"%s: %s",caller,reason);
    Scr_Error(text);
}
void CODOL_Scr_SetMatchDataDef(void)
{
    if(Scr_GetNumParam()!=1) {
        Scr_Error("SetMatchDataDef takes exactly one argument: <def asset name>");return;
    }
    switch(CODOL_SelectServerMatchData(Scr_GetString(0))) {
    case CODOL_MATCHDATA_DEF_LOADED:
    case CODOL_MATCHDATA_DEF_UNCHANGED: return;
    case CODOL_MATCHDATA_DEF_ALREADY_SET: Scr_Error("Already set match data def");return;
    case CODOL_MATCHDATA_DEF_NAME_TOO_LONG: Scr_Error("def name too long.");return;
    case CODOL_MATCHDATA_DEF_TOO_LARGE:
        Scr_Error("setMatchDataDef: match data definition exceeds the record buffer");return;
    default:
        Scr_Error("setMatchDataDef: match data definition asset is unavailable");return;
    }
}
void CODOL_Scr_SetMatchData(void)
{
    codol_structured_path_t path[CODOL_MATCHDATA_MAX_PATH];codol_structured_field_t f;
    codol_server_matchdata_t *m=CODOL_ServerMatchData();
    int params=Scr_GetNumParam(),count=0,value;unsigned slot;float number;const char *text;
    if(!m) {Scr_Error(no_definition);return;}
    if(!server_path(m->schema.definitions,params,path,&f,&count)) {
        Scr_Error("setMatchData: invalid match data field path");return;
    }
    if(params==count) {Scr_Error("Not enough arguments. See log.");return;}
    if(params!=count+1) {Scr_Error("Too many arguments. See log.");return;}
    slot=(unsigned)count;
    if(f.type.kind==3 || f.type.kind==4) {
        text=Scr_GetString(slot);
        if(f.type.kind==3 && strlen(text)+1>f.type.index) {
            server_value_error("SetMatchData",slot,va("String is too long (field holds %u characters)",f.type.index ? f.type.index-1 : 0));return;
        }
        if(!CODOL_StructuredWriteText(m->schema.definitions,path,(size_t)count,
            m->record,sizeof(m->record),text)) {
            server_value_error("SetMatchData",slot,f.type.kind==4 ?
                "String is not an entry of the required enum" : "Incorrect data type");
        }
        return;
    }
    if(f.type.kind==8) {
        uint32_t bits;number=Scr_GetFloat(slot);memcpy(&bits,&number,4);
        if(!CODOL_StructuredWriteScalar(&m->schema.definitions->layout,f.type.kind,
            f.logical_index,m->record,sizeof(m->record),bits))
            server_value_error("SetMatchData",slot,"Incorrect data type");
        return;
    }
    value=Scr_GetInt(slot);
    if(f.type.kind==1 && (value<0 || value>255)) {
        server_value_error("SetMatchData",slot,"Given int value is too large to fit in a byte");
        return;
    }
    if(!CODOL_StructuredWriteScalar(&m->schema.definitions->layout,f.type.kind,
        f.logical_index,m->record,sizeof(m->record),
        f.type.kind==2 ? (uint32_t)(value!=0) : (uint32_t)value))
        server_value_error("SetMatchData",slot,"Incorrect data type");
}
void CODOL_Scr_GetMatchData(void)
{
    codol_structured_path_t path[CODOL_MATCHDATA_MAX_PATH];codol_structured_field_t f;
    codol_server_matchdata_t *m=CODOL_ServerMatchData();
    int params=Scr_GetNumParam(),count=0;uint32_t value;float number;const char *text;
    if(!m) {Scr_Error(no_definition);return;}
    if(!server_path(m->schema.definitions,params,path,&f,&count)) {
        Scr_Error("getMatchData: invalid match data field path");return;
    }
    if(params!=count) {Scr_Error("Too many arguments. See log.");return;}
    if(f.type.kind==3 || f.type.kind==4) {
        if(!CODOL_StructuredReadText(m->schema.definitions,path,(size_t)count,
            m->record,sizeof(m->record),&text)) {
            Scr_Error("getMatchData: invalid stored match data text");return;
        }
        Scr_AddString(text);return;
    }
    if(!CODOL_StructuredReadScalar(&m->schema.definitions->layout,f.type.kind,
        f.logical_index,m->record,sizeof(m->record),&value)) {
        Scr_Error("getMatchData: invalid stored match data scalar");return;
    }
    if(f.type.kind==8) {memcpy(&number,&value,4);Scr_AddFloat(number);}
    else if(f.type.kind==9)Scr_AddInt(value&0x8000 ? (int)value-65536 : (int)value);
    else {int32_t integer;memcpy(&integer,&value,4);Scr_AddInt(integer);}
}
void CODOL_Scr_ClearMatchData(void)
{ CODOL_ClearServerMatchData(); }
static void matchdata_report_sink(void *context,const char *text,size_t length)
{
    fileHandle_t file=*(const fileHandle_t *)context;
    if(file)FS_Write(text,(int)length,file);
}
/* Definition names contain path separators; keep them out of the file name. */
static void matchdata_file_stem(const char *name,char *out,size_t capacity)
{
    size_t n;
    for(n=0;n+1<capacity && name[n];++n) {
        char c=name[n];
        out[n]=(c>='0'&&c<='9')||(c>='a'&&c<='z')||(c>='A'&&c<='Z') ? c : '_';
    }
    out[n]=0;
}
void CODOL_Scr_SendMatchData(void)
{
    codol_server_matchdata_submission_t submission;
    char stem[CODOL_SERVER_MATCHDATA_NAME],file[128];fileHandle_t handle;
    const char *selected=CODOL_ServerMatchDataDef();
    int status;
    if(!selected) {Scr_Error(no_definition);return;}
    status=CODOL_PrepareServerMatchDataSubmission(&submission);
    if(!status) {
        Scr_Error("sendMatchData: the selected match data definition is unavailable");return;
    }
    if(status<0) {
        Com_PrintWarning(CON_CHANNEL_SERVER,"Unknown def file %s\n",selected);return;
    }
    matchdata_file_stem(submission.name,stem,sizeof(stem));
    snprintf(file,sizeof(file),"matchdata/%s_%04u.mdr",stem,submission.id);
    if(FS_SV_HomeWriteFile(file,submission.record,(int)submission.size)!=(int)submission.size) {
        Com_PrintWarning(CON_CHANNEL_SERVER,"sendMatchData: failed to write %s\n",file);
        return;
    }
    snprintf(file,sizeof(file),"matchdata/%s_%04u.txt",stem,submission.id);
    handle=FS_SV_FOpenFileWrite(file);
    if(handle) {
        CODOL_WriteServerMatchDataReport(matchdata_report_sink,&handle);
        FS_FCloseFile(handle);
    }
    status=CODOL_DeliverServerMatchData(&submission);
    Com_Printf(CON_CHANNEL_SERVER,"sendMatchData: %s record %u, %u bytes, %s\n",
        submission.name,submission.id,(unsigned)submission.size,
        status>0 ? "delivered" : status ? "delivery rejected" : "retained, no delivery sink");
}
#endif
