#include "game.h"
#include <string.h>
void game_reset(Game *g){
 int i;memset(g,0,sizeof(*g));g->player=(Actor){64,100,100,1,0,0,0,0,0};
 for(i=0;i<4;++i)g->enemies[i]=(Actor){144+i*23,79+i*12,40,-1,20+i*9,0,0,0,0};
 g->moves.charge=100;g->moves.grab=-1;combat_reset(g);rules_reset(g);for(i=0;i<5;++i)g->impact.last_from[i]=-1;
}
void game_hit_enemy(Game *g,int i,int damage,int down){combat_hurt_enemy(g,i,damage,down);}
void game_step(Game *g,Input in){
 int i;if(g->paused || g->won || (g->player.hp<=0 && !g->physics.body[0].phase))return;
 ++g->ticks;if(g->ticks>=99*30){g->player.hp=0;return;}
 if(g->player.hp<=0)in=(Input){0};
 combat_tick(g,in.x,in.y,in.attack,in.jump,in.special);
 combat_tick(g,in.x,in.y,0,0,0);
 g->won=1;for(i=0;i<4;++i)if(g->enemies[i].hp>0 || g->physics.body[i+1].phase==BODY_FLIGHT || g->physics.body[i+1].phase==BODY_VICTIM || g->combat.enemy[i].z<0)g->won=0;
}
int game_selftest(void){int result=bk3_selftest();if(result)return result;result=combat_selftest();if(result)return result;result=physics_selftest();if(result)return result;result=rules_selftest();if(result)return result;result=source_ai_selftest();if(result)return result;result=impact_selftest();return result?result:enemy_selftest();}
