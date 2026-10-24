#ifndef LITE_MAX_H
#define LITE_MAX_H
/* SoR2 Max logic; appended after legacy Game and upstream Fx fields. */
typedef struct {
 int active,mode,anim,frame,timer,combo,combo_wait,contact,hitstop;
 int takeoff,z,vz,vx,direction,air_attack,escape,land;
 int throw_kind,throw_frame,throw_timer,throw_released,throw_origin;
 unsigned mask,ticks,hits,throws,atomic;
} MaxCombat;
enum { MX_IDLE,MX_ATTACK,MX_JUMP,MX_HOLD,MX_GRABHIT,MX_THROW,MX_HOLDJUMP,MX_NEUTRAL,MX_FORWARD,MX_SLIDE,MX_AIRSLAM,MX_ATOMIC,MX_LAND };
struct Game;
void max_tick(struct Game *g,float x,float y,int attack,int jump,int special);
unsigned max_render_pose(const struct Game *g);
int max_selftest(void);
#endif
