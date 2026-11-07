/* Player presentation producers: screen blur and player-card display slots.
 *
 * Both are real engine builtins, not script wrappers. IW4 still names them in
 * its builtin table - setblurforplayer (name 0x6f73f0, handler 0x5dc9a0) and
 * setcarddisplayslot (name 0x719750, handler 0x5df250) - and C1 1.1.1.13 has
 * the same two handlers with the names stripped, located through their error
 * strings: blur at 0x518130 ("Time must be positive" 0xc52fbc, "Blur value must
 * be greater than 0" 0xc52fd4) and the card slot at 0x51e150 ("Invalid slot
 * number %i, must be between 0 and %i." 0xc53824).
 *
 * Neither engine keeps server-side state for either call: no gclient field, no
 * configstring, no return value. They format one reliable command and send it
 * to a single client, which is why this module has no per-client record and no
 * reset hook.
 */
#ifndef CODOL_SCRIPT_PLAYER_PRESENTATION_H
#define CODOL_SCRIPT_PLAYER_PRESENTATION_H
#ifdef CODOL_SERVER

/* C1 command letters, read from the senders and confirmed on the receiving
 * side through C1's client command dispatcher 0x469320 (char table 0x46a118,
 * jump table 0x46a024). IW4's letters for the same two commands are 'l' and
 * 'O' and are deliberately not used. */
#define CODOL_BLUR_COMMAND_LETTER 'i'        /* C1 0x51828a pushes 0x69 */
#define CODOL_CARD_SLOT_COMMAND_LETTER 'L'   /* C1 0x51e2d5 pushes 0x4c */

/* C1 0x51e28c bounds the slot with 0x13 and its receiver 0x469af1 indexes
 * (localClient * 0x13 + slot) records of 0x68 bytes at 0x2c119d0. IW4's own
 * bound is 0x12; C1's is used. */
#define CODOL_CARD_DISPLAY_SLOTS 19

/* The two trailing integers of the blur command. C1 0x51827f/0x518281 and IW4
 * 0x5dca53/0x5dca55 always send these literals; the receiver's applier
 * (C1 0x42c020) treats them as a selector and a priority. */
#define CODOL_BLUR_COMMAND_SELECTOR 0
#define CODOL_BLUR_COMMAND_PRIORITY 1

/* Reusable producers behind the two script entry points. Both return zero when
 * the recipient is out of range; the caller has already validated the players.
 * milliseconds carries the engine's truncated conversion, including the x87
 * integer indefinite for an unusable time. */
int CODOL_SendPlayerBlur(unsigned client, float blur, int milliseconds);
int CODOL_SendCardDisplaySlot(unsigned viewer, int card_client, int slot);

/* The engine's own seconds-to-milliseconds conversion for the blur command:
 * C1 0x518221 multiplies by 1000.0 and calls the MSVC _ftol2 helper at
 * 0xae0410, which truncates toward zero and yields 0x80000000 for a value that
 * is not finite or does not fit a signed 32-bit integer. */
int CODOL_BlurMilliseconds(float seconds);

#endif
#endif
