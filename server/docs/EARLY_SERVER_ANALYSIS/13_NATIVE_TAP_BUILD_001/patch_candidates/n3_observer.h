#ifndef CODOL_NATIVE_TAP_OBSERVER_H
#define CODOL_NATIVE_TAP_OBSERVER_H

/*
 * Candidate-only native message observer interface.
 *
 * This header is NOT part of the original source tree. It is a review artifact
 * for the isolated experiment copy created by EARLY-NATIVE-TAP-BUILD-001.
 *
 * It is intentionally self-contained: it pulls in "msg.h" itself so that the
 * msg_t typedef (an anonymous-struct typedef, not a "struct msg_t" tag) is
 * always the single definition from the tree. client_s is only forward
 * declared; callers already include "server.h".
 */

#ifdef CODOL_SERVER
#include "msg.h"

struct client_s;

void CODOL_NativeTapObserveMessage(const char *kind, struct client_s *client,
                                   msg_t *msg);
#else
static inline void CODOL_NativeTapObserveMessage(const char *kind, void *client,
                                                 void *msg)
{
    (void)kind;
    (void)client;
    (void)msg;
}
#endif

#endif /* CODOL_NATIVE_TAP_OBSERVER_H */
