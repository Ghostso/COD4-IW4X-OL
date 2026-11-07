/* CoDOL player hitbox probe (developer diagnostic).
 *
 * codol_hitprobe <entnum> [models|freeze|unfreeze] sweeps horizontal bullet
 * traces (the retained G_LocationalTrace with the bullet content mask and
 * bulletPriorityMap, as Bullet_Trace uses them) through an entity at every
 * height from its feet to well above its head.  It prints which hit
 * location each height resolves to, the top of the hittable volume, and the
 * world heights of the head tags in the server pose, so the server hit
 * volume can be measured against the model the client draws. It also lists
 * the outfit the client draws and which parts the server pose holds.
 * "freeze" sets the client's bFrozen (freezeControls) so a bot can be
 * measured in its idle stance; "models" adds per-bone boxes and bind heights.
 */
#include "q_shared.h"
#include "entity.h"
#include "g_shared.h"
#include "cm_public.h"
#include "dobj.h"
#include "cscr_stringlist.h"
#include "xassets/xmodel.h"
#include "qcommon.h"
#include "cmd.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "codol_animation_tables.h"
#include "codol_entities.h"
#include "codol_events.h"
#include "codol_engine_state.h"
#include "codol_entitystate_ext.h"
/* Last: server.h leaves pack(1) behind it (svs, archived entities). */
#include "server.h"

extern char bulletPriorityMap[];

static const char *const probe_hitloc[]={"none","helmet","head","neck","torso_upper","torso_lower",
    "r_arm_up","l_arm_up","r_arm_lo","l_arm_lo","r_hand","l_hand","r_leg_up","l_leg_up",
    "r_leg_lo","l_leg_lo","r_foot","l_foot","gun","shield"};
#define PROBE_LOCS ((int)(sizeof(probe_hitloc)/sizeof(probe_hitloc[0])))

static const char *loc_name(int loc)
{
    return loc>=0 && loc<PROBE_LOCS ? probe_hitloc[loc] : "?";
}

static void probe_tag(gentity_t *ent,const char *tag)
{
    float mat[4][3];
    int name=SL_FindString(tag);
    if(!name || !G_DObjGetWorldTagMatrix(ent,(unsigned)name,mat)) {
        Com_Printf(CON_CHANNEL_DONT_FILTER,"  tag %-12s <absent>\n",tag);
        return;
    }
    Com_Printf(CON_CHANNEL_DONT_FILTER,"  tag %-12s z=%+7.2f (world %.1f %.1f %.1f)\n",tag,
        mat[3][2]-ent->r.currentOrigin[2],mat[3][0],mat[3][1],mat[3][2]);
}

/* Entities linked to this one (world weapons ride tag_weapon_right). */
static void probe_children(gentity_t *ent)
{
    int i;
    for(i=0;i<MAX_GENTITIES;++i) {
        gentity_t *child=&g_entities[i];
        if(!child->r.inuse || !child->tagInfo || child->tagInfo->parent!=ent)continue;
        Com_Printf(CON_CHANNEL_DONT_FILTER,"  child %d tag %s z=%+7.2f (world %.1f %.1f %.1f)\n",i,
            child->tagInfo->name ? SL_ConvertToString(child->tagInfo->name) : "-",
            child->r.currentOrigin[2]-ent->r.currentOrigin[2],
            child->r.currentOrigin[0],child->r.currentOrigin[1],child->r.currentOrigin[2]);
    }
}

/* One horizontal line through the target at height h above its origin,
 * offset sideways by side units; returns the hit location or -1. */
static int probe_line(gentity_t *ent,const vec3_t fwd,const vec3_t right,float h,float side)
{
    trace_t tr;
    vec3_t start,end;
    int i;
    for(i=0;i<3;++i) {
        start[i]=ent->r.currentOrigin[i]+fwd[i]*80.0f+right[i]*side;
        end[i]=ent->r.currentOrigin[i]-fwd[i]*80.0f+right[i]*side;
    }
    start[2]=end[2]=ent->r.currentOrigin[2]+h;
    G_LocationalTrace(&tr,start,end,ENTITYNUM_NONE,0x2806831,bulletPriorityMap);
    if(tr.fraction>=1.0f || tr.hitType!=TRACE_HITTYPE_ENTITY || tr.hitId!=ent->s.number)return -1;
    return tr.partGroup;
}

static void probe_sweep(gentity_t *ent)
{
    vec3_t fwd,right,up,ang;
    float h,top=-1000.0f,bottom=1000.0f,runStart=0;
    float locMin[PROBE_LOCS],locMax[PROBE_LOCS];
    int prev=-2,i;
    static const float sides[]={0.0f,-3.0f,3.0f,-6.0f,6.0f,-10.0f,10.0f,-14.0f,14.0f};
    for(i=0;i<PROBE_LOCS;++i){locMin[i]=1000.0f;locMax[i]=-1000.0f;}
    VectorSet(ang,0.0f,ent->r.currentAngles[1],0.0f);
    AngleVectors(ang,fwd,right,up);
    Com_Printf(CON_CHANNEL_DONT_FILTER," sweep (height above origin: first location across the width)\n");
    for(h=-4.0f;h<=100.0f;h+=0.25f) {
        int loc=-1,s;
        for(s=0;s<(int)(sizeof(sides)/sizeof(sides[0]));++s) {
            int l=probe_line(ent,fwd,right,h,sides[s]);
            if(l<0)continue;
            if(loc<0)loc=l;
            if(l<PROBE_LOCS){ if(h<locMin[l])locMin[l]=h; if(h>locMax[l])locMax[l]=h; }
        }
        if(loc>=0){ if(h>top)top=h; if(h<bottom)bottom=h; }
        if(loc!=prev) {
            if(prev!=-2)Com_Printf(CON_CHANNEL_DONT_FILTER,"   %+7.2f..%+7.2f %s\n",runStart,h-0.25f,prev<0?"(miss)":loc_name(prev));
            prev=loc; runStart=h;
        }
    }
    Com_Printf(CON_CHANNEL_DONT_FILTER,"   %+7.2f..%+7.2f %s\n",runStart,h-0.25f,prev<0?"(miss)":loc_name(prev));
    Com_Printf(CON_CHANNEL_DONT_FILTER," hittable z %+.2f .. %+.2f above origin\n",bottom,top);
    for(i=0;i<PROBE_LOCS;++i) if(locMax[i]>-1000.0f)
        Com_Printf(CON_CHANNEL_DONT_FILTER,"   loc %-12s z %+7.2f .. %+7.2f\n",loc_name(i),locMin[i],locMax[i]);
}

static void probe_models(gentity_t *ent)
{
    DObj *obj=Com_GetServerDObj(ent->s.number);
    int m,b;
    if(!obj){ Com_Printf(CON_CHANNEL_DONT_FILTER,"  no server DObj\n"); return; }
    Com_Printf(CON_CHANNEL_DONT_FILTER,"  DObj models %d bones %d radius %.1f\n",obj->numModels,obj->numBones,obj->radius);
    for(m=0;m<obj->numModels;++m) {
        XModel *x=obj->models[m];
        if(!x)continue;
        Com_Printf(CON_CHANNEL_DONT_FILTER,"   [%d] %s bones %d roots %d mins %.1f %.1f %.1f maxs %.1f %.1f %.1f\n",m,x->name,
            (unsigned char)x->numBones,(unsigned char)x->numRootBones,x->mins[0],x->mins[1],x->mins[2],x->maxs[0],x->maxs[1],x->maxs[2]);
        for(b=0;b<(unsigned char)x->numBones;++b) {
            const char *bn=SL_ConvertToString(x->boneNames[b]);
            int cls=x->partClassification ? (unsigned char)x->partClassification[b] : -1;
            if(!bn)continue;
            if(!strcmp(bn,"j_head") || !strcmp(bn,"j_helmet") || !strcmp(bn,"j_neck") || !strcmp(bn,"tag_eye") ||
               !strcmp(bn,"j_spine4") || !strcmp(bn,"j_head_end") || !strcmp(bn,"j_mainroot") || !strcmp(bn,"tag_origin") ||
               cls==1 || cls==2 || cls==3) {
                const XBoneInfo_t *bi=x->boneInfo ? x->boneInfo+b : NULL;
                Com_Printf(CON_CHANNEL_DONT_FILTER,"     bone %3d %-16s cls %2d(%s)",b,bn,cls,loc_name(cls));
                if(x->baseMat)Com_Printf(CON_CHANNEL_DONT_FILTER," bind %.1f %.1f %.1f",x->baseMat[b].trans[0],x->baseMat[b].trans[1],x->baseMat[b].trans[2]);
                if(bi)Com_Printf(CON_CHANNEL_DONT_FILTER," box %.1f %.1f %.1f .. %.1f %.1f %.1f r2 %.1f",
                    bi->bounds[0][0],bi->bounds[0][1],bi->bounds[0][2],bi->bounds[1][0],bi->bounds[1][1],bi->bounds[1][2],bi->radiusSquared);
                Com_Printf(CON_CHANNEL_DONT_FILTER,"\n");
            }
        }
    }
}

/* Poses every bone and checks the skeleton: each bone's model-space matrix
 * must be finite and near the body, including the bones past index 127 that
 * only a 253-bone DObj holds. Per model: its DObj bone range and the height
 * of its first and last bone. */
static void probe_skeleton(gentity_t *ent,DObj *obj)
{
    int partBits[DOBJ_PART_BIT_WORDS];
    const DObjAnimMat *mats;
    unsigned b,m,start=0,bad=0,upper=0;
    float upperMin=1e9f,upperMax=-1e9f;
    memset(partBits,0xff,sizeof(partBits));
    G_DObjCalcPose(ent,partBits);
    mats=DObjGetRotTransArray(obj);
    if(!mats){ Com_Printf(CON_CHANNEL_DONT_FILTER,"  skeleton: none\n"); return; }
    for(b=0;b<obj->numBones;++b) {
        const DObjAnimMat *x=mats+b;
        int ok=1,k;
        for(k=0;k<4;++k) if(!isfinite(x->quat[k])) ok=0;
        for(k=0;k<3;++k) if(!isfinite(x->trans[k]) || fabsf(x->trans[k])>200.0f) ok=0;
        if(!ok){ ++bad; continue; }
        if(b>=128) {
            ++upper;
            if(x->trans[2]<upperMin)upperMin=x->trans[2];
            if(x->trans[2]>upperMax)upperMax=x->trans[2];
        }
    }
    Com_Printf(CON_CHANNEL_DONT_FILTER,"  skeleton: %u bones posed, %u at index 128+ (z %.1f..%.1f), %u non-finite or far\n",
        (unsigned)obj->numBones,upper,upper?upperMin:0.0f,upper?upperMax:0.0f,bad);
    for(m=0;m<obj->numModels;++m) {
        const XModel *x=obj->models[m];
        unsigned count=x ? (unsigned char)x->numBones : 0;
        if(!count)continue;
        Com_Printf(CON_CHANNEL_DONT_FILTER,"   [%u] %s dobj bones %u..%u first z %.1f last %s z %.1f\n",m,x->name,start,start+count-1,
            mats[start].trans[2],SL_ConvertToString(x->boneNames[count-1]),mats[start+count-1].trans[2]);
        start+=count;
    }
}

/* Hide-part mask of one entity through every stage that carries it: the
 * entityState (words 0..3 native, 4..7 extension), the server DObj, the C1
 * wire words the snapshot overlay publishes (+0xec..+0x108, script models
 * and general entities only) and the newest archived (killcam) copy read
 * back from the archive stream. Lists the hidden DObj bone indices. */
static void probe_hide_words(const char *what,const uint32_t w[8])
{
    Com_Printf(CON_CHANNEL_DONT_FILTER,"  hide %-9s %08x %08x %08x %08x | %08x %08x %08x %08x\n",what,
        w[0],w[1],w[2],w[3],w[4],w[5],w[6],w[7]);
}
static void probe_hide(gentity_t *ent)
{
    uint32_t words[8];
    DObj *obj=Com_GetServerDObj(ent->s.number);
    codol_entity_state_t wire;
    unsigned i,b,found=0;
    int type,j;
    CODOL_EntityStateHidePartBits(&ent->s,words);
    probe_hide_words("entity",words);
    Com_Printf(CON_CHANNEL_DONT_FILTER,"  hidden bones:");
    for(b=0;b<256;++b) if(words[b>>5]&(0x80000000u>>(b&31))) {
        Com_Printf(CON_CHANNEL_DONT_FILTER," %u",b);
        if(obj && b<obj->numBones) {
            unsigned m,start=0;
            for(m=0;m<obj->numModels;++m) {
                unsigned count=(unsigned char)obj->models[m]->numBones;
                if(b<start+count){ Com_Printf(CON_CHANNEL_DONT_FILTER,"(%s/%s)",obj->models[m]->name,
                    SL_ConvertToString(obj->models[m]->boneNames[b-start])); break; }
                start+=count;
            }
        }
    }
    Com_Printf(CON_CHANNEL_DONT_FILTER,"\n");
    if(obj) {
        for(i=0;i<8;++i)words[i]=(uint32_t)obj->hidePartBits[i];
        probe_hide_words("dobj",words);
    }
    memset(&wire,0,sizeof(wire));
    type=CODOL_EntityTypeToWire((unsigned)ent->s.eType);
    wire.number=(uint16_t)ent->s.number; wire.type=(uint16_t)(type>0?type:0);
    if(type>=0 && CODOL_OverlayEnginePartBits(&wire,&ent->s)) {
        unsigned have=0;
        memset(words,0,sizeof(words));
        for(i=0;i<8;++i) {
            unsigned f;
            for(f=0;f<CODOL_ENTITY_FIELDS;++f) if(CODOL_EntityField(wire.type,f)->offset==0x0ec+4*i) {
                words[i]=wire.field[f]; ++have; break;
            }
        }
        if(have==8)probe_hide_words("wire",words);
        else Com_Printf(CON_CHANNEL_DONT_FILTER,"  hide wire      not published for entity type %d\n",ent->s.eType);
    } else Com_Printf(CON_CHANNEL_DONT_FILTER,"  hide wire      overlay refused (type %d)\n",ent->s.eType);
    for(j=svs.nextCachedSnapshotEntities-1;svs.numCachedSnapshotEntities>0 &&
        j>=0 && j>=svs.nextCachedSnapshotEntities-svs.numCachedSnapshotEntities;--j) {
        const archivedEntity_t *a=&svs.cachedSnapshotEntities[j%svs.numCachedSnapshotEntities];
        if(a->s.number!=ent->s.number)continue;
        if(!found) {
            CODOL_EntityStateHidePartBits(&a->s,words);
            probe_hide_words("archived",words);
        }
        ++found;
    }
    Com_Printf(CON_CHANNEL_DONT_FILTER,"  archived copies read back: %u (of %d cached entities)\n",found,svs.nextCachedSnapshotEntities);
}

extern XModel *cached_models[];

/* The complete outfit the client draws: entity model plus attachments. */
static void probe_outfit(gentity_t *ent)
{
    DObj *obj=Com_GetServerDObj(ent->s.number);
    unsigned i,total=0;
    for(i=0;i<20;++i) {
        unsigned index=i ? ent->attachModelNames[i-1] : ent->model;
        XModel *x;
        int m,inPose=0,b,helm=0,head=0;
        if(!index || index>=CODOL_NATIVE_MODELS || !(x=cached_models[index]))continue;
        /* A priority part may be posed from its reduced gameplay copy
         * (codol_pose_budget.c), which keeps the source name pointer. */
        if(obj)for(m=0;m<obj->numModels;++m) {
            if(obj->models[m]==x)inPose=1;
            else if(obj->models[m] && obj->models[m]->name==x->name && !inPose)inPose=2;
        }
        for(b=0;b<(unsigned char)x->numBones;++b) if(x->partClassification) {
            if(x->partClassification[b]==1)++helm;
            if(x->partClassification[b]==2)++head;
        }
        total+=(unsigned char)x->numBones;
        Com_Printf(CON_CHANNEL_DONT_FILTER,"  part %2u %-28s bones %3d maxs.z %5.1f helmet-bones %d head-bones %d %s\n",
            i,x->name,(unsigned char)x->numBones,x->maxs[2],helm,head,inPose==1?"in server pose":inPose?"in server pose (gameplay copy)":"NOT in server pose");
    }
    Com_Printf(CON_CHANNEL_DONT_FILTER,"  outfit bones %u (server pose limit %d)\n",total,DOBJ_MAX_BONES);
}

static void CODOL_HitProbe_f(void)
{
    int n;
    gentity_t *ent;
    if(Cmd_Argc()<2){ Com_Printf(CON_CHANNEL_DONT_FILTER,"usage: codol_hitprobe <entnum> [models|skeleton|hide|freeze|unfreeze]\n"); return; }
    n=atoi(Cmd_Argv(1));
    if(n<0 || n>=MAX_GENTITIES){ Com_Printf(CON_CHANNEL_DONT_FILTER,"bad entity\n"); return; }
    ent=&g_entities[n];
    if(!ent->r.inuse){ Com_Printf(CON_CHANNEL_DONT_FILTER,"entity %d not in use\n",n); return; }
    if(Cmd_Argc()>2 && ent->client && (!strcmp(Cmd_Argv(2),"freeze") || !strcmp(Cmd_Argv(2),"unfreeze"))) {
        ent->client->bFrozen=!strcmp(Cmd_Argv(2),"freeze");
        Com_Printf(CON_CHANNEL_DONT_FILTER,"client %d frozen %d\n",n,ent->client->bFrozen);
        return;
    }
    Com_Printf(CON_CHANNEL_DONT_FILTER,"codol_hitprobe %d: origin %.1f %.1f %.1f angles %.1f %.1f %.1f mins %.1f %.1f %.1f maxs %.1f %.1f %.1f svFlags %d contents 0x%x\n",
        n,ent->r.currentOrigin[0],ent->r.currentOrigin[1],ent->r.currentOrigin[2],
        ent->r.currentAngles[0],ent->r.currentAngles[1],ent->r.currentAngles[2],
        ent->r.mins[0],ent->r.mins[1],ent->r.mins[2],ent->r.maxs[0],ent->r.maxs[1],ent->r.maxs[2],ent->r.svFlags,ent->r.contents);
    if(ent->client)
        Com_Printf(CON_CHANNEL_DONT_FILTER,"  ps viewheight target %d current %.2f pm_flags 0x%x viewangles %.1f %.1f legs %d torso %d\n",
            ent->client->ps.viewHeightTarget,ent->client->ps.viewHeightCurrent,ent->client->ps.pm_flags,
            ent->client->ps.viewangles[0],ent->client->ps.viewangles[1],ent->client->ps.legsAnim,ent->client->ps.torsoAnim);
    if(ent->client)
        Com_Printf(CON_CHANNEL_DONT_FILTER,"  archiveTime %d (killcam / delayed view reads archived frames while > 0)\n",
            G_GetClientArchiveTime(ent->s.number));
    if(ent->client) {
        unsigned legs=(unsigned)ent->client->ps.legsAnim&~0x400u,torso=(unsigned)ent->client->ps.torsoAnim&~0x400u;
        Com_Printf(CON_CHANNEL_DONT_FILTER,"  anims legs %s torso %s\n",
            legs && legs<CODOL_AnimationCount ? (const char *)(CODOL_AnimationRecords+legs*0x60) : "-",
            torso && torso<CODOL_AnimationCount ? (const char *)(CODOL_AnimationRecords+torso*0x60) : "-");
    }
    probe_tag(ent,"tag_origin"); probe_tag(ent,"j_mainroot"); probe_tag(ent,"j_spine4"); probe_tag(ent,"j_neck");
    probe_tag(ent,"j_head"); probe_tag(ent,"j_helmet"); probe_tag(ent,"j_head_end"); probe_tag(ent,"tag_eye");
    probe_tag(ent,"tag_weapon_right"); probe_tag(ent,"tag_weapon_left");
    probe_children(ent);
    probe_outfit(ent);
    if(Cmd_Argc()>2)probe_models(ent);
    if(Cmd_Argc()>2 && !strcmp(Cmd_Argv(2),"hide")){ probe_hide(ent); return; }
    if(Cmd_Argc()>2 && !strcmp(Cmd_Argv(2),"skeleton") && Com_GetServerDObj(ent->s.number))
        probe_skeleton(ent,Com_GetServerDObj(ent->s.number));
    probe_sweep(ent);
}

void CODOL_RegisterHitProbe(void)
{
    Cmd_AddCommand("codol_hitprobe",CODOL_HitProbe_f);
}
