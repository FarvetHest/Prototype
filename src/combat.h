#ifndef LITE_COMBAT_H
#define LITE_COMBAT_H
/* Appended to Game to retain the v0.6 profiler/debug ABI. All timers: 60 Hz. */
typedef struct { int state,timer,speed,direction,level,frame,anim_timer,upper,fpg,z,vz,vx,projectile; unsigned mask; } EnemyBrain;
typedef struct { int action,frame,timer,target,back,hits,hold,escape,elapsed,pending_cost,raw_charge,charge_wait,vault_x,vault_y; unsigned rng,ticks; EnemyBrain enemy[4]; } Combat;
enum { CB_NONE,CB_HOLD,CB_HEAD,CB_KNEE,CB_JUMPKNEE,CB_FRONTTHROW,CB_BACKTHROW,CB_VAULT,CB_NEUTRAL,CB_FORWARD,CB_ROLL_DOWN,CB_ROLL_UP };
struct Game;
void combat_reset(struct Game *g);
void combat_tick(struct Game *g,float x,float y,int attack,int jump,int special);
void combat_hurt_enemy(struct Game *g,int i,int damage,int down);
void combat_enemy_attack_frame(struct Game *g,int i,int collision,int damage);
int combat_selftest(void);
#endif
