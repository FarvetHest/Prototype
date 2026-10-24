#ifndef LITE_DEATH_H
#define LITE_DEATH_H
struct Game;
typedef struct { int active,timer,cry,hidden; } DeathFx;
extern DeathFx death_fx[4];
void death_reset(struct Game *g);
void death_spawn(struct Game *g,int i);
void death_begin(struct Game *g,int i);
void death_tick(struct Game *g);
int death_pending(const struct Game *g,int i);
int death_visible(const struct Game *g,int i);
int death_selftest(void);
#endif
