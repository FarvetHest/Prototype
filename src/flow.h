#ifndef LITE_FLOW_H
#define LITE_FLOW_H
enum { FLOW_TITLE,FLOW_PLAY,FLOW_RESPAWN,FLOW_CONTINUE,FLOW_GAMEOVER,FLOW_CLEAR };
enum { FLOW_RESET_NONE,FLOW_RESET_NEW,FLOW_RESET_LIFE };
typedef struct { int state,lives,credits,timer,notice,request; unsigned score,best,runs; } Flow;
extern Flow flow;
struct Game;
void flow_init(Flow *f);
void flow_new(Flow *f);
void flow_button(Flow *f,int confirm,int cancel);
void flow_tick(Flow *f,const struct Game *g,unsigned score);
int flow_selftest(void);
#endif
