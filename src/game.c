#include "game.h"
#include "sfx.h"
#include <string.h>
#include <stddef.h>
unsigned player_character;
/* Max is an authored heavyweight adapter on the BK3 combat core. */
float character_speed(void){return player_character==PLAYER_MAX?.8f:1.f;}
int character_damage(int encoded){int d=encoded&63;if(player_character==PLAYER_MAX){d=(d*3+1)/2;if(d>63)d=63;}return (encoded&~63)|d;}
int character_frame_ticks(int script,int ticks){return player_character==PLAYER_MAX && script>=BK_PUNCH1 && script<=BK_TUCK?(ticks*3+1)/2:ticks;}
void game_reset(Game *g){
 int i;bk3_machine_reset(g);death_reset(g);memset(g,0,sizeof(*g));g->reaction.holder=-1;g->player=(Actor){64,100,100,1,0,0,0,0,0};
 for(i=0;i<4;++i)g->enemies[i]=(Actor){144+i*23,79+i*12,40,-1,20+i*9,0,0,0,0};
 for(i=0;i<4;++i)g->extra[i].type=i&1;
 g->moves.charge=100;g->moves.grab=-1;combat_reset(g);rules_reset(g);for(i=0;i<5;++i)g->impact.last_from[i]=-1;
}
/* Restore only the player; enemy HP/positions and run score belong to the session. */
void game_respawn(Game *g){Game fresh;unsigned rng=g->combat.rng,ticks=g->combat.ticks;int i;
 reaction_release(g);g->reaction.shock=0;rules_end_hold(g);game_reset(&fresh);g->player=fresh.player;g->moves=fresh.moves;g->bk3=fresh.bk3;
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
int game_selftest(void){int result=bk3_selftest();if(result)return result;result=combat_selftest();if(result)return result;result=physics_selftest();if(result)return result;result=rules_selftest();if(result)return result;result=source_ai_selftest();if(result)return result;result=impact_selftest();if(result)return result;result=enemy_selftest();if(result)return result;result=variety_selftest();if(result)return result;result=reaction_selftest();if(result)return result;result=bk3_machine_selftest();if(result)return result;result=death_selftest();return result?result:sfx_selftest();}

int character_selftest(void){
 unsigned saved=player_character;Game g;int result=0,hp,i;float x;
 player_character=PLAYER_MAX;
 if(character_damage(0xc2)!=0xc3 || character_damage(0xff)!=0xff || character_damage(0xc0)!=0xc0 || character_frame_ticks(BK_PUNCH1,2)!=3){result=1501;goto done;}
 game_reset(&g);for(i=0;i<4;++i){g.enemies[i].x=220;g.enemies[i].stun=10000;}
 x=g.player.x;bk3_tick(&g,1,0,0,0);if(g.player.x-x<.499f || g.player.x-x>.501f){result=1502;goto done;}
 game_reset(&g);hp=g.enemies[0].hp;if(!impact_apply(&g,0,1,2) || hp-g.enemies[0].hp!=3){result=1503;goto done;}
 game_reset(&g);hp=g.player.hp;if(!impact_apply(&g,1,0,2) || hp-g.player.hp!=2){result=1504;goto done;}
 done:player_character=saved;return result;
}
