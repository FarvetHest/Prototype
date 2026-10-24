#include "game.h"
#include "physics_data.h"
#include <string.h>
static const Actor *actor(const Game *g,int i){return i?&g->enemies[i-1]:&g->player;}
void rules_reset(Game *g){int i;memset(&g->rules,0,sizeof(g->rules));
 for(i=0;i<5;++i){ActorRules *r=&g->rules.actor[i];r->type=i?(i%2?14:16):6;r->status58=128;r->depth=8;r->gripper=r->held=-1;r->enabled=1;}
 for(i=0;i<4;++i){g->rules.ai[i].mode=2;g->rules.ai[i].target=-1;}
}
unsigned rules_flags(const Game *g,int i){unsigned f=g->rules.actor[i].status58;int phase=g->physics.body[i].phase;
 if(!g->rules.actor[i].enabled || actor(g,i)->hp<=0 || phase==BODY_FLIGHT || phase==BODY_BOUNCE || phase==BODY_GETUP || phase==BODY_VICTIM)f&=~128u;
 if(!i && ((g->moves.special && (player_character!=PLAYER_MAX || g->max.mode==MX_NEUTRAL)) || g->moves.roll || (g->combat.action==CB_VAULT && player_character!=PLAYER_MAX)))f&=~128u;
 return f;
}
int rules_depth_overlap(const Game *g,int a,int b){int y1=(int)(actor(g,a)->y*.76f),y2=(int)(actor(g,b)->y*.76f);int gap=y1-y2;if(gap<0)gap=-gap;
 return gap<=g->rules.actor[a].depth+g->rules.actor[b].depth;
}
int rules_can_grab(const Game *g,int a,int b,int moving){const ActorRules *r=&g->rules.actor[b];float box[4],x=actor(g,a)->x*2;unsigned flags=rules_flags(g,b);
 /* Chk_CharacterGrab_Move: movement, 5C, 58 bits 7/4/5, z, viewport, body X. */
 if(!moving || a==b || r->type==20 || r->type==52 || g->physics.body[b].inv || !(flags&128) || (flags&48) || r->gripper>=0 || r->held>=0 || g->motion.z[b]!=0)return 0;
 if(actor(g,a)->hp<=0 || !(rules_flags(g,a)&128) || actor(g,a)->x*2<0 || actor(g,a)->x*2>480 || x<0 || x>480 || actor(g,b)->x*2<0 || actor(g,b)->x*2>480)return 0;
 if(!rules_depth_overlap(g,a,b) || !physics_rect(g,b,box))return 0;
 return x>=box[0] && x<=box[1];
}
void rules_begin_hold(Game *g,int target){ActorRules *p=&g->rules.actor[0],*e=&g->rules.actor[target+1];
 g->extra[target].action=0;g->extra[target].z=g->extra[target].vz=g->extra[target].vx=0;
 p->status58|=32;e->status58|=16;p->held=target+1;e->gripper=0;
 g->physics.body[target+1].phase=0;g->physics.body[target+1].freeze=0;g->enemies[target].stun=0;
 g->rules.ai[target].mode=g->combat.back?14:12;
}
void rules_end_hold(Game *g){int i=g->rules.actor[0].held;g->rules.actor[0].held=-1;g->rules.actor[0].status58&=~32;
 if(i>0 && i<=4){ActorRules *r=&g->rules.actor[i];r->status58&=~16;r->gripper=-1;
  if(g->rules.ai[i-1].mode==12 || g->rules.ai[i-1].mode==14){g->rules.ai[i-1].mode=2;g->combat.enemy[i-1].state=0;g->combat.enemy[i-1].timer=0;}
 }
}
int rules_hold_valid(const Game *g){int i=g->combat.target+1;
 return i>=1 && i<=4 && g->rules.actor[0].held==i && g->rules.actor[i].gripper==0 && (g->rules.actor[i].status58&16) && g->enemies[i-1].hp>0 && g->rules.actor[i].enabled;
}
int rules_recovery_inv(const Game *g,int i){return i?((g->rules.actor[i].statusde&8)?30:0):(g->rules.pvp?30:60);}
int rules_selftest(void){Game g;int i;
 game_reset(&g);g.enemies[0].x=64;g.enemies[0].y=100;
 if(rules_can_grab(&g,0,1,0) || !rules_can_grab(&g,0,1,1))return 501;
 for(i=0;i<3;++i){game_reset(&g);g.enemies[0].x=64;g.enemies[0].y=100;g.rules.actor[1].status58=i==0?0:i==1?144:160;if(rules_can_grab(&g,0,1,1))return 502+i;}
 game_reset(&g);g.enemies[0].x=64;g.enemies[0].y=100;g.physics.body[1].inv=1;if(rules_can_grab(&g,0,1,1))return 505;
 g.physics.body[1].inv=0;g.motion.z[1]=1;if(rules_can_grab(&g,0,1,1))return 506;
 g.motion.z[1]=0;g.enemies[0].y=121;if(!rules_can_grab(&g,0,1,1))return 507;
 g.enemies[0].y=123;if(rules_can_grab(&g,0,1,1))return 508;
 game_reset(&g);g.rules.actor[1].type=20;g.enemies[0].x=64;g.enemies[0].y=100;if(rules_can_grab(&g,0,1,1))return 509;
 game_reset(&g);g.combat.target=0;rules_begin_hold(&g,0);if(!rules_hold_valid(&g))return 510;
 g.rules.actor[1].status58&=~16;if(rules_hold_valid(&g))return 511;
 rules_end_hold(&g);if(g.rules.actor[0].held!=-1 || g.rules.actor[1].gripper!=-1)return 512;
 if(rules_recovery_inv(&g,1))return 513;
 g.rules.actor[1].statusde=8;if(rules_recovery_inv(&g,1)!=30)return 514;
 if(rules_recovery_inv(&g,0)!=60)return 515;
 g.rules.pvp=1;if(rules_recovery_inv(&g,0)!=30)return 516;
 return 0;
}
