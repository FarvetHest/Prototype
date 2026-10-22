#ifndef LITE_HELD_H
#define LITE_HELD_H
struct Game;
typedef struct { int ticks,armed; } HeldAttack;
extern HeldAttack held_attack;
void held_reset(void);
int held_tick(const struct Game *g,int down,int edge,int rear);
int held_selftest(void);
#endif
