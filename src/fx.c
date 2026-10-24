#include "game.h"
#include "stage.h"
#include "fx_data.h"
#include <string.h>
#include <stdlib.h>
/* ScreenShake ($FF881D, mode 1): sub_339AE runs once per frame while the flag is set.
   Counter $FF881C increments first; at 15 the shake ends. Bit 1 of the counter selects the
   +2/-2 vertical inertia, which is added to ScreenFGVPos and clamped at 0 (loc_33A3E). The
   scroll position starts at 0 in the flat Lite arena, so the picture only moves one way. */
void fx_shake(Game *g){g->fx.shake_on=1;}
static void shake_tick(Fx *f){
 if(!f->shake_on)return;
 ++f->shake_n;
 if(f->shake_n>=15){f->shake_on=0;f->shake_n=0;f->shake_pos=0;}
 else {f->shake_pos+=(f->shake_n&2)?2:-2;if(f->shake_pos<0)f->shake_pos=0;}
 /* The port presents every second 60 Hz step. Keep whichever of the two steps moved farther from
    the swing centre, so the 15 Hz jolt keeps its source amplitude instead of aliasing to a fixed offset. */
 f->shake_view=(abs(f->shake_prev-2)>abs(f->shake_pos-2))?f->shake_prev:f->shake_pos;
 f->shake_prev=f->shake_pos;
}
/* Vertical scroll adds to the plane position, which moves the picture up. */
int fx_shake_y(const Game *g){return -g->fx.shake_view;}
/* Chk_Hit/Chk_Enemy*: $62/$63 = $303 (light) or $703 (heavy), picked from the attack box top
   (&$3F > 8). Dust is $1509 from loc_243D8. Both live in the same per-object slot (bit 3 of $58). */
static int pending_top=0;
void fx_note_attack_top(int y){pending_top=y;}
void fx_spark(Game *g,int from,int victim){FxSlot *s=&g->fx.slot[from];const Actor *v=victim?&g->enemies[victim-1]:&g->player,*a=from?&g->enemies[from-1]:&g->player;
 s->active=1;s->idx=((pending_top&63)>8)?7:3;s->count=3;s->x=(int)(v->x*2);s->y=pending_top;s->flip=a->facing<0;}
void fx_dust(Game *g,int body){FxSlot *s=&g->fx.slot[body];s->active=1;s->idx=0x15;s->count=9;s->x=s->y=0;s->flip=0;}
void fx_tick(Game *g){int i;Fx *f=&g->fx;shake_tick(f);
 for(i=0;i<5;++i){FxSlot *s=&f->slot[i];if(!s->active)continue;--s->idx;if(--s->count<0)s->active=0;}}
static unsigned colour(int v){int p=fx_palette[v&15],r=p&15,gr=(p>>4)&15,b=(p>>8)&15;
 return 0xff000000u|((b*255/14)<<16)|((gr*255/14)<<8)|(r*255/14);}
/* Map a sub_30B6 table row to its decoded frame: tiles start at 0x5DD (hit) / 0x5EA (smoke). */
static int frame_of(int row){int tile=fx_tile_word[row],size=fx_size_word[row]>>8;
 if(tile>=0x5EA)return tile<0x5F6?3+(tile-0x5EA)/4:-1;
 if(tile==0x5DD)return size==0x0A?0:1;
 return tile==0x5E6?2:-1;}
int fx_spans(const Game *g,FxSpan *out,int max){int i,n=0;
 for(i=0;i<5;++i){const FxSlot *s=&g->fx.slot[i];int row,frame,x,y,px,py;const unsigned char *p;
  if(!s->active)continue;
  row=(s->idx&0xfe)>>1;if(row>10)continue;frame=frame_of(row);if(frame<0)continue;
  if(s->idx>=0x0c && s->idx<0x16){const Actor *a=i?&g->enemies[i-1]:&g->player; /* loc_3100: smoke at the body's X, 12 above its ground Y */
   x=(int)(a->x*2);y=stage_foot_y(a->y)-12;
  }else {x=s->x-(fx_size_word[row]&255);y=s->y;}
  p=fx_frames[frame].px;
  for(py=0;py<fx_frames[frame].h;++py){px=0;
   while(px<fx_frames[frame].w){int v=p[py*fx_frames[frame].w+px],e=px;
    while(e<fx_frames[frame].w && p[py*fx_frames[frame].w+e]==v)++e;
    if(v){int sx=s->flip?fx_frames[frame].w-e:px;if(n<max)out[n++]=(FxSpan){x+sx,y+py,e-px,1,colour(v)};}
    px=e;}
  }}
 return n;}
int fx_selftest(void){Game g;int i,pos[16],view[16],seen=0;
 game_reset(&g);
 /* Shake: 14 active source frames, then rest. Position follows sub_339AE with the loc_33A3E clamp. */
 fx_shake(&g);
 for(i=1;i<=15;++i){fx_tick(&g);pos[i]=g.fx.shake_pos;view[i]=g.fx.shake_view;}
 {static const int want[15]={0,2,4,2,0,2,4,2,0,2,4,2,0,2,0};for(i=1;i<=15;++i)if(pos[i]!=want[i-1])return 1601;}
 if(g.fx.shake_on || g.fx.shake_n || fx_shake_y(&g)!=-view[15])return 1602;
 fx_tick(&g);fx_tick(&g);if(fx_shake_y(&g)!=0)return 1603;
 /* A second trigger while shaking does not restart the counter. */
 game_reset(&g);fx_shake(&g);fx_tick(&g);fx_tick(&g);fx_tick(&g);fx_shake(&g);if(g.fx.shake_n!=3)return 1604;
 /* Presented offset keeps the jolt amplitude: two-step sampling never collapses to a constant. */
 game_reset(&g);seen=0;fx_shake(&g);for(i=0;i<14;i+=2){fx_tick(&g);fx_tick(&g);if(g.fx.shake_view>=0)seen|=1<<g.fx.shake_view;}
 if(seen!=(1|16))return 1605;
 /* Light spark $303 = 4 frames of the 2x2 star; heavy $703 = 2 partial + 2 big (24x24) frames. */
 game_reset(&g);fx_note_attack_top(64+5);fx_spark(&g,0,1);
 for(i=0;i<4;++i){FxSpan sp[300];int n=fx_spans(&g,sp,300);if(!g.fx.slot[0].active || n<=0 || sp[0].y<64+5)return 1606;fx_tick(&g);}
 if(g.fx.slot[0].active)return 1607;
 game_reset(&g);fx_note_attack_top(64+9);fx_spark(&g,0,1);if(g.fx.slot[0].idx!=7 || g.fx.slot[0].count!=3)return 1608;
 {int rows[4],k;for(k=0;k<4;++k){rows[k]=frame_of((g.fx.slot[0].idx&0xfe)>>1);fx_tick(&g);}if(rows[0]!=1 || rows[1]!=1 || rows[2]!=0 || rows[3]!=0)return 1609;}
 game_reset(&g);fx_note_attack_top(64+8);fx_spark(&g,0,1);if(g.fx.slot[0].idx!=3)return 1610;
 /* Landing dust $1509: 10 frames, smoke frames 0,0,0,0,0,0,1,1,2,2 from rows 10,10,9,9,8,8,7,7,6,6. */
 game_reset(&g);fx_dust(&g,1);
 {static const int want[10]={3,3,3,3,3,3,4,4,5,5};int k;for(k=0;k<10;++k){if(!g.fx.slot[1].active || frame_of((g.fx.slot[1].idx&0xfe)>>1)!=want[k])return 1611;fx_tick(&g);}if(g.fx.slot[1].active)return 1612;}
 /* Shake belongs to thrown victims only; every knockdown makes one dust cloud (first contact), none on the bounce. */
 game_reset(&g);physics_hit(&g,1,4,1,1);g.physics.body[1].freeze=0;
 for(i=0;i<140;++i){physics_body_tick(&g,1);}
 if(g.fx.shake_on || g.fx.shake_n)return 1614;
 game_reset(&g);physics_victim_start(&g,1,0);for(i=0;i<40;++i)if(physics_victim_tick(&g,1))break;
 for(i=0;i<140;++i){physics_body_tick(&g,1);if(g.fx.shake_on)seen|=256;}
 if(!(seen&256))return 1615;
 game_reset(&g);physics_hit(&g,1,4,1,1);g.physics.body[1].freeze=0;
 {int dust_starts=0,was=0;for(i=0;i<140;++i){physics_body_tick(&g,1);if(g.fx.slot[1].active && !was)++dust_starts;was=g.fx.slot[1].active;}if(dust_starts!=1)return 1616;}
 /* Flipped sparks mirror their pixels and keep the same left edge. */
 game_reset(&g);g.enemies[0].x=100;fx_note_attack_top(70);fx_spark(&g,0,1);
 {FxSpan a[300],b[300];int na=fx_spans(&g,a,300),nb;g.fx.slot[0].flip=1;nb=fx_spans(&g,b,300);if(na!=nb || na<=0)return 1613;}
 return 0;
}
