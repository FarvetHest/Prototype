#include "game.h"
#include "bk3_data.h"
#include "combat_data.h"
#include "stage.h"
static const Actor *actor(const Game *g,int i){return i?&g->enemies[i-1]:&g->player;}
int impact_overlap(const Game *g,int from,int to,int id){const Actor *a=actor(g,from);const signed char *box;float x,y,r[4];int z;
 if(from==to || id<=0 || id>=(from?(from%2?4:5):27))return 0;
 if(!(rules_flags(g,to)&128) || g->physics.body[to].inv || !rules_depth_overlap(g,from,to) || a->x<0 || a->x>240)return 0;
 if(!to && g->moves.invincible)return 0;
 if(!physics_rect(g,to,r))return 0;
 box=(from?(from%2?garcia_boxes[id]:donovan_boxes[id]):bk3_attack_boxes[id])+(a->facing>0?4:0);
 z=from?-(int)(g->motion.z[from]*65536):g->bk3.z;
 x=a->x*2+box[0];y=stage_foot_y(a->y)+z/65536.f+box[2];
 return !(r[1]<x || r[0]>x+(int)box[1] || r[3]<y || r[2]>y+(int)box[3]);
}
int impact_apply(Game *g,int from,int to,int encoded){int damage=encoded&63,freeze=2+(damage>>2),facing=actor(g,from)->facing;
 if(!damage || from==to || !(rules_flags(g,to)&128) || g->physics.body[to].inv || (!to && g->moves.invincible))return 0;
 if(freeze>8)freeze=8;
 if(encoded&64)facing=-facing;
 if(!to){rules_end_hold(g);g->moves.grab=-1;g->moves.grab_timer=0;g->combat.target=-1;g->combat.escape=0;g->combat.hold=0;g->combat.action=CB_NONE;}
 physics_hit(g,to,damage,(encoded&128)!=0,facing);
 /* loc_25192 / SetHitFlag: enemy target 5, player target 10 source ticks. */
 g->physics.body[to].inv=to?5:10;
 if(from)g->impact.freeze[from]=freeze;else g->bk3.hitstop=freeze;
 g->impact.freeze[to]=0;g->impact.last_from[to]=from;g->impact.damage[to]=encoded;++g->impact.contacts[from];
 if(to && (g->rules.actor[to].status58&16) && g->physics.body[to].phase==BODY_FLIGHT){rules_end_hold(g);g->moves.grab=-1;g->combat.target=-1;}
 return 1;
}
int impact_selftest(void){Game g;int i,hp;
 game_reset(&g);g.enemies[0].x=80;g.enemies[0].y=119;if(!impact_overlap(&g,0,1,5))return 701;
 g.enemies[0].y=123;if(impact_overlap(&g,0,1,5))return 702;
 game_reset(&g);g.enemies[0].x=80;g.enemies[0].y=100;g.rules.actor[1].enabled=0;if(impact_overlap(&g,0,1,5))return 703;
 g.rules.actor[1].enabled=1;g.rules.actor[1].status58=0;if(impact_overlap(&g,0,1,5))return 704;
 game_reset(&g);if(!impact_apply(&g,0,1,2) || g.enemies[0].hp!=38 || g.physics.body[1].inv!=5 || g.bk3.hitstop!=2)return 705;
 if(impact_apply(&g,0,1,2) || g.enemies[0].hp!=38)return 706;
 for(i=0;i<5;++i){physics_body_tick(&g,1);}
 if(g.physics.body[1].inv)return 707;
 if(!impact_apply(&g,0,1,2) || g.enemies[0].hp!=36)return 708;
 game_reset(&g);if(!impact_apply(&g,1,0,1) || g.player.hp!=99 || g.physics.body[0].inv!=10 || g.impact.freeze[1]!=2)return 709;
 g.physics.body[0].inv=0;if(!impact_apply(&g,2,0,1) || g.player.hp!=98)return 710;
 game_reset(&g);g.enemies[0].facing=1;impact_apply(&g,0,1,2);if(g.enemies[0].facing!=-1)return 711;
 game_reset(&g);impact_apply(&g,0,1,66);if(g.enemies[0].facing!=1 || g.enemies[0].hp!=38)return 712;
 game_reset(&g);g.combat.target=0;g.combat.action=CB_HOLD;g.moves.grab=0;rules_begin_hold(&g,0);impact_apply(&g,2,0,1);if(g.combat.target!=-1 || g.rules.actor[1].gripper!=-1 || g.moves.grab!=-1)return 713;
 game_reset(&g);g.combat.target=0;g.combat.action=CB_HOLD;rules_begin_hold(&g,0);impact_apply(&g,0,1,2);for(i=0;i<40;++i){source_ai_tick(&g,0);}
 if(g.physics.body[1].phase || g.physics.body[1].inv || !rules_hold_valid(&g))return 714;
 game_reset(&g);g.enemies[0].x=82;g.enemies[0].y=100;g.combat.enemy[0].state=9;g.rules.ai[0].mode=0x1a;g.combat.enemy[0].frame=2;g.combat.enemy[0].anim_timer=4;
 source_ai_tick(&g,0);hp=g.player.hp;if(hp!=99 || g.impact.freeze[1]!=2)return 715;
 source_ai_tick(&g,0);source_ai_tick(&g,0);if(g.combat.enemy[0].anim_timer!=3 || g.player.hp!=hp)return 716;
 game_reset(&g);g.moves.invincible=1;if(impact_apply(&g,1,0,1) || g.player.hp!=100)return 717;
 game_reset(&g);g.player.hp=1;impact_apply(&g,1,0,1);if(g.player.hp || g.physics.body[0].phase!=BODY_FLIGHT)return 718;
 game_reset(&g);g.enemies[0].x=48;g.enemies[0].y=100;g.player.facing=-1;if(!impact_overlap(&g,0,1,5))return 719;
 game_reset(&g);if(impact_overlap(&g,0,1,27) || impact_overlap(&g,1,0,4))return 720;
 return 0;
}
