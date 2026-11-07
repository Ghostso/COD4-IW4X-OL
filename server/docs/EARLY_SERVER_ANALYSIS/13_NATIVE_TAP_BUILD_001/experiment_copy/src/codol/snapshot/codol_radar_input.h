/* Script-owned radar input, distinct from captured playerState output. */
#ifndef CODOL_RADAR_INPUT_H
#define CODOL_RADAR_INPUT_H
#ifdef __cplusplus
extern "C" {
#endif
int CODOL_ClientRadarBlockInput(unsigned client);
void CODOL_SetClientRadarBlockInput(unsigned client, int value);
void CODOL_ResetClientRadarInput(unsigned client);
void CODOL_ResetAllRadarInput(void);
#ifdef __cplusplus
}
#endif
#endif
