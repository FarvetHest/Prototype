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
static void spawn(Level *l,Game *g){Game fresh;int i;const Wave *w=&waves[l->wave];
 game_reset(&fresh);rules_end_hold(g);
 for(i=0;i<4;++i){
  g->enemies[i]=fresh.enemies[i];g->enemies[i].x=w->x[i];g->enemies[i].y=w->y[i];
  g->enemies[i].facing=g->player.x>w->x[i]?1:-1;
  g->combat.enemy[i]=fresh.combat.enemy[i];g->combat.enemy[i].level=w->ai;g->combat.enemy[i].timer=30+i*8;
  g->physics.body[i+1]=fresh.physics.body[i+1];g->physics.body[i+1].inv=20;
  g->motion.z[i+1]=g->motion.vz[i+1]=g->motion.vx[i+1]=0;
  g->moves.down[i]=g->moves.thrown[i]=0;g->moves.throw_hit[i]=0;
  g->rules.actor[i+1]=fresh.rules.actor[i+1];g->rules.ai[i]=fresh.rules.ai[i];g->pose[i]=fresh.pose[i];
  g->impact.freeze[i+1]=0;g->impact.last_from[i+1]=-1;
 }
 if(l->wave==1){food_spawn(l,0);}if(l->wave==3){food_spawn(l,1);}
 g->ticks=0;g->won=0;l->locked=1;l->go=0;l->slots=15;++l->generation;
}
static void spawn_boss(Level *l,Game *g){int i;
 spawn(l,g);for(i=0;i<4;++i)g->enemies[i].hp=0;
 g->enemies[LEVEL_BOSS_SLOT].hp=LEVEL_BOSS_HP;g->enemies[LEVEL_BOSS_SLOT].x=190;g->enemies[LEVEL_BOSS_SLOT].y=100;
 g->combat.enemy[LEVEL_BOSS_SLOT].level=10;l->boss=1;l->boss_phase=BOSS_APPROACH;l->boss_timer=30;l->slots=1<<LEVEL_BOSS_SLOT;
 food_spawn(l,2);
}
void level_start(Level *l,Game *g){memset(l,0,sizeof(*l));l->enabled=1;spawn(l,g);}
void level_step(Level *l,Game *g){int i,busy=0;float delta,limit;
 if(!l->enabled || g->paused || g->player.hp<=0)return;
 ++l->timer;g->won=l->finished;if(l->finished)return;level_food_step(l,g);
 for(i=0;i<4;++i)if(g->enemies[i].hp>0 || g->physics.body[i+1].phase || g->combat.enemy[i].z<0)busy=1;
 if(l->locked){
  if(busy)return;
  if(l->wave==LEVEL_WAVES-1 && !l->boss){++l->clears;spawn_boss(l,g);return;}
  if(l->boss==1)l->boss=2;
  l->locked=0;l->go=1;l->slots=0;++l->clears;
 }
 if(l->wave==LEVEL_WAVES-1 && g->player.x>=220){l->finished=1;l->go=0;g->won=1;return;}
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
 g.player.x=220;level_step(&l,&g);if(!g.won || !l.finished || l.go || l.clears!=6)return 1214;
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
