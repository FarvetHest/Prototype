#ifndef LITE_LEVEL_H
#define LITE_LEVEL_H
struct Game;
#define LEVEL_WAVES 5
#define LEVEL_WIDTH 2852
#define LEVEL_CAMERA_MAX ((LEVEL_WIDTH-480)/2)
#define LEVEL_BOSS_SLOT 1
#define LEVEL_BOSS_HP 240
#define LEVEL_FOODS 3
enum { BOSS_APPROACH,BOSS_WINDUP,BOSS_DASH,BOSS_RECOVER };
typedef struct {float x,y;int kind,active;} Food;
typedef struct {
 int enabled,wave,locked,go,finished,timer;float camera;unsigned generation;int slots;unsigned clears;
 int boss,boss_phase,boss_timer,boss_move,boss_dir,boss_attacks,boss_rushes;
 Food food[LEVEL_FOODS];unsigned food_spawned,food_taken;int heal_notice,heal_amount;
} Level;
extern Level level;
void level_start(Level *l,struct Game *g);
void level_step(Level *l,struct Game *g);
int level_selftest(void);
int level_boss_selftest(void);
int level_is_boss(int i);
void level_food_step(Level *l,struct Game *g);
#endif
