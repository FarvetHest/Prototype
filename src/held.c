#include "game.h"
#include "held.h"
HeldAttack held_attack;
void held_reset(void){held_attack=(HeldAttack){0,0};}
/* The original release threshold is 40 ticks at 60Hz. One input tick is 30Hz. */
int held_tick(const Game *g,int down,int edge,int rear){
 int ready=g->player.hp>0 && !g->paused && !g->player.stun && !g->player.jump && !g->physics.body[0].phase && g->combat.action==CB_NONE && !rear;
 int threshold=player_character==PLAYER_MAX?60:40;
 int can_start=ready && g->bk3.mode==0 && !g->bk3.hitstop;
 if(!ready){held_reset();return edge;}
 if(edge==1 && can_start){held_attack.armed=1;held_attack.ticks=0;}
 if(down){if(held_attack.armed && held_attack.ticks<threshold+2)held_attack.ticks+=2;}
 else {int charged=held_attack.armed && held_attack.ticks>=threshold && can_start;held_reset();if(charged)return 3;}
 return edge;
}
int held_selftest(void){Game g;int i;
 game_reset(&g);held_reset();if(held_tick(&g,1,1,0)!=1)return 1101;
 for(i=0;i<18;++i){held_tick(&g,1,0,0);}if(held_tick(&g,0,0,0)!=0)return 1102;
 held_tick(&g,1,1,0);for(i=0;i<19;++i){held_tick(&g,1,0,0);}if(held_tick(&g,0,0,0)!=3 || held_attack.armed)return 1103;
 if(held_tick(&g,0,0,0)!=0)return 1104;
 held_tick(&g,1,1,0);for(i=0;i<30;++i){held_tick(&g,1,0,0);}g.paused=1;held_tick(&g,1,0,0);g.paused=0;if(held_tick(&g,0,0,0))return 1105;
 held_tick(&g,1,1,0);for(i=0;i<30;++i){held_tick(&g,1,0,0);}g.player.stun=1;held_tick(&g,1,0,0);g.player.stun=0;if(held_tick(&g,0,0,0))return 1106;
 held_tick(&g,1,1,0);for(i=0;i<30;++i){held_tick(&g,1,0,0);}held_tick(&g,1,0,1);if(held_tick(&g,0,0,0))return 1107;
 for(i=0;i<30;++i){held_tick(&g,1,0,0);}if(held_tick(&g,0,0,0))return 1108;
 held_tick(&g,1,1,0);for(i=0;i<30;++i){held_tick(&g,1,0,0);}g.bk3.mode=1;if(held_tick(&g,0,0,0))return 1109;
 held_reset();return 0;
}
