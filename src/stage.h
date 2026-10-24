#ifndef LITE_STAGE_H
#define LITE_STAGE_H
void stage_init(void);
void stage_draw(void);
void stage_draw_foreground(void);
void stage_set_view(float player_x);
int stage_world_x(int x);
int stage_world_y(int y);
extern unsigned stage_native_view;
extern int stage_view_pan,stage_camera_pixels,stage_shake_y;
int stage_foot_y(float world_y);
extern unsigned stage_draw_count;
#endif
