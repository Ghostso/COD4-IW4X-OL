#ifndef CODOL_SCRIPT_NOTIFY_H
#define CODOL_SCRIPT_NOTIFY_H
#ifdef __cplusplus
extern "C" {
#endif
void CODOL_ClearPlayerCommandNotifications(unsigned client);
void CODOL_ClearCommandNotifications(void);
void CODOL_HandleActionNotify(unsigned client, const char *action_id);
int CODOL_IsActionNotifyCommand(const char *command);
#ifdef __cplusplus
}
#endif
#endif
