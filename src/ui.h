#ifndef LITE_UI_H
#define LITE_UI_H
#include "game.h"
extern unsigned ui_score,ui_timer,ui_player_hp,ui_enemy_hp,ui_draw_count;
extern int ui_target;
void ui_init(const Game *g);
void ui_reset(const Game *g);
void ui_step(const Game *g);
void ui_spawn_enemies(const Game *g,unsigned mask);
void ui_begin(void);
void ui_health_sync(const Game *g);
void ui_text(int x,int y,const char *text);
void ui_draw(const Game *g,int selftest_error);
void ui_food(void);
void ui_end(void);
#endif
