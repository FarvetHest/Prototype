/* Zack hold timers from sub_2C6D6/2C80E/2C8BA/2C91A.
   Guard/counter are an explicit Obj_Blondie adaptation, not Obj_Zack code. */
#include "game.h"
#include "sfx.h"
static float ab(float x){return x<0?-x:x;}
void reaction_release(Game *g){int i=g->reaction.holder;
 if(i>=0 && i<4){g->rules.actor[i+1].status58&=~32;g->rules.actor[i+1].held=-1;
  g->extra[i].action=0;g->enemies[i].attack=0;g->combat.enemy[i].state=7;g->rules.ai[i].mode=2;
 }
 g->rules.actor[0].status58&=~16;g->rules.actor[0].gripper=-1;g->reaction.holder=-1;g->reaction.hold_timer=0;g->reaction.hold_cooldown=60;
 if(!g->physics.body[0].phase)g->player.stun=0;
}
int reaction_capture(Game *g,int i){Actor *e=&g->enemies[i];Reactions *r=&g->reaction;
 if(enemy_type(g,i)!=EN_ZACK || r->holder>=0 || r->hold_cooldown || g->player.hp<=0 || e->hp<=0 || g->combat.action!=CB_NONE || g->player.attack || g->player.stun || g->player.jump || g->motion.z[0] || g->physics.body[0].phase || g->moves.invincible || g->physics.body[0].inv || !(rules_flags(g,0)&128) || (g->rules.actor[0].status58&48) || g->rules.actor[i+1].gripper>=0)return 0;
 if(ab((g->player.y-e->y)*.76f)>7 || ab((g->player.x-e->x)*2)+ab((g->player.y-e->y)*.76f)>=30)return 0;
 r->holder=i;r->side=g->player.facing==e->facing;
 e->x=g->player.x-e->facing*(r->side?8:12);if(e->x<10)e->x=10;if(e->x>230)e->x=230;e->y=g->player.y+1/.76f;r->hold_timer=r->side?60:120;r->strike_wait=14;
 g->rules.actor[0].status58|=16;g->rules.actor[0].gripper=i+1;g->rules.actor[i+1].status58|=32;g->rules.actor[i+1].held=0;
 g->player.stun=1;g->player.attack=0;g->moves.run_dir=0;bk3_suspend(g);++r->captures;return 1;
}
int reaction_player_tick(Game *g,int jump,int special){Reactions *r=&g->reaction;int i=r->holder;
 if(r->hold_cooldown)--r->hold_cooldown;
 if(r->shock){
  if(g->physics.body[0].phase!=BODY_FLIGHT || g->moves.special)r->shock=0;
  else if(--r->shock_timer<=0){r->shock_frame^=1;r->shock_timer=4;}
 }
 if(i<0)return 0;
 if(i>=4 || g->player.hp<=0 || g->enemies[i].hp<=0 || g->physics.body[i+1].phase || g->enemies[i].stun || !(g->rules.actor[0].status58&16) || g->rules.actor[0].gripper!=i+1 || --r->hold_timer<=0){reaction_release(g);return 0;}
 if(special){reaction_release(g);return 0;}
 if(jump && r->side){
  reaction_release(g);g->combat.action=CB_HOLD;g->combat.target=i;g->combat.back=0;g->moves.grab=i;rules_begin_hold(g,i);return 0;
 }
 g->player.stun=1;g->player.x=g->enemies[i].x+g->enemies[i].facing*(r->side?8:12);if(g->player.x<10)g->player.x=10;if(g->player.x>230)g->player.x=230;
 g->player.y=g->enemies[i].y-1/.76f;g->player.facing=r->side?g->enemies[i].facing:-g->enemies[i].facing;
 if(!r->side && !g->extra[i].action && --r->strike_wait<=0){
  g->extra[i].action=EP_KICK;g->extra[i].frame=g->extra[i].timer=0;g->combat.enemy[i].mask=0;g->rules.ai[i].mode=0x4c;g->enemies[i].attack=1;r->strike_wait=g->combat.enemy[i].level+1;
 }
 return 1;
}
void reaction_hit(Game *g,int from,int to,int encoded){Reactions *r=&g->reaction;
 if(to && r->holder==to-1)reaction_release(g);
 if(!to){
  if(r->holder>=0){
   if(from==r->holder+1 && !(encoded&128) && g->player.hp>0){g->physics.body[0].phase=0;g->player.stun=1;}
   else reaction_release(g);
  }
  r->shock=0;
  if(from>0 && enemy_type(g,from-1)==EN_ELECTRA && g->extra[from-1].action==EP_UPPER && g->physics.body[0].phase==BODY_FLIGHT){r->shock=1;r->shock_frame=0;r->shock_timer=4;++r->shocks;}
 }
}
int reaction_block(Game *g,int from,int to){int i=to-1,l;EnemyExtra *v;Actor *e;Reactions *r=&g->reaction;
 static const unsigned char chance[11]={2,3,4,5,6,7,8,9,10,15,20};
 static const unsigned char counter[11]={0,5,10,20,30,30,35,40,45,45,50};
 if(g->combat.action==CB_NEUTRAL)return 0;
 if(from || to<1 || to>4 || enemy_type(g,i)!=EN_ZACK || r->holder>=0 || g->combat.target==i || g->physics.body[to].phase || g->motion.z[to] || g->enemies[i].stun)return 0;
 e=&g->enemies[i];v=&g->extra[i];l=g->combat.enemy[i].level;if(l<0)l=0;if(l>10)l=10;
 if((g->player.x-e->x)*e->facing<0 || ab((g->player.y-e->y)*.76f)>7 || ab((g->player.x-e->x)*2)>80)return 0;
 if(v->action!=14 && (v->action || bk3_random_range(g,100)>=chance[l]))return 0;
 v->action=14;v->frame=v->timer=0;v->wait=30;v->vx=-e->facing*196608;g->rules.ai[i].mode=6;g->combat.enemy[i].mask=0;++r->blocks;if(v->z<3)++v->z;
 if(l>=3 && (g->bk3.script==BK_BLITZ || g->combat.action==CB_FORWARD || v->z>=3) && bk3_random_range(g,100)<counter[l]){v->action=15;v->vx=0;v->z=0;g->rules.ai[i].mode=0x4c;++r->counters;}
 sfx_emit(0x218,g->combat.ticks,(int)(e->x*256/240));return 1;
}
int reaction_selftest(void){Game g;int j;
 game_reset(&g);enemy_set_type(&g,0,EN_ZACK);g.enemies[0].x=70;g.enemies[0].y=100;g.enemies[0].facing=-1;
 if(!reaction_capture(&g,0) || g.reaction.hold_timer!=120)return 1701;
 for(j=0;j<13;++j)reaction_player_tick(&g,0,0);
 if(g.extra[0].action)return 1702;
 reaction_player_tick(&g,0,0);if(g.extra[0].action!=EP_KICK)return 1703;
 physics_hit(&g,1,2,0,1);reaction_hit(&g,0,1,2);if(g.reaction.holder!=-1 || (g.rules.actor[0].status58&16))return 1704;
 game_reset(&g);enemy_set_type(&g,0,EN_ZACK);g.enemies[0].x=70;g.enemies[0].y=100;g.enemies[0].facing=1;
 if(!reaction_capture(&g,0) || g.reaction.hold_timer!=60)return 1705;
 reaction_player_tick(&g,1,0);if(g.reaction.holder!=-1 || g.combat.target!=0 || !rules_hold_valid(&g))return 1706;
 game_reset(&g);enemy_set_type(&g,0,EN_ZACK);g.enemies[0].x=82;g.enemies[0].y=100;g.enemies[0].facing=-1;g.extra[0].action=14;
 if(!impact_apply(&g,0,1,2) || g.enemies[0].hp!=40 || g.reaction.blocks!=1)return 1707;
 game_reset(&g);enemy_set_type(&g,0,EN_ELECTRA);g.extra[0].action=EP_UPPER;impact_apply(&g,1,0,133);
 if(!g.reaction.shock || g.reaction.shock_timer!=4 || g.player.hp!=95)return 1708;
 for(j=0;j<4;++j)reaction_player_tick(&g,0,0);
 if(g.reaction.shock_frame!=1)return 1709;
 g.physics.body[0].phase=BODY_BOUNCE;reaction_player_tick(&g,0,0);if(g.reaction.shock)return 1710;
 game_reset(&g);enemy_set_type(&g,0,EN_ZACK);g.enemies[0].x=82;g.enemies[0].y=100;g.enemies[0].facing=-1;g.combat.enemy[0].level=10;
 for(j=0;j<100 && !g.reaction.counters;++j){g.extra[0].action=14;g.extra[0].z=2;reaction_block(&g,0,1);}
 if(!g.reaction.counters || g.extra[0].action!=15)return 1711;
 g.enemies[0].facing=1;g.extra[0].action=14;if(reaction_block(&g,0,1))return 1712;
 return 0;
}
