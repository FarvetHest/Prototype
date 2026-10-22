/* CE decisions and object animation are distinct registers in BK3. */
#include "game.h"
#include "bk3_data.h"
#include "combat_data.h"
#include "physics_data.h"
static float ab(float x){return x<0?-x:x;}
static int attack_mode(int m){return m==0x1a || m==0x1c || m==0x30;}
static int toward(float x,float y){return ab(y)<=2?(x>0?2:6):ab(x)<=16?(y>0?4:0):y>0?(x>0?3:5):(x>0?1:7);}
static const unsigned char *profile(EnemyBrain *b){int l=b->level;if(l<0)l=0;if(l>10)l=10;return garcia_profiles[l];}
static int rnd(Game *g,int n){return (int)bk3_random_range(g,(unsigned)n);}
static void select_state(Game *g,int i,int state){EnemyBrain *b=&g->combat.enemy[i];SourceAI *a=&g->rules.ai[i];const unsigned char *p=profile(b);b->state=state;
 switch(state){
 case 0:b->timer=p[6]+rnd(g,p[7]);break;
 case 1:b->speed=p[10]+rnd(g,p[11]);b->direction=rnd(g,8);b->timer=p[8]+rnd(g,p[9]);break;
 case 2:b->speed=p[13]+rnd(g,p[14]);b->timer=p[12];break;
 case 3:b->timer=p[17]+rnd(g,p[18]);a->offset=p[15]+rnd(g,p[16]);b->speed=p[19];break;
 case 4:b->speed=p[22]+rnd(g,p[23]);a->offset=rnd(g,2);b->timer=p[20]+rnd(g,p[21]);break;
 case 5:b->speed=p[26]+rnd(g,p[27]);b->timer=p[24]+rnd(g,p[25]);break;
 case 6:b->speed=24;b->timer=30;a->offset=rnd(g,3)-1;break;
 case 8:case 10:b->timer=p[28]+rnd(g,p[29]);if(state==10)b->timer/=2;break;
 case 12:b->speed=8;b->direction=0;b->timer=25+rnd(g,20);break;
 }
}
static void decide(Game *g,int i,float x,float y){EnemyBrain *b=&g->combat.enemy[i];SourceAI *a=&g->rules.ai[i];const unsigned char *p=profile(b);int roll,s;float d=ab(x)+ab(y);++a->decisions;
 if(g->rules.actor[i+1].status89&64){select_state(g,i,12);return;}
 if(d>160){select_state(g,i,6);return;}if(d>120){select_state(g,i,4);return;}
 if(ab(y)<=7 && (rules_flags(g,0)&128)){
  if(!(i&1) && !(g->combat.ticks&2) && d>96){a->mode=0x2e;b->fpg=1;return;}
  if(ab(x)<=50){select_state(g,i,(i&1) && b->level>=5 && g->motion.z[0]!=0?10:8);return;}
 }
 roll=rnd(g,100);for(s=0;s<4;++s){roll-=p[s];if(roll<0)break;}select_state(g,i,s);
}
static void start_attack(Game *g,int i,int upper){EnemyBrain *b=&g->combat.enemy[i];SourceAI *a=&g->rules.ai[i];a->mode=upper==2?0x30:upper?0x1c:0x1a;b->upper=upper;b->frame=0;b->anim_timer=0;b->mask=0;g->enemies[i].attack=1;}
static void animate(Game *g,int i){EnemyBrain *b=&g->combat.enemy[i];SourceAI *a=&g->rules.ai[i];int kind=!(i&1)?EP_JAB:b->upper==2?EP_KICK:b->upper?EP_UPPER:EP_JAB;const EnemyFrame *f=enemy_frames(i,kind);int n=enemy_count(i,kind);
 if(!b->anim_timer){if(b->frame>=n){a->mode=2;g->enemies[i].attack=0;b->fpg=1;return;}b->anim_timer=f[b->frame].ticks;b->mask=0;}
 b->fpg=f[b->frame].fpg;g->pose[i].kind=kind;g->pose[i].fpg=b->fpg;g->pose[i].hurt=f[b->frame].hurt;combat_enemy_attack_frame(g,i,f[b->frame].collision,f[b->frame].damage);if(!--b->anim_timer){if(++b->frame>=n){a->mode=2;g->enemies[i].attack=0;b->fpg=1;}}
}
static void move(Game *g,int i,int direction){static const int vx[]={0,1,1,1,0,-1,-1,-1},vy[]={-1,-1,0,1,1,1,0,-1};Actor *e=&g->enemies[i];EnemyBrain *b=&g->combat.enemy[i];SourceAI *a=&g->rules.ai[i];float x=e->x+vx[direction]*b->speed/32.f,y=e->y+vy[direction]*b->speed/(16*.76f);
 /* Flat arena adapter for Chk_Boundary: probes retain source asymmetric X reach. */
 float probe=x+(vx[direction]>0?10:vx[direction]<0?-5:0),py=y+vy[direction]*g->rules.actor[i+1].depth/.76f;
 a->blocked=probe<10 || probe>230 || py<76 || py>126;
 if(a->blocked){b->state=0;b->timer=0;b->fpg=1;return;}e->x=x;e->y=y;b->direction=direction;b->fpg=1+(g->combat.ticks/8)%3;
}
static void source_ai_step(Game *g,int i){EnemyBrain *b=&g->combat.enemy[i];SourceAI *a=&g->rules.ai[i];Actor *e=&g->enemies[i];const unsigned char *p=profile(b);float x,y,d;int direction,s;
 if(e->cooldown>0)--e->cooldown;
 if(g->combat.target==i){
  if(g->physics.body[i+1].phase==BODY_HURT)physics_body_tick(g,i+1);
  else {if(g->physics.body[i+1].inv)--g->physics.body[i+1].inv;b->fpg=7;}
  return;
 }
 if(g->physics.body[i+1].phase){physics_body_tick(g,i+1);return;}
 if(g->physics.body[i+1].inv)--g->physics.body[i+1].inv;
 if(e->hp<=0){b->fpg=9;return;}if(e->stun){--e->stun;b->fpg=7;return;}
 if(g->impact.freeze[i+1]>0){--g->impact.freeze[i+1];return;}
 if(attack_mode(a->mode)){animate(g,i);return;}
 if(a->mode==0x2e){a->mode=2;b->fpg=1;return;}
 e->attack=0;x=(g->player.x-e->x)*2;y=(g->player.y-e->y)*.76f;d=ab(x)+ab(y);
 a->target=(rules_flags(g,0)&128)?0:-1;a->cache=(a->cache+1)%30;a->active=a->target==0;
 if(!(g->combat.ticks&7)){e->facing=x>=0?1:-1;++a->face_ticks;}
 if(a->active && d<24)select_state(g,i,5);
 if(!a->active){if(b->state!=0 && b->state!=1){select_state(g,i,rnd(g,256)<160?0:1);}if(--b->timer<0)select_state(g,i,rnd(g,256)<160?0:1);if(b->state==1)move(g,i,b->direction&7);else b->fpg=1;return;}
 s=b->state;if(s<0 || s>12)s=b->state=7;a->visited|=1u<<s;a->previous=s;
 if(s==7){decide(g,i,x,y);return;}
 if(s>=8 && s<=11){
  if(ab(y)>7 || (s==8 && ab(x)>50) || (s==9 && ab(x)>40)){decide(g,i,x,y);return;}
  b->fpg=1;if(--b->timer>=0)return;
  if(s==8){b->state=9;b->timer=p[28]+rnd(g,p[29]);start_attack(g,i,0);}
  else if(s==9){if(i&1){b->state=(bk3_random32(g)&3)?10:11;b->timer=p[28]+rnd(g,p[29]);}else{b->state=7;b->timer=0;}start_attack(g,i,0);}
  else{b->state=7;b->timer=0;start_attack(g,i,s==11?2:1);}return;
 }
 if(s>=1 && s<=4 && ab(x)<=50 && ab(y)<=7){select_state(g,i,8);return;}
 if(!s){b->fpg=1;if(--b->timer<0)decide(g,i,x,y);return;}
 direction=b->direction&7;
 if(s==2)direction=toward(x,y);
 else if(s==3){int desired=a->offset+i*8-20;b->speed=ab(d-desired)<=3?6:p[19];if(d==desired){b->fpg=1;if(--b->timer<0)decide(g,i,x,y);return;}direction=(d>desired)==(x>0)?2:6;}
 else if(s==4)direction=flank_directions[toward(x,y)*2+(a->offset&1)];
 else if(s==5)direction=toward(x,y)^4;
 else if(s==6)direction=(toward(x,y)+a->offset)&7;
 move(g,i,direction);if(--b->timer<0)decide(g,i,x,y);
}
void source_ai_tick(Game *g,int i){float x=g->enemies[i].x,y=g->enemies[i].y;int frozen=g->impact.freeze[i+1]>0;
 source_ai_step(g,i);
 if(g->physics.body[i+1].phase || frozen)return;
 if(attack_mode(g->rules.ai[i].mode))return;
 enemy_pose_tick(g,i,g->combat.target==i?EP_HELD:g->enemies[i].hp<=0?EP_FLOOR:g->enemies[i].stun?EP_HURT:(x!=g->enemies[i].x || y!=g->enemies[i].y)?EP_WALK:EP_IDLE);
 g->combat.enemy[i].fpg=g->pose[i].fpg;
}
int source_ai_selftest(void){Game g;int i,s;unsigned seed;
 game_reset(&g);seed=g.combat.rng;if(bk3_random_range(&g,0) || seed!=g.combat.rng)return 601;
 for(s=0;s<=12;++s){game_reset(&g);g.enemies[0].x=100;g.enemies[0].y=100;g.combat.enemy[0].state=s;g.combat.enemy[0].timer=20;g.combat.enemy[0].speed=8;source_ai_tick(&g,0);if(!(g.rules.ai[0].visited&(1u<<s)))return 602+s;}
 game_reset(&g);g.enemies[0].x=70;g.enemies[0].y=100;source_ai_tick(&g,0);if(g.combat.enemy[0].state!=5)return 615;
 game_reset(&g);g.enemies[0].x=82;g.enemies[0].y=100;g.combat.enemy[0].state=8;g.combat.enemy[0].timer=0;source_ai_tick(&g,0);if(g.combat.enemy[0].state!=9 || g.rules.ai[0].mode!=0x1a)return 616;
 for(i=0;i<16;++i){source_ai_tick(&g,0);}
 if(g.combat.enemy[0].state!=9 || g.rules.ai[0].mode!=2)return 617;
 game_reset(&g);g.enemies[1].x=82;g.enemies[1].y=100;g.combat.enemy[1].state=9;g.combat.enemy[1].timer=0;source_ai_tick(&g,1);if(g.combat.enemy[1].state<10 || g.combat.enemy[1].state>11 || g.rules.ai[1].mode!=0x1a)return 618;
 game_reset(&g);g.enemies[1].x=150;g.enemies[1].y=100;g.combat.enemy[1].state=10;g.combat.enemy[1].timer=0;source_ai_tick(&g,1);if(g.rules.ai[1].mode!=0x1c)return 619;
 game_reset(&g);g.enemies[1].x=150;g.enemies[1].y=100;g.combat.enemy[1].state=11;g.combat.enemy[1].timer=0;source_ai_tick(&g,1);if(g.rules.ai[1].mode!=0x30)return 620;
 game_reset(&g);g.combat.enemy[0].state=7;g.rules.actor[1].status89=64;source_ai_tick(&g,0);if(g.combat.enemy[0].state!=12)return 621;
 game_reset(&g);g.rules.actor[0].enabled=0;g.combat.enemy[0].state=8;source_ai_tick(&g,0);if(g.rules.ai[0].target!=-1 || g.rules.ai[0].mode!=2)return 622;
 game_reset(&g);g.enemies[0].x=150;g.enemies[0].y=125;g.combat.enemy[0].state=7;source_ai_tick(&g,0);if(g.combat.enemy[0].state!=6)return 623;
 game_reset(&g);g.enemies[0].x=10;g.enemies[0].y=100;g.combat.enemy[0].state=1;g.combat.enemy[0].direction=6;source_ai_tick(&g,0);if(!g.rules.ai[0].blocked || g.enemies[0].x!=10)return 624;
 game_reset(&g);g.enemies[0].x=150;g.enemies[0].y=100;g.enemies[0].facing=1;g.combat.ticks=1;source_ai_tick(&g,0);if(g.enemies[0].facing!=1)return 625;
 g.combat.ticks=8;source_ai_tick(&g,0);if(g.enemies[0].facing!=-1)return 626;
 return 0;
}
