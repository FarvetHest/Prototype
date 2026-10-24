#include "game.h"
#include "sfx.h"
#include <string.h>
#include <stddef.h>
unsigned player_character;
/* Character-specific attacks live in max.c. Shared BK3 damage is unchanged. */
float character_speed(void){return 1.f;}
int character_damage(int encoded){return encoded;}
int character_frame_ticks(int script,int ticks){(void)script;return ticks;}
void game_reset(Game *g){
 int i;bk3_machine_reset(g);death_reset(g);memset(g,0,sizeof(*g));g->reaction.holder=-1;g->player=(Actor){64,100,100,1,0,0,0,0,0};
 for(i=0;i<4;++i)g->enemies[i]=(Actor){144+i*23,79+i*12,40,-1,20+i*9,0,0,0,0};
 for(i=0;i<4;++i)g->extra[i].type=i&1;
 g->moves.charge=100;g->moves.grab=-1;combat_reset(g);rules_reset(g);for(i=0;i<5;++i)g->impact.last_from[i]=-1;
}
/* Restore only the player; enemy HP/positions and run score belong to the session. */
void game_respawn(Game *g){Game fresh;unsigned rng=g->combat.rng,ticks=g->combat.ticks;int i;
 reaction_release(g);g->reaction.shock=0;rules_end_hold(g);game_reset(&fresh);g->player=fresh.player;g->max=fresh.max;g->moves=fresh.moves;g->bk3=fresh.bk3;
 memcpy(&g->combat,&fresh.combat,offsetof(Combat,enemy));g->combat.rng=rng;g->combat.ticks=ticks;
 g->physics.body[0]=fresh.physics.body[0];g->physics.body[0].inv=120;g->physics.z=g->physics.vz=g->physics.landed=g->physics.vaults=g->physics.rolltimer=0;
 g->motion.z[0]=g->motion.vz[0]=g->motion.vx[0]=g->motion.jump_x=g->motion.jump_y=0;
 g->rules.actor[0]=fresh.rules.actor[0];g->impact.freeze[0]=0;g->impact.last_from[0]=-1;
 for(i=0;i<4;++i){
  if(g->rules.actor[i+1].gripper==0){g->rules.actor[i+1].gripper=-1;g->rules.actor[i+1].status58&=~16;}
  if(g->physics.body[i+1].phase==BODY_VICTIM){g->physics.body[i+1]=fresh.physics.body[i+1];g->enemies[i].stun=0;g->motion.z[i+1]=g->motion.vz[i+1]=0;g->rules.ai[i].mode=2;g->combat.enemy[i].state=0;}
 }
 g->ticks=0;g->paused=0;g->won=0;
}
void game_hit_enemy(Game *g,int i,int damage,int down){combat_hurt_enemy(g,i,damage,down);}
void game_step(Game *g,Input in){
 int i;bk3_put8(0xfffff505u,g->paused);if(g->player.hp<=0 && g->reaction.holder>=0)reaction_release(g);if(g->paused || g->won || (g->player.hp<=0 && !g->physics.body[0].phase))return;
 ++g->ticks;if(g->ticks>=99*30){g->player.hp=0;return;}
 if(g->player.hp<=0)in=(Input){0};
 bk3_machine_step(g,in.x,in.y,in.attack,in.jump,in.special);
 bk3_machine_step(g,in.x,in.y,0,0,0);
 g->won=1;for(i=0;i<4;++i)if(g->enemies[i].hp>0 || g->physics.body[i+1].phase==BODY_FLIGHT || g->physics.body[i+1].phase==BODY_VICTIM || g->combat.enemy[i].z<0 || death_pending(g,i))g->won=0;
}
int game_selftest(void){int result=bk3_selftest();if(result)return result;result=combat_selftest();if(result)return result;result=physics_selftest();if(result)return result;result=rules_selftest();if(result)return result;result=source_ai_selftest();if(result)return result;result=impact_selftest();if(result)return result;result=enemy_selftest();if(result)return result;result=variety_selftest();if(result)return result;result=reaction_selftest();if(result)return result;result=bk3_machine_selftest();if(result)return result;result=death_selftest();if(result)return result;result=fx_selftest();return result?result:sfx_selftest();}

int character_selftest(void){return max_selftest();}
