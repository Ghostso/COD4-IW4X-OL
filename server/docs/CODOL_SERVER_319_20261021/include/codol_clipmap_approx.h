/* codol_clipmap_approx.h -- minimal collision approximation for coop_train_mp_firingrange.
 * Generated from map entity strings; not a full clipMap parse. Ground plane z=-116
 * matches the single design spawn point; clip boxes are 64x64x64 approximations of
 * script_brushmodel clip volumes until real brush bounds are extracted.
 */
#ifndef CODOL_CLIPMAP_APPROX_H
#define CODOL_CLIPMAP_APPROX_H
#include <stddef.h>

#define CODOL_GROUND_Z (-116.0f)
#define CODOL_WORLD_MIN_X (-2500.0f)
#define CODOL_WORLD_MAX_X (2500.0f)
#define CODOL_WORLD_MIN_Y (-2800.0f)
#define CODOL_WORLD_MAX_Y (2800.0f)
#define CODOL_WORLD_MIN_Z (-130.0f)
#define CODOL_WORLD_MAX_Z (300.0f)

/* Each row: midX, midY, midZ, halfX, halfY, halfZ */
static const float codol_map_clip_boxes[][6] = {
  {-824.0f, -96.0f, -57.0f, 32.0f, 32.0f, 32.0f},
  {-563.0f, -433.0f, -80.0f, 32.0f, 32.0f, 32.0f},
  {-704.0f, -943.0f, -66.0f, 32.0f, 32.0f, 32.0f},
  {-726.0f, 35.0f, -58.0f, 32.0f, 32.0f, 32.0f},
  {-177.0f, 155.0f, -64.0f, 32.0f, 32.0f, 32.0f},
  {-407.0f, 14.0f, -66.0f, 32.0f, 32.0f, 32.0f},
  {-177.0f, 146.0f, -66.0f, 32.0f, 32.0f, 32.0f},
  {-734.0f, 650.0f, -33.0f, 32.0f, 32.0f, 32.0f},
  {-75.0f, -434.0f, -64.0f, 32.0f, 32.0f, 32.0f},
  {-718.0f, 424.0f, -13.0f, 32.0f, 32.0f, 32.0f},
  {-669.0f, 424.0f, -75.0f, 32.0f, 32.0f, 32.0f},
  {-763.0f, 424.0f, -75.0f, 32.0f, 32.0f, 32.0f},
  {-661.0f, 164.0f, -92.0f, 32.0f, 32.0f, 32.0f},
  {-769.0f, 164.0f, -92.0f, 32.0f, 32.0f, 32.0f},
  {-678.0f, -77.0f, -64.0f, 32.0f, 32.0f, 32.0f},
  {435.0f, -230.0f, -69.0f, 32.0f, 32.0f, 32.0f},
  {-684.0f, -1235.0f, -98.0f, 32.0f, 32.0f, 32.0f},
  {-644.0f, -1475.0f, -60.0f, 32.0f, 32.0f, 32.0f},
  {-513.0f, -594.0f, -64.0f, 32.0f, 32.0f, 32.0f},
  {1208.0f, 401.0f, -58.0f, 32.0f, 32.0f, 32.0f},
  {1317.0f, 1380.0f, 61.0f, 32.0f, 32.0f, 32.0f},
  {1056.0f, 1483.0f, 148.0f, 32.0f, 32.0f, 32.0f},
  {-236.0f, 1226.0f, 25.0f, 32.0f, 32.0f, 32.0f},
  {-128.0f, 1308.0f, 21.0f, 32.0f, 32.0f, 32.0f},
  {-481.0f, -804.0f, -64.0f, 32.0f, 32.0f, 32.0f},
  {334.0f, -147.0f, -69.0f, 32.0f, 32.0f, 32.0f},
  {1161.0f, 1719.0f, 55.0f, 32.0f, 32.0f, 32.0f},
  {-456.0f, 8.0f, -57.0f, 32.0f, 32.0f, 32.0f},
  {294.0f, 792.0f, -1.0f, 32.0f, 32.0f, 32.0f},
};
static const size_t codol_map_clip_box_count = sizeof(codol_map_clip_boxes) / sizeof(codol_map_clip_boxes[0]);

#endif
