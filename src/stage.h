#ifndef LITE_STAGE_H
#define LITE_STAGE_H
void stage_init(void);
void stage_draw(void);
int stage_foot_y(float world_y);
extern unsigned stage_draw_count;
#endif
