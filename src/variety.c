/* BK3 source modes, animation records and per-type AI profiles. Arena movement
   adapts source coordinates to Lite; see assets/enemy-variety.json for provenance. */
#include "game.h"
#include "bk3_data.h"
#include "combat_data.h"
#include "physics_data.h"
#include "bk3_data.h"
#include "variety_data.h"
#include "reaction_data.h"
#include <string.h>
static float ab(float x){return x<0?-x:x;}
static float clamp(float x,float lo,float hi){return x<lo?lo:x>hi?hi:x;}
int enemy_type(const Game *g,int i){int t=g->extra[i].type;return t>=0 && t<=EN_ZACK?t:i&1;}
void enemy_set_type(Game *g,int i,int type){memset(&g->extra[i],0,sizeof(g->extra[i]));g->extra[i].type=type;g->pose[i]=(EnemyPose){0};g->rules.actor[i+1].type=type==EN_ELECTRA?28:type==EN_ZACK?30:type?16:14;}
const EnemyFrame *variety_sequence(int t,int k,int *n){
#define S(kind,name) case kind:if(t==EN_ELECTRA){*n=sizeof(electra_##name)/sizeof(EnemyFrame);return electra_##name;}*n=sizeof(zack_##name)/sizeof(EnemyFrame);return zack_##name;
 if(t==EN_ZACK && (k==16 || k==17)){*n=1;return k==16?defense_holder:defense_backholder;}
 if(t==EN_ZACK && (k==14 || k==15)){*n=1;return k==14?defense_guard:defense_counter;}
 switch(k){S(EP_IDLE,idle) S(EP_WALK,walk) S(EP_HELD,held) S(EP_HURT2,hurt2) S(EP_HURT,hurt) S(EP_FLIGHT,flight) S(EP_FLOOR,floor) S(EP_GETUP,getup) S(EP_FRONT,front) S(EP_BACK,back) S(EP_JAB,jab) S(EP_UPPER,uppercut) S(EP_KICK,kick) S(13,jump) S(14,guard)}
#undef S
 *n=1;return electra_idle;
}
const signed char *enemy_box(const Game *g,int i,int id,int hurt){int t=enemy_type(g,i);if(id<0)return 0;
 if(t==EN_ZACK && g->extra[i].action>=14){if(hurt)return id<(int)(sizeof(counter_hurt)/8)?counter_hurt[id]:0;return id<(int)(sizeof(counter_boxes)/8)?counter_boxes[id]:0;}
#define BOX(type,prefix) case type:if(hurt)return id<(int)(sizeof(prefix##_hurt_boxes)/8)?prefix##_hurt_boxes[id]:0;return id<(int)(sizeof(prefix##_boxes)/8)?prefix##_boxes[id]:0;
 if(t==EN_GALSIA){if(hurt)return id<9?garcia_hurt_boxes[id]:0;return id<4?garcia_boxes[id]:0;}
 if(t==EN_DONOVAN){if(hurt)return id<12?donovan_hurt_boxes[id]:0;return id<5?donovan_boxes[id]:0;}
#undef BOX
 if(t==EN_ELECTRA){if(hurt)return id<(int)(sizeof(electra_hurt_boxes)/8)?electra_hurt_boxes[id]:0;return id<(int)(sizeof(electra_attack_boxes)/8)?electra_attack_boxes[id]:0;}
 if(hurt)return id<(int)(sizeof(zack_hurt_boxes)/8)?zack_hurt_boxes[id]:0;
 return id<(int)(sizeof(zack_attack_boxes)/8)?zack_attack_boxes[id]:0;
}
static const unsigned char *profile(Game *g,int i){int l=g->combat.enemy[i].level,t=enemy_type(g,i);if(l<0)l=0;if(l>(t==EN_ELECTRA?6:10))l=t==EN_ELECTRA?6:10;return t==EN_ELECTRA?electra_profiles[l]:zack_profiles[l];}
static int random(Game *g,int n){return (int)bk3_random_range(g,(unsigned)n);}
static void begin(Game *g,int i,int action){EnemyExtra *v=&g->extra[i];v->action=action;v->frame=v->timer=0;g->combat.enemy[i].mask=0;g->enemies[i].attack=action>=EP_JAB && action<=EP_KICK;g->rules.ai[i].mode=action==EP_JAB?0x48:action==EP_UPPER?0x4a:action==EP_KICK?0x4c:action==13?4:6;}
static void move(Game *g,int i,int dx,int dy,int speed){Actor *e=&g->enemies[i];float x=e->x+dx*speed/32.f,y=e->y+dy*speed/(16*.76f);g->rules.ai[i].blocked=x<10 || x>230 || y<76 || y>126;e->x=clamp(x,10,230);e->y=clamp(y,76,126);g->combat.enemy[i].fpg=1;}
static void decide(Game *g,int i,float x,float y){EnemyBrain *b=&g->combat.enemy[i];const unsigned char *p=profile(g,i);int roll,s;float d=ab(x)+ab(y);++g->rules.ai[i].decisions;
 if(g->rules.actor[i+1].status89&64){b->state=enemy_type(g,i)==EN_ELECTRA?11:13;b->timer=20+random(g,20);b->speed=8;return;}
 if(enemy_type(g,i)==EN_ELECTRA){
  /* loc_2B444: <32 retreat jump; aligned <80 mode48, <136 mode4A. */
  if(d<32 && random(g,100)<p[30]){begin(g,i,13);g->extra[i].vz=-360448;g->extra[i].vx=-(x>=0?1:-1)*131072;return;}
  if(ab(y)<=7 && (rules_flags(g,0)&128) && ab(x)<136){b->state=ab(x)<80?8:9;b->timer=0;return;}
 }else if(reaction_capture(g,i)){return;}else if(ab(y)<=7 && ab(x)<=60 && (rules_flags(g,0)&128)){
  /* loc_2C648 then loc_2C464: two jabs, then mode4A finisher. */
  b->state=8;b->timer=p[28]+random(g,p[28]);return;
 }
 if(d>(enemy_type(g,i)==EN_ELECTRA?160:184)){b->state=6;b->timer=30;b->speed=24;return;}
 if(enemy_type(g,i)==EN_ZACK && ab(y)<=7 && ab(x)<88){b->state=2;b->timer=p[12];b->speed=p[13];return;}
 roll=random(g,100);for(s=0;s<4;++s){roll-=p[s];if(roll<0)break;}if(s>3)s=4;b->state=s;
 if(!s)b->timer=p[6]+random(g,p[7]);
 else if(s==1){b->speed=p[10]+random(g,p[11]);b->timer=p[8]+random(g,p[9]);b->direction=random(g,8);}
 else if(s==2){b->speed=p[13]+random(g,p[14]);b->timer=p[12];}
 else if(s==3){b->speed=p[19];b->timer=p[17]+random(g,p[18]);g->rules.ai[i].offset=p[15]+random(g,p[16]);}
 else{b->speed=p[22]+random(g,p[23]);b->timer=p[20]+random(g,p[21]);g->rules.ai[i].offset=random(g,2);}
}
static void animate(Game *g,int i){EnemyExtra *v=&g->extra[i];EnemyBrain *b=&g->combat.enemy[i];Actor *e=&g->enemies[i];const EnemyFrame *f;int n=enemy_count(g,i,v->action),action=v->action;
 f=enemy_frames(g,i,action);if(action==14 && v->wait>0){--v->wait;e->x=clamp(e->x+v->vx/131072.f,10,230);if(v->vx>0){v->vx-=32768;if(v->vx<0)v->vx=0;}else if(v->vx<0){v->vx+=32768;if(v->vx>0)v->vx=0;}}
 if(!v->timer){if(v->frame>=n){
   if(action==14 && v->wait>0){v->frame=0;}else{
   if(enemy_type(g,i)==EN_ELECTRA && action==EP_JAB){begin(g,i,EP_KICK);return;}
   v->action=0;e->attack=0;g->rules.ai[i].mode=2;if(action==EP_KICK)b->state=7;return;
  }}v->timer=f[v->frame].ticks;b->mask=0;}
 g->pose[i].kind=action;g->pose[i].fpg=f[v->frame].fpg;g->pose[i].hurt=f[v->frame].hurt;b->fpg=f[v->frame].fpg;
 if(action==13){
  /* Electra sub_2B48A: source vx=-2, vz=-5.5, gravity .25. */
  e->x=clamp(e->x+v->vx/131072.f,10,230);v->z+=v->vz;v->vz+=16384;
  if(v->z>=0){v->z=v->vz=v->vx=0;v->action=0;g->rules.ai[i].mode=2;b->state=7;e->jump=0;g->motion.z[i+1]=0;return;}
  e->jump=1;g->motion.z[i+1]=-v->z/65536.f;
 }else if(((action>=EP_JAB && action<=EP_KICK) || action==15))combat_enemy_attack_frame(g,i,f[v->frame].collision,f[v->frame].damage);
 if(!--v->timer && ++v->frame>=n && action==13)v->frame=n-1;
}
int variety_tick(Game *g,int i){EnemyExtra *v=&g->extra[i];EnemyBrain *b=&g->combat.enemy[i];SourceAI *a=&g->rules.ai[i];Actor *e=&g->enemies[i];const unsigned char *p=profile(g,i);float x=(int)(g->player.x*2)-(int)(e->x*2),y=(int)(g->player.y*.76f)-(int)(e->y*.76f),d=ab(x)+ab(y);int sx=x>0?1:-1,sy=y>2?1:y<-2?-1:0,s;
 /* A hit/hold is handled before this adapter. physics_hit cancels source mode. */
 if(v->action && a->mode==2){v->action=0;v->z=v->vz=v->vx=0;}
 if(v->action){animate(g,i);return 1;}
 if(g->reaction.holder==i)return 1;
 a->active=(rules_flags(g,0)&128)!=0;a->target=a->active?0:-1;
 if(!(g->combat.ticks&7)){e->facing=sx;++a->face_ticks;}
 if(!a->active){e->attack=0;b->state=7;move(g,i,d>112?sx:-sx,0,12);return 1;}
 if(b->state<0 || b->state>13)b->state=7;
 s=b->state;a->visited|=1u<<s;a->previous=s;
 if(s==7){decide(g,i,x,y);if(v->action==13){v->vx=-e->facing*131072;animate(g,i);}return 1;}
 if(enemy_type(g,i)==EN_ELECTRA && (s==8 || s==9)){
  if(ab(y)>7 || ab(x)>136){decide(g,i,x,y);return 1;}
  if(--b->timer>=0)return 1;
  if(random(g,100)<p[s==8?29:28]){begin(g,i,s==8?EP_JAB:EP_UPPER);b->state=7;}else{b->state=11;b->timer=25+random(g,20);b->speed=8;}return 1;
 }
 if(enemy_type(g,i)==EN_ZACK && s>=8 && s<=11){
  if(ab(y)>7 || (s<=9 && ab(x)>60)){decide(g,i,x,y);return 1;}
  if(--b->timer>=0)return 1;
  if(s<=9){b->state=s+1;b->timer=p[28]+random(g,p[29]);begin(g,i,EP_JAB);}else{b->state=7;b->timer=0;begin(g,i,EP_UPPER);}return 1;
 }
 if(!s){if(--b->timer<0)decide(g,i,x,y);return 1;}
 if(s==1){static const int dx[]={0,1,1,1,0,-1,-1,-1},dy[]={-1,-1,0,1,1,1,0,-1};move(g,i,dx[b->direction&7],dy[b->direction&7],b->speed);}
 else if(s==3){int desired=a->offset;move(g,i,d>desired?sx:-sx,0,b->speed);}
 else if(s==4)move(g,i,ab(x)>40?sx:0,a->offset?1:-1,b->speed);
 else if(s==5 || s==11 || s==13)move(g,i,-sx,0,b->speed);
 else move(g,i,ab(x)>16?sx:0,sy,b->speed);
 if(--b->timer<0 || a->blocked || (ab(y)<=7 && ab(x)<(enemy_type(g,i)==EN_ELECTRA?136:60)))decide(g,i,x,y);
 return 1;
}
int variety_selftest(void){Game g;int t,k,j;
 for(t=2;t<=3;++t){game_reset(&g);enemy_set_type(&g,0,t);if(enemy_type(&g,0)!=t || enemy_type(&g,1)!=1)return 1601;
  for(k=0;k<15;++k){const EnemyFrame *f=enemy_frames(&g,0,k);for(j=0;j<enemy_count(&g,0,k);++j)if(!f[j].ticks || f[j].fpg<1000 || !enemy_box(&g,0,f[j].hurt,1) || !enemy_box(&g,0,f[j].collision,0))return 1602+t;}
  /* Every source frame lasts exactly its 60-Hz timer, including non-hit poses. */
  for(k=EP_JAB;k<=EP_KICK;++k){const EnemyFrame *f=enemy_frames(&g,0,k);int tick;
   g.enemies[0].x=220;g.enemies[0].y=100;begin(&g,0,k);
   for(j=0;j<enemy_count(&g,0,k);++j)for(tick=0;tick<f[j].ticks;++tick){
    variety_tick(&g,0);if(g.pose[0].fpg!=f[j].fpg || g.pose[0].hurt!=f[j].hurt)return 1610+t;
   }
   variety_tick(&g,0);
   if(g.extra[0].action!=(t==EN_ELECTRA && k==EP_JAB?EP_KICK:0))return 1614+t;
  }
  g.extra[0].action=0;g.rules.ai[0].mode=2;
  g.enemies[0].x=82;g.enemies[0].y=100;g.combat.enemy[0].state=8;g.combat.enemy[0].timer=0;g.combat.enemy[0].level=10;variety_tick(&g,0);
  if(t==3 && (g.extra[0].action!=EP_JAB || g.combat.enemy[0].state!=9))return 1606;
 }
 game_reset(&g);enemy_set_type(&g,0,EN_ZACK);g.enemies[0].x=100;g.enemies[0].y=100;g.combat.enemy[0].state=7;
 variety_tick(&g,0);if(g.combat.enemy[0].state!=2)return 1620;
 for(j=0;j<20;++j)variety_tick(&g,0);
 if(g.enemies[0].x>=100)return 1621;
 game_reset(&g);enemy_set_type(&g,0,EN_ZACK);g.enemies[0].x=100;g.enemies[0].y=100;g.combat.enemy[0].state=7;g.rules.actor[1].status89=64;variety_tick(&g,0);if(g.combat.enemy[0].state!=13)return 1622;
 begin(&g,0,EP_JAB);physics_hit(&g,1,2,0,1);if(g.extra[0].action)return 1623;
 begin(&g,0,EP_JAB);g.combat.target=0;rules_begin_hold(&g,0);if(g.extra[0].action)return 1624;
 game_reset(&g);enemy_set_type(&g,0,EN_ELECTRA);g.enemies[0].x=100;begin(&g,0,13);g.extra[0].vz=-360448;g.extra[0].vx=-131072;
 for(j=0;j<45;++j)variety_tick(&g,0);
 if(g.extra[0].action || g.motion.z[1]!=0 || g.enemies[0].x!=55)return 1625;
 return 0;
}
