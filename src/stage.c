#include <pspkernel.h>
#include <pspge.h>
#include <pspgu.h>
#include <string.h>
#include "stage.h"
extern const unsigned char stage_texture[];
typedef struct { short u,v,x,y,z; } StageVertex;
static void *texture;
unsigned stage_draw_count;
int stage_foot_y(float world_y) { return 220+(int)((world_y-76)*0.76f); }
void stage_init(void) {
    texture=(unsigned char *)sceGeEdramGetAddr()+1343488;
    memcpy((void *)((unsigned)texture|0x40000000u),stage_texture,512*256*2);
    sceKernelDcacheWritebackAll();
}
void stage_draw(void) {
    int i;StageVertex *v=(StageVertex *)sceGuGetMemory(30*sizeof(StageVertex));
    sceGuEnable(GU_TEXTURE_2D);sceGuDisable(GU_ALPHA_TEST);sceGuDisable(GU_BLEND);
    sceGuTexMode(GU_PSM_5650,0,0,GU_TRUE);sceGuTexImage(0,512,256,512,texture);
    sceGuTexFunc(GU_TFX_REPLACE,GU_TCC_RGB);sceGuTexFilter(GU_NEAREST,GU_NEAREST);
    sceGuTexWrap(GU_CLAMP,GU_CLAMP);
    for(i=0;i<15;++i) {
        v[i*2]=(StageVertex){i*32,0,i*32,32,0};
        v[i*2+1]=(StageVertex){i*32+32,240,i*32+32,272,0};
    }
    sceGuDrawArray(GU_SPRITES,GU_TEXTURE_16BIT|GU_VERTEX_16BIT|GU_TRANSFORM_2D,30,0,v);
    stage_draw_count=1;
}
