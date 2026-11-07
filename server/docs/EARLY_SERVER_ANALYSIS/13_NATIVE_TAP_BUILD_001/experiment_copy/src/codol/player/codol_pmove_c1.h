/* Native C1 movement-state core.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_PMOVE_C1_H
#define CODOL_PMOVE_C1_H

#include "bg_public.h"
#include "codol_usercmd.h"

#ifdef __cplusplus
extern "C" {
#endif

enum {
    CODOL_PM_C1_INPUT_READY      = 1u << 0,
    CODOL_PM_C1_STANCE_READY     = 1u << 1,
    CODOL_PM_C1_VIEWHEIGHT_READY = 1u << 2,
    CODOL_PM_C1_GROUND_READY     = 1u << 3,
    CODOL_PM_C1_SLIDE_READY      = 1u << 4,
    CODOL_PM_C1_LADDER_READY     = 1u << 5,
    CODOL_PM_C1_MANTLE_READY     = 1u << 6,
    CODOL_PM_C1_DIVE_READY       = 1u << 7,
    CODOL_PM_C1_WEAPON_READY     = 1u << 8
};

typedef struct {
    struct pmove_t *host;       /* trace/touch callback storage, not input */
    struct playerState_s *ps;
    codol_usercmd_t cmd;        /* authoritative C1 command */
    codol_usercmd_t oldcmd;     /* previously executed C1 command */
    struct pml_t local;
} codol_pmove_c1_t;

typedef enum {
    CODOL_PM_C1_MOVE_NORMAL = 0,
    CODOL_PM_C1_MOVE_MANTLE,
    CODOL_PM_C1_MOVE_LADDER
} codol_pmove_c1_mode_t;

/* Entry seam for ClientThink.  It consumes the structurally bound full C1
 * command.  Zero means the native core is intentionally inactive and the
 * caller must preserve the current live path. */
int CODOL_PmoveC1Try(struct pmove_t *pm);
unsigned CODOL_PmoveC1Implemented(void);
unsigned CODOL_PmoveC1Required(void);
int CODOL_PmoveC1Active(void);
void CODOL_PmoveC1ResetClient(unsigned client);
void CODOL_PmoveC1ResetAll(void);
/* Every wire command in arrival order, including ones the server does not
 * execute; the command before the executing one becomes its first oldcmd. */
void CODOL_PmoveC1NoteWireCommand(unsigned client, const codol_usercmd_t *command);
/* Nonzero when the C1 mover owns this command's clock. The level.time+200
 * ceiling is then applied here (to ucmd and to the C1 mover), and
 * ClientThink_real skips only its retained level.time-1000 floor. */
int CODOL_PmoveC1OwnsClientClock(const struct playerState_s *ps,
                                 struct usercmd_s *ucmd, int level_time);

/* Component entry points for the native core.  Do not splice them into the
 * retained Pmove path: CODOL_PmoveC1Try gates the complete core atomically. */
void REGPARM(2) CODOL_PM_UpdateStanceC1(struct pmove_t *pm,
                                        struct pml_t *pml);

/* C1 PM_UpdateViewheight 0x00411D80.  Exported separately because linked,
 * vehicle and later native C1 movement paths need the same state producer. */
void CODOL_PM_UpdateViewheightC1(struct pmove_t *pm, struct pml_t *pml);

/* C1 gives an active mantle exclusive ownership of the movement frame. */
int CODOL_PM_C1MantleOwnsFrame(struct pmove_t *pm, struct pml_t *pml);

/* Atomic C1 ordering: mantle owns the frame before ladder acquisition runs. */
codol_pmove_c1_mode_t CODOL_PM_C1SelectMove(codol_pmove_c1_t *move);
void CODOL_PM_CheckLadderC1(codol_pmove_c1_t *move);
void CODOL_PM_LadderVelocityC1(codol_pmove_c1_t *move);

#ifdef __cplusplus
}
#endif
#endif
