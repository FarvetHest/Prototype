#ifndef LITE_ENEMY_H
#define LITE_ENEMY_H
typedef struct { unsigned short ticks,fpg; unsigned char hurt,collision,damage; } EnemyFrame;
typedef struct { int kind,frame,timer,fpg,hurt,ticks; } EnemyPose;
enum { EP_IDLE,EP_WALK,EP_HELD,EP_HURT2,EP_HURT,EP_FLIGHT,EP_FLOOR,EP_GETUP,EP_FRONT,EP_BACK,EP_JAB,EP_UPPER,EP_KICK };
struct Game;
const EnemyFrame *enemy_frames(int index,int kind);
int enemy_count(int index,int kind);
void enemy_pose_tick(struct Game *g,int index,int kind);
int enemy_selftest(void);
#endif
