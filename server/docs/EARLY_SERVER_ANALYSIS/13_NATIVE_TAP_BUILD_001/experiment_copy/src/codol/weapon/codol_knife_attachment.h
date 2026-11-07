#ifndef CODOL_KNIFE_ATTACHMENT_H
#define CODOL_KNIFE_ATTACHMENT_H
#ifdef __cplusplus
extern "C" {
#endif
struct gentity_s;
struct trace_s;
int CODOL_KnifeWorldImpact(struct gentity_s *,struct trace_s *,const float *);
int CODOL_KnifeDamageImpact(struct gentity_s *,struct gentity_s *,struct gentity_s *,
 const float *,const float *,int,int,int,unsigned,int,unsigned,unsigned,int,struct trace_s *);
int CODOL_RunAttachedKnife(struct gentity_s *);
void CODOL_KnifeCorpseCreated(unsigned,unsigned);
void CODOL_ResetKnifeAttachment(unsigned);
void CODOL_ResetKnifeAttachments(void);
void CODOL_KnifePlayerSpawning(struct gentity_s *);
#ifdef __cplusplus
}
#endif
#endif
