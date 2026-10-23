#ifndef LITE_LEVEL_H
#define LITE_LEVEL_H
struct Game;
#define LEVEL_WAVES 5
#define LEVEL_CUES 20
#define LEVEL_CAMERA_STEP 3.0f
#define LEVEL_MID_GATE 512
#define LEVEL_WIDTH 2852
#define LEVEL_CAMERA_MAX ((LEVEL_WIDTH-480)/2)
#define LEVEL_BOSS_SLOT 1
#define LEVEL_BOSS_HP 240
#define LEVEL_FOODS 3
#define LEVEL_INTRO 24   /* 30 Hz ticks of fade-in when a run starts */
#define LEVEL_OUTRO 45   /* 30 Hz ticks of fade-out after the last exit, before the results screen */
#define LEVEL_BANNER 60  /* 30 Hz ticks a "WAVE n" / "WARNING" banner stays up */
enum { BOSS_APPROACH,BOSS_WINDUP,BOSS_DASH,BOSS_RECOVER };
typedef struct {float x,y;int kind,active;} Food;
typedef struct {
 int enabled,wave,locked,go,finished,timer;float camera;unsigned generation;int slots;unsigned clears;
 int boss,boss_phase,boss_timer,boss_move,boss_dir,boss_attacks,boss_rushes;
 Food food[LEVEL_FOODS];unsigned food_spawned,food_taken;int heal_notice,heal_amount;
 /* Added in the level-flow rework. Appended last so debugger tools that read the
    leading fields by offset (tools/check_level.py reads the first 40 bytes) keep working. */
 unsigned entering;float entry_x[4];int entry_delay[4];int intro,outro,banner;
 int pickup_timer,pickup_item;
 /* Stream state appended after the v0.17 ABI. Cue records are not full-screen waves. */
 int cue,gate,spawn_wait,spawned,retired,overlap;
 unsigned spawn_mask;float camera_step;int stream,go_timer;
} Level;
extern Level level;
void level_start(Level *l,struct Game *g);
void level_step(Level *l,struct Game *g);
int level_selftest(void);
int level_boss_selftest(void);
int level_is_boss(int i);
void level_food_step(Level *l,struct Game *g);
int level_pickup_button(Level *l,struct Game *g,int attack,int jump,int special);
int level_pickup_active(struct Game *g);
void level_cancel_pickup(Level *l);
int level_entry_selftest(void);
/* Called by the enemy AI every 60 Hz step; non-zero while the enemy is still walking in. */
int level_entering(struct Game *g,int i);
int level_fade(const Level *l);       /* 0 (clear) .. 8 (black), for the blinds transition */
int level_go_bob(const Level *l);     /* 0..4 half-pixels, sideways motion of the GO arrow */
#endif
