#include "game.h"
#include "level.h"
#include <string.h>
Level level;
int level_is_boss(int i){return level.enabled && level.boss==1 && i==LEVEL_BOSS_SLOT;}
static float ab(float x){return x<0?-x:x;}
static void food_spawn(Level *l,int i){
 static const float x[]={380,920,1246};
 if(l->food_spawned&(1u<<i))return;
 l->food[i]=(Food){x[i],112,i==2,1};l->food_spawned|=1u<<i;
}
void level_food_step(Level *l,Game *g){int i;
 if(!l->enabled || l->finished || g->paused || g->player.hp<=0)return;
 if(l->heal_notice)--l->heal_notice;
 if(g->player.hp>=100 || g->player.jump || g->player.attack || g->player.stun || g->physics.body[0].phase || g->moves.roll || g->combat.action!=CB_NONE)return;
 for(i=0;i<LEVEL_FOODS;++i){Food *f=&l->food[i];int hp=g->player.hp;
  if(!f->active || ab(f->x-l->camera-g->player.x)>8 || ab(f->y-g->player.y)>6)continue;
  g->player.hp+=f->kind?60:25;if(g->player.hp>100)g->player.hp=100;
  f->active=0;l->food_taken|=1u<<i;l->heal_amount=g->player.hp-hp;l->heal_notice=45;break;
 }
}

typedef struct {int camera,ai;float x[4],y[4];} Wave;
/* Camera and combat X use half-screen-pixel units, matching the existing controller. */
static const Wave waves[LEVEL_WAVES]={
 {0,1,{150,210,225,180},{82,96,116,124}},
 {260,2,{22,210,225,185},{92,80,117,124}},
 {530,4,{200,222,20,180},{80,96,120,125}},
 {800,5,{22,205,225,180},{84,98,117,125}},
 {LEVEL_CAMERA_MAX,7,{200,225,20,175},{80,96,118,124}}
};
/* Enemies no longer pop into view: they start just outside the 0..240 half-pixel screen
   and walk to their mark. Until they arrive level_entering() keeps them untouchable and
   outside the arena clamp. Delays are 60 Hz AI steps, so the group trickles in one by one. */
#define ENTRY_SPEED 1.0f
static void enter_from_edge(Level *l,Game *g,int i,float target,int delay){
 float from=target<120?-24.0f:264.0f;
 g->enemies[i].x=from;g->enemies[i].facing=target>from?1:-1;
 l->entry_x[i]=target;l->entry_delay[i]=delay;l->entering|=1u<<i;
}
int level_entering(Game *g,int i){Level *l=&level;Actor *e=&g->enemies[i];float dx;
 if(!l->enabled || !(l->entering&(1u<<i)))return 0;
 if(e->hp<=0){l->entering&=~(1u<<i);return 0;} /* killed (or zeroed by a debugger) mid-entrance: just stop */
 if(g->physics.body[i+1].inv<2)g->physics.body[i+1].inv=2;
 if(l->entry_delay[i]>0){--l->entry_delay[i];return 1;}
 dx=l->entry_x[i]-e->x;
 /* The arrival step itself is spent on the mark; normal AI takes over on the next one. */
 if(dx<=ENTRY_SPEED && dx>=-ENTRY_SPEED){e->x=l->entry_x[i];l->entering&=~(1u<<i);return 1;}
 e->x+=dx>0?ENTRY_SPEED:-ENTRY_SPEED;e->facing=dx>0?1:-1;return 1;
}
static void spawn(Level *l,Game *g){Game fresh;int i;const Wave *w=&waves[l->wave];
 game_reset(&fresh);rules_end_hold(g);l->entering=0;
 for(i=0;i<4;++i){
  g->enemies[i]=fresh.enemies[i];g->enemies[i].x=w->x[i];g->enemies[i].y=w->y[i];
  enter_from_edge(l,g,i,w->x[i],(l->wave?6:36)+i*20);
  g->combat.enemy[i]=fresh.combat.enemy[i];g->combat.enemy[i].level=w->ai;g->combat.enemy[i].timer=30+i*8;
  g->physics.body[i+1]=fresh.physics.body[i+1];g->physics.body[i+1].inv=20;
  g->motion.z[i+1]=g->motion.vz[i+1]=g->motion.vx[i+1]=0;
  g->moves.down[i]=g->moves.thrown[i]=0;g->moves.throw_hit[i]=0;
  g->rules.actor[i+1]=fresh.rules.actor[i+1];g->rules.ai[i]=fresh.rules.ai[i];g->pose[i]=fresh.pose[i];
  g->impact.freeze[i+1]=0;g->impact.last_from[i+1]=-1;
 }
 if(l->wave==1){food_spawn(l,0);}if(l->wave==3){food_spawn(l,1);}
 g->ticks=0;g->won=0;l->locked=1;l->go=0;l->slots=15;++l->generation;l->banner=LEVEL_BANNER;
}
static void spawn_boss(Level *l,Game *g){int i;
 spawn(l,g);for(i=0;i<4;++i)g->enemies[i].hp=0;
 /* The four ordinary slots stay empty; only the captain walks in, from the right edge. */
 l->entering=0;
 g->enemies[LEVEL_BOSS_SLOT].hp=LEVEL_BOSS_HP;g->enemies[LEVEL_BOSS_SLOT].y=100;
 enter_from_edge(l,g,LEVEL_BOSS_SLOT,190,30);
 g->combat.enemy[LEVEL_BOSS_SLOT].level=10;l->boss=1;l->boss_phase=BOSS_APPROACH;l->boss_timer=30;l->slots=1<<LEVEL_BOSS_SLOT;
 food_spawn(l,2);
}
void level_start(Level *l,Game *g){memset(l,0,sizeof(*l));l->enabled=1;spawn(l,g);l->intro=LEVEL_INTRO;}
/* Blinds transition: 0 = clear, 8 = fully black. Fade-in at the start of a run, fade-out at the exit. */
int level_fade(const Level *l){int f=0,o;
 if(!l->enabled)return 0;
 if(l->intro>0)f=(l->intro*8+LEVEL_INTRO-1)/LEVEL_INTRO;
 o=l->outro*8/LEVEL_OUTRO;if(o>f)f=o;
 return f>8?8:f;
}
int level_go_bob(const Level *l){int p=(l->timer>>1)&7;return p<4?p:8-p;}
void level_step(Level *l,Game *g){int i,busy=0;float delta,limit;
 if(!l->enabled || g->paused || g->player.hp<=0)return;
 ++l->timer;if(l->intro>0)--l->intro;if(l->banner>0)--l->banner;
 g->won=l->finished;if(l->finished)return;level_food_step(l,g);
 for(i=0;i<4;++i)if(g->enemies[i].hp>0 || g->physics.body[i+1].phase || g->combat.enemy[i].z<0)busy=1;
 if(l->locked){
  if(busy)return;
  if(l->wave==LEVEL_WAVES-1 && !l->boss){++l->clears;spawn_boss(l,g);return;}
  if(l->boss==1)l->boss=2;
  l->locked=0;l->go=1;l->slots=0;++l->clears;
 }
 if(l->wave==LEVEL_WAVES-1 && (l->outro || g->player.x>=220)){
  /* Final exit: once started the fade-out cannot be cancelled by walking back, and the
     results screen only appears when it has finished instead of cutting in abruptly. */
  l->go=0;if(++l->outro>LEVEL_OUTRO){l->finished=1;g->won=1;}
  return;
 }
 if(g->physics.body[0].phase || g->combat.target>=0)return;
 limit=l->wave+1<LEVEL_WAVES?waves[l->wave+1].camera:LEVEL_CAMERA_MAX;
 delta=g->player.x-120;if(delta<0)delta=0;if(delta>limit-l->camera)delta=limit-l->camera;
 if(delta>0){
  l->camera+=delta;g->player.x-=delta;
  for(i=0;i<4;++i){g->enemies[i].x-=delta;if(g->physics.body[i+1].phase==BODY_VICTIM)g->physics.body[i+1].vx-=(int)(delta*131072);}
 }
 if(l->wave+1<LEVEL_WAVES && l->camera>=limit){++l->wave;spawn(l,g);}
}
int level_selftest(void){Level l;Game g;int i,w;
 game_reset(&g);level_start(&l,&g);if(!l.locked || l.wave || l.camera || l.generation!=1 || l.slots!=15)return 1201;
 g.player.x=220;level_step(&l,&g);if(l.camera || !l.locked || g.won)return 1202;
 for(i=0;i<4;++i){g.enemies[i].hp=0;}g.physics.body[1].phase=BODY_FLIGHT;level_step(&l,&g);if(!l.locked)return 1203;
 g.physics.body[1].phase=0;g.player.x=100;level_step(&l,&g);if(l.locked || !l.go || l.slots || g.won || l.clears!=1)return 1204;
 g.player.x=150;level_step(&l,&g);if(l.camera!=30 || g.player.x!=120)return 1205;
 g.player.x=20;level_step(&l,&g);if(l.camera!=30)return 1206;
 g.paused=1;g.player.x=220;level_step(&l,&g);if(l.camera!=30)return 1207;g.paused=0;
 for(w=1;w<LEVEL_WAVES;++w){
  while(l.wave<w){g.player.x=220;level_step(&l,&g);}
  if(!l.locked || l.go || l.generation!=(unsigned)(w+1) || g.enemies[0].hp!=40 || g.combat.enemy[0].level!=waves[w].ai)return 1208;
  for(i=0;i<4;++i){g.enemies[i].hp=0;g.physics.body[i+1].phase=0;g.combat.enemy[i].z=0;}g.player.x=100;level_step(&l,&g);
  if(g.won || (w<4 && (l.locked || !l.go)))return 1209;
 }
 if(!l.boss || !l.locked || l.go || l.slots!=2 || g.enemies[1].hp!=LEVEL_BOSS_HP || g.enemies[0].hp || l.generation!=6)return 1210;
 g.player.x=220;level_step(&l,&g);if(g.won || l.finished)return 1211;
 g.enemies[1].hp=0;g.physics.body[2].phase=BODY_FLIGHT;level_step(&l,&g);if(l.boss!=1 || !l.locked)return 1212;
 g.physics.body[2].phase=0;g.player.x=100;level_step(&l,&g);if(l.boss!=2 || l.locked || !l.go || g.won)return 1213;
 g.player.x=220;level_step(&l,&g);if(g.won || l.finished || !l.outro || l.go || l.clears!=6)return 1214;
 g.player.x=100;for(i=0;i<LEVEL_OUTRO-1;++i){level_step(&l,&g);if(g.won || l.finished)return 1226;} /* walking back does not cancel the exit */
 level_step(&l,&g);if(!g.won || !l.finished || l.go || l.clears!=6)return 1227;
 game_reset(&g);level_start(&l,&g);food_spawn(&l,0);l.camera=260;g.player.x=120;g.player.y=112;g.player.hp=50;level_food_step(&l,&g);if(g.player.hp!=75 || l.food[0].active || l.food_taken!=1 || l.heal_amount!=25)return 1215;
 food_spawn(&l,0);level_food_step(&l,&g);if(g.player.hp!=75 || l.food[0].active)return 1216;
 food_spawn(&l,2);l.camera=1186;g.player.x=60;g.player.hp=80;level_food_step(&l,&g);if(g.player.hp!=100 || l.heal_amount!=20 || l.food[2].active)return 1217;
 level_start(&l,&g);food_spawn(&l,0);l.camera=260;g.player.x=120;g.player.hp=100;level_food_step(&l,&g);if(!l.food[0].active)return 1218;
 g.player.hp=40;g.player.jump=1;level_food_step(&l,&g);if(g.player.hp!=40 || !l.food[0].active)return 1219;
 g.player.jump=0;g.paused=1;level_food_step(&l,&g);if(g.player.hp!=40)return 1220;
 g.paused=0;g.player.hp=0;level_food_step(&l,&g);if(g.player.hp || !l.food[0].active)return 1221;
 g.player.hp=40;g.player.y=90;level_food_step(&l,&g);if(g.player.hp!=40)return 1222;
 g.player.y=112;g.player.attack=1;level_food_step(&l,&g);if(g.player.hp!=40)return 1223;
 g.player.attack=0;game_respawn(&g);if(!l.food[0].active || l.food_spawned!=1)return 1224;
 level_start(&l,&g);if(l.food_spawned || l.food_taken || l.boss)return 1225;
 return 0;
}
/* Entrances, banner and fades. Uses the global `level`, because the AI reads that one. */
int level_entry_selftest(void){Level saved=level;Game g;int i,n,arrived[4],result=0,seen=0;
#define CHECK(c,code) do{if(!(c)){result=code;goto done;}}while(0)
 /* A fresh run: everyone starts off-screen, protected, and the transitions are armed. */
 game_reset(&g);level_start(&level,&g);
 CHECK(level.entering==15 && level.intro==LEVEL_INTRO && level.banner==LEVEL_BANNER && !level.outro,1230);
 CHECK(level_fade(&level)==8,1231);
 for(i=0;i<4;++i)CHECK(g.enemies[i].x<0 || g.enemies[i].x>240,1232);
 CHECK(g.enemies[0].facing==-1,1233); /* wave 0 comes from the right and faces left */
 for(i=0;i<4;++i)CHECK(!impact_apply(&g,0,i+1,2) && g.enemies[i].hp==40,1234);
 for(i=1;i<4;++i)CHECK(level.entry_delay[i]>level.entry_delay[i-1],1239); /* they leave one after another */
 /* Walk-in: staggered, ends exactly on the mark, protected the whole way. */
 for(i=0;i<4;++i)arrived[i]=-1;
 for(n=0;n<600 && level.entering;++n){
  for(i=0;i<4;++i){source_ai_tick(&g,i);
   if(arrived[i]<0 && !(level.entering&(1u<<i)))arrived[i]=n;
   if(level.entering&(1u<<i)){CHECK(g.physics.body[i+1].inv>0,1235);CHECK(!impact_apply(&g,0,i+1,2),1236);}
  }
 }
 CHECK(!level.entering,1237);
 for(i=0;i<4;++i)CHECK(arrived[i]>=0 && g.enemies[i].hp==40,1238);
 /* (checked after level_start below: departures are staggered, arrival order depends on distance) */
 for(i=0;i<4;++i)if(arrived[i]<36)result=1240; /* nobody shows up before the opening fade/READY is over */
 CHECK(!result,1240);
 /* Banner and fade-in run down with level_step. */
 game_reset(&g);level_start(&level,&g);
 for(i=0;i<LEVEL_INTRO;++i){int f=level_fade(&level);level_step(&level,&g);CHECK(level_fade(&level)<=f,1241);}
 CHECK(level_fade(&level)==0 && level.intro==0,1242);
 for(i=0;i<LEVEL_BANNER;++i){level_step(&level,&g);}CHECK(level.banner==0,1243);
 /* The captain walks in alone, from the right, and starts fighting only on arrival. */
 game_reset(&g);level_start(&level,&g);level.wave=LEVEL_WAVES-1;spawn_boss(&level,&g);
 CHECK(level.boss==1 && level.entering==(1u<<LEVEL_BOSS_SLOT) && g.enemies[LEVEL_BOSS_SLOT].x>240,1244);
 CHECK(g.enemies[LEVEL_BOSS_SLOT].hp==LEVEL_BOSS_HP && g.enemies[0].hp==0,1245);
 for(n=0;n<600 && level.entering;++n){
  source_ai_tick(&g,LEVEL_BOSS_SLOT);
  if(level.entering){CHECK(!impact_apply(&g,0,LEVEL_BOSS_SLOT+1,2) && g.enemies[LEVEL_BOSS_SLOT].hp==LEVEL_BOSS_HP,1246);CHECK(level.boss_phase==BOSS_APPROACH && level.boss_timer==30,1247);}
 }
 CHECK(!level.entering && g.enemies[LEVEL_BOSS_SLOT].x==190,1248);
 /* An enemy that dies while still walking in (e.g. zeroed by a test fixture) stops entering. */
 game_reset(&g);level_start(&level,&g);g.enemies[2].hp=0;source_ai_tick(&g,2);
 CHECK(!(level.entering&4) && (level.entering&11)==11,1254);
 /* The ordinary AI must be unaffected once nothing is entering (and when the level is off). */
 level.enabled=0;level.entering=15;CHECK(!level_entering(&g,0),1249);
 /* Fade stays within range for every intro/outro value. */
 level.enabled=1;level.entering=0;
 for(n=0;n<=LEVEL_INTRO;++n)for(i=0;i<=LEVEL_OUTRO+1;++i){level.intro=n;level.outro=i;seen=level_fade(&level);CHECK(seen>=0 && seen<=8,1250);}
 level.intro=0;level.outro=LEVEL_OUTRO;CHECK(level_fade(&level)==8,1251);
 level.outro=0;CHECK(level_fade(&level)==0,1252);
 for(n=0;n<64;++n){level.timer=n;seen=level_go_bob(&level);CHECK(seen>=0 && seen<=4,1253);}
done:
#undef CHECK
 level=saved;return result;
}
