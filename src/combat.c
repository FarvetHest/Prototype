#include "game.h"
#include "bk3_data.h"
#include "combat_data.h"
#include "physics_data.h"
#include "stage.h"
#include <string.h>
static float bound(float x,float lo,float hi){return x<lo?lo:x>hi?hi:x;}
static int dir(float x){return x>.5f?1:x<-.5f?-1:0;}
static void dec(int *x){if(*x>0)--*x;}
/* sub_23CE6 / sub_23CB8: 68000 word rotation, XOR and add-with-extend. */
static unsigned random16(Combat *c){unsigned s=c->rng&65535,r=((s<<2)|(s>>14))&65535;r^=s;c->rng=((s<<1)|(r&1))&65535;return c->rng;}
unsigned bk3_random32(Game *g){unsigned s=g->physics.rng32;if(!s)s=0x2a6d365au;unsigned product=s*41u;unsigned sum=((product&65535)+(product>>16))&65535;g->physics.rng32=(sum<<16)|(product&65535);return sum;}
unsigned bk3_random_range(Game *g,unsigned n){return n?(random16(&g->combat)*n)>>16:0;}
static const Bk3Frame *sequence(int action,int *n){
#define SEQ(id,name) case id:*n=sizeof(bk3_##name)/sizeof(bk3_##name[0]);return bk3_##name;
 switch(action){SEQ(CB_HEAD,headbutt) SEQ(CB_KNEE,knee) SEQ(CB_JUMPKNEE,jumpknee) SEQ(CB_FRONTTHROW,frontthrow) SEQ(CB_BACKTHROW,backthrow) SEQ(CB_VAULT,vault) SEQ(CB_NEUTRAL,special1) SEQ(CB_FORWARD,special2) SEQ(CB_ROLL_DOWN,rolldown) SEQ(CB_ROLL_UP,rollup)}
#undef SEQ
 *n=1;return bk3_frontgrab;
}
void combat_reset(Game *g){int i;Combat *c=&g->combat;memset(c,0,sizeof(*c));c->target=-1;c->raw_charge=112;c->rng=0xace1;
 for(i=0;i<4;++i){c->enemy[i].level=5;c->enemy[i].timer=20+i*9;c->enemy[i].fpg=1;}}
static void release(Game *g){Combat *c=&g->combat;g->moves.grab=-1;g->moves.grab_timer=0;rules_end_hold(g);g->moves.grab_cooldown=0;c->target=-1;c->hold=0;c->escape=0;}
static void throw_launch(Game *g,int back);
static void action_start(Game *g,int action){Combat *c=&g->combat;int n;const Bk3Frame *f=sequence(action,&n);
 bk3_suspend(g);c->action=action;c->frame=0;c->timer=f[0].ticks;c->elapsed=0;g->bk3.mask=0;g->bk3.hitstop=0;g->bk3.queued=0;
 if(action==CB_FRONTTHROW || action==CB_BACKTHROW)throw_launch(g,action==CB_BACKTHROW);
 if(action==CB_ROLL_DOWN || action==CB_ROLL_UP)g->moves.roll=26;
 if(action==CB_BACKTHROW){g->physics.z=0;g->physics.vz=-3*65536;g->physics.landed=0;}
 if(action==CB_FORWARD){g->physics.z=0;g->physics.vz=AXEL_SPECIAL_VZ;g->physics.landed=0;}
 g->player.hit=0;g->player.attack=action!=CB_HOLD;g->moves.run_dir=0;g->motion.z[0]=0;}
static void hold_anchor(Game *g){Combat *c=&g->combat;Actor *p=&g->player,*e=&g->enemies[c->target];
 /* Chk_CharacterGrab offsets: Axel 32 pixels front / 16 pixels back. */
 p->x=bound(e->x-p->facing*(c->back?8:16),10,230);p->y=bound(e->y+1/.76f,76,126);e->facing=c->back?p->facing:-p->facing;e->attack=0;e->stun=0;g->motion.z[c->target+1]=0;}
void combat_hurt_enemy(Game *g,int i,int damage,int down){physics_hit(g,i+1,damage,down,g->player.facing);}
static void throw_launch(Game *g,int back){physics_victim_start(g,g->combat.target+1,back);}
static void action_finish(Game *g){Combat *c=&g->combat;int action=c->action;
 g->player.attack=0;g->player.jump=0;g->motion.z[0]=0;g->bk3.z=0;g->bk3.active=0;g->moves.special=0;g->moves.invincible=0;g->physics.z=0;g->moves.roll=0;
 if(action==CB_NEUTRAL || action==CB_FORWARD){g->player.hp-=c->pending_cost;c->pending_cost=0;}
 if(action==CB_VAULT && c->target>=0){Actor *p=&g->player,*e=&g->enemies[c->target];p->facing=-p->facing;c->back=!c->back;p->x=bound(e->x-p->facing*(c->back?8:16),10,230);
  if(g->physics.vaults++){p->x=bound(p->x-p->facing*6,10,230);release(g);}
 }
 if(c->target>=0 && g->enemies[c->target].hp>0 && !g->moves.down[c->target]){c->action=CB_HOLD;g->moves.grab=c->target;}
 else {c->action=CB_NONE;release(g);}
}
static void charge_tick(Game *g){Combat *c=&g->combat;
 /* HUD sub_5192: empty -> 16 immediately, then +16 every 49 frames. */
 if(c->action==CB_NEUTRAL || c->action==CB_FORWARD){c->raw_charge=0;c->charge_wait=0;}
 else if(!c->raw_charge){c->raw_charge=16;c->charge_wait=48;}
 else if(c->raw_charge>=112){if(!(c->ticks&3)){if(c->raw_charge>=192)c->raw_charge=96;c->raw_charge+=16;}}
 else if(c->raw_charge<112){if(c->charge_wait)--c->charge_wait;else{c->raw_charge+=16;c->charge_wait=48;}}
 g->moves.charge=c->raw_charge>=112?100:c->raw_charge*100/112;
}
static int special_start(Game *g,int dx){Combat *c=&g->combat;int cost=14-(c->raw_charge>>3);if(cost<0)cost=0;
 if(g->player.hp<=cost)return 0;
 c->pending_cost=cost;release(g);if(dx)g->player.facing=dx;action_start(g,dx?CB_FORWARD:CB_NEUTRAL);
 g->physics.body[0].phase=0;g->player.stun=0;g->moves.special_forward=dx!=0;return 1;
}
static void action_tick(Game *g){Combat *c=&g->combat;Bk3 *bk=&g->bk3;const Bk3Frame *f;int n,i;
 if(!c->timer){if(!g->physics.rolltimer)++c->frame;bk->mask=0;f=sequence(c->action,&n);
  if(c->frame>=n){if(c->action>=CB_ROLL_DOWN && g->physics.rolltimer<3){++g->physics.rolltimer;bk->fpg=1;g->moves.roll=1;return;}g->physics.rolltimer=0;action_finish(g);return;}c->timer=f[c->frame].ticks;}
 f=sequence(c->action,&n);f+=c->frame;
 bk->active=1;bk->fpg=f->fpg;bk->damage=f->damage;bk->collision=f->collision;bk->z=0;
 g->player.attack=c->action<CB_ROLL_DOWN;
 if(c->action>=CB_ROLL_DOWN){
  /* Init_Roll clears d0 before word_945C: literal ROM uses entry 0, speed 1. */
  g->player.y=bound(g->player.y+g->moves.roll_dir/.76f,76,126);g->moves.invincible=1;
  if(g->moves.roll>0)--g->moves.roll;
 }
 if(bk->hitstop){for(i=0;i<4;++i)dec(&bk->enemy_inv[i]);--bk->hitstop;return;}
 if(c->target>=0){
  if(c->action==CB_FRONTTHROW || c->action==CB_BACKTHROW){
   if(physics_victim_tick(g,c->target+1))release(g);
  }else if(c->action==CB_VAULT){
   /* Init vault: offset to victim's X and -64 Z, retained until completion. */
   g->player.x=g->enemies[c->target].x;g->physics.z=-64*65536;g->motion.z[0]=64;g->player.jump=1;
  }else hold_anchor(g);
 }
 if(c->action==CB_NEUTRAL || c->action==CB_FORWARD){g->moves.special=1;g->moves.invincible=1;
  if(c->action==CB_FORWARD && n-c->frame<=4 && !g->physics.landed){
   g->physics.z+=g->physics.vz;g->physics.vz+=BK3_GRAVITY_FP;
   if(g->physics.z>=0 && g->physics.vz>=0){g->physics.z=0;g->physics.landed=1;}
  }
 }
 if(c->action==CB_BACKTHROW && n-c->frame<=4){
  /* Obj_BackGrabThrow: Axel moves 1.5 pixels in remaining frames 4..2. */
  if(n-c->frame!=1)g->player.x=bound(g->player.x+g->player.facing*.75f,10,230);
  if(!g->physics.landed){g->physics.z+=g->physics.vz;g->physics.vz+=BK3_GRAVITY_FP;
   if(g->physics.z>=0 && g->physics.vz>=0){g->physics.z=0;g->physics.landed=1;}
  }
 }
 if(c->action!=CB_VAULT && c->action!=CB_FORWARD && c->action!=CB_BACKTHROW)g->physics.z=0;
 bk->z=g->physics.z;g->motion.z[0]=-bk->z/65536.0f;
 for(i=0;i<4;++i)dec(&bk->enemy_inv[i]);
 if(bk->hitstop){--bk->hitstop;return;}
 if(c->action!=CB_FORWARD || !g->physics.landed)bk3_damage_frame(g,f->collision,f->damage);
 if(c->target>=0 && (g->enemies[c->target].hp<=0 || g->moves.down[c->target]))release(g);
 --c->timer;++c->elapsed;
}
void combat_enemy_attack_frame(Game *g,int i,int collision,int damage){EnemyBrain *b=&g->combat.enemy[i];
 if(b->mask || !impact_overlap(g,i+1,0,collision))return;
 if(impact_apply(g,i+1,0,damage))b->mask=1;
}
void combat_tick(Game *g,float x,float y,int attack,int jump,int special){Combat *c=&g->combat;Actor *p=&g->player;int i,dx=dir(x),dy=dir(y);++c->ticks;
 dec(&g->moves.grab_cooldown);dec(&g->moves.invincible);if(g->physics.body[0].phase)physics_body_tick(g,0);else{dec(&g->physics.body[0].inv);dec(&p->stun);}
 g->motion.vx[0]=0;
 if(!p->stun && !p->jump && !p->attack && c->action==CB_NONE && !g->moves.roll && dy && dy!=g->moves.last_y){
  if(g->moves.tap_y==dy && c->ticks-(unsigned)g->moves.tap_y_tick<=16){g->moves.roll_dir=dy;g->moves.tap_y=0;action_start(g,dy>0?CB_ROLL_DOWN:CB_ROLL_UP);}
  else {g->moves.tap_y=dy;g->moves.tap_y_tick=c->ticks;}
 }
 g->moves.last_y=dy;
 if(special && !(c->action==CB_HOLD && c->back && (g->rules.actor[c->target+1].status5a&1)) && !g->moves.special && !g->moves.roll && !p->jump && g->physics.body[0].phase<=BODY_HURT)special_start(g,c->action==CB_HOLD?0:dx);
 if(c->action==CB_HOLD){
  if(c->back && c->target>=0 && (g->rules.actor[c->target+1].status5a&1)){charge_tick(g);for(i=0;i<4;++i)source_ai_tick(g,i);return;}
  g->rules.actor[0].hold_timer=(g->rules.actor[0].hold_timer-1)&65535;c->hold=g->rules.actor[0].hold_timer;
  if(!rules_hold_valid(g) || p->stun || !c->hold){release(g);c->action=CB_NONE;}
  else {
   if(dx==-p->facing){if(++c->escape>=20 && !attack){p->x=bound(p->x-p->facing*(c->back?8:4),10,230);release(g);c->action=CB_NONE;}}else c->escape=0;
   if(c->action==CB_HOLD){
    if(jump){c->vault_x=(int)(p->x*65536);action_start(g,CB_VAULT);}
    else if(attack){if(c->back)action_start(g,CB_BACKTHROW);else if(dx==-p->facing)action_start(g,CB_FRONTTHROW);else if(!dx)action_start(g,CB_HEAD);else action_start(g,++c->hits>=3?CB_JUMPKNEE:CB_KNEE);}
    else {hold_anchor(g);g->bk3.active=1;g->bk3.fpg=c->back?79:68;g->bk3.z=0;p->attack=0;}
   }
  }
 }
 if(c->action>CB_HOLD)action_tick(g);
 else if(c->action==CB_NONE){
  if(g->moves.roll){--g->moves.roll;g->moves.invincible=2;p->y=bound(p->y+g->moves.roll_dir*1.5f,76,126);}
  else if(!p->stun && p->hp>0){bk3_tick(g,x,y,attack,jump);
   if((dx || dy) && !p->attack && !p->jump && !g->moves.grab_cooldown)for(i=0;i<4;++i){Actor *e=&g->enemies[i];
    if(rules_can_grab(g,0,i+1,dx || dy)){c->target=i;c->back=e->facing==p->facing;c->hits=0;c->hold=g->rules.actor[0].hold_timer;rules_begin_hold(g,i);g->physics.vaults=0;action_start(g,CB_HOLD);g->moves.grab=i;hold_anchor(g);g->bk3.active=1;g->bk3.fpg=c->back?79:68;break;}
   }
  }else bk3_suspend(g);
 }
 charge_tick(g);
 for(i=0;i<4;++i)source_ai_tick(g,i);
}
int bk3_special_trace[160][5];
/* Executed on the PSP CPU before rendering; integration tests also inspect live state. */
int combat_selftest(void){Game g;int i,j,hp,peak=0;unsigned seed;
 game_reset(&g);seed=g.combat.rng;if(random16(&g.combat)!=22979 || g.combat.rng==seed)return 301;
 game_reset(&g);g.combat.raw_charge=0;charge_tick(&g);if(g.combat.raw_charge!=16)return 302;
 for(i=0;i<48;++i){charge_tick(&g);}if(g.combat.raw_charge!=16)return 303;
 charge_tick(&g);if(g.combat.raw_charge!=32)return 304;
 game_reset(&g);if(!special_start(&g,0) || g.combat.pending_cost || g.player.hp!=100)return 305;
 g.combat.raw_charge=16;g.combat.action=0;if(!special_start(&g,1) || g.combat.pending_cost!=12 || g.player.hp!=100)return 306;
 action_finish(&g);if(g.player.hp!=88)return 307;
 game_reset(&g);g.player.hp=12;g.combat.raw_charge=16;if(special_start(&g,0))return 308;
 game_reset(&g);g.combat.target=0;g.moves.grab=0;g.combat.action=CB_HOLD;g.enemies[0].facing=-1;hold_anchor(&g);
 if(g.player.x!=128 || g.enemies[0].x!=144)return 309;
 hp=g.enemies[0].hp;throw_launch(&g,0);if(g.enemies[0].hp!=hp || g.physics.body[1].phase!=BODY_VICTIM)return 310;
 game_reset(&g);g.combat.target=0;g.combat.action=CB_HOLD;g.combat.back=1;hold_anchor(&g);if(g.player.x!=136 || g.enemies[0].x!=144)return 312;
 game_reset(&g);g.combat.target=0;g.combat.action=CB_HOLD;rules_begin_hold(&g,0);combat_tick(&g,1,0,1,0,0);if(g.combat.action!=CB_KNEE || g.bk3.fpg!=72)return 313;
 game_reset(&g);g.combat.target=0;g.combat.action=CB_HOLD;rules_begin_hold(&g,0);combat_tick(&g,-1,0,1,0,0);if(g.combat.action!=CB_FRONTTHROW || g.bk3.fpg!=153)return 314;
 game_reset(&g);g.combat.target=0;g.combat.action=CB_HOLD;g.combat.back=1;rules_begin_hold(&g,0);combat_tick(&g,0,0,1,0,0);if(g.combat.action!=CB_BACKTHROW)return 315;
 game_reset(&g);g.combat.target=0;g.combat.action=CB_HOLD;rules_begin_hold(&g,0);combat_tick(&g,0,0,1,0,0);if(g.combat.action!=CB_HEAD || g.bk3.fpg!=69)return 316;
 game_reset(&g);g.combat.target=0;g.combat.action=CB_HOLD;g.combat.hits=2;rules_begin_hold(&g,0);combat_tick(&g,1,0,1,0,0);if(g.combat.action!=CB_JUMPKNEE)return 317;
 game_reset(&g);for(j=0;j<4;++j){g.enemies[j].x=220;g.enemies[j].y=126;g.enemies[j].stun=10000;}
 special_start(&g,1);
 for(i=0;i<160;++i){if(g.combat.action)action_tick(&g);bk3_special_trace[i][0]=g.physics.z;bk3_special_trace[i][1]=g.physics.vz;bk3_special_trace[i][2]=g.physics.landed;bk3_special_trace[i][3]=g.combat.frame;bk3_special_trace[i][4]=g.combat.action;if(-g.physics.z>peak)peak=-g.physics.z;}
 if(peak!=34*65536 || !g.physics.landed || g.combat.action || g.player.hp!=100)return 318;
 /* Grab register and input-order regression cases. */
 game_reset(&g);g.combat.target=0;g.combat.back=1;g.combat.action=CB_HOLD;rules_begin_hold(&g,0);g.rules.actor[0].hold_timer=123;g.rules.actor[1].status5a=1;
 combat_tick(&g,1,0,1,1,1);if(g.combat.action!=CB_HOLD || g.rules.actor[0].hold_timer!=123)return 319;
 game_reset(&g);g.combat.target=0;g.combat.action=CB_HOLD;rules_begin_hold(&g,0);combat_tick(&g,1,0,0,0,1);if(g.combat.action!=CB_NEUTRAL || g.rules.actor[0].held!=-1)return 320;
 game_reset(&g);g.combat.target=0;g.combat.action=CB_HOLD;rules_begin_hold(&g,0);g.rules.actor[1].status58&=~16;combat_tick(&g,0,0,0,0,0);if(g.combat.action || g.rules.actor[0].held!=-1)return 321;
 game_reset(&g);g.combat.target=0;g.combat.action=CB_HOLD;rules_begin_hold(&g,0);g.rules.actor[0].hold_timer=1;combat_tick(&g,0,0,0,0,0);if(g.combat.action)return 322;
 game_reset(&g);g.combat.target=0;g.combat.action=CB_HOLD;rules_begin_hold(&g,0);combat_tick(&g,0,0,0,0,0);if(g.rules.actor[0].hold_timer!=65535 || g.combat.action!=CB_HOLD)return 323;
 release(&g);g.combat.target=0;rules_begin_hold(&g,0);if(g.rules.actor[0].hold_timer!=65535)return 324;
 game_reset(&g);g.enemies[0].x=64;g.enemies[0].y=103;combat_tick(&g,0,1,0,0,0);if(g.moves.grab!=0)return 325;
 game_reset(&g);g.enemies[0].x=64;g.enemies[0].y=100;physics_hit(&g,1,1,0,1);if(!rules_can_grab(&g,0,1,1))return 326;
 return 0;
}
