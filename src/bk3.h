#ifndef LITE_BK3_H
#define LITE_BK3_H
/* Fixed point uses the original 16.16 values; z grows downward. */
typedef struct {
 int active,script,frame,timer,mode,takeoff,landing,combo,next_combo,combo_timeout,queued;
 int air_attack,run,tapdir,taptimer,lastx,hitstop,z,vz,airvx;
 unsigned mask,ticks;
 int fpg,damage,collision,enemy_inv[4];
} Bk3;
enum { BK_IDLE,BK_WALK,BK_RUN,BK_JUMP,BK_PUNCH1,BK_PUNCH2,BK_KICK,BK_BLITZ,BK_AIR1,BK_AIR2,BK_BACKHAND,BK_DOUBLEKICK };
struct Game;
void bk3_tick(struct Game *g,float x,float y,int attack,int jump);
void bk3_suspend(struct Game *g);
void bk3_damage_frame(struct Game *g,int collision,int damage);
int bk3_selftest(void);
#endif
