#ifndef LITE_RULES_H
#define LITE_RULES_H
/* Small source-style SST bank, appended after the v0.8 debug ABI. */
typedef struct { int type,status58,status5a,status5b,status89,statusde,depth,hold_timer,gripper,held,script,enabled; } ActorRules;
typedef struct { int mode,offset,target,cache,face_ticks,blocked,previous,active; unsigned visited,decisions; } SourceAI;
typedef struct { ActorRules actor[5]; SourceAI ai[4]; int pvp; } Rules;
struct Game;
void rules_reset(struct Game *g);
unsigned rules_flags(const struct Game *g,int index);
int rules_depth_overlap(const struct Game *g,int a,int b);
int rules_can_grab(const struct Game *g,int a,int b,int moving);
void rules_begin_hold(struct Game *g,int target);
void rules_end_hold(struct Game *g);
int rules_hold_valid(const struct Game *g);
int rules_recovery_inv(const struct Game *g,int index);
unsigned bk3_random_range(struct Game *g,unsigned range);
unsigned bk3_random32(struct Game *g);
void source_ai_tick(struct Game *g,int i);
int rules_selftest(void);
int source_ai_selftest(void);
#endif
