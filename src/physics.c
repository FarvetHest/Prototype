#include "game.h"
#include "bk3_data.h"
#include "combat_data.h"
#include "physics_data.h"
#include "stage.h"
#include "sfx.h"
#include <string.h>
static Actor *actor(Game *g,int i){return i?&g->enemies[i-1]:&g->player;}
static float bound(float x,float lo,float hi){return x<lo?lo:x>hi?hi:x;}
static void dec(int *n){if(*n>0)--*n;}
static const EnemyFrame *body_frames(Game *g,int i,int phase,int back,int *n){int k=phase==BODY_VICTIM?(back?EP_BACK:EP_FRONT):phase==BODY_GETUP?EP_GETUP:back?EP_HURT2:EP_HURT;*n=enemy_count(g,i-1,k);return enemy_frames(g,i-1,k);}
static void sync_body(Game *g,int i){Body *b=&g->physics.body[i];Actor *a=actor(g,i);
 g->motion.z[i]=-b->z/65536.0f;g->motion.vz[i]=-b->vz/65536.0f;
 a->stun=b->phase?1:0;
 if(i){EnemyBrain *e=&g->combat.enemy[i-1];e->z=b->z;e->vz=b->vz;e->vx=b->vx;e->fpg=b->fpg;
  g->moves.down[i-1]=b->phase>=BODY_FLIGHT && b->phase!=BODY_VICTIM?1:0;
  e->projectile=b->phase==BODY_FLIGHT && b->back>=0;g->moves.thrown[i-1]=e->projectile;
 }else {g->player.jump=b->phase==BODY_FLIGHT;}
}
void physics_hit(Game *g,int i,int damage,int down,int facing){Body *b=&g->physics.body[i];Actor *a=actor(g,i);int airborne=g->motion.z[i]>0,old_hp=a->hp;
 memset(b,0,sizeof(*b));b->back=-1;b->chain=i && (g->rules.actor[i].status58&16);b->fpg=i?enemy_frames(g,i-1,b->chain?EP_HURT2:EP_HURT)[0].fpg:148;a->hp-=damage;if(a->hp<0)a->hp=0;a->attack=0;
 b->freeze=2+(damage>>2);if(b->freeze>8)b->freeze=8;
 /* Chk_Hit/sub_25954: Axel's ordinary unarmed moves select FFFAC400. */
 a->facing=-facing;
 if(down || !a->hp || airborne){b->phase=BODY_FLIGHT;b->z=-(int)(g->motion.z[i]*65536);b->vz=i && ((g->combat.action==CB_NONE && g->bk3.mode==1 && g->bk3.script==BK_BLITZ) || g->combat.action==CB_FORWARD)?-474112:BK3_HIT_VZ;b->vx=facing*(a->hp || (g->rules.actor[i].statusde&4)?2:3)*65536;b->fpg=i?enemy_frames(g,i-1,EP_FLIGHT)[0].fpg:49;b->timer=i?enemy_frames(g,i-1,EP_FLIGHT)[0].ticks:0;b->hurt=0;}
 else {b->phase=BODY_HURT;b->timer=i?3:3;b->frame=0;b->hurt=4;}
 if(i){g->extra[i-1].action=0;g->extra[i-1].z=g->extra[i-1].vz=g->extra[i-1].vx=0;g->rules.ai[i-1].mode=2;g->combat.enemy[i-1].state=0;g->combat.enemy[i-1].anim_timer=0;}
 else {bk3_suspend(g);g->moves.special=0;g->moves.invincible=0;g->combat.action=CB_NONE;}
 if(i && old_hp>0 && a->hp<=0)death_begin(g,i-1);
 if(i && g->reaction.holder==i-1)reaction_release(g);
 sync_body(g,i);
}
void physics_victim_start(Game *g,int i,int back){Body *b=&g->physics.body[i];int n;const EnemyFrame *f=body_frames(g,i,BODY_VICTIM,back,&n);
 memset(b,0,sizeof(*b));b->phase=BODY_VICTIM;b->timer=f[0].ticks;b->back=back;b->hurt=f[0].hurt;b->fpg=f[0].fpg;
 /* While attached, vx stores the victim's own held X origin (16.16 screen pixels). */
 b->vx=(int)(actor(g,i)->x*131072);
 b->pending=character_damage(back?(back_release[1]&65535):front_release[3])&63;sync_body(g,i);
}
int physics_victim_tick(Game *g,int i){Body *b=&g->physics.body[i];int n,remaining;const EnemyFrame *f=body_frames(g,i,BODY_VICTIM,b->back,&n);const unsigned *offset=b->back?back_offsets:front_offsets;unsigned packed;
 if(!b->timer){++b->frame;b->timer=f[b->frame].ticks;}
 /* Enemy_Forward/BackwardThrow: the final timer tick uses the NEXT remaining ID. */
 remaining=n-b->frame-(b->timer==1);packed=offset[remaining+1];
 /* Source offsets are relative to the victim's held origin, not Axel's pivot.
    Retain its ground Y as well, so attachment does not reverse depth ordering. */
 actor(g,i)->x=bound(b->vx/131072.0f+g->player.facing*(b->back?-1:1)*(signed char)(packed>>8)/2.0f,10,230);
 b->z=(signed char)(packed&255)*65536;b->fpg=f[b->frame].fpg;b->hurt=f[b->frame].hurt;
 --b->timer;
 if(remaining*2==(int)offset[0]){
  b->phase=BODY_FLIGHT;b->vz=b->back?(int)back_release[0]:(int)(short)front_release[0]*65536+(int)front_release[1];
  b->vx=g->player.facing*(b->back?-(int)(back_release[1]>>16):(int)(short)front_release[2])*65536;
  b->freeze=1;b->hurt=0;g->combat.enemy[i-1].mask=0;sync_body(g,i);return 1;
 }
 sync_body(g,i);return 0;
}
int physics_rect(const Game *g,int index,float r[4]){const Actor *a=index?&g->enemies[index-1]:&g->player;const Body *b=&g->physics.body[index];const signed char *box;int id=1;
 if(b->phase)id=b->hurt;
 else if(index){id=g->pose[index-1].fpg?g->pose[index-1].hurt:enemy_frames(g,index-1,EP_IDLE)[0].hurt;}
 else if(!index && g->bk3.active){unsigned j;for(j=0;j<sizeof(axel_hurt_ids)/sizeof(axel_hurt_ids[0]);++j)if(axel_hurt_ids[j][0]==g->bk3.fpg){id=axel_hurt_ids[j][1];break;}}
 if(!id)return 0;
 if(!index && player_character==PLAYER_MAX){int height=g->bk3.script==BK_TUCK?56:82;
  r[0]=a->x*2-16;r[1]=a->x*2+16;r[3]=stage_foot_y(a->y)-g->motion.z[0];r[2]=r[3]-height;return 1;
 }
 box=index?enemy_box(g,index-1,id,1):axel_hurt[id];if(!box)return 0;box+=a->facing>0?4:0;
 r[0]=a->x*2+box[0];r[1]=r[0]+(unsigned char)box[1];r[2]=stage_foot_y(a->y)-g->motion.z[index]+box[2];r[3]=r[2]+(unsigned char)box[3];return 1;
}
static void floor_impact(Game *g,int i){Body *b=&g->physics.body[i];Actor *a=actor(g,i);
 sfx_emit(0x346,g->combat.ticks,(int)(a->x*256/240));
 /* loc_24380: ScreenShake=1 on the first floor impact; loc_243D8: landing dust on every ground contact. */
 fx_shake(g);fx_dust(g,i);
 /* loc_24380: throw damage is applied ONCE on the first ground impact. */
 if(b->pending){a->hp-=b->pending;if(a->hp<0)a->hp=0;if(i && a->hp<=0)death_begin(g,i-1);b->pending=0;}
 b->phase=BODY_BOUNCE;b->z=-1;b->vz=BK3_BOUNCE_VZ;b->vx=(b->vx/65536>>1)*65536;
 b->timer=i?20:40;b->frame=0;b->hurt=0;b->fpg=i?enemy_frames(g,i-1,EP_FLOOR)[0].fpg:50;b->back=-1;
}
void physics_body_tick(Game *g,int i){Body *b=&g->physics.body[i];Actor *a=actor(g,i);int n,j;const EnemyFrame *f=enemy_frames(g,0,EP_HURT);
 if(!i || !bk3_machine_stats.dispatching)dec(&b->inv);
 if(!b->phase || b->phase==BODY_VICTIM)return;
 if(b->freeze){--b->freeze;sync_body(g,i);return;}
 if(b->phase==BODY_FLIGHT || b->phase==BODY_BOUNCE){
  if(i && b->phase==BODY_FLIGHT){
   if(b->back>=0){
    /* Release changes motion, not the source throw animation. Finish its somersault. */
    f=body_frames(g,i,BODY_VICTIM,b->back,&n);
    if(b->timer<=0 && b->frame<n-1){++b->frame;b->timer=f[b->frame].ticks;}
    b->fpg=f[b->frame].fpg;if(b->timer>0)--b->timer;
   }else {const EnemyFrame *flight=enemy_frames(g,i-1,EP_FLIGHT);if(b->timer>0)--b->timer;b->fpg=flight[b->timer>0 || enemy_count(g,i-1,EP_FLIGHT)<2?0:1].fpg;}
  }
  if(b->phase==BODY_FLIGHT || b->z<0){
   a->x=bound(a->x+b->vx/131072.0f,10,230);b->z+=b->vz;b->vz+=BK3_GRAVITY_FP;
   if(i && b->phase==BODY_FLIGHT && b->back>=0){EnemyBrain *e=&g->combat.enemy[i-1];
    for(j=1;j<=4;++j)if(j!=i && !(e->mask&(1u<<(j-1))) && g->enemies[j-1].hp>0 && !g->moves.down[j-1] && !g->physics.body[j].inv){
     float box[4],x=a->x*2,y=stage_foot_y(a->y)+b->z/65536.0f;
     if(rules_depth_overlap(g,i,j) && physics_rect(g,j,box) && x>=box[0] && x<=box[1] && y>=box[2] && y<=box[3]){
      int encoded=0x90;if((b->vx<0?-1:1)!=a->facing)encoded|=64;fx_note_attack_top((int)y);
      if(impact_apply(g,i,j,encoded)){g->impact.freeze[i]=0;g->physics.body[j].freeze=8;b->freeze=8;e->mask|=1u<<(j-1);g->moves.throw_hit[i-1]=e->mask;}
     }
    }
   }
   if(b->z>=0 && b->vz>=0){if(b->phase==BODY_FLIGHT)floor_impact(g,i);else {b->z=0;fx_dust(g,i);}}
  }
  if(b->phase==BODY_BOUNCE){dec(&b->timer);if(!b->timer && b->z>=0){
   b->z=0;b->vz=0;b->vx=0;if(a->hp<=0){b->phase=0;b->fpg=i?enemy_frames(g,i-1,EP_FLOOR)[0].fpg:50;}
   else {b->phase=BODY_GETUP;b->frame=0;if(i){f=body_frames(g,i,BODY_GETUP,0,&n);b->timer=f[0].ticks;}else b->timer=bk3_getup[0].ticks;}
  }}
 }else if(b->phase==BODY_HURT || b->phase==BODY_GETUP){
  if(i){f=body_frames(g,i,b->phase,b->chain,&n);b->fpg=f[b->frame].fpg;b->hurt=f[b->frame].hurt;}
  else {const Bk3Frame *p=b->phase==BODY_HURT?bk3_hit:bk3_getup;n=4;b->fpg=p[b->frame].fpg;b->hurt=b->phase==BODY_HURT?16:0;}
  if(--b->timer<=0){if(++b->frame==n){int recover=b->phase==BODY_GETUP;b->phase=0;b->fpg=1;b->hurt=1;if(recover)b->inv=rules_recovery_inv(g,i);}
   else if(i)b->timer=f[b->frame].ticks;else b->timer=(b->phase==BODY_HURT?bk3_hit:bk3_getup)[b->frame].ticks;}
 }
 sync_body(g,i);
}
/* Independent traces read by the emulator test and compared to pinned source equations. */
int physics_fall_trace[128][4],physics_victim_trace[2][40][4];
int physics_selftest(void){Game g;int i,k,released;
 game_reset(&g);physics_hit(&g,1,4,1,1);g.physics.body[1].freeze=0;
 if(g.physics.body[1].vz!=BK3_HIT_VZ)return 401;
 for(i=0;i<128;++i){physics_body_tick(&g,1);physics_fall_trace[i][0]=g.physics.body[1].z;physics_fall_trace[i][1]=g.physics.body[1].vz;physics_fall_trace[i][2]=g.physics.body[1].phase;physics_fall_trace[i][3]=g.enemies[0].hp;}
 if(g.physics.body[1].phase || g.physics.body[1].inv!=0)return 402;
 for(k=0;k<2;++k){game_reset(&g);physics_victim_start(&g,1,k);released=0;
  for(i=0;i<40;++i){if(!released)released=physics_victim_tick(&g,1);else physics_body_tick(&g,1);
   physics_victim_trace[k][i][0]=g.physics.body[1].phase;physics_victim_trace[k][i][1]=g.physics.body[1].z;physics_victim_trace[k][i][2]=g.physics.body[1].pending;physics_victim_trace[k][i][3]=g.enemies[0].hp;}
  if(!released)return 403+k;
 }
 game_reset(&g);physics_victim_start(&g,1,1);for(i=0;i<29;++i){released=physics_victim_tick(&g,1);}
 if(!released || g.enemies[0].hp!=40 || g.physics.body[1].pending!=14)return 405;
 physics_body_tick(&g,1);physics_body_tick(&g,1);if(g.enemies[0].hp!=26 || g.physics.body[1].pending)return 406;
 game_reset(&g);physics_hit(&g,1,4,1,1);g.physics.body[1].freeze=0;
 for(i=0;i<70;++i){physics_body_tick(&g,1);}if(g.physics.body[1].phase!=BODY_GETUP)return 407;
 game_reset(&g);g.bk3.mode=1;g.bk3.script=BK_BLITZ;physics_hit(&g,1,4,1,1);if(g.physics.body[1].vz!=-474112)return 408;
 game_reset(&g);g.bk3.script=BK_BLITZ;physics_hit(&g,1,4,1,1);if(g.physics.body[1].vz!=BK3_HIT_VZ)return 409;
 for(k=0;k<2;++k){game_reset(&g);g.player.x=112;g.player.y=101.31579f;g.enemies[0].x=120;g.enemies[0].y=100;physics_victim_start(&g,1,k);physics_victim_tick(&g,1);if(g.enemies[0].x!=(k?120:108) || g.enemies[0].y!=100)return 410+k;}
 for(k=0;k<2;++k){game_reset(&g);physics_victim_start(&g,k+1,0);released=0;for(i=0;i<26;++i){released=physics_victim_tick(&g,k+1);}if(!released)return 412+k;
  physics_body_tick(&g,k+1);physics_body_tick(&g,k+1);if(g.physics.body[k+1].phase!=BODY_FLIGHT || g.physics.body[k+1].fpg!=enemy_frames(&g,k,EP_FRONT)[3].fpg)return 414+k;}
 return 0;
}

