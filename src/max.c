/* Native C translation of the pinned SoR2 Max handlers. Enemy bodies, world
   bounds, block reactions and audio mixing remain the remake's shared services. */
#include "game.h"
#include "max_sor2_data.h"
#include "level.h"
#include "stage.h"
#include "sfx.h"
#include <string.h>
#include <stddef.h>
volatile unsigned max_abi[]={sizeof(Game),offsetof(Game,max),sizeof(MaxCombat),offsetof(Game,fx),sizeof(Fx)};
static float bound(float x,float lo,float hi){return x<lo?lo:x>hi?hi:x;}
static int dir(float x){return x>.5f?1:x<-.5f?-1:0;}
static const MaxFrame *frame(const MaxCombat *m){return &max_sequences[m->anim/2][m->frame];}
static void enter(Game *g,int mode,int anim){MaxCombat *m=&g->max;
 m->mode=mode;m->anim=anim;m->frame=0;m->timer=max_sequences[anim/2][0].ticks;m->mask=0;m->contact=0;
 g->bk3.active=1;g->bk3.fpg=frame(m)->fpg;g->bk3.queued=0;g->bk3.hitstop=0;
}
static void release(Game *g){int i=g->combat.target;
 if(i>=0 && g->physics.body[i+1].phase==BODY_VICTIM){Body *b=&g->physics.body[i+1];b->phase=BODY_FLIGHT;b->pending=0;b->back=-1;b->vx=b->vz=0;b->freeze=0;}
 rules_end_hold(g);g->combat.target=-1;g->combat.action=CB_NONE;g->moves.grab=-1;g->moves.grab_timer=0;
}
static void idle(Game *g){release(g);g->max.z=g->max.vz=g->max.vx=0;g->player.jump=g->player.attack=0;g->moves.special=g->moves.invincible=0;g->motion.z[0]=0;g->bk3.z=0;enter(g,MX_IDLE,0);}
static void anchor(Game *g){int i=g->combat.target;Actor *e=&g->enemies[i];
 g->player.x=bound(e->x-g->player.facing*(g->combat.back?12:16),10,230);g->player.y=bound(e->y+1/.76f,76,126);
 e->facing=g->combat.back?g->player.facing:-g->player.facing;e->attack=0;
}
/* Source damage uses SEVEN bits, $80 = knockdown. It must never pass through
   BK3's six-bit damage + $40 reversed-facing encoding. */
static int hit(Game *g,int i,int encoded,int facing,int top){int damage=encoded&127,freeze;Actor *e=&g->enemies[i];
 if(!damage || e->hp<=0 || g->physics.body[i+1].inv || !(rules_flags(g,i+1)&128))return 0;
 if(reaction_block(g,0,i+1))return 1;
 physics_hit(g,i+1,damage,(encoded&128)!=0,facing);
 freeze=4+(damage>>2);if(freeze>8)freeze=8;
 g->physics.body[i+1].freeze=freeze;g->physics.body[i+1].inv=5;g->max.hitstop=freeze;
 g->impact.last_from[i+1]=0;g->impact.damage[i+1]=encoded;++g->impact.contacts[0];++g->max.hits;
 fx_note_attack_top(top);fx_spark(g,0,i+1);sfx_emit(damage<8?0x18:damage<16?0x26:damage<24?0x21:0x32,g->combat.ticks,(int)(e->x*256/240));
 reaction_hit(g,0,i+1,encoded&128);
 if(g->physics.body[i+1].phase==BODY_FLIGHT && g->combat.target==i)release(g);
 return 1;
}
static void collide(Game *g){MaxCombat *m=&g->max;const MaxFrame *f=frame(m);int i;float left,right,top;
 if(!(f->width || f->height) || !(f->damage&127))return;
 left=g->player.x*2;right=left+g->player.facing*f->width;if(left>right){float t=left;left=right;right=t;}
 top=stage_foot_y(g->player.y)+m->z/65536.f-f->height;
 for(i=0;i<4;++i){float box[4];int facing=g->player.facing*(f->width<0?-1:1);
  if((m->mask&(1u<<i)) || !rules_depth_overlap(g,0,i+1) || !physics_rect(g,i+1,box) || box[1]<left || box[0]>right || box[2]>top || box[3]<top)continue;
  if(m->anim==0x52)facing=-facing;
  if(hit(g,i,f->damage,facing,(int)top)){m->mask|=1u<<i;m->contact=1;}
 }
}
static void victim_pose(Game *g,int i,int k,int j){Body *b=&g->physics.body[i+1];int n=enemy_count(g,i,k);const EnemyFrame *f=enemy_frames(g,i,k);
 if(j>=n){j=n-1;}if(j<0){j=0;}b->fpg=f[j].fpg;b->hurt=f[j].hurt;g->motion.z[i+1]=-b->z/65536.f;g->motion.vz[i+1]=-b->vz/65536.f;
}
static void throw_begin(Game *g,int kind){MaxCombat *m=&g->max;int i=g->combat.target;Body *b=&g->physics.body[i+1];
 m->throw_kind=kind;m->throw_frame=0;m->throw_timer=kind==2?10:16;m->throw_released=0;m->throw_origin=(int)(g->enemies[i].x*131072);
 memset(b,0,sizeof(*b));b->phase=BODY_VICTIM;b->back=kind==1;b->inv=0;g->enemies[i].stun=1;
 ++m->throws;enter(g,kind==2?MX_AIRSLAM:MX_THROW,kind==1?0x32:kind==2?0x50:0x30);
 g->combat.action=kind==1?CB_BACKTHROW:CB_FRONTTHROW;
}
/* Enemy_Forward/BackwardThrow: FrameID is a REMAINING counter, and the
   timer==1 tick indexes the next row before the frame advances. Tables overlap
   subsequent labelled rows in ROM, so extraction includes that shared tail. */
static void throw_tick(Game *g){MaxCombat *m=&g->max;int i=g->combat.target,rem,idx,side=g->player.facing;
 static const int front_ticks[5]={16,4,6,20,99},back_ticks[5]={16,4,6,3,99};const short *offsets;
 Body *b;if(i<0 || m->throw_released)return;b=&g->physics.body[i+1];
 if(!m->throw_timer){++m->throw_frame;m->throw_timer=m->throw_kind==2?99:m->throw_kind==1?back_ticks[m->throw_frame]:front_ticks[m->throw_frame];}
 rem=(m->throw_kind==2?2:5)-m->throw_frame-(m->throw_timer==1);idx=rem*4;
 offsets=m->throw_kind==1?max_word_D640:m->throw_kind==2?max_word_D266:max_word_D276;
 /* SoR2 Obj_Partner*GrabThrow indexes the tables by the VICTIM's orientation bit ($E&1); bit 1 = facing right (SpriteOrientation), so column 1 is used when facing right. */
 {int o=g->enemies[i].facing>0?1:0;b->z=(offsets[idx+2+o]+(m->throw_kind==2?m->z/65536:0))*65536;
  g->enemies[i].x=bound(m->throw_origin/131072.f+offsets[idx+o]/2.f,10,230);}
 victim_pose(g,i,m->throw_kind==1?EP_BACK:EP_FRONT,m->throw_kind==2?2:m->throw_frame);
 --m->throw_timer;
 if(rem==1){
  b->phase=BODY_FLIGHT;b->pending=m->throw_kind==1?62:m->throw_kind==2?40:34;b->vz=m->throw_kind==2?-131072:0;
  b->vx=side*(m->throw_kind==2?2:-2)*65536; /* front and back throws carry the victim on behind Max, like the last table row */b->back=m->throw_kind==1;b->frame=m->throw_frame;b->timer=1;b->freeze=0;
  m->throw_released=1;rules_end_hold(g);g->moves.grab=-1;g->combat.target=-1;
 }
}
static void hold_jump(Game *g,int dx){MaxCombat *m=&g->max;
 m->z=0;m->vz=-262144;m->vx=0;m->direction=dx;m->takeoff=4;m->air_attack=0;m->land=0;
 enter(g,MX_HOLDJUMP,6);g->combat.action=CB_VAULT;g->player.jump=1;
 if(!g->combat.back)g->enemies[g->combat.target].x+=g->player.facing*4;
}
static void special_begin(Game *g,int dx){release(g);if(dx)g->player.facing=dx;
 g->physics.body[0].phase=0;g->player.stun=0;g->max.z=0;g->max.combo=g->max.combo_wait=0;
 enter(g,dx?MX_FORWARD:MX_NEUTRAL,dx?0x4a:0x46);g->combat.action=dx?CB_FORWARD:CB_NEUTRAL;g->moves.special=1;g->moves.special_forward=dx!=0;g->moves.invincible=!dx;
}
static void finish(Game *g){MaxCombat *m=&g->max;int mode=m->mode,contact=m->contact;
 if(mode==MX_NEUTRAL || mode==MX_FORWARD){if(mode==MX_FORWARD || contact)g->player.hp-=8;idle(g);}
 else if(mode==MX_ATTACK){if(contact && m->anim!=0x4c && m->combo<3)++m->combo;else m->combo=0;enter(g,MX_IDLE,0);}
 else if(mode==MX_GRABHIT && m->anim!=0x4e && g->combat.target>=0 && rules_hold_valid(g) && g->combat.hits<3){enter(g,MX_HOLD,g->combat.back?0xa:8);g->combat.action=CB_HOLD;}
 else if(mode==MX_IDLE || mode==MX_HOLD){enter(g,mode,m->anim);}
 else if(mode==MX_JUMP || mode==MX_HOLDJUMP || mode==MX_AIRSLAM || mode==MX_ATOMIC){m->frame=max_counts[m->anim/2]-1;m->timer=1;}
 else idle(g);
}
static void present(Game *g){MaxCombat *m=&g->max;
 g->bk3.active=1;g->bk3.fpg=frame(m)->fpg;g->bk3.frame=m->frame;g->bk3.timer=m->timer;g->bk3.z=m->z;g->bk3.vz=m->vz;g->bk3.airvx=m->vx;g->bk3.mode=m->mode==MX_IDLE?0:m->mode==MX_JUMP?2:1;
 g->bk3.damage=frame(m)->damage;g->bk3.collision=0;g->bk3.mask=m->mask;g->bk3.hitstop=m->hitstop;g->bk3.script=m->mode==MX_SLIDE?BK_BLITZ:m->mode==MX_JUMP?BK_JUMP:BK_PUNCH1;
 g->player.attack=m->mode!=MX_IDLE && m->mode!=MX_HOLD && m->mode!=MX_LAND && !(m->mode==MX_JUMP && !m->air_attack);
 g->player.jump=m->mode==MX_JUMP || m->mode==MX_HOLDJUMP || m->mode==MX_AIRSLAM || m->mode==MX_ATOMIC;
 g->motion.z[0]=-m->z/65536.f;g->motion.vz[0]=-m->vz/65536.f;g->moves.run_dir=0;g->moves.combo=m->combo+1;g->moves.charge=0;g->combat.raw_charge=0;
}
void max_tick(Game *g,float x,float y,int attack,int jump,int special){MaxCombat *m=&g->max;Actor *p=&g->player;int dx=dir(x),dy=dir(y),i,remaining,started=0;
 (void)max_abi[0];++g->combat.ticks;++g->bk3.ticks;++m->ticks;fx_tick(g);g->rules.actor[0].depth=4;
 if(g->bk3.taptimer>0)--g->bk3.taptimer;
 if(dx && dx!=g->bk3.lastx){if(g->bk3.tapdir==dx && g->bk3.taptimer>0)g->bk3.run=dx;g->bk3.tapdir=dx;g->bk3.taptimer=16;}
 g->bk3.lastx=dx;if(dx!=g->bk3.run)g->bk3.run=0;
 if(g->moves.grab_cooldown)--g->moves.grab_cooldown;
 if(g->physics.body[0].phase)physics_body_tick(g,0);else{if(g->physics.body[0].inv)--g->physics.body[0].inv;if(p->stun)--p->stun;}
 if(reaction_player_tick(g,jump,special) || level_pickup_active(g))return;
 if(!m->active){m->active=1;enter(g,MX_IDLE,0);}
 if((p->stun || p->hp<=0 || g->physics.body[0].phase) && !(special && p->hp>8 && g->physics.body[0].phase<=BODY_HURT)){
  release(g);m->active=0;m->z=m->vz=0;g->moves.special=g->moves.invincible=0;return;
 }
 if(g->combat.action==CB_HOLD && m->mode!=MX_HOLD && m->mode!=MX_GRABHIT){enter(g,MX_HOLD,g->combat.back?0xa:8);}
 if(m->mode==MX_IDLE && m->combo_wait>0 && --m->combo_wait==0)m->combo=0;
 if(m->hitstop){--m->hitstop;present(g);return;}
 if(!m->timer){++m->frame;m->mask=0;if(m->frame>=max_counts[m->anim/2])finish(g);else m->timer=frame(m)->ticks;}
 if(special && p->hp>8 && m->mode!=MX_JUMP && m->mode!=MX_HOLDJUMP && m->mode!=MX_AIRSLAM && m->mode!=MX_ATOMIC && m->mode!=MX_NEUTRAL && m->mode!=MX_FORWARD){special_begin(g,dx);started=1;}
 if(m->mode==MX_IDLE && !started){
  if(jump){m->z=m->vx=0;m->vz=-311296;m->takeoff=4;m->direction=dx;m->air_attack=0;enter(g,MX_JUMP,4);started=1;}
  else if(attack){
   int anim=attack==3?0x62:attack==2?0x4c:m->combo==3?(m->combo_wait>=14?0x40:0x3e):m->combo==2?0x3c:0x3a;
   if(attack>=2)m->combo=0;
   if(dx && g->bk3.run==dx){m->combo=0;m->vx=327680;enter(g,MX_SLIDE,0x48);}else enter(g,MX_ATTACK,anim);
   m->combo_wait=16;
  }else{
   int anim=dx||dy?2:0;if(m->anim!=anim)enter(g,MX_IDLE,anim);
   p->x=bound(p->x+dx*.5f,10,230);p->y=bound(p->y+dy*.5f/.76f,76,126);if(dx)p->facing=dx;
   if((dx||dy) && !g->moves.grab_cooldown)for(i=0;i<4;++i)if(rules_can_grab(g,0,i+1,1)){
    g->combat.target=i;g->combat.back=g->enemies[i].facing==p->facing;g->combat.hits=0;g->combat.escape=0;rules_begin_hold(g,i);g->moves.grab=i;anchor(g);enter(g,MX_HOLD,g->combat.back?0xa:8);g->combat.action=CB_HOLD;break;
   }
  }
 }
 if(m->mode==MX_HOLD){
  if(g->combat.target<0 || !rules_hold_valid(g)){idle(g);}
  else if(dx==-p->facing && ++m->escape>=20){idle(g);}
  else{
   if(dx!=-p->facing)m->escape=0;
   if(jump && (g->combat.back || !attack)){hold_jump(g,dx);started=1;}
   else if(attack){if(g->combat.back)throw_begin(g,1);else if(dx==-p->facing)throw_begin(g,0);else{int anim=dx?++g->combat.hits>=3?0x44:0x42:0x4e;enter(g,MX_GRABHIT,anim);g->combat.action=dx?CB_KNEE:CB_HEAD;}}
   else anchor(g);
  }
 }
 if(m->mode==MX_GRABHIT){if(g->combat.target<0 || !rules_hold_valid(g))idle(g);else anchor(g);}
 remaining=max_counts[m->anim/2]-m->frame;
 if(m->mode==MX_FORWARD && remaining<=17)p->x=bound(p->x+p->facing*2.5f,10,230);
 if(m->mode==MX_SLIDE && remaining==3){p->x=bound(p->x+p->facing*m->vx/131072.f,10,230);m->vx-=8192;}
 if(m->mode==MX_THROW || m->mode==MX_AIRSLAM)throw_tick(g);
 if((m->mode==MX_JUMP || m->mode==MX_HOLDJUMP || m->mode==MX_AIRSLAM || m->mode==MX_ATOMIC) && !started){
  if(m->takeoff){--m->takeoff;if(dx)m->direction=dx;}
  else{
   m->z+=m->vz;m->vz+=16384;
   if(m->z>=0 && m->vz>=0){
    int atomic=m->mode==MX_ATOMIC,held=m->mode==MX_HOLDJUMP,ordinary=m->mode==MX_JUMP;
    m->z=0;
    if(atomic){int target=g->combat.target;collide(g);if(target>=0){Body *b=&g->physics.body[target+1];b->phase=0;b->inv=0;g->motion.z[target+1]=0;hit(g,target,0xc6,-p->facing,stage_foot_y(p->y)-32);}++m->atomic;fx_shake(g);}
    if(held && g->combat.target>=0){int target=g->combat.target;memset(&g->physics.body[target+1],0,sizeof(Body));g->enemies[target].stun=0;g->motion.z[target+1]=g->motion.vz[target+1]=0;}
    if(ordinary)enter(g,MX_LAND,0x1e);else idle(g);
    m->z=0;g->player.jump=0;fx_dust(g,0);
   }else{
    if(m->mode==MX_JUMP && attack && !m->air_attack){m->air_attack=1;enter(g,MX_JUMP,dy>0?0x38:m->direction?0x36:0x34);}
    if(m->mode==MX_HOLDJUMP && g->combat.target>=0){
     int target=g->combat.target;Body *b=&g->physics.body[target+1];b->phase=BODY_VICTIM;b->back=0;b->z=m->z;g->enemies[target].x=p->x;g->enemies[target].attack=0;victim_pose(g,target,EP_HELD,0);
     if(attack && m->z && ((!g->combat.back && m->vz<0) || (g->combat.back && m->vz>=0))){if(g->combat.back){enter(g,MX_ATOMIC,0x52);g->combat.action=CB_VAULT;}else throw_begin(g,2);}
    }
    if(m->mode!=MX_JUMP || m->anim!=0x34){int step=m->vx;if(m->direction){step+=m->direction*16384;if(step>-131072 && step<131072)m->vx=step;p->x=bound(p->x+step/131072.f,10,230);}}
    if(m->mode==MX_ATOMIC && g->combat.target>=0){int target=g->combat.target;Body *b=&g->physics.body[target+1];b->z=m->z;g->enemies[target].x=p->x;victim_pose(g,target,EP_FRONT,2);}
   }
  }
 }
 if(m->mode==MX_ATTACK || m->mode==MX_GRABHIT || m->mode==MX_SLIDE || m->mode==MX_NEUTRAL || m->mode==MX_FORWARD || (m->mode==MX_JUMP && m->air_attack))collide(g);
 present(g);if(m->timer>0)--m->timer;
 if(!bk3_machine_stats.dispatching)for(i=0;i<4;++i)source_ai_tick(g,i);
}
unsigned max_render_pose(const Game *g){const Body *b=&g->physics.body[0];int anim=0,j=0;
 if(level.enabled && level.pickup_timer)anim=0x1c;
 else if(g->reaction.shock)anim=0x1a;
 else if(g->reaction.holder>=0)anim=0x10;
 else if(b->phase){anim=b->phase==BODY_HURT?0x12:b->phase==BODY_GETUP?0x18:b->phase==BODY_FLIGHT?0x14:0x16;j=b->frame;}
 else if(g->max.active)return frame(&g->max)->fpg;
 else if(g->player.hp<=0)anim=0x16;
 if(j>=max_counts[anim/2]){j=max_counts[anim/2]-1;}return max_sequences[anim/2][j].fpg;
}
/* Independent expected SoR2 constants and state-boundary tests on the MIPS CPU. */
int max_selftest(void){Game g;unsigned saved=player_character;int i,ret=0,hp;float x;
#define CHECK(c,n) if(!(c)){ret=n;goto done;}
 player_character=PLAYER_MAX;game_reset(&g);for(i=0;i<4;++i){g.enemies[i].x=220;g.enemies[i].stun=10000;}
 x=g.player.x;max_tick(&g,1,0,0,0,0);CHECK(g.player.x-x==.5f,2401);
 CHECK(max_seq_3a[2].damage==16 && max_seq_52[0].damage==0xc6,2402);
 idle(&g);max_tick(&g,0,0,1,0,0);for(i=0;i<40;++i)max_tick(&g,0,0,0,0,0);CHECK(g.max.mode==MX_IDLE && g.max.combo==0,2403);
 idle(&g);hp=g.player.hp;special_begin(&g,0);for(i=0;i<80;++i){max_tick(&g,0,0,0,0,0);}CHECK(g.player.hp==hp,2404);
 special_begin(&g,1);for(i=0;i<80;++i){max_tick(&g,0,0,0,0,0);}CHECK(g.player.hp==hp-8,2405);
 idle(&g);g.enemies[0].hp=100;g.enemies[0].x=100;g.enemies[0].y=100;g.combat.target=0;g.combat.back=1;rules_begin_hold(&g,0);g.moves.grab=0;enter(&g,MX_HOLD,0xa);g.combat.action=CB_HOLD;
 max_tick(&g,0,0,0,1,0);CHECK(g.max.mode==MX_HOLDJUMP && g.combat.back==1,2406);
 for(i=0;i<4;++i){max_tick(&g,0,0,0,0,0);}max_tick(&g,0,0,1,0,0);CHECK(g.max.mode==MX_HOLDJUMP,2407);
 for(i=0;i<40 && g.max.mode==MX_HOLDJUMP;++i)max_tick(&g,0,0,g.max.vz>=-16384,0,0);
 CHECK(g.max.mode==MX_ATOMIC,2408);
 for(i=0;i<80;++i){max_tick(&g,0,0,0,0,0);}CHECK(g.enemies[0].hp==30 && g.max.atomic==1 && g.combat.target==-1,2409);
 game_reset(&g);for(i=0;i<4;++i){g.enemies[i].x=220;g.enemies[i].stun=10000;}
 g.enemies[0].x=80;g.combat.target=0;g.combat.back=0;rules_begin_hold(&g,0);g.moves.grab=0;enter(&g,MX_HOLD,8);g.combat.action=CB_HOLD;
 max_tick(&g,0,0,0,1,0);for(i=0;i<60 && g.max.mode==MX_HOLDJUMP;++i){max_tick(&g,0,0,0,0,0);}
 CHECK(g.combat.target==-1 && g.physics.body[1].phase==BODY_NONE && !g.motion.z[1] && g.enemies[0].hp==40,2410);
 game_reset(&g);g.player.hp=8;max_tick(&g,0,0,0,0,1);CHECK(g.max.mode==MX_IDLE && g.player.hp==8,2411);
 /* Throws carry the victim over Max and on behind him, for both facings and both grabs (regression: tables were indexed by the wrong orientation). */
 {int f,back;for(f=-1;f<=1;f+=2)for(back=0;back<2;++back){float start,rel=0,end;
  game_reset(&g);for(i=1;i<4;++i){g.enemies[i].x=220;g.enemies[i].stun=10000;}
  g.player.x=100;g.player.y=100;g.player.facing=f;g.enemies[0].y=101.3f;g.enemies[0].hp=100;g.enemies[0].x=100+f*(back?12:16);g.enemies[0].facing=back?f:-f;
  g.combat.target=0;g.combat.back=back;rules_begin_hold(&g,0);g.moves.grab=0;enter(&g,MX_HOLD,back?0xa:8);g.combat.action=CB_HOLD;
  start=(g.enemies[0].x-g.player.x)*f;max_tick(&g,back?0:-f,0,1,0,0);
  for(i=0;i<60 && g.physics.body[1].phase!=BODY_FLIGHT;++i)max_tick(&g,0,0,0,0,0);
  rel=(g.enemies[0].x-g.player.x)*f;for(i=0;i<20;++i)max_tick(&g,0,0,0,0,0);end=(g.enemies[0].x-g.player.x)*f;
  CHECK(start>0 && rel<0 && end<=rel+.01f && g.player.x==100,2412+back+(f>0?2:0));}}
 done:player_character=saved;return ret;
#undef CHECK
}
