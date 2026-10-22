#include "game.h"
#include "enemy_data.h"
const EnemyFrame *enemy_frames(int i,int k){return enemy_sequences[i&1][k];}
int enemy_count(int i,int k){return enemy_sizes[i&1][k];}
void enemy_pose_tick(Game *g,int i,int kind){EnemyPose *p=&g->pose[i];const EnemyFrame *f=enemy_frames(i,kind);int n=enemy_count(i,kind);
 if(!p->fpg || p->kind!=kind){p->kind=kind;p->frame=0;p->timer=f[0].ticks;}
 else if(!p->timer){p->frame=(p->frame+1)%n;p->timer=f[p->frame].ticks;}
 p->fpg=f[p->frame].fpg;p->hurt=f[p->frame].hurt;if(p->timer>0)--p->timer;++p->ticks;
}
int enemy_selftest(void){Game g;int i,j;
 game_reset(&g);for(i=0;i<32;++i)enemy_pose_tick(&g,0,EP_IDLE);if(g.pose[0].frame!=3 || g.pose[0].timer)return 801;
 enemy_pose_tick(&g,0,EP_IDLE);if(g.pose[0].frame || g.pose[0].timer!=7)return 802;
 for(i=0;i<2;++i)for(j=0;j<13;++j){const EnemyFrame *f=enemy_frames(i,j);int n=enemy_count(i,j),k;for(k=0;k<n;++k)if(f[k].fpg<1000 || !f[k].ticks)return 803;}
 game_reset(&g);enemy_pose_tick(&g,0,EP_WALK);if(g.pose[0].kind!=EP_WALK || g.pose[0].timer!=7)return 804;
 enemy_pose_tick(&g,0,EP_HELD);if(g.pose[0].fpg!=enemy_frames(0,EP_HELD)[0].fpg)return 805;
 game_reset(&g);g.enemies[0].x=82;g.enemies[0].y=100;g.rules.ai[0].mode=0x1a;g.combat.enemy[0].state=9;g.combat.enemy[0].frame=2;g.combat.enemy[0].anim_timer=1;g.rules.actor[0].enabled=0;source_ai_tick(&g,0);
 if(g.combat.enemy[0].frame!=3 || g.pose[0].fpg!=enemy_frames(0,EP_JAB)[2].fpg || g.pose[0].hurt!=enemy_frames(0,EP_JAB)[2].hurt)return 806;
 game_reset(&g);g.combat.target=0;g.combat.action=CB_HOLD;rules_begin_hold(&g,0);physics_hit(&g,1,2,0,1);if(!g.physics.body[1].chain)return 807;
 physics_body_tick(&g,1);physics_body_tick(&g,1);physics_body_tick(&g,1);if(g.physics.body[1].fpg!=enemy_frames(0,EP_HURT2)[0].fpg)return 808;
 return 0;
}
