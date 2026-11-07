#ifndef CODOL_BOT_H
#define CODOL_BOT_H
#include "player.h"
struct client_s;
void CODOL_RegisterBotMethods(void);
/* 0 legacy bot, 1 command staged, 2 receiver disappeared during notify. */
int CODOL_BotBuildCommand(struct client_s *,usercmd_t *);
int CODOL_ClientIsBotClient(unsigned client);
/* Called only from the three native player_die early-return branches. */
void CODOL_ReportDeathGateRefusal(struct gentity_s *victim, int gate);
#endif
