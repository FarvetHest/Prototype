/* BK3 RAM and LoadEnemyObj: big endian, six 0x100-byte slots from E100.
   Table destinations call existing translated Lite handlers during migration.
   This is not a 68000 CPU emulator; hardware I/O is deliberately not RAM. */
#include "game.h"
#include "machine.h"
#include "machine_data.h"
#include "level.h"
#include <string.h>

unsigned char bk3_work_ram[65536] __attribute__((aligned(16)));
Bk3MachineStats bk3_machine_stats;
static Game *owner;
static unsigned char shadow[5][256];
static unsigned addresses[5];
static int seeded;
static int offset(uint32_t address,unsigned size){
 unsigned a=address&0xffffffu;
 if(a<0xff0000u || a>0x1000000u-size || (size>1 && (a&1))){++bk3_machine_stats.faults;return -1;}
 return (int)(a-0xff0000u);
}
uint8_t bk3_ram8(uint32_t a){int p=offset(a,1);return p<0?0:bk3_work_ram[p];}
uint16_t bk3_ram16(uint32_t a){int p=offset(a,2);return p<0?0:(unsigned)bk3_work_ram[p]*256+bk3_work_ram[p+1];}
uint32_t bk3_ram32(uint32_t a){int p=offset(a,4);return p<0?0:((uint32_t)bk3_work_ram[p]<<24)|((uint32_t)bk3_work_ram[p+1]<<16)|((uint32_t)bk3_work_ram[p+2]<<8)|bk3_work_ram[p+3];}
int bk3_put8(uint32_t a,uint8_t v){int p=offset(a,1);if(p<0)return 0;bk3_work_ram[p]=v;return 1;}
int bk3_put16(uint32_t a,uint16_t v){int p=offset(a,2);if(p<0)return 0;bk3_work_ram[p]=v>>8;bk3_work_ram[p+1]=v;return 1;}
int bk3_put32(uint32_t a,uint32_t v){int p=offset(a,4);if(p<0)return 0;bk3_work_ram[p]=v>>24;bk3_work_ram[p+1]=v>>16;bk3_work_ram[p+2]=v>>8;bk3_work_ram[p+3]=v;return 1;}
uint32_t bk3_sst_address(int i){return i==0?0xffdf00u:i>0 && i<=4?(level_is_boss(i-1)?0xffe100u:0xffe200u+(i-1)*256):0;}
#define FIND(table) for(n=0;n<sizeof(table)/sizeof(table[0]);++n)if(table[n].mode==mode)return table[n].label
const char *bk3_state_label(unsigned id,unsigned mode){unsigned n;
 /* 0x100 is a Lite extension: SoR2 Barbon adapted to BK3 bank, never BK3 Garcia ID 0x0E. */
 if(id==0x100){FIND(bk3_states_garcia);}
 if(id==6){FIND(bk3_states_axel);}
 if(id==0x0e || id==0x10){FIND(bk3_states_garcia);}
 if(id==0x1c){FIND(bk3_states_electra);}
 if(id==0x1e){FIND(bk3_states_zack);}
 if(id==0x20){FIND(bk3_states_blondie);}
 return 0;
}
#undef FIND
static Actor *actor(Game *g,int i){return i?&g->enemies[i-1]:&g->player;}
static int mapped_type(unsigned id){return id==0xe?EN_GALSIA:id==0x10?EN_DONOVAN:id==0x1c?EN_ELECTRA:id==0x1e?EN_ZACK:id==0x100?EN_BARBON:-1;}
static unsigned mode(Game *g,int i){Body *b=&g->physics.body[i];int action=g->combat.action;
 if(i && death_fx[i-1].active==2 && !death_visible(g,i-1))return 0;
 if(i && death_pending(g,i-1) && !b->phase)return 8;
 if(b->phase==BODY_HURT)return 4;
 if(b->phase==BODY_VICTIM)return b->back?0x12:0x10;
 if(b->phase)return 0xa;
 if(actor(g,i)->hp<=0)return 6;
 if(!i){
  if(g->reaction.holder>=0)return g->reaction.side?0xe:0xc;
  switch(action){case CB_HOLD:return g->combat.back?0x1c:0x1a;case CB_FRONTTHROW:return 0x1e;case CB_BACKTHROW:return 0x20;case CB_VAULT:return 0x22;case CB_NEUTRAL:return 0x24;case CB_FORWARD:return 0x26;case CB_ROLL_DOWN:case CB_ROLL_UP:return 0x42;case CB_NONE:break;default:return 0x1a;}
  if(g->bk3.mode==1 && g->bk3.script==BK_BLITZ)return 0x32;
  if(g->player.jump)return 0x18;
  if(g->player.attack)return 0x14;
  if(level.pickup_timer && level.enabled)return 0x2c;
  return 2;
 }
 if(g->combat.target==i-1)return g->combat.back?0xe:0xc;
 if(g->reaction.holder==i-1)return g->reaction.side?0x1c:0x1a;
 if(enemy_type(g,i-1)>=EN_ELECTRA){int a=g->extra[i-1].action;
  if(a==EP_JAB || a==15)return 0x16;
  if(a==EP_UPPER)return 0x18;
  if(a==EP_KICK)return 0x1a;
  return 2;
 }
 return g->rules.ai[i-1].mode;
}
/* Explicit field bridge: byte/word/long widths, never a host struct overlay.
   Unported fields remain untouched in the original RAM bank. */
static const unsigned char fields[][2]={{0,2},{0xc,2},{0xf,1},{0x16,2},{0x18,2},{0x1e,1},{0x68,2},{0x40,4},{0x44,4},{0x58,1},{0x5a,1},{0x5b,1},{0x5c,2},{0x5e,2},{0x60,2},{0x6c,1},{0x89,1},{0xb0,1},{0xb1,1},{0xb6,2},{0xde,1}};
static void word(unsigned char *p,unsigned o,unsigned v){p[o]=v>>8;p[o+1]=v;}
static void lng(unsigned char *p,unsigned o,unsigned v){p[o]=v>>24;p[o+1]=v>>16;p[o+2]=v>>8;p[o+3]=v;}
static unsigned link(int i){return i>=0 && i<5?bk3_sst_address(i)&65535:0;}
static int unlink(unsigned a){int i;for(i=0;i<5;++i)if(link(i)==a)return i;return -1;}
static void image(Game *g,int i,unsigned char p[256],int buttons,int edges){Actor *a=actor(g,i);ActorRules *r=&g->rules.actor[i];
 static const unsigned ids[]={0xe,0x10,0x1c,0x1e,0x100};unsigned id=i?ids[enemy_type(g,i-1)]:6;
 memset(p,0,256);word(p,0,mode(g,i));word(p,0xc,id);p[0xf]=a->facing<0?1:0;
 word(p,0x16,i?g->combat.enemy[i-1].anim_timer:g->bk3.timer);word(p,0x18,i?g->combat.enemy[i-1].fpg:g->bk3.fpg);
 lng(p,0x40,(uint32_t)(int32_t)(a->x*131072.f));lng(p,0x44,(uint32_t)(int32_t)(a->y*.76f*65536.f));
 p[0x58]=r->status58;p[0x5a]=r->status5a;p[0x5b]=r->status5b;p[0x89]=r->status89;p[0xde]=r->statusde;
 word(p,0x5c,g->physics.body[i].inv);word(p,0x5e,link(r->held));word(p,0x60,link(r->gripper));
 p[0x6c]=a->hp<0?0:a->hp>255?255:a->hp;word(p,0xb6,r->hold_timer);
 if(i && death_pending(g,i-1)){word(p,0x68,death_fx[i-1].timer<0?0:death_fx[i-1].timer);p[0x1e]=death_visible(g,i-1)?0:16;}
 if(!i){p[0xb0]=buttons;p[0xb1]=edges;}
}
static void publish(Game *g,int i,int buttons,int edges,int reconcile){unsigned char data[256];unsigned k;unsigned a=bk3_sst_address(i),off=a&65535;
 image(g,i,data,buttons,edges);
 if(addresses[i] && addresses[i]!=a){memset(bk3_work_ram+(addresses[i]&65535),0,256);memset(shadow[i],0,256);}
 for(k=0;k<sizeof(fields)/sizeof(fields[0]);++k){unsigned f=fields[k][0],n=fields[k][1];
  if(!reconcile || !seeded || addresses[i]!=a || memcmp(data+f,shadow[i]+f,n))memcpy(bk3_work_ram+off+f,data+f,n);
 }
 memcpy(shadow[i],data,256);addresses[i]=a;
}
static void pull(Game *g,int i){unsigned a=bk3_sst_address(i),id=bk3_ram16(a+0xc);Actor *p=actor(g,i);ActorRules *r=&g->rules.actor[i];
 p->x=(int32_t)bk3_ram32(a+0x40)/131072.f;p->y=(int32_t)bk3_ram32(a+0x44)/(.76f*65536.f);
 p->hp=bk3_ram8(a+0x6c);p->facing=(bk3_ram8(a+0xf)&1)?-1:1;
 r->status58=bk3_ram8(a+0x58);r->status5a=bk3_ram8(a+0x5a);r->status5b=bk3_ram8(a+0x5b);r->status89=bk3_ram8(a+0x89);r->statusde=bk3_ram8(a+0xde);
 r->hold_timer=bk3_ram16(a+0xb6);r->held=unlink(bk3_ram16(a+0x5e));r->gripper=unlink(bk3_ram16(a+0x60));g->physics.body[i].inv=bk3_ram16(a+0x5c);
 if(i){int type=mapped_type(id);
  if(type>=0 && type!=enemy_type(g,i-1))enemy_set_type(g,i-1,type);
 }
}
void bk3_machine_reset(Game *g){if(owner==g){owner=0;seeded=0;}}
static void bind(Game *g){if(owner==g)return;memset(bk3_work_ram,0,sizeof(bk3_work_ram));memset(shadow,0,sizeof(shadow));memset(addresses,0,sizeof(addresses));memset(&bk3_machine_stats,0,sizeof(bk3_machine_stats));owner=g;seeded=0;}
void bk3_machine_step(Game *g,float x,float y,int attack,int jump,int special){int i,s,buttons=(y<-.5f?1:y>.5f?2:0)|(x<-.5f?4:x>.5f?8:0)|(attack?16:0)|(jump?32:0)|(special?64:0),edges=(attack==1?16:0)|(jump?32:0)|(special?64:0);unsigned a,m,id;
 bind(g);for(i=0;i<5;++i)publish(g,i,buttons,edges,1);seeded=1;
 bk3_put8(BK3_PauseFlag,g->paused);bk3_put32(BK3_XCam,(unsigned)(level.camera*65536.f));bk3_put16(BK3_Max_Enemy,4);
 ++bk3_machine_stats.ticks;bk3_machine_stats.count=0;
 /* Pull all live fields before the player can hit another actor. */
 for(i=0;i<5;++i)pull(g,i);
 a=bk3_sst_address(0);m=bk3_ram16(a);id=bk3_ram16(a+0xc);
 if(m && id==6 && bk3_state_label(id,m&0xfffeu)){
  bk3_machine_stats.order[bk3_machine_stats.count++]=a;bk3_machine_stats.last_mode[0]=m&0xfffeu;++bk3_machine_stats.state_calls[0];
  /* Update_CharacterObj masks odd mode bit before relative word lookup. */
  bk3_machine_stats.dispatching=1;combat_tick(g,x,y,attack>=2?attack:((bk3_ram8(a+0xb1)&16)?1:0),(bk3_ram8(a+0xb1)&32)!=0,(bk3_ram8(a+0xb1)&64)!=0);bk3_machine_stats.dispatching=0;
 }else if(m)++bk3_machine_stats.faults;else ++bk3_machine_stats.skipped;
 /* Player damage/holds are committed before any enemy is dispatched. */
 for(i=0;i<5;++i)publish(g,i,buttons,edges,1);
 for(s=0;s<6;++s){a=0xffe100u+s*256u;m=bk3_ram16(a);if(!m){++bk3_machine_stats.skipped;continue;}
  id=bk3_ram16(a+0xc);i=-1;for(int j=1;j<5;++j)if(bk3_sst_address(j)==a)i=j;
  if(i<0 || mapped_type(id)<0 || (m&1) || !bk3_state_label(id,m)){++bk3_machine_stats.faults;continue;}
  bk3_machine_stats.order[bk3_machine_stats.count++]=a;bk3_machine_stats.last_mode[i]=m;++bk3_machine_stats.state_calls[i];
  /* LoadEnemyObj decrements word 5C before the object's handler. */
  if(g->physics.body[i].inv)--g->physics.body[i].inv;
  bk3_machine_stats.dispatching=1;source_ai_tick(g,i-1);bk3_machine_stats.dispatching=0;++bk3_machine_stats.calls;
  for(int j=0;j<5;++j)publish(g,j,buttons,edges,1);
 }
 death_tick(g);for(i=0;i<5;++i)publish(g,i,buttons,edges,1);
}
int bk3_machine_selftest(void){Game g;unsigned f;int hp;
 game_reset(&g);level.enabled=0;bind(&g);
 if(!bk3_put32(0xffff9000u,0x89abcdefu) || bk3_work_ram[0x9000]!=0x89 || bk3_ram32(0xff9000)!=0x89abcdefu)return 1801;
 bk3_put16(0xff9000,0xfffe);if((int16_t)bk3_ram16(0xff9000)!=-2 || bk3_ram8(0xff9001)!=0xfe)return 1802;
 f=bk3_machine_stats.faults;if(bk3_put16(0xff9001,1) || bk3_put32(0xfffffe,1) || bk3_put8(0xc00000,1) || bk3_machine_stats.faults!=f+3)return 1803;
 if(!bk3_state_label(0x1e,0x1a) || strcmp(bk3_state_label(0x1e,0x1a),"sub_2C80E"))return 1804;
 if(bk3_state_label(6,0x3a) || bk3_state_label(0x1e,3))return 1805;
 game_reset(&g);bk3_machine_step(&g,0,0,0,0,0);
 if(bk3_machine_stats.count!=5 || bk3_machine_stats.order[0]!=0xffdf00 || bk3_machine_stats.order[1]!=0xffe200 || bk3_machine_stats.order[4]!=0xffe500)return 1806;
 bk3_put16(0xffe200,0);f=bk3_machine_stats.state_calls[1];bk3_machine_step(&g,0,0,0,0,0);if(bk3_machine_stats.state_calls[1]!=f)return 1807;
 bk3_put16(0xffe200,2);bk3_put8(0xffe26c,23);bk3_machine_step(&g,0,0,0,0,0);if(g.enemies[0].hp!=23)return 1808;
 bk3_put16(0xffe25c,9);bk3_machine_step(&g,0,0,0,0,0);if(g.physics.body[1].inv!=8)return 1809;
 hp=g.enemies[0].hp;g.enemies[0].hp=hp-2;bk3_machine_step(&g,0,0,0,0,0);if(bk3_ram8(0xffe26c)!=hp-2)return 1810;
 bk3_put16(0xffe20c,0xffff);f=bk3_machine_stats.faults;bk3_machine_step(&g,0,0,0,0,0);if(bk3_machine_stats.faults!=f+1)return 1811;
 game_reset(&g);bk3_machine_step(&g,0,0,3,0,0);if(g.bk3.script!=BK_DOUBLEKICK || g.bk3.mode!=1)return 1812;
 game_reset(&g);enemy_set_type(&g,0,EN_ELECTRA);bk3_machine_step(&g,0,0,0,0,0);bk3_put16(0xffe20c,0xffff);f=bk3_machine_stats.state_calls[1];bk3_machine_step(&g,0,0,0,0,0);if(enemy_type(&g,0)!=EN_ELECTRA || bk3_machine_stats.state_calls[1]!=f)return 1813;
 owner=0;seeded=0;return 0;
}
