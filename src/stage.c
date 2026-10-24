#include <pspkernel.h>
#include <pspgu.h>
#include "stage.h"
#include "level.h"
#include "stage_data.h"
extern const unsigned char stage_texture[];
typedef struct {short u,v,x,y,z;} StageVertex;
unsigned stage_draw_count,stage_slice_count;
/* Original NTSC height 224; preserve pixel aspect on the 480x272 PSP screen.
   Widescreen field is 395 source pixels. The 480-unit legacy combat arena is
   retained; a bounded local view follows the player within its extra 85 pixels. */
unsigned stage_native_view=1;
int stage_view_pan,stage_camera_pixels;
int stage_foot_y(float world_y){return 220+(int)((world_y-76)*.76f);}
int stage_world_x(int x){return stage_native_view?(x-stage_view_pan)*17/14:x;}
int stage_world_y(int y){return stage_native_view?(y-48)*17/14:y;}
void stage_set_view(float player_x){
 int pan=(int)(player_x*2)-197;if(pan<0)pan=0;if(pan>85)pan=85;
 stage_view_pan=stage_native_view?pan:0;
 stage_camera_pixels=(level.enabled?(int)(level.camera*2):0)+stage_view_pan;
}
void stage_init(void){sceKernelDcacheWritebackAll();}
static void plane(const unsigned char *map,const unsigned short *defs,int def_count,int priority){
 int tx,ty,count=0,first=stage_camera_pixels/8;
 int columns=stage_native_view?51:61,rows=stage_native_view?28:30;
 StageVertex *v=(StageVertex *)sceGuGetMemory(columns*rows*2*sizeof(StageVertex));
 for(ty=0;ty<rows;++ty)for(tx=first;tx<first+columns;++tx){
  int block,idx,a,tile,u0,u1,v0,v1,x,y;
  if(tx<0 || tx>=STAGE_WIDTH/8)continue;
  block=map[(ty/2)*STAGE_MAP_STRIDE+tx/2];idx=block*4+(ty&1)*2+(tx&1);
  if(idx>=def_count)continue;
  a=defs[idx];if((a>>15)!=priority)continue;
  tile=a&2047;if(!tile)continue;
  tile=tile*4+((a>>13)&3);u0=(tile%64)*8;v0=(tile/64)*8;u1=u0+8;v1=v0+8;
  if(a&2048){int t=u0;u0=u1;u1=t;}if(a&4096){int t=v0;v0=v1;v1=t;}
  x=tx*8-(stage_camera_pixels-stage_view_pan);y=ty*8+48;
  v[count++]=(StageVertex){u0,v0,stage_world_x(x),stage_world_y(y),0};
  v[count++]=(StageVertex){u1,v1,stage_world_x(x+8),stage_world_y(y+8),0};
 }
 if(count){sceGuDrawArray(GU_SPRITES,GU_TEXTURE_16BIT|GU_VERTEX_16BIT|GU_TRANSFORM_2D,count,0,v);++stage_draw_count;stage_slice_count+=count/2;}
}
static void draw(int priority){
 sceGuEnable(GU_TEXTURE_2D);sceGuEnable(GU_ALPHA_TEST);sceGuAlphaFunc(GU_GREATER,0,0xff);sceGuDisable(GU_BLEND);
 sceGuTexMode(GU_PSM_T8,0,0,GU_FALSE);sceGuTexImage(0,512,512,512,stage_texture);
 sceGuClutMode(GU_PSM_8888,0,255,0);sceGuClutLoad(8,stage_palette);
 sceGuTexFunc(GU_TFX_REPLACE,GU_TCC_RGBA);sceGuTexFilter(GU_NEAREST,GU_NEAREST);sceGuTexWrap(GU_CLAMP,GU_CLAMP);
 plane(stage_map_b,stage_defs_b,sizeof(stage_defs_b)/sizeof(stage_defs_b[0]),priority);
 plane(stage_map_a,stage_defs_a,sizeof(stage_defs_a)/sizeof(stage_defs_a[0]),priority);
}
void stage_draw(void){stage_draw_count=stage_slice_count=0;draw(0);}
void stage_draw_foreground(void){draw(1);}
