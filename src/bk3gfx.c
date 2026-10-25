/* Source-indexed BK3 sprites in T4 system RAM. No extra VRAM reservation and
 * no file access or page decompression during a frame. */
#include <pspkernel.h>
#include <pspgu.h>
#include <stdio.h>
#include <stdlib.h>
#include <malloc.h>
#include <string.h>
#include "game.h"
#include "bk3vm.h"
#include "bk3gfx.h"
#include "stage.h"
#include "bk3gfx_data.h"
#define PAGE_BYTES (512u*512u/2u)
#define PAGE_COUNT (sizeof(bk3gfx_pages)/sizeof(*bk3gfx_pages))
#define ACTOR_COUNT (sizeof(bk3gfx_actors)/sizeof(*bk3gfx_actors))
typedef struct {short u,v;unsigned color;short x,y,z,pad;} GfxVertex;
static unsigned char *textures;
static unsigned palette[ACTOR_COUNT][16] __attribute__((aligned(16)));
Bk3GfxStats bk3gfx_stats;
unsigned bk3gfx_preview_id;
static const Bk3GfxActor *find_actor(unsigned id){unsigned i;for(i=0;i<ACTOR_COUNT;++i)if(bk3gfx_actors[i].id==id)return &bk3gfx_actors[i];return 0;}
static int decode(unsigned char *dst,const unsigned char *src,unsigned size){
 unsigned i=0,j=0;
 while(i<size){
  unsigned ctrl=src[i++],n=(ctrl&127)+1;
  if(n>PAGE_BYTES-j)return 0;
  if(ctrl&128){unsigned char v;if(i==size)return 0;v=src[i++];while(n--)dst[j++]=v;}
  else {if(n>size-i)return 0;while(n--)dst[j++]=src[i++];}
 }
 return j==PAGE_BYTES;
}
int bk3gfx_init(const char *path){
 FILE *f;unsigned i,j,max=0;unsigned char *scratch;
 bk3gfx_stats=(Bk3GfxStats){0};f=fopen(path,"rb");if(!f){bk3gfx_stats.error=2621;return 0;}
 if(!textures)textures=memalign(16,PAGE_COUNT*PAGE_BYTES);
 for(i=0;i<PAGE_COUNT;++i)if(bk3gfx_pages[i][1]>max)max=bk3gfx_pages[i][1];
 scratch=malloc(max);
 if(!textures || !scratch){free(scratch);fclose(f);bk3gfx_stats.error=2622;return 0;}
 for(i=0;i<PAGE_COUNT;++i){
  unsigned size=bk3gfx_pages[i][1],hash=2166136261u;unsigned char *dest=textures+i*PAGE_BYTES;
  if(fseek(f,(long)bk3gfx_pages[i][0],SEEK_SET) || fread(scratch,1,size,f)!=size || !decode(dest,scratch,size))break;
  for(j=0;j<PAGE_BYTES;++j)hash=(hash^dest[j])*16777619u;
  if(hash!=bk3gfx_pages[i][2])break;
  ++bk3gfx_stats.pages;
 }
 free(scratch);fclose(f);
 if(i!=PAGE_COUNT){bk3gfx_stats.error=2623;return 0;}
 for(i=0;i<ACTOR_COUNT;++i)for(j=0;j<16;++j){
  unsigned w=bk3gfx_palettes[i][j],r=(w&14)*255/14,g=((w>>4)&14)*255/14,b=((w>>8)&14)*255/14;
  palette[i][j]=j?(0xff000000u|r|(g<<8)|(b<<16)):0;
 }
 sceKernelDcacheWritebackAll();bk3gfx_stats.bytes=PAGE_COUNT*PAGE_BYTES;bk3gfx_stats.ready=1;return 1;
}
const Bk3GfxRecord *bk3gfx_record(unsigned id,unsigned address){
 const Bk3GfxActor *a=find_actor(id);unsigned lo,hi;
 ++bk3gfx_stats.lookups;
 if(a){
  lo=a->start;hi=lo+a->count;
  while(lo<hi){unsigned mid=lo+(hi-lo)/2;if(bk3gfx_records[mid].address<address)lo=mid+1;else hi=mid;}
  if(lo<a->start+a->count && bk3gfx_records[lo].address==address)return &bk3gfx_records[lo];
 }
 ++bk3gfx_stats.missing;return 0;
}
const signed char *bk3gfx_box(unsigned id,unsigned index,int hurt){
 const Bk3GfxActor *a=find_actor(id);const unsigned short *m;unsigned k;
 if(!a || !index)return 0;
 m=bk3gfx_box_meta[a-bk3gfx_actors];k=hurt?0:2;
 return index<m[k+1]?bk3gfx_boxes[m[k]+index]:0;
}
int bk3gfx_draw(unsigned id,unsigned address,int x,int y,int facing){
 const Bk3GfxActor *a=find_actor(id);const Bk3GfxRecord *r;const Bk3GfxPose *f;
 int flip,left,count,k;GfxVertex *v;
 if(!bk3gfx_stats.ready || !a)return 0;
 r=bk3gfx_record(id,address);if(!r)return 0;
 f=&bk3gfx_poses[r->pose];flip=(facing>0)^r->flip;left=x-(flip?f->w-f->px:f->px);count=(f->w+31)/32;
 sceGuEnable(GU_TEXTURE_2D);sceGuEnable(GU_ALPHA_TEST);sceGuTexMode(GU_PSM_T4,0,0,GU_TRUE);
 sceGuTexImage(0,512,512,512,textures+f->page*PAGE_BYTES);
 sceGuClutMode(GU_PSM_8888,0,15,0);sceGuClutLoad(2,palette[a-bk3gfx_actors]);
 sceGuTexFunc(GU_TFX_MODULATE,GU_TCC_RGBA);sceGuTexFilter(GU_NEAREST,GU_NEAREST);
 v=(GfxVertex *)sceGuGetMemory(count*2*sizeof(*v));
 for(k=0;k<count;++k){int sx=k*32,ex=sx+32,u0,u1;if(ex>f->w)ex=f->w;
  u0=flip?f->u+f->w-sx:f->u+sx;u1=flip?f->u+f->w-ex:f->u+ex;
  v[k*2]=(GfxVertex){u0,f->v,0xffffffffu,stage_world_x(left+sx),stage_world_y(y-f->py),0,0};
  v[k*2+1]=(GfxVertex){u1,f->v+f->h,0xffffffffu,stage_world_x(left+ex),stage_world_y(y-f->py+f->h),0,0};
 }
 sceGuDrawArray(GU_SPRITES,GU_TEXTURE_16BIT|GU_COLOR_8888|GU_VERTEX_16BIT|GU_TRANSFORM_2D,count*2,0,v);
 sceGuTexMode(GU_PSM_T8,0,0,GU_TRUE);sceGuClutMode(GU_PSM_8888,0,255,0);++bk3gfx_stats.draws;return 1;
}
int bk3gfx_preview(unsigned slot,int x,int y,int facing){
 unsigned id;const Bk3GfxActor *a;
 if(!bk3gfx_preview_id || !slot)return 0;
 id=14+((bk3gfx_preview_id-14+(slot-1)*2)%64);a=find_actor(id);
 return a?bk3gfx_draw(id,a->first,x,y,facing):0;
}
int bk3gfx_selftest(void){
 Game g;unsigned actor,i;int hurt,type;
 if(!bk3gfx_stats.ready)return 0;
 memset(&g,0,sizeof(g));
 /* Compare the new source dispatch with the previously validated native
  * Garcia/Donovan boxes. This catches dispatch, byte width and table offsets. */
 for(type=0;type<2;++type){
  g.extra[0].type=type;
  for(hurt=0;hurt<2;++hurt){unsigned count=hurt?(type?12:9):(type?5:4);
   for(i=1;i<count;++i){
    const signed char *a=bk3gfx_box(type?16:14,i,hurt),*b=enemy_box(&g,0,(int)i,hurt);
    if(!a || !b || memcmp(a,b,8))return 2624;
   }
  }
 }
 for(actor=0;actor<ACTOR_COUNT;++actor){
  const Bk3GfxActor *a=&bk3gfx_actors[actor];
  if(a->id>76)continue;
  for(i=a->start;i<a->start+a->count;++i){
   const Bk3GfxRecord *r=&bk3gfx_records[i];
   if((r->hurt && !bk3gfx_box(a->id,r->hurt,1)) || (r->collision && !bk3gfx_box(a->id,r->collision,0)))return 2625;
   if(bk3vm_stats.ready){int kind;for(kind=0;kind<2;++kind){
    unsigned index=kind?r->hurt:r->collision;
    const signed char *native=bk3gfx_box(a->id,index,kind),*source=bk3vm_collision_box(a->id,index,kind);
    if(index && (!native || !source || memcmp(native,source,8)))return 2626;
   }}
  }
 }
 return 0;
}
