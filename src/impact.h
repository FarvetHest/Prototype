#ifndef LITE_IMPACT_H
#define LITE_IMPACT_H
/* Appended debug ABI: source hitstop/contact registers for the five arena actors. */
typedef struct { int freeze[5],last_from[5],damage[5]; unsigned contacts[5]; } Impact;
struct Game;
int impact_overlap(const struct Game *g,int from,int to,int collision);
int impact_apply(struct Game *g,int from,int to,int damage);
unsigned impact_sound(int encoded);
int impact_selftest(void);
#endif
