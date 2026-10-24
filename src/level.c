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
void level_cancel_pickup(Level *l){l->pickup_timer=0;l->pickup_item=-1;}
static int pickup_ready(const Game *g){return g->player.hp>0 && g->player.hp<100 && !g->paused && !g->player.jump && !g->player.attack && !g->player.stun && !g->physics.body[0].phase && !g->moves.roll && g->combat.action==CB_NONE && g->bk3.mode==0 && !g->bk3.hitstop;}
int level_pickup_button(Level *l,Game *g,int attack,int jump,int special){int i;
 if(!l->enabled || l->finished)return 0;
 if(l->pickup_timer)return 1;
 if(attack!=1 || jump || special || !pickup_ready(g))return 0;
 for(i=0;i<LEVEL_FOODS;++i){Food *f=&l->food[i];
  if(!f->active || ab(f->x-l->camera-g->player.x)>8 || ab(f->y-g->player.y)>6)continue;
  l->pickup_item=i;l->pickup_timer=6;bk3_suspend(g);g->moves.run_dir=0;return 1;
 }
 return 0;
}
int level_pickup_active(Game *g){
 if(!level.enabled || !level.pickup_timer)return 0;
 if(g->player.hp<=0 || g->player.stun || g->physics.body[0].phase || g->player.jump){level_cancel_pickup(&level);return 0;}
 bk3_suspend(g);g->player.attack=0;return 1;
}
void level_food_step(Level *l,Game *g){int i,hp;
 if(!l->enabled || g->paused)return;
 if(l->heal_notice)--l->heal_notice;
 if(!l->pickup_timer)return;
 if(g->player.hp<=0 || g->player.stun || g->physics.body[0].phase || l->finished){level_cancel_pickup(l);return;}
 i=l->pickup_item;
 if(--l->pickup_timer==3 && i>=0 && i<LEVEL_FOODS && l->food[i].active){
  hp=g->player.hp;g->player.hp+=l->food[i].kind?60:25;if(g->player.hp>100)g->player.hp=100;
  l->food[i].active=0;l->food_taken|=1u<<i;l->heal_amount=g->player.hp-hp;l->heal_notice=45;
 }
 if(!l->pickup_timer)l->pickup_item=-1;
}

/* BK3 Chk_Area/GetNextEnemyGroup/sub_499C6: position/delay/count-driven queue.
   Coordinates and encounters below are authored for the Lite 2852-pixel background. */
typedef struct {short trigger,y;unsigned char family,ai; signed char side;} Cue;
static const Cue cues[LEVEL_CUES]={
 {0,88,0,1,1},{0,114,1,1,1},{64,100,0,1,1},{128,122,3,1,-1},
 {192,84,2,2,1},{256,112,1,2,1},{320,96,0,2,-1},{384,122,3,2,1},
 {448,82,2,4,1},{512,108,1,4,1},{576,120,0,4,1},{640,90,3,4,-1},
 {704,102,2,5,1},{768,124,1,5,1},{832,80,0,5,-1},{896,112,3,5,1},
 {960,96,2,7,1},{1024,122,1,7,-1},{1088,84,0,7,1},{1152,108,3,7,1}
};
static int busy(const Level *l,const Game *g){int i,n=0;for(i=0;i<4;++i)if((l->slots&(1<<i)) && (g->enemies[i].hp>0 || g->physics.body[i+1].phase || g->combat.enemy[i].z<0 || g->combat.target==i))++n;return n;}
static int free_slot(const Level *l,int family){int i;for(i=family&1;i<4;i+=2)if(!(l->slots&(1<<i)))return i;return -1;}
static void enter_from_edge(Level *l,Game *g,int i,int side,int delay){
 g->enemies[i].x=side<0?-10:250;g->enemies[i].facing=side<0?1:-1;
 l->entry_x[i]=side<0?12:228;l->entry_delay[i]=delay;l->entering|=1u<<i;
}
int level_entering(Game *g,int i){Level *l=&level;Actor *e=&g->enemies[i];float dx;
 if(!l->enabled || !(l->entering&(1u<<i)))return 0;
 if(e->hp<=0){l->entering&=~(1u<<i);return 0;}
 if(g->physics.body[i+1].inv<2)g->physics.body[i+1].inv=2;
 if(l->entry_delay[i]>0){--l->entry_delay[i];return 1;}
 dx=l->entry_x[i]-e->x;
 if(dx<=1 && dx>=-1){e->x=l->entry_x[i];l->entering&=~(1u<<i);return 1;}
 e->x+=dx>0?1:-1;e->facing=dx>0?1:-1;return 1;
}
static void spawn_slot(Level *l,Game *g,int i,int hp,int ai,int y,int side,int delay,int type){Game fresh;int j;
 game_reset(&fresh);g->enemies[i]=fresh.enemies[i];g->enemies[i].hp=hp;g->enemies[i].y=y;
 g->combat.enemy[i]=fresh.combat.enemy[i];g->combat.enemy[i].level=ai;g->combat.enemy[i].state=7;g->combat.enemy[i].timer=0;
 g->physics.body[i+1]=fresh.physics.body[i+1];g->physics.body[i+1].inv=2;
 g->motion.z[i+1]=g->motion.vz[i+1]=g->motion.vx[i+1]=0;
 g->moves.down[i]=g->moves.thrown[i]=0;g->moves.throw_hit[i]=0;
 g->bk3.enemy_inv[i]=0;g->bk3.mask&=~(1u<<i);
 for(j=0;j<4;++j)g->moves.throw_hit[j]&=~(1u<<i);
 g->rules.actor[i+1]=fresh.rules.actor[i+1];g->rules.ai[i]=fresh.rules.ai[i];g->pose[i]=fresh.pose[i];enemy_set_type(g,i,type);
 g->impact.freeze[i+1]=0;g->impact.last_from[i+1]=-1;
 enter_from_edge(l,g,i,side,delay);l->slots|=1<<i;l->spawn_mask|=1u<<i;
}
static void collect_slots(Level *l,const Game *g){int i;for(i=0;i<4;++i)if((l->slots&(1<<i)) && g->enemies[i].hp<=0 && !g->physics.body[i+1].phase && g->combat.enemy[i].z>=0 && g->combat.target!=i){l->slots&=~(1<<i);l->entering&=~(1u<<i);++l->retired;}}
static void feed(Level *l,Game *g){int end=l->gate?LEVEL_CUES:10,n,i;
 if(l->boss || l->spawn_wait)return;
 while(l->cue<end){const Cue *c=&cues[l->cue];n=busy(l,g);
  if(c->trigger>l->camera && !(n<2 && c->trigger<=l->camera+64))return;
  i=free_slot(l,c->family);if(i<0)return;
  spawn_slot(l,g,i,40,c->ai,c->y,c->side,l->cue<2?30+l->cue*12:0,c->family);
  if(n>0)++l->overlap;
  ++l->cue;++l->spawned;l->wave=(l->cue-1)/4;
  if(l->cue>=2){l->spawn_wait=8;return;}
 }
}
static void spawn_boss(Level *l,Game *g){
 spawn_slot(l,g,LEVEL_BOSS_SLOT,LEVEL_BOSS_HP,10,100,1,12,EN_DONOVAN);
 l->boss=1;l->boss_phase=BOSS_APPROACH;l->boss_timer=30;l->locked=1;l->go=0;l->banner=LEVEL_BANNER;
 g->ticks=0;g->won=0;++l->generation;food_spawn(l,2);
}
void level_start(Level *l,Game *g){int i;memset(l,0,sizeof(*l));l->enabled=l->stream=1;l->pickup_item=-1;l->generation=1;
 for(i=0;i<4;++i){g->enemies[i].hp=0;g->enemies[i].attack=0;g->physics.body[i+1].phase=0;}
 feed(l,g);l->intro=LEVEL_INTRO;l->banner=LEVEL_BANNER;
}
int level_fade(const Level *l){int f=0,o;if(!l->enabled)return 0;if(l->intro>0)f=(l->intro*8+LEVEL_INTRO-1)/LEVEL_INTRO;o=l->outro*8/LEVEL_OUTRO;if(o>f)f=o;return f>8?8:f;}
int level_go_bob(const Level *l){int p=(l->timer>>1)&7;return p<4?p:8-p;}
void level_step(Level *l,Game *g){int i,n,end;float delta,limit;
 if(!l->enabled || g->paused || g->player.hp<=0)return;
 l->camera_step=0;++l->timer;if(l->intro>0)--l->intro;if(l->banner>0)--l->banner;if(l->go_timer>0)--l->go_timer;
 g->won=l->finished;if(l->finished)return;level_food_step(l,g);
 /* Only debugger fixtures turn the stream off while retaining food/boss mechanics. */
 if(!l->stream)return;
 if(l->spawn_wait>0)--l->spawn_wait;
 collect_slots(l,g);n=busy(l,g);
 if(!l->gate && l->cue==10 && !n && l->camera>=LEVEL_MID_GATE){l->gate=1;++l->clears;l->go_timer=45;g->ticks=0;}
 if(l->cue==LEVEL_CUES && !n && !l->boss && l->camera>=LEVEL_CAMERA_MAX-64 && g->combat.target<0 && !g->physics.body[0].phase){spawn_boss(l,g);n=1;}
 if(l->boss==1 && !n){l->boss=2;++l->clears;l->go_timer=45;}
 l->locked=l->boss==1 || (!l->gate && l->camera>=LEVEL_MID_GATE && (n || l->cue<10));
 l->go=!l->locked && (!n || l->go_timer>0);
 if(l->boss==2 && l->camera>=LEVEL_CAMERA_MAX && (l->outro || g->player.x>=220)){
  l->go=0;if(++l->outro>LEVEL_OUTRO){l->finished=1;g->won=1;}return;
 }
 feed(l,g);
 if(g->physics.body[0].phase || g->combat.target>=0 || g->reaction.holder>=0 || l->pickup_timer)return;
 limit=l->gate?LEVEL_CAMERA_MAX:LEVEL_MID_GATE;end=l->gate?LEVEL_CUES:10;
 /* A full family pool defers its record and holds the camera at that record. */
 if(l->cue<end && free_slot(l,cues[l->cue].family)<0 && cues[l->cue].trigger<limit){limit=cues[l->cue].trigger;if(limit<l->camera)limit=l->camera;}
 delta=g->player.x-128;if(delta<0)delta=0;if(delta>LEVEL_CAMERA_STEP)delta=LEVEL_CAMERA_STEP;if(delta>limit-l->camera)delta=limit-l->camera;
 /* Keep living bodies in view rather than shifting them outside their combat bounds. */
 for(i=0;i<4;++i)if((l->slots&(1<<i)) && !(l->entering&(1u<<i)) && g->enemies[i].hp>0 && g->enemies[i].x-10<delta){delta=g->enemies[i].x-10;if(delta<0)delta=0;}
 if(delta>0){l->camera+=delta;l->camera_step=delta;g->player.x-=delta;
  for(i=0;i<4;++i)if((l->slots&(1<<i)) && !(l->entering&(1u<<i))){g->enemies[i].x-=delta;if(g->physics.body[i+1].phase==BODY_VICTIM)g->physics.body[i+1].vx-=(int)(delta*131072);}
 }
 if(l->camera>=260){food_spawn(l,0);}if(l->camera>=800){food_spawn(l,1);}
 feed(l,g);
}

static void test_retire_all(Game *g){int i;for(i=0;i<4;++i){g->enemies[i].hp=0;g->physics.body[i+1].phase=0;g->combat.enemy[i].z=0;}g->combat.target=-1;}
int level_selftest(void){Level l;Game g;int i,n;float old,world;
 game_reset(&g);level_start(&l,&g);if(l.cue!=2 || l.slots!=3 || l.locked || l.spawned!=2)return 1201;
 g.player.x=220;world=l.camera+g.player.x;level_step(&l,&g);if(l.camera!=3 || l.camera+g.player.x!=world)return 1202;
 g.paused=1;old=l.camera;level_step(&l,&g);if(l.camera!=old)return 1203;g.paused=0;
 g.player.x=20;old=l.camera;level_step(&l,&g);if(l.camera!=old)return 1204;
 g.combat.target=0;g.player.x=220;old=l.camera;level_step(&l,&g);if(l.camera!=old)return 1205;g.combat.target=-1;
 game_reset(&g);level_start(&l,&g);l.camera=64;l.spawn_wait=0;g.player.x=100;g.enemies[0].hp=17;level_step(&l,&g);
 if(l.cue!=3 || l.slots!=7 || g.enemies[0].hp!=17 || l.overlap<2)return 1206;
 l.camera=128;l.spawn_wait=0;level_step(&l,&g);if(l.slots!=15 || l.cue!=4)return 1207;
 g.player.x=220;l.camera=192;old=l.camera;level_step(&l,&g);if(l.camera!=old || l.cue!=4)return 1208;
 g.enemies[0].hp=0;g.physics.body[1].phase=BODY_FLIGHT;l.spawn_wait=0;level_step(&l,&g);if(l.cue!=4 || !(l.slots&1))return 1209;
 g.physics.body[1].phase=0;level_step(&l,&g);if(l.cue!=5 || g.enemies[0].hp!=40 || g.enemies[1].hp!=40)return 1210;
 game_reset(&g);level_start(&l,&g);l.cue=10;l.camera=LEVEL_MID_GATE;g.player.x=220;level_step(&l,&g);if(!l.locked || l.gate || l.camera!=LEVEL_MID_GATE)return 1211;
 test_retire_all(&g);l.spawn_wait=0;level_step(&l,&g);if(l.gate!=1 || l.clears!=1 || l.cue!=11 || !l.go_timer)return 1212;
 game_reset(&g);level_start(&l,&g);
 for(n=0;n<1500 && !l.boss;++n){test_retire_all(&g);g.player.x=220;old=l.camera;level_step(&l,&g);if(l.camera-old>LEVEL_CAMERA_STEP || l.camera<old)return 1213;}
 if(l.boss!=1 || l.spawned!=20 || g.enemies[1].hp!=240 || l.slots!=2)return 1214;
 g.enemies[1].hp=0;g.physics.body[2].phase=BODY_FLIGHT;level_step(&l,&g);if(l.boss!=1)return 1260;
 g.physics.body[2].phase=0;g.player.x=220;level_step(&l,&g);if(l.boss!=2 || l.clears!=2)return 1261;
 for(n=0;n<100 && !l.finished;++n){g.player.x=220;level_step(&l,&g);}if(!l.finished || !g.won || l.camera!=LEVEL_CAMERA_MAX)return 1262;
 game_reset(&g);level_start(&l,&g);food_spawn(&l,0);l.camera=260;g.player.x=120;g.player.y=112;g.player.hp=50;
 level_food_step(&l,&g);if(g.player.hp!=50 || !l.food[0].active)return 1215;
 if(!level_pickup_button(&l,&g,1,0,0) || l.pickup_timer!=6)return 1216;
 level_food_step(&l,&g);level_food_step(&l,&g);if(g.player.hp!=50 || !l.food[0].active)return 1217;
 level_food_step(&l,&g);if(g.player.hp!=75 || l.food[0].active || l.food_taken!=1)return 1218;
 for(i=0;i<3;++i){level_food_step(&l,&g);}if(l.pickup_timer || l.pickup_item!=-1)return 1219;
 food_spawn(&l,0);if(l.food[0].active || level_pickup_button(&l,&g,1,0,0))return 1220;
 food_spawn(&l,2);l.camera=1186;g.player.x=60;g.player.hp=80;
 if(!level_pickup_button(&l,&g,1,0,0))return 1221;
 for(i=0;i<6;++i){level_food_step(&l,&g);}if(g.player.hp!=100 || l.heal_amount!=20 || l.food[2].active)return 1222;
 level_start(&l,&g);food_spawn(&l,0);l.camera=260;g.player.x=120;g.player.y=112;
 if(level_pickup_button(&l,&g,1,0,0))return 1223;
 g.player.hp=40;g.player.jump=1;if(level_pickup_button(&l,&g,1,0,0))return 1224;
 g.player.jump=0;g.paused=1;if(level_pickup_button(&l,&g,1,0,0))return 1225;g.paused=0;
 g.player.attack=1;if(level_pickup_button(&l,&g,1,0,0))return 1228;g.player.attack=0;
 if(level_pickup_button(&l,&g,0,0,0) || level_pickup_button(&l,&g,2,0,0) || level_pickup_button(&l,&g,1,1,0) || level_pickup_button(&l,&g,1,0,1))return 1229;
 level_pickup_button(&l,&g,1,0,0);g.player.stun=2;level_food_step(&l,&g);if(l.pickup_timer || !l.food[0].active || g.player.hp!=40)return 1255;
 g.player.stun=0;level_pickup_button(&l,&g,1,0,0);g.paused=1;level_food_step(&l,&g);if(l.pickup_timer!=6)return 1256;g.paused=0;
 level_cancel_pickup(&l);game_respawn(&g);if(!l.food[0].active || l.pickup_timer)return 1257;
 level_start(&l,&g);if(l.food_spawned || l.food_taken || l.boss || l.pickup_timer)return 1258;
 return 0;
}
int level_entry_selftest(void){Level saved=level;Game g;int i,n,result=0;float x;
#define CHECK(c,code) do{if(!(c)){result=code;goto done;}}while(0)
 game_reset(&g);level_start(&level,&g);CHECK(level.entering==3 && level_fade(&level)==8,1230);
 for(i=0;i<2;++i)CHECK(g.enemies[i].x>240 && !impact_apply(&g,0,i+1,2),1231);
 for(n=0;n<100 && level.entering;++n)for(i=0;i<2;++i){source_ai_tick(&g,i);}
 CHECK(!level.entering,1232);
 level.camera=64;level.spawn_wait=0;g.player.x=100;level_step(&level,&g);CHECK(level.entering&4,1233);
 x=g.enemies[2].x;g.player.x=220;level_step(&level,&g);CHECK(g.enemies[2].x==x,1234);
 for(n=0;n<80 && (level.entering&4);++n){source_ai_tick(&g,2);}CHECK(!(level.entering&4),1235);
 game_reset(&g);level_start(&level,&g);for(i=0;i<LEVEL_INTRO;++i){level_step(&level,&g);}CHECK(!level.intro && !level_fade(&level),1236);
 level.intro=0;level.outro=LEVEL_OUTRO;CHECK(level_fade(&level)==8,1237);
 for(n=0;n<64;++n){level.timer=n;CHECK(level_go_bob(&level)>=0 && level_go_bob(&level)<=4,1238);}
 done:level=saved;return result;
#undef CHECK
}
