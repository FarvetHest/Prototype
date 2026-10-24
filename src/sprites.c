#include <pspkernel.h>
#include <pspge.h>
#include <pspgu.h>
#include <string.h>
#include "sprites.h"
#include "stage.h"
#include "level.h"
#include "sprite_data.h"

#define TEXTURE_BYTES (512*512*3)
#define TEXTURE_VRAM_OFFSET (512*272*2*2)
typedef struct { short u,v; unsigned color; short x,y,z,pad; } SpriteVertex;
typedef struct { float x,y; unsigned phase; } Animation;
static Animation animation[5];
static float actor_lift[5];
static int actor_family[5];
static void *texture_vram;
unsigned actor_frames[5],actor_states[5];
unsigned actor_visibility[5]={1,1,1,1,1};
unsigned sprite_draw_count,sprite_slice_count,missing_sprite_frames,missing_sprite_family,missing_sprite_id;
static unsigned frame_draws,frame_slices;
static const Actor *get_actor(const Game *g,int i) { return i ? &g->enemies[i-1] : &g->player; }
static int family(int i) { return actor_family[i]; }
static const SpriteFrame *find_frame(int set,unsigned id) {
    unsigned i;
    for(i=0;i<SPRITE_FRAME_COUNT;++i) if(sprite_frames[i].family==set && sprite_frames[i].id==(int)id) return &sprite_frames[i];
    ++missing_sprite_frames;missing_sprite_family=(unsigned)set;missing_sprite_id=id;return &sprite_frames[0];
}
void sprites_reset(const Game *g) {
    int i;
    for(i=0;i<5;++i) {
        const Actor *a=get_actor(g,i);
        actor_visibility[i]=i?death_visible(g,i-1):1;actor_family[i]=i?enemy_type(g,i-1)+1:0;actor_lift[i]=0;animation[i]=(Animation){a->x,a->y,0}; actor_frames[i]=i?enemy_frames(g,i-1,EP_IDLE)[0].fpg:1; actor_states[i]=ANIM_IDLE;
    }
}
void sprites_spawn_enemies(const Game *g,unsigned mask){int i;for(i=0;i<4;++i)if(mask&(1u<<i)){
 actor_family[i+1]=enemy_type(g,i)+1;const Actor *a=&g->enemies[i];animation[i+1]=(Animation){a->x,a->y,0};actor_lift[i+1]=0;
 actor_states[i+1]=ANIM_IDLE;actor_frames[i+1]=enemy_frames(g,i,EP_IDLE)[0].fpg;
}}
void sprites_init(const Game *g) {
    /* One fixed atlas upload. Total reserved VRAM: 1343488 of 2097152 bytes. */
    texture_vram=(unsigned char *)sceGeEdramGetAddr()+TEXTURE_VRAM_OFFSET;
    memcpy((void *)((unsigned)texture_vram|0x40000000u),sprite_atlas,TEXTURE_BYTES);
    sceKernelDcacheWritebackAll();
    sprites_reset(g);
}
void sprites_step(const Game *g) {
    int i;
    if(g->paused) return;
    for(i=0;i<5;++i) {
        actor_visibility[i]=i?death_visible(g,i-1):1;actor_family[i]=i?enemy_type(g,i-1)+1:0;const Actor *a=get_actor(g,i); Animation *v=&animation[i];
        unsigned state=ANIM_IDLE, frame=1, set=family(i);
        int moved=(a->x!=v->x || a->y!=v->y),finished=(g->won || g->player.hp<=0);
        if(a->hp<=0 || (i && g->moves.down[i-1])) state=ANIM_DOWN;
        else if(!finished && !i && g->moves.special) state=ANIM_SPECIAL;
        else if(!finished && !i && g->moves.roll) state=ANIM_ROLL;
        else if(!finished && !i && g->moves.grab>=0) state=ANIM_GRAB;
        else if(!finished && a->stun) state=ANIM_HURT;
        else if(!finished && a->jump) state=ANIM_JUMP;
        else if(!finished && a->attack) state=ANIM_ATTACK;
        else if(!finished && moved) state=!i && g->moves.run_dir?ANIM_RUN:ANIM_WALK;
        if(state!=actor_states[i]) v->phase=0; else ++v->phase;
        actor_states[i]=state;
        if(state==ANIM_DOWN) {
            if(set==0) frame=v->phase<4?48:v->phase<8?49:50;
            else if(a->hp<=0) frame=v->phase<4?7:v->phase<8?8:9;
            else frame=g->moves.down[i-1]>22?7:g->moves.down[i-1]>12?8:g->moves.down[i-1]>6?9:12;
        } else if(state==ANIM_RUN) {static const unsigned f[]={169,170,171,172,173};frame=f[(v->phase/2)%5];}
        else if(state==ANIM_ROLL) {static const unsigned f[]={101,102,132,133,134};frame=f[((24-g->moves.roll)*5/24)>4?4:(24-g->moves.roll)*5/24];}
        else if(state==ANIM_SPECIAL) {
            static const unsigned neutral[]={34,35,36,37,38,39,40,41,42,43},forward[]={24,25,26,27,28};
            unsigned elapsed=18-g->moves.special;
            frame=g->moves.special_forward?forward[elapsed*5/18]:neutral[elapsed*10/18];
        } else if(state==ANIM_GRAB)frame=a->attack?(a->attack>5?71:a->attack>2?72:73):68;
        else if(state==ANIM_HURT) frame=set==0?148:7;
        else if(state==ANIM_JUMP) frame=a->attack && g->moves.attack_kind==HIT_AIR?(g->motion.jump_x!=0?23:20):a->jump>18?60:a->jump>12?12:a->jump>4?13:60;
        else if(state==ANIM_ATTACK) {
            if(set==0) {
                if(g->moves.attack_kind==HIT_BLITZ){static const unsigned blitz[]={60,61,62,63,64,65,66,67};frame=blitz[(12-a->attack)*8/12];}
                else if(g->moves.attack_kind==HIT_GRAB)frame=a->attack>7?74:a->attack>3?75:76;
                else if(g->moves.combo==3)frame=a->attack>6?18:a->attack>=3?19:20;
                else frame=a->attack>6?14:a->attack>=3?(g->moves.combo==2?16:15):14;
            }
            else if(set==1) frame=a->attack>4?17:4;
            else frame=a->attack>4?5:4;
        } else if(state==ANIM_WALK) {
            if(set==0) frame=5+(v->phase/3)%4;
            else frame=1+(v->phase/4)%3;
        } else {
            if(set==0) frame=1+(v->phase/6)%4;
            else if(set==1) { static const unsigned idle[4]={1,17,18,17};frame=idle[(v->phase/7)%4]; }
            else frame=1+(v->phase/8)%3;
        }
        if(!i && g->bk3.active && a->hp>0 && !a->stun)frame=g->bk3.fpg;
        if(i)frame=g->pose[i-1].fpg?g->pose[i-1].fpg:enemy_frames(g,i-1,a->hp<=0?EP_FLOOR:EP_IDLE)[0].fpg;
        if(g->physics.body[i].phase){frame=g->physics.body[i].fpg;actor_states[i]=g->physics.body[i].phase==BODY_HURT?ANIM_HURT:ANIM_DOWN;}
        if(!i && level.enabled && level.pickup_timer && !g->physics.body[0].phase && a->hp>0){frame=910;actor_states[i]=ANIM_GRAB;}
        if(!i && g->reaction.shock && g->physics.body[0].phase==BODY_FLIGHT)frame=920+g->reaction.shock_frame;
        else if(!i && g->reaction.holder>=0)frame=g->reaction.side?923:922;
        actor_frames[i]=frame;actor_lift[i]=g->motion.z[i];
        v->x=a->x;v->y=a->y;
    }
}
void sprites_begin(void) {
    frame_draws=frame_slices=0;
    sceGuEnable(GU_TEXTURE_2D);sceGuEnable(GU_ALPHA_TEST);
    sceGuAlphaFunc(GU_GREATER,0,0xff);sceGuDisable(GU_BLEND);
    sceGuTexMode(GU_PSM_T8,0,0,GU_TRUE);sceGuTexImage(0,512,512,512,texture_vram);
    sceGuTexFunc(GU_TFX_MODULATE,GU_TCC_RGBA);sceGuTexFilter(GU_NEAREST,GU_NEAREST);
    sceGuTexWrap(GU_CLAMP,GU_CLAMP);sceGuTexScale(1,1);sceGuTexOffset(0,0);
    sceGuClutMode(GU_PSM_8888,0,255,0);
}
void sprites_draw(const Actor *a,int index) {
    if(!actor_visibility[index])return;
    int set=family(index),flip=(set==0 ? a->facing<0 : a->facing>0);
    const SpriteFrame *f=find_frame(set,actor_frames[index]);
    SpriteVertex *v;int slice,count=(f->w+31)/32,lift=0;
    int x=(int)(a->x*2),y=stage_foot_y(a->y),left;
    unsigned color=0xffffffffu;
    lift=(int)actor_lift[index];
    y-=lift;
    /* FPG control point 0 is retained, including during mirrored attacks. */
    left=x-(flip ? f->w-f->px : f->px);
    /* Source pose/palette retained during hurt; no synthetic red tint. */
    sceGuTexImage(0,512,512,512,(f->v/512<3?(const unsigned char *)texture_vram:sprite_atlas)+(f->v/512)*512*512);
    sceGuClutLoad(32,sprite_palettes[set]);
    v=(SpriteVertex *)sceGuGetMemory(count*2*sizeof(SpriteVertex));
    for(slice=0;slice<count;++slice) {
        int sx=slice*32,ex=sx+32;
        int u0,u1;
        if(ex>f->w) ex=f->w;
        u0=flip?f->u+f->w-sx:f->u+sx;u1=flip?f->u+f->w-ex:f->u+ex;
        v[slice*2]=(SpriteVertex){u0,f->v%512,color,stage_world_x(left+sx),stage_world_y(y-f->py),0,0};
        v[slice*2+1]=(SpriteVertex){u1,f->v%512+f->h,color,stage_world_x(left+ex),stage_world_y(y-f->py+f->h),0,0};
    }
    sceGuDrawArray(GU_SPRITES,GU_TEXTURE_16BIT|GU_COLOR_8888|GU_VERTEX_16BIT|GU_TRANSFORM_2D,count*2,0,v);
    ++frame_draws;frame_slices+=count;
}
void sprites_end(void) { sprite_draw_count=frame_draws;sprite_slice_count=frame_slices; }
void sprites_portrait(int type,unsigned frame){
 const SpriteFrame *f=find_frame(type+1,frame);SpriteVertex *v;int u=f->u+f->px-12,w=24,h=f->h<24?f->h:24;
 if(u<f->u)u=f->u;
 if(u+w>f->u+f->w)w=f->u+f->w-u;
 sceGuEnable(GU_TEXTURE_2D);sceGuTexMode(GU_PSM_T8,0,0,GU_TRUE);
 sceGuTexImage(0,512,512,512,(f->v/512<3?(const unsigned char *)texture_vram:sprite_atlas)+(f->v/512)*512*512);
 sceGuClutMode(GU_PSM_8888,0,255,0);sceGuClutLoad(32,sprite_palettes[type+1]);
 sceGuTexFunc(GU_TFX_MODULATE,GU_TCC_RGBA);sceGuTexFilter(GU_NEAREST,GU_NEAREST);
 v=(SpriteVertex *)sceGuGetMemory(2*sizeof(*v));v[0]=(SpriteVertex){u,f->v%512,0xffffffffu,300,28,0,0};v[1]=(SpriteVertex){u+w,f->v%512+h,0xffffffffu,300+w,28+h,0,0};
 sceGuDrawArray(GU_SPRITES,GU_TEXTURE_16BIT|GU_COLOR_8888|GU_VERTEX_16BIT|GU_TRANSFORM_2D,2,0,v);
}

/* Validate complete, non-looping attack sequences on the same selector as rendering. */
int sprites_selftest(void){
    Game g;int n;unsigned expected;
    static const unsigned blitz[]={60,61,62,63,64,65,66,67};
    static const unsigned neutral[]={34,35,36,37,38,39,40,41,42,43};
    static const unsigned forward[]={24,25,26,27,28};
    static const unsigned roll[]={101,102,132,133,134};
    game_reset(&g);sprites_reset(&g);g.moves.attack_kind=HIT_BLITZ;
    for(n=12;n>0;--n){g.player.attack=n;sprites_step(&g);if(actor_frames[0]!=blitz[(12-n)*8/12])return 101;}
    game_reset(&g);sprites_reset(&g);
    for(n=18;n>0;--n){g.moves.special=n;sprites_step(&g);if(actor_frames[0]!=neutral[(18-n)*10/18])return 102;}
    g.moves.special_forward=1;
    for(n=18;n>0;--n){g.moves.special=n;sprites_step(&g);if(actor_frames[0]!=forward[(18-n)*5/18])return 103;}
    game_reset(&g);sprites_reset(&g);g.moves.combo=1;g.moves.attack_kind=HIT_NORMAL;
    for(n=8;n>0;--n){g.player.attack=n;sprites_step(&g);expected=n>6?14:n>=3?15:14;if(actor_frames[0]!=expected)return 104;}
    g.moves.combo=2;
    for(n=8;n>0;--n){g.player.attack=n;sprites_step(&g);expected=n>6?14:n>=3?16:14;if(actor_frames[0]!=expected)return 105;}
    g.moves.combo=3;
    for(n=8;n>0;--n){g.player.attack=n;sprites_step(&g);expected=n>6?18:n>=3?19:20;if(actor_frames[0]!=expected)return 106;}
    game_reset(&g);sprites_reset(&g);g.moves.grab=0;
    for(n=8;n>0;--n){g.player.attack=n;sprites_step(&g);expected=n>5?71:n>2?72:73;if(actor_frames[0]!=expected)return 107;}
    g.moves.grab=-1;g.moves.attack_kind=HIT_GRAB;
    for(n=10;n>0;--n){g.player.attack=n;sprites_step(&g);expected=n>7?74:n>3?75:76;if(actor_frames[0]!=expected)return 108;}
    game_reset(&g);sprites_reset(&g);
    for(n=24;n>0;--n){g.moves.roll=n;sprites_step(&g);if(actor_frames[0]!=roll[(24-n)*5/24])return 109;}
    game_reset(&g);g.combat.action=CB_VAULT;g.bk3.active=1;g.motion.z[0]=64;
    for(n=900;n<=904;++n){g.bk3.fpg=n;sprites_step(&g);if(actor_frames[0]!=(unsigned)n || actor_lift[0]!=64)return 110;}
    g.combat.action=CB_NONE;g.bk3.fpg=11;sprites_step(&g);if(actor_lift[0]!=64)return 111;
    g.combat.action=CB_HOLD;g.bk3.fpg=68;g.motion.z[0]=0;sprites_step(&g);if(actor_lift[0]!=0)return 112;
    game_reset(&g);g.player.stun=1;sprites_step(&g);if(actor_frames[0]!=148 || find_frame(0,actor_frames[0])->id!=148)return 113;
    return 0;
}


