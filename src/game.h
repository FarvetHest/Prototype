#ifndef LITE_GAME_H
#define LITE_GAME_H
#include "bk3.h"
#include "machine.h"
#include "death.h"
#include "combat.h"
#include "physics.h"
#include "rules.h"
#include "impact.h"
#include "enemy.h"
#define ENEMIES 4
#define TICK_US 33333u
typedef struct { float x, y; int hp, facing, cooldown, stun, attack, jump; unsigned hit; } Actor;
enum { HIT_NORMAL=1,HIT_AIR,HIT_BLITZ,HIT_GRAB };
typedef struct {
    int run_dir,roll,roll_dir,last_x,last_y,tap_x,tap_y,tap_x_tick,tap_y_tick;
    int combo,combo_window,queued,attack_kind,charge,special,special_forward;
    int grab,grab_timer,grab_hits,invincible,down[4],thrown[4];
    unsigned throw_hit[4];
    int air_strike,grab_cooldown;
} Mechanics;
typedef struct { float z[5],vz[5],vx[5],jump_x,jump_y; } Motion;

typedef struct Game { Actor player, enemies[ENEMIES]; unsigned ticks; int paused, won; Mechanics moves; Motion motion; Bk3 bk3; Combat combat; Physics physics; Rules rules; Impact impact; EnemyPose pose[4]; EnemyExtra extra[4]; Reactions reaction; } Game;
typedef struct { float x, y; int attack, jump, special; } Input;
void game_hit_enemy(Game *g,int i,int damage,int down);
void game_reset(Game *g);
void game_respawn(Game *g);
void game_step(Game *g, Input in);
int game_selftest(void);
#endif
