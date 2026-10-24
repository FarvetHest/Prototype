/* Enemy_Death loc_241DE: word68=100; Enemy_Disappear: bit1 of low byte69
   drives AnimationStatus bit4, and mode clears when the counter reaches zero. */
#include "game.h"
#include "sfx.h"
#include <string.h>
DeathFx death_fx[4];
static Game *owner;
static void bind(Game *g){if(owner!=g){owner=g;memset(death_fx,0,sizeof(death_fx));}}
void death_reset(Game *g){if(owner==g){owner=0;memset(death_fx,0,sizeof(death_fx));}}
void death_spawn(Game *g,int i){bind(g);if(i>=0 && i<4)memset(&death_fx[i],0,sizeof(death_fx[i]));}
void death_begin(Game *g,int i){DeathFx *d;if(i<0 || i>=4)return;bind(g);d=&death_fx[i];if(d->active)return;
 d->active=1;d->timer=-1;d->hidden=0;
 /* The source chooses two male IDs or Electra217. The WAV routing uses the
    corresponding original SoRR voice family; cosmetic choice never consumes AI RNG. */
 d->cry=enemy_type(g,i)==EN_ELECTRA?0x217:((g->combat.ticks+i)&1)?0x20b:0x20a;
 sfx_emit(d->cry,g->combat.ticks,(int)(g->enemies[i].x*256/240));
}
void death_tick(Game *g){int i;if(owner!=g || g->paused)return;for(i=0;i<4;++i){DeathFx *d=&death_fx[i];
 if(d->active!=1)continue;
 if(g->enemies[i].hp>0){memset(d,0,sizeof(*d));continue;}
 if(g->physics.body[i+1].phase || g->combat.enemy[i].z<0)continue;
 if(d->timer<0){d->timer=100;d->hidden=0;}
 else if(--d->timer<=0){d->timer=0;d->active=2;d->hidden=1;}
 else d->hidden=(d->timer&2)!=0;
 }}
int death_pending(const Game *g,int i){return owner==g && i>=0 && i<4 && death_fx[i].active==1;}
int death_visible(const Game *g,int i){return owner!=g || i<0 || i>=4 || !death_fx[i].hidden;}
int death_selftest(void){Game g;int n,visible=0,hidden=0;unsigned rng;
 game_reset(&g);rng=g.combat.rng;physics_hit(&g,1,40,0,1);
 if(!death_pending(&g,0) || death_fx[0].timer!=-1 || g.combat.rng!=rng)return 1901;
 for(n=0;n<150 && g.physics.body[1].phase;++n){physics_body_tick(&g,1);death_tick(&g);}
 if(g.physics.body[1].phase || death_fx[0].timer!=100)return 1902;
 for(n=99;n>0;--n){death_tick(&g);if(death_fx[0].timer!=n || death_visible(&g,0)!=(!(n&2)))return 1903;visible+=death_visible(&g,0);hidden+=!death_visible(&g,0);}
 if(!visible || !hidden || !death_pending(&g,0))return 1904;
 g.paused=1;death_tick(&g);if(death_fx[0].timer!=1)return 1905;g.paused=0;death_tick(&g);
 if(death_pending(&g,0) || death_visible(&g,0))return 1906;
 death_spawn(&g,0);if(!death_visible(&g,0) || death_fx[0].active)return 1907;
 game_reset(&g);enemy_set_type(&g,0,EN_ELECTRA);physics_hit(&g,1,40,1,1);if(death_fx[0].cry!=0x217)return 1908;
 owner=0;return 0;
}
