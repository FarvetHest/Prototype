#ifndef LITE_SPRITES_H
#define LITE_SPRITES_H
#include "game.h"
enum { ANIM_IDLE, ANIM_WALK, ANIM_ATTACK, ANIM_JUMP, ANIM_HURT, ANIM_DOWN, ANIM_RUN, ANIM_ROLL, ANIM_SPECIAL, ANIM_GRAB };
extern unsigned actor_frames[5], actor_states[5];
extern unsigned sprite_draw_count, sprite_slice_count;
int sprites_selftest(void);
void sprites_init(const Game *g);
void sprites_reset(const Game *g);
void sprites_spawn_enemies(const Game *g,unsigned mask);
void sprites_step(const Game *g);
void sprites_begin(void);
void sprites_end(void);
void sprites_draw(const Actor *actor, int index);
#endif
