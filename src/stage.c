#include <pspkernel.h>
#include <pspgu.h>
#include "stage.h"
#include "level.h"
#include "stage_data.h"
extern const unsigned char stage_texture[];
typedef struct {short u,v,x,y,z;} StageVertex;
static const unsigned char *texture;
unsigned stage_draw_count,stage_slice_count;
int stage_foot_y(float world_y){return 220+(int)((world_y-76)*.76f);}
void stage_init(void){texture=stage_texture;sceKernelDcacheWritebackRange((void *)texture,STAGE_BYTES);}
void stage_draw(void){
 int camera=level.enabled?(int)(level.camera*2):0,x=0,count=0,batch=0,page=-1;
 StageVertex *v=(StageVertex *)sceGuGetMemory(34*sizeof(StageVertex));
 sceGuEnable(GU_TEXTURE_2D);sceGuDisable(GU_ALPHA_TEST);sceGuDisable(GU_BLEND);
 sceGuTexMode(GU_PSM_5650,0,0,GU_TRUE);sceGuTexFunc(GU_TFX_REPLACE,GU_TCC_RGB);
 sceGuTexFilter(GU_NEAREST,GU_NEAREST);sceGuTexWrap(GU_CLAMP,GU_CLAMP);
 stage_draw_count=stage_slice_count=0;
 while(x<480){int world=camera+x,next=world/512,u=world%512,width=32-world%32;
  if(width>480-x)width=480-x;
  if(next!=page){
   if(count>batch){sceGuDrawArray(GU_SPRITES,GU_TEXTURE_16BIT|GU_VERTEX_16BIT|GU_TRANSFORM_2D,count-batch,0,v+batch);++stage_draw_count;}
   page=next;batch=count;sceGuTexImage(0,512,256,512,texture+page*262144);sceGuTexFlush();
  }
  v[count++]=(StageVertex){u,0,x,32,0};v[count++]=(StageVertex){u+width,240,x+width,272,0};
  x+=width;++stage_slice_count;
 }
 if(count>batch){sceGuDrawArray(GU_SPRITES,GU_TEXTURE_16BIT|GU_VERTEX_16BIT|GU_TRANSFORM_2D,count-batch,0,v+batch);++stage_draw_count;}
}
