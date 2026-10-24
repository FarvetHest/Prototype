/* CE decisions and object animation are distinct registers in BK3. */
#include "game.h"
#include "level.h"
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
  if(enemy_type(g,i)==EN_GALSIA && !(g->combat.ticks&2) && d>96){a->mode=0x2e;b->fpg=1;return;}
  if(ab(x)<=50){select_state(g,i,(enemy_type(g,i)==EN_DONOVAN) && b->level>=5 && g->motion.z[0]!=0?10:8);return;}
 }
 roll=rnd(g,100);for(s=0;s<4;++s){roll-=p[s];if(roll<0)break;}select_state(g,i,s);
}
static void start_attack(Game *g,int i,int upper){EnemyBrain *b=&g->combat.enemy[i];SourceAI *a=&g->rules.ai[i];a->mode=upper==2?0x30:upper?0x1c:0x1a;b->upper=upper;b->frame=0;b->anim_timer=0;b->mask=0;g->enemies[i].attack=1;}
static void animate(Game *g,int i){EnemyBrain *b=&g->combat.enemy[i];SourceAI *a=&g->rules.ai[i];int kind=enemy_type(g,i)==EN_GALSIA?EP_JAB:b->upper==2?EP_KICK:b->upper?EP_UPPER:EP_JAB;const EnemyFrame *f=enemy_frames(g,i,kind);int n=enemy_count(g,i,kind);
 if(!b->anim_timer){if(b->frame>=n){a->mode=2;g->enemies[i].attack=0;b->fpg=1;return;}b->anim_timer=f[b->frame].ticks;b->mask=0;}
 b->fpg=f[b->frame].fpg;g->pose[i].kind=kind;g->pose[i].fpg=b->fpg;g->pose[i].hurt=f[b->frame].hurt;combat_enemy_attack_frame(g,i,f[b->frame].collision,f[b->frame].damage);if(!--b->anim_timer){if(++b->frame>=n){a->mode=2;g->enemies[i].attack=0;b->fpg=1;}}
}
static void move(Game *g,int i,int direction){static const int vx[]={0,1,1,1,0,-1,-1,-1},vy[]={-1,-1,0,1,1,1,0,-1};Actor *e=&g->enemies[i];EnemyBrain *b=&g->combat.enemy[i];SourceAI *a=&g->rules.ai[i];float x=e->x+vx[direction]*b->speed/32.f,y=e->y+vy[direction]*b->speed/(16*.76f);
 /* Flat arena adapter for Chk_Boundary: probes retain source asymmetric X reach. */
 float probe=x+(vx[direction]>0?10:vx[direction]<0?-5:0),py=y+vy[direction]*g->rules.actor[i+1].depth/.76f;
 a->blocked=probe<10 || probe>230 || py<76 || py>126;
 if(a->blocked){b->state=0;b->timer=0;b->fpg=1;return;}e->x=x;e->y=y;b->direction=direction;b->fpg=1+(g->combat.ticks/8)%3;
}
/* Lite captain uses existing Donovan poses, hit boxes and interruptible bodies.
   Telegraph/dash/recovery are deliberately local boss design, not a BK3 boss port. */
static void boss_step(Game *g,int i){EnemyBrain *b=&g->combat.enemy[i];Actor *e=&g->enemies[i];
 float x=g->player.x-e->x,y=g->player.y-e->y;int rage=e->hp<=LEVEL_BOSS_HP/2;
 if(!(rules_flags(g,0)&128)){level.boss_phase=BOSS_APPROACH;level.boss_timer=15;b->fpg=1;return;}
 if(level.boss_phase==BOSS_RECOVER){b->fpg=1;if(--level.boss_timer<=0)level.boss_phase=BOSS_APPROACH;return;}
 if(level.boss_phase==BOSS_WINDUP){
  b->fpg=1;if(--level.boss_timer>0)return;
  if(level.boss_move==1){level.boss_phase=BOSS_DASH;level.boss_timer=42;++level.boss_rushes;return;}
  level.boss_phase=BOSS_RECOVER;level.boss_timer=rage?24:36;
  start_attack(g,i,level.boss_move==2?1:0);++level.boss_attacks;return;
 }
 if(level.boss_phase==BOSS_DASH){
  e->facing=level.boss_dir;
  if((x*level.boss_dir>=-4 && x*level.boss_dir<=24 && ab(y)<=9)){
   level.boss_phase=BOSS_RECOVER;level.boss_timer=rage?30:45;start_attack(g,i,2);++level.boss_attacks;return;
  }
  b->speed=rage?64:48;move(g,i,level.boss_dir>0?2:6);
  if(--level.boss_timer<=0 || g->rules.ai[i].blocked){level.boss_phase=BOSS_RECOVER;level.boss_timer=30;}
  return;
 }
 e->facing=x>=0?1:-1;
 if(level.boss_timer>0)--level.boss_timer;
 if(!level.boss_timer && ab(y)<=8 && ab(x)<=90){
  level.boss_move=g->motion.z[0]>0?2:ab(x)>32 || (level.boss_attacks&1)?1:0;
  level.boss_dir=e->facing;level.boss_phase=BOSS_WINDUP;level.boss_timer=rage?14:24;b->fpg=1;return;
 }
 b->speed=rage?22:16;move(g,i,toward(x*2,y*.76f));
}
static void source_ai_step(Game *g,int i){EnemyBrain *b=&g->combat.enemy[i];SourceAI *a=&g->rules.ai[i];Actor *e=&g->enemies[i];const unsigned char *p=profile(b);float x,y,d;int direction,s;
 if(e->cooldown>0)--e->cooldown;
 /* Walking in from off-screen: untouchable, outside the arena clamp, no decisions yet. */
 if(level_entering(g,i))return;
 if(level_is_boss(i) && (g->combat.target==i || g->physics.body[i+1].phase || e->stun)){
  level.boss_phase=BOSS_RECOVER;level.boss_timer=30;e->attack=0;
 }
 if(g->combat.target==i){
  if(g->physics.body[i+1].phase==BODY_HURT)physics_body_tick(g,i+1);
  else {if(!bk3_machine_stats.dispatching && g->physics.body[i+1].inv)--g->physics.body[i+1].inv;b->fpg=7;}
  return;
 }
 if(g->physics.body[i+1].phase){physics_body_tick(g,i+1);return;}
 if(!bk3_machine_stats.dispatching && g->physics.body[i+1].inv)--g->physics.body[i+1].inv;
 if(e->hp<=0){b->fpg=9;return;}if(e->stun){--e->stun;b->fpg=7;return;}
 if(g->impact.freeze[i+1]>0){--g->impact.freeze[i+1];return;}
 if(enemy_type(g,i)>=EN_ELECTRA){variety_tick(g,i);return;}
 if(attack_mode(a->mode)){animate(g,i);return;}
 if(level_is_boss(i)){e->attack=0;boss_step(g,i);return;}
 if(a->mode==0x2e){a->mode=2;b->fpg=1;return;}
 e->attack=0;x=(int)(g->player.x*2)-(int)(e->x*2);y=(int)(g->player.y*.76f)-(int)(e->y*.76f);d=ab(x)+ab(y);
 a->active=(rules_flags(g,0)&128)!=0;
 if(--a->cache<0 || !a->active || a->target!=0){a->target=a->active?0:-1;a->cache=a->active?30:0;}
 if(!(g->combat.ticks&7)){e->facing=x>=0?1:-1;++a->face_ticks;}
 if(a->active && d<24)select_state(g,i,5);
 if(!a->active){
  /* loc_268BA: still track an existing, temporarily unhittable player. */
  if(g->player.hp>0 && g->rules.actor[0].enabled){int desired=96+i*8-20;
   a->target=0;a->cache=30;b->timer=2;b->speed=12;
   if(d!=desired){b->direction=(d>desired)==(x>0)?2:6;move(g,i,b->direction);--b->timer;}else b->fpg=1;
   return;
  }
  if((b->state!=0 && b->state!=1) || b->timer==1 || --b->timer<0){
   e->facing=e->x<=120?1:-1;select_state(g,i,((bk3_random_range(g,65536)&255)<160)?0:1);
   if(e->x<0){b->state=1;b->direction=2;}else if(e->x>240){b->state=1;b->direction=6;}
  }
  if(b->state==1)move(g,i,b->direction&7);else b->fpg=1;
  return;
 }
 s=b->state;if(s<0 || s>12)s=b->state=7;a->visited|=1u<<s;a->previous=s;
 if(s==7){decide(g,i,x,y);return;}
 if(s>=8 && s<=11){
  if(ab(y)>7 || (s==8 && ab(x)>50) || (s==9 && ab(x)>40)){decide(g,i,x,y);return;}
  b->fpg=1;if(--b->timer>=0)return;
  if(s==8){b->state=9;b->timer=p[28]+rnd(g,p[29]);start_attack(g,i,0);}
  else if(s==9){if(enemy_type(g,i)==EN_DONOVAN){b->state=(bk3_random32(g)&3)?10:11;b->timer=p[28]+rnd(g,p[29]);}else{b->state=7;b->timer=0;}start_attack(g,i,0);}
  else{b->state=7;b->timer=0;start_attack(g,i,s==11?2:1);}return;
 }
 if(s>=1 && s<=4 && ab(x)<=50 && ab(y)<=7){select_state(g,i,(enemy_type(g,i)==EN_DONOVAN) && b->level>=5 && g->motion.z[0]!=0?10:8);return;}
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
 if(attack_mode(g->rules.ai[i].mode) || (enemy_type(g,i)>=EN_ELECTRA && g->extra[i].action))return;
 enemy_pose_tick(g,i,g->reaction.holder==i?16+g->reaction.side:g->combat.target==i?EP_HELD:g->enemies[i].hp<=0?EP_FLOOR:g->enemies[i].stun?EP_HURT:(x!=g->enemies[i].x || y!=g->enemies[i].y)?EP_WALK:EP_IDLE);
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
 game_reset(&g);g.physics.body[0].phase=BODY_FLIGHT;g.enemies[0].x=144;g.enemies[0].y=100;source_ai_tick(&g,0);if(g.enemies[0].x>=144 || g.rules.ai[0].active || g.rules.ai[0].target!=0 || g.enemies[0].attack)return 627;
 game_reset(&g);g.enemies[0].x=200;g.enemies[0].y=100;source_ai_tick(&g,0);if(g.rules.ai[0].cache!=30)return 628;
 source_ai_tick(&g,0);if(g.rules.ai[0].cache!=29)return 629;
 g.rules.actor[0].enabled=0;source_ai_tick(&g,0);if(g.rules.ai[0].target!=-1)return 630;
 game_reset(&g);g.enemies[0].x=89.49f;g.enemies[0].y=100;g.combat.enemy[0].state=7;source_ai_tick(&g,0);if(g.combat.enemy[0].state!=8)return 631;
 game_reset(&g);g.player.hp=0;g.combat.enemy[0].state=0;g.combat.enemy[0].timer=20;seed=g.combat.rng;source_ai_tick(&g,0);if(g.combat.enemy[0].timer!=19 || g.combat.rng!=seed)return 632;
 game_reset(&g);g.enemies[1].x=82;g.enemies[1].y=100;g.combat.enemy[1].state=2;g.motion.z[0]=20;source_ai_tick(&g,1);if(g.combat.enemy[1].state!=10)return 633;
 game_reset(&g);g.enemies[1].x=82;g.enemies[1].y=100;g.combat.enemy[1].level=4;g.combat.enemy[1].state=2;g.motion.z[0]=20;source_ai_tick(&g,1);if(g.combat.enemy[1].state!=8)return 634;
 game_reset(&g);g.enemies[0].x=82;g.enemies[0].y=100;g.combat.enemy[0].state=2;g.motion.z[0]=20;source_ai_tick(&g,0);if(g.combat.enemy[0].state!=8)return 635;
 /* Attack identity follows ObjID, not the allocator slot parity. */
 game_reset(&g);enemy_set_type(&g,0,EN_DONOVAN);g.enemies[0].x=82;g.enemies[0].y=100;g.combat.enemy[0].state=2;g.motion.z[0]=20;source_ai_tick(&g,0);if(g.combat.enemy[0].state!=10)return 636;
 game_reset(&g);enemy_set_type(&g,1,EN_GALSIA);g.enemies[1].x=82;g.enemies[1].y=100;g.combat.enemy[1].state=2;g.motion.z[0]=20;source_ai_tick(&g,1);if(g.combat.enemy[1].state!=8)return 637;
 game_reset(&g);enemy_set_type(&g,0,EN_DONOVAN);g.rules.ai[0].mode=0x1c;g.combat.enemy[0].upper=1;source_ai_tick(&g,0);if(g.pose[0].kind!=EP_UPPER)return 638;
 game_reset(&g);enemy_set_type(&g,1,EN_GALSIA);g.rules.ai[1].mode=0x1c;g.combat.enemy[1].upper=1;source_ai_tick(&g,1);if(g.pose[1].kind!=EP_JAB)return 639;
 return 0;
}

int level_boss_selftest(void){Level saved=level;Game g;int n,result=0;
#define CHECK(condition,code) do{if(!(condition)){result=code;goto done;}}while(0)
 game_reset(&g);level=(Level){0};level.enabled=1;level.boss=1;g.enemies[1].hp=LEVEL_BOSS_HP;g.enemies[1].x=90;g.enemies[1].y=100;
 source_ai_tick(&g,1);CHECK(level.boss_phase==BOSS_WINDUP && level.boss_move==0 && !g.enemies[1].attack,1301);
 for(n=0;n<23;++n){source_ai_tick(&g,1);}CHECK(!g.enemies[1].attack,1302);
 source_ai_tick(&g,1);CHECK(g.enemies[1].attack && g.rules.ai[1].mode==0x1a,1303);
 for(n=0;n<60;++n){source_ai_tick(&g,1);}CHECK(level.boss_attacks>=1,1304);
 game_reset(&g);g.enemies[1].hp=240;g.enemies[1].x=140;g.enemies[1].y=100;level.boss_phase=0;level.boss_timer=0;
 source_ai_tick(&g,1);CHECK(level.boss_move==1 && level.boss_dir==-1,1305);
 for(n=0;n<24;++n){source_ai_tick(&g,1);}CHECK(level.boss_phase==BOSS_DASH && level.boss_rushes==1,1306);
 for(n=0;n<42 && !g.enemies[1].attack;++n){source_ai_tick(&g,1);}CHECK(g.enemies[1].attack && g.rules.ai[1].mode==0x30,1307);
 g.enemies[1].stun=10;g.rules.ai[1].mode=2;source_ai_tick(&g,1);CHECK(level.boss_phase==BOSS_RECOVER && !g.enemies[1].attack,1308);
 game_reset(&g);g.enemies[1].hp=100;g.enemies[1].x=90;g.enemies[1].y=100;level.boss_phase=0;level.boss_timer=0;g.motion.z[0]=20;
 source_ai_tick(&g,1);CHECK(level.boss_move==2 && level.boss_timer==14,1309);
 for(n=0;n<14;++n){source_ai_tick(&g,1);}CHECK(g.rules.ai[1].mode==0x1c,1310);
 game_reset(&g);g.player.hp=0;level.boss_phase=0;level.boss_timer=0;source_ai_tick(&g,1);CHECK(!g.enemies[1].attack && level.boss_phase==0,1311);
 game_reset(&g);g.enemies[1].x=82;g.enemies[1].y=100;g.enemies[1].hp=240;physics_hit(&g,2,10,0,1);CHECK(g.enemies[1].hp==230 && g.physics.body[2].phase,1312);
 done:if(!result){game_reset(&g);enemy_set_type(&g,1,EN_BARBON);g.enemies[1].x=90;g.enemies[1].y=100;g.combat.enemy[1].state=8;g.combat.enemy[1].timer=0;source_ai_tick(&g,1);if(g.extra[1].action!=EP_JAB || g.combat.enemy[1].state!=9 || enemy_count(&g,1,EP_JAB)!=4 || enemy_frames(&g,1,EP_JAB)[1].ticks!=2)result=1313;}level=saved;return result;
#undef CHECK
}
