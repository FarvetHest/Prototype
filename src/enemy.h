#ifndef LITE_ENEMY_H
#define LITE_ENEMY_H
typedef struct { unsigned short ticks,fpg; unsigned char hurt,collision,damage; } EnemyFrame;
typedef struct { int kind,frame,timer,fpg,hurt,ticks; } EnemyPose;
enum { EP_IDLE,EP_WALK,EP_HELD,EP_HURT2,EP_HURT,EP_FLIGHT,EP_FLOOR,EP_GETUP,EP_FRONT,EP_BACK,EP_JAB,EP_UPPER,EP_KICK };
enum { EN_GALSIA,EN_DONOVAN,EN_ELECTRA,EN_ZACK,EN_BARBON };
typedef struct { int type,action,frame,timer,z,vz,vx,wait; } EnemyExtra;
typedef struct { int holder,side,hold_timer,hold_cooldown,strike_wait,shock,shock_frame,shock_timer; unsigned captures,blocks,counters,shocks; } Reactions;
struct Game;
void reaction_release(struct Game *g);
int reaction_capture(struct Game *g,int i);
int reaction_player_tick(struct Game *g,int jump,int special);
void reaction_hit(struct Game *g,int from,int to,int encoded);
int reaction_block(struct Game *g,int from,int to);
int reaction_selftest(void);
int enemy_type(const struct Game *g,int i);
void enemy_set_type(struct Game *g,int i,int type);
const signed char *enemy_box(const struct Game *g,int i,int id,int hurt);
int variety_tick(struct Game *g,int i);
int variety_selftest(void);
const EnemyFrame *enemy_frames(const struct Game *g,int index,int kind);
int enemy_count(const struct Game *g,int index,int kind);
void enemy_pose_tick(struct Game *g,int index,int kind);
int enemy_selftest(void);
#endif
