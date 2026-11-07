#ifndef CODOL_BOT_NAV_H
#define CODOL_BOT_NAV_H
#define CODOL_BOT_NODES 2048
/* CSV stance/negotiation types; tactical-placement rows remain navigable.
 * CODOL_BOT_CLIMB is the hand-authored CSV's player mantle (bots only);
 * CODOL_BOT_NEGOTIATE is a map node_negotiation_begin/_end pair, the link
 * T5 Path_IsNegotiationLink gives every actor (a window sill, a low wall). */
enum { CODOL_BOT_STAND, CODOL_BOT_CROUCH, CODOL_BOT_PRONE, CODOL_BOT_CLIMB, CODOL_BOT_NEGOTIATE };
/* What the last CODOL_BotNavRouteFiltered did, for the caller's failure line:
 * nodes taken off the open set, links the caller's filter rejected, and why
 * it stopped (0 found, 1 frontier exhausted, 2 bad node index, 3 path longer
 * than the caller's capacity). */
typedef struct { int expanded, filtered, stop; } codol_bot_route_stats_t;
const codol_bot_route_stats_t *CODOL_BotNavLastRouteStats(void);
/* Undirected connected component of a node (0-based label); -1 off the graph. */
int CODOL_BotNavComponent(int node);
enum { CODOL_BOT_TACTIC_NONE,CODOL_BOT_TACTIC_CLAYMORE,CODOL_BOT_TACTIC_GRENADE,CODOL_BOT_TACTIC_JAVELIN };
typedef struct { float angles[3],target[3]; unsigned char hasAngles,hasTarget,tactic; } codol_bot_annotation_t;
const codol_bot_annotation_t *CODOL_BotNavAnnotation(int node);
typedef int (*codol_bot_edge_filter_t)(int from,int to,void *context);
int CODOL_BotNavRouteFiltered(int from,int to,unsigned short *path,int capacity,codol_bot_edge_filter_t allow,void *context);
int CODOL_BotNavLoad(const char *path);
/* Per-map load: "waypoints/<mapname>_wp.csv", or an empty graph when the
 * map ships none.  Owned by the map lifecycle, not by one category's GSC. */
int CODOL_BotNavLoadForMap(const char *mapname);
int CODOL_BotNavCount(void);
const float *CODOL_BotNavPoint(int node);
int CODOL_BotNavStance(int node);
int CODOL_BotNavNearest(const float *point);
int CODOL_BotNavRoute(int from,int to,unsigned short *path,int capacity);
/* Map-graph negotiation pairs (T5 node_negotiation_begin -> _end).  For a
 * begin node: the index of its end node, else -1.  Record is the index of
 * the node's entity record in codol_script_path_nodes (its "animscript",
 * "angles" keys); -1 for CSV nodes. */
int CODOL_BotNavNegotiationEnd(int node);
int CODOL_BotNavRecord(int node);
/* T5 Path_DisconnectPaths / Path_ConnectPaths, per entity: every link whose
 * segment (swept as the actor hull) crosses [mins,maxs] is cut and tagged
 * with the entity; ConnectPaths(entity) restores exactly the links that
 * entity cut, wherever the entity is now (the zm clip brush is moved 10000
 * units down by disable_trigger before connectpaths is called).  Both return
 * the number of links changed.  A cut link is skipped by the planner. */
int CODOL_BotNavDisconnectPaths(int entnum,const float *mins,const float *maxs);
int CODOL_BotNavConnectPaths(int entnum);
/* Non-zero when the directed link from -> to is currently cut (its cutter's
 * entity number + 1), 0 when open or absent. */
int CODOL_BotNavLinkBlocked(int from,int to);
#endif
