#include "game.h"
#include "bk3_data.h"
#include "stage.h"
#include <string.h>
int bk3_jump_trace[48][4],bk3_punch_trace[8][4];
static int direction(float x){return x>.5f?1:x<-.5f?-1:0;}
static float bound(float x,float low,float high){return x<low?low:x>high?high:x;}
static const Bk3Frame *frames(int script,int *count){
#define SCRIPT(id,name) case id:*count=(int)(sizeof(bk3_##name)/sizeof(bk3_##name[0]));return bk3_##name;
 switch(script){SCRIPT(BK_IDLE,idle) SCRIPT(BK_WALK,walk) SCRIPT(BK_RUN,run) SCRIPT(BK_JUMP,jump)
 SCRIPT(BK_PUNCH1,punch1) SCRIPT(BK_PUNCH2,punch2) SCRIPT(BK_KICK,kick) SCRIPT(BK_BLITZ,blitz) SCRIPT(BK_AIR1,air1) SCRIPT(BK_AIR2,air2) SCRIPT(BK_BACKHAND,backhand) SCRIPT(BK_DOUBLEKICK,doublekick)}
#undef SCRIPT
 *count=34;return bk3_idle;
}
static void enter(Bk3 *b,int script){int count;const Bk3Frame *f=frames(script,&count);
 b->script=script;b->frame=0;b->timer=f[0].ticks;b->mask=0;
}
static void attack_start(Game *g){Bk3 *b=&g->bk3;
 int rear=b->queued==2;
 b->queued=0;b->mode=1;g->player.hit=0;
 if(rear){b->combo=b->next_combo=0;b->run=0;enter(b,BK_BACKHAND);g->moves.attack_kind=HIT_NORMAL;}
 else if(b->run){b->combo=0;enter(b,BK_BLITZ);b->run=0;g->moves.attack_kind=HIT_BLITZ;}
 else{b->combo=b->next_combo+1;enter(b,b->next_combo<2?BK_PUNCH1:b->next_combo==2?BK_PUNCH2:b->combo_timeout>=16?BK_DOUBLEKICK:BK_KICK);
 b->combo_timeout=22;g->moves.attack_kind=HIT_NORMAL;}
}
void bk3_suspend(Game *g){Bk3 *b=&g->bk3;
 if(b->active){b->active=0;b->mode=0;b->queued=0;b->z=b->vz=b->airvx=0;b->next_combo=0;b->combo_timeout=0;b->run=0;b->lastx=b->tapdir=b->taptimer=0;g->player.jump=0;g->player.attack=0;g->motion.z[0]=0;}
}
static void collide(Game *g,const Bk3Frame *f){
 Bk3 *b=&g->bk3;int i,hit=0;
 if(!f->collision || !(f->damage&63))return;
 for(i=0;i<4;++i){
  if((b->mask&(1u<<i)) || !impact_overlap(g,0,i+1,f->collision))continue;
  if(!impact_apply(g,0,i+1,f->damage))continue;
  b->mask|=1u<<i;b->enemy_inv[i]=5;g->player.hit|=1u<<i;hit=1;
 }
 if(hit){int freeze=2+((f->damage&63)>>2);b->hitstop=freeze>8?8:freeze;}
}
void bk3_damage_frame(Game *g,int collision,int damage){Bk3Frame f={1,1,collision,damage};collide(g,&f);}
void bk3_tick(Game *g,float x,float y,int attack,int jump){
 Bk3 *b=&g->bk3;Actor *p=&g->player;int dx=direction(x),dy=direction(y),n,i,started_jump=0,air_step;const Bk3Frame *f;
 if(!b->active){b->active=1;enter(b,BK_IDLE);
  if(p->jump){b->mode=2;b->takeoff=4;b->z=0;b->vz=BK3_JUMP_FP;b->airvx=0;enter(b,BK_JUMP);}}
 ++b->ticks;
 for(i=0;i<4;++i)if(b->enemy_inv[i])--b->enemy_inv[i];
 if(b->mode==0 && !b->hitstop && b->combo_timeout>0 && --b->combo_timeout==0)b->next_combo=0;
 if(b->taptimer>0)--b->taptimer;
 if(dx && dx!=b->lastx){if(b->tapdir==dx && b->taptimer>0)b->run=dx;b->tapdir=dx;b->taptimer=BK3_DOUBLE_TAP;}
 b->lastx=dx;if(dx!=b->run)b->run=0;
 if(attack)b->queued=attack==2?2:1;
 if(b->hitstop){--b->hitstop;return;}
 if(!b->timer){
  f=frames(b->script,&n);++b->frame;b->mask=0;
  if(b->frame>=n){
   if(b->mode==1){if(b->script!=BK_BLITZ && b->script!=BK_BACKHAND)b->next_combo=b->combo%4;b->mode=0;enter(b,BK_IDLE);}
   else if(b->mode==2){b->frame=n-1;b->timer=1;}
   else enter(b,b->script);
  }else b->timer=f[b->frame].ticks;
 }
 if(b->mode==0){
  if(jump){started_jump=1;b->mode=2;b->takeoff=4;b->landing=0;b->z=0;b->vz=BK3_JUMP_FP;b->airvx=0;b->air_attack=0;b->run=0;enter(b,BK_JUMP);b->queued=attack;}
  else if(b->queued)attack_start(g);
  else{
   int script=b->run?BK_RUN:(dx||dy)?BK_WALK:BK_IDLE;
   if(b->script!=script)enter(b,script);
   p->x=bound(p->x+dx*(b->run?BK3_RUN_FP:BK3_WALK_FP)/131072.0f,10,230);
   if(!b->run)p->y=bound(p->y+dy*BK3_WALK_FP/(65536.0f*2*.76f),76,126);
   if(dx)p->facing=dx;
  }
 }else if(b->mode==1 && b->script==BK_BLITZ){
  n=10-b->frame;if(n<=9 && n>3)p->x=bound(p->x+p->facing*.75f,10,230);
 }
 if(b->mode==2 && !started_jump){
  if(b->landing){if(--b->landing==0){b->mode=0;b->air_attack=0;enter(b,BK_IDLE);}}
  else if(b->takeoff){--b->takeoff;if(dx)p->facing=dx;}
  else{
   b->z+=b->vz;b->vz+=BK3_GRAVITY_FP;
   if(b->z>=0 && b->vz>=0){b->z=0;b->airvx=0;b->landing=1;b->queued=0;enter(b,BK_JUMP);b->frame=2;b->timer=1;}
   else{
    if((attack || b->queued) && !b->air_attack){b->air_attack=1;b->queued=0;g->moves.attack_kind=HIT_AIR;enter(b,b->airvx?BK_AIR2:BK_AIR1);}
    if(b->script!=BK_AIR1){
     /* Obj_Jumping loc_98E4..9958: 1/4 pixel acceleration, ±2 pixels cap. */
     air_step=b->airvx;
     if(dx>0){air_step+=BK3_AIR_ACCEL_FP;if(air_step<BK3_AIR_LIMIT_FP)b->airvx=air_step;}
     if(dx<0){air_step-=BK3_AIR_ACCEL_FP;if(air_step>-BK3_AIR_LIMIT_FP)b->airvx=air_step;}
     /* The 68000 branches skip storing at the limit but still add d0 to position. */
     p->x=bound(p->x+air_step/131072.0f,10,230);
    }
   }
  }
 }
 f=frames(b->script,&n);f+=b->frame;b->fpg=f->fpg;b->damage=f->damage;b->collision=f->collision;
 if(b->mode==1 || (b->mode==2 && b->air_attack))collide(g,f);
 if(b->timer>0)--b->timer;
 g->motion.z[0]=-b->z/65536.0f;g->motion.vz[0]=-b->vz/65536.0f;g->motion.jump_x=b->airvx/65536.0f;
 p->jump=b->mode==2?1:0;p->attack=b->mode==1 || (b->mode==2 && b->air_attack)?1:0;p->cooldown=p->attack;
 g->moves.run_dir=b->mode==0?b->run:0;g->moves.combo=b->combo;g->moves.queued=b->queued;
}

static void quiet(Game *g){int i;game_reset(g);for(i=0;i<4;++i){g->enemies[i].x=220;g->enemies[i].y=126;g->enemies[i].stun=10000;g->enemies[i].cooldown=10000;}}
int bk3_selftest(void){
 Game g;Input in={0};int i;float before;int peak=0;
 if(BK3_WALK_FP!=81920 || BK3_RUN_FP!=163840 || BK3_JUMP_FP!=-311296)return 201;
 quiet(&g);before=g.player.x;bk3_tick(&g,1,0,0,0);if(g.player.x-before!=.625f)return 202;
 quiet(&g);before=g.player.y;bk3_tick(&g,0,1,0,0);if(g.player.y-before<.82f || g.player.y-before>.83f)return 203;
 quiet(&g);bk3_tick(&g,1,0,0,0);bk3_tick(&g,0,0,0,0);before=g.player.x;bk3_tick(&g,1,0,0,0);
 if(!g.bk3.run || g.player.x-before!=1.25f)return 204;
 bk3_tick(&g,0,0,0,0);if(g.bk3.run)return 205;
 quiet(&g);bk3_tick(&g,1,0,0,0);for(i=0;i<17;++i){bk3_tick(&g,0,0,0,0);}bk3_tick(&g,1,0,0,0);if(g.bk3.run)return 206;
 quiet(&g);bk3_tick(&g,0,0,0,1);for(i=0;i<4;++i){bk3_tick(&g,0,0,0,0);if(g.bk3.z)return 207;}
 bk3_tick(&g,0,0,0,0);if(g.bk3.z!=-311296 || g.bk3.vz!=-294912)return 208;
 for(i=0;i<50;++i){bk3_tick(&g,0,0,0,0);if(-g.bk3.z>peak)peak=-g.bk3.z;}
 if(g.player.jump || g.bk3.z || peak!=3112960)return 209;
 quiet(&g);bk3_tick(&g,0,0,0,1);for(i=0;i<13;++i){bk3_tick(&g,1,0,0,0);}if(g.bk3.airvx!=114688)return 210;
 for(i=0;i<16;++i){bk3_tick(&g,-1,0,0,0);}if(g.bk3.airvx!=-114688)return 211;
 quiet(&g);bk3_tick(&g,0,0,1,0);if(g.bk3.script!=BK_PUNCH1 || g.bk3.fpg!=1)return 212;
 bk3_tick(&g,0,0,0,0);if(g.bk3.fpg!=80 || g.bk3.damage!=2 || g.bk3.collision!=5)return 213;
 for(i=0;i<3;++i){bk3_tick(&g,0,0,0,0);}if(g.bk3.next_combo!=1 || g.bk3.mode)return 214;
 bk3_tick(&g,0,0,1,0);if(g.bk3.script!=BK_PUNCH1 || g.bk3.combo!=2)return 215;
 for(i=0;i<4;++i){bk3_tick(&g,0,0,0,0);}bk3_tick(&g,0,0,1,0);if(g.bk3.script!=BK_PUNCH2 || g.bk3.combo!=3)return 216;
 for(i=0;i<12;++i){bk3_tick(&g,0,0,0,0);}bk3_tick(&g,0,0,1,0);if(g.bk3.script!=BK_DOUBLEKICK || g.bk3.combo!=4)return 217;
 quiet(&g);g.enemies[0].x=80;g.enemies[0].y=100;bk3_tick(&g,0,0,1,0);bk3_tick(&g,0,0,0,0);
 if(g.enemies[0].hp!=38 || !g.bk3.hitstop)return 218;
 for(i=0;i<5;++i){bk3_tick(&g,0,0,0,0);}if(g.enemies[0].hp!=38)return 219;
 quiet(&g);g.enemies[0].x=48;g.enemies[0].y=100;bk3_tick(&g,0,0,1,0);bk3_tick(&g,0,0,0,0);if(g.enemies[0].hp!=40)return 220;
 quiet(&g);g.enemies[0].x=80;g.enemies[0].y=126;bk3_tick(&g,0,0,1,0);bk3_tick(&g,0,0,0,0);if(g.enemies[0].hp!=40)return 221;
 quiet(&g);in.x=1;game_step(&g,in);if(g.bk3.ticks!=2)return 222;
 g.paused=1;before=g.player.x;game_step(&g,in);if(g.player.x!=before || g.bk3.ticks!=2)return 223;
 quiet(&g);g.ticks=99*30-1;game_step(&g,in);if(g.player.hp)return 224;
 quiet(&g);for(i=0;i<48;++i){bk3_tick(&g,0,0,0,i==0);bk3_jump_trace[i][0]=g.bk3.z;bk3_jump_trace[i][1]=g.bk3.vz;bk3_jump_trace[i][2]=g.bk3.takeoff;bk3_jump_trace[i][3]=g.bk3.mode;}
 quiet(&g);for(i=0;i<8;++i){bk3_tick(&g,0,0,i==0,0);bk3_punch_trace[i][0]=g.bk3.fpg;bk3_punch_trace[i][1]=g.bk3.damage;bk3_punch_trace[i][2]=g.bk3.collision;bk3_punch_trace[i][3]=g.bk3.mode;}
 quiet(&g);bk3_tick(&g,0,0,2,0);if(g.bk3.script!=BK_BACKHAND || g.bk3.fpg!=14 || g.player.facing!=1)return 225;
 quiet(&g);g.enemies[0].x=48;g.enemies[0].y=100;in=(Input){0,0,2,0,0};game_step(&g,in);in.attack=0;for(i=0;i<3;++i){game_step(&g,in);}if(g.enemies[0].hp>=40 || g.enemies[0].facing!=1)return 226;
 quiet(&g);g.enemies[0].x=82;g.enemies[0].y=100;in=(Input){0,0,2,0,0};game_step(&g,in);in.attack=0;for(i=0;i<12;++i){game_step(&g,in);}if(g.enemies[0].hp!=40)return 227;
 quiet(&g);bk3_tick(&g,0,0,2,0);for(i=0;i<24;++i){bk3_tick(&g,0,0,0,0);}if(g.bk3.mode || g.bk3.next_combo || g.player.facing!=1)return 228;
 quiet(&g);g.bk3.next_combo=3;g.bk3.combo_timeout=22;bk3_tick(&g,0,0,1,0);if(g.bk3.script!=BK_DOUBLEKICK)return 229;
 quiet(&g);g.bk3.next_combo=3;g.bk3.combo_timeout=16;bk3_tick(&g,0,0,1,0);if(g.bk3.script!=BK_KICK)return 230;
 quiet(&g);bk3_tick(&g,0,0,1,0);for(i=0;i<3;++i){bk3_tick(&g,0,0,0,0);}if(g.bk3.combo_timeout!=22)return 231;
 quiet(&g);bk3_tick(&g,0,0,1,0);g.bk3.hitstop=5;bk3_tick(&g,0,0,0,0);if(g.bk3.combo_timeout!=22)return 232;
 quiet(&g);g.bk3.active=1;g.bk3.next_combo=2;g.bk3.combo_timeout=1;bk3_tick(&g,0,0,0,0);if(g.bk3.next_combo || g.bk3.combo_timeout)return 233;
 return 0;
}
