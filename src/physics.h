#ifndef LITE_PHYSICS_H
#define LITE_PHYSICS_H
/* Frame timers, velocities and heights follow 60 Hz BK3 object rules. */
typedef struct { int phase,frame,timer,pending,back,chain,inv,freeze,hurt,fpg,z,vz,vx; } Body;
typedef struct { Body body[5]; int z,vz,landed,vaults,rolltimer; unsigned rng32; } Physics;
enum { BODY_NONE,BODY_HURT,BODY_FLIGHT,BODY_BOUNCE,BODY_GETUP,BODY_VICTIM };
struct Game;
void physics_hit(struct Game *g,int index,int damage,int down,int facing);
void physics_body_tick(struct Game *g,int index);
void physics_victim_start(struct Game *g,int index,int back);
int physics_victim_tick(struct Game *g,int index);
int physics_rect(const struct Game *g,int index,float rect[4]);
int physics_selftest(void);
#endif
