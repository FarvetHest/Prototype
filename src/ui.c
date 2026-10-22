#include <pspkernel.h>
#include <pspge.h>
#include <pspgu.h>
#include <stdio.h>
#include <string.h>
#include "ui.h"
#include "flow.h"
#include "level.h"
#include "stage.h"
#include "hud_data.h"
#define MAX_UI_VERTICES 1024
typedef struct { short u,v,x,y,z; } UiVertex;
static UiVertex *vertices;
static unsigned count,target_age;
static int old_hp[4],old_player;
static void *texture;
unsigned ui_score,ui_timer,ui_player_hp,ui_enemy_hp,ui_draw_count;
int ui_target=-1;
static const HudFrame *find(int set,int id) {
    unsigned i;for(i=0;i<HUD_FRAME_COUNT;++i) if(hud_frames[i].set==set && hud_frames[i].id==id) return &hud_frames[i];
    return 0;
}
static void image(int set,int id,int x,int y,int clip) {
    const HudFrame *f=find(set,id);int sx,width;
    if(!f) return;
    width=clip>=0 && clip<f->w?clip:f->w;
    for(sx=0;sx<width;sx+=32) {
        int end=sx+32;if(end>width)end=width;
        if(count+2>MAX_UI_VERTICES)return;
        vertices[count++]=(UiVertex){f->u+sx,f->v,x+sx,y,0};
        vertices[count++]=(UiVertex){f->u+end,f->v+f->h,x+end,y+f->h,0};
    }
}
void ui_text(int x,int y,const char *s) {
    for(;*s;++s) {
        int code=(unsigned char)*s;
        if(code==' '){x+=4;continue;}
        if(code>='A' && code<='Z')code+='a'-'A';
        image(HUD_FUENTE,code,x,y,-1);x+=8;
    }
}
void ui_reset(const Game *g) {
    int i;ui_score=0;ui_timer=99;ui_target=-1;target_age=0;
    ui_player_hp=(unsigned)g->player.hp;ui_enemy_hp=0;old_player=g->player.hp;
    for(i=0;i<4;++i)old_hp[i]=g->enemies[i].hp;
}
void ui_init(const Game *g) {
    texture=(unsigned char *)sceGeEdramGetAddr()+1343488;
    memcpy((void *)((unsigned)texture|0x40000000u),hud_texture,256*256*4);
    sceKernelDcacheWritebackAll();ui_reset(g);
}
void ui_step(const Game *g) {
    int i;
    if(g->paused)return;
    for(i=0;i<4;++i) {
        int hp=g->enemies[i].hp;
        if(hp<old_hp[i]) {
            ui_score+=(unsigned)((old_hp[i]-hp)*5);
            if(old_hp[i]>0 && hp<=0)ui_score+=200;
            ui_target=i;target_age=90;
        }
        old_hp[i]=hp;
    }
    if(g->player.hp<old_player && g->player.hp>0) {
        float best=1000000;int closest=-1;
        for(i=0;i<4;++i)if(g->enemies[i].hp>0) {
            float dx=g->enemies[i].x-g->player.x,dy=g->enemies[i].y-g->player.y;
            float distance=dx*dx+dy*dy;if(distance<best){best=distance;closest=i;}
        }
        if(closest>=0){ui_target=closest;target_age=90;}
    }
    old_player=g->player.hp;
    if(target_age)--target_age;
    if(ui_target>=0 && g->enemies[ui_target].hp<=0 && !target_age)ui_target=-1;
    ui_player_hp=(unsigned)(g->player.hp>0?g->player.hp:0);
    ui_enemy_hp=ui_target>=0?(unsigned)(g->enemies[ui_target].hp>0?g->enemies[ui_target].hp:0):0;
    ui_timer=g->ticks/30>=99?0:99-g->ticks/30;
}
void ui_health_sync(const Game *g){old_player=g->player.hp;ui_player_hp=(unsigned)(g->player.hp>0?g->player.hp:0);}
void ui_begin(void) {
    count=0;vertices=(UiVertex *)sceGuGetMemory(MAX_UI_VERTICES*sizeof(UiVertex));
    sceGuEnable(GU_TEXTURE_2D);sceGuEnable(GU_ALPHA_TEST);sceGuDisable(GU_BLEND);
    sceGuAlphaFunc(GU_GREATER,0,0xff);
    sceGuTexMode(GU_PSM_8888,0,0,GU_TRUE);sceGuTexImage(0,256,256,256,texture);
    sceGuTexFunc(GU_TFX_REPLACE,GU_TCC_RGBA);sceGuTexFilter(GU_NEAREST,GU_NEAREST);
    sceGuTexWrap(GU_CLAMP,GU_CLAMP);
}
void ui_food(void){int i;
 if(!level.enabled || level.finished || flow.state==FLOW_TITLE)return;
 for(i=0;i<LEVEL_FOODS;++i){const Food *f=&level.food[i];int x=(int)((f->x-level.camera)*2),id=f->kind?18:4;const HudFrame *h=find(HUD_ITEM,id);
  if(f->active && h && x>=-24 && x<=504)image(HUD_ITEM,id,x-h->w/2,stage_foot_y(f->y)-h->h,-1);
 }
}
static void bar(int x,int y,unsigned hp,unsigned max) {
    if(hp>max)hp=max;
    image(HUD_BARRA,24,x,y,-1);
    if(hp)image(HUD_BARRA_AMARILLA,24,x+1,y+1,(int)(104*hp/max));
}
void ui_draw(const Game *g,int error) {
    char score[32];unsigned value=ui_score>9999999?9999999:ui_score;
    if(flow.state==FLOW_TITLE) {
        ui_text(152,98,"SORR PSP LITE");ui_text(216,118,"V0.16");
        ui_text(158,140,"START OR CROSS");
        snprintf(score,sizeof(score),"BEST %07u",flow.best>9999999?9999999:flow.best);ui_text(160,164,score);
        if(error)ui_text(180,190,"SELFTEST ERROR");
        return;
    }
    if(level.enabled){
        if(level.boss==1)ui_text(340,8,"BOSS");
        else {snprintf(score,sizeof(score),"WAVE %d OF %d",level.wave+1,LEVEL_WAVES);ui_text(320,8,score);}
        if(level.heal_notice && flow.state==FLOW_PLAY){snprintf(score,sizeof(score),"HP %d",level.heal_amount);ui_text(208,62,score);}
        if(level.boss==1 && level.boss_phase==BOSS_WINDUP && !g->paused && flow.state==FLOW_PLAY)ui_text(208,80,"WATCH");
        if(level.go && flow.state==FLOW_PLAY && !g->paused && ((level.timer/15)&1)==0)ui_text(382+level_go_bob(&level)*2,80,"GO");
        /* Wave / boss banner: steady first, then flickers out over its last half second. */
        if(level.banner>0 && flow.state==FLOW_PLAY && !g->paused && (level.banner>15 || (level.banner&4))){
            if(level.boss==1)ui_text(212,96,"WARNING");
            else {snprintf(score,sizeof(score),"WAVE %d",level.wave+1);ui_text(218,96,score);}
        }}
    image(HUD_SORR,176,8,8,-1);image(HUD_SORR,250,26,8,-1);
    snprintf(score,sizeof(score),"%07u",value);ui_text(80,8,score);
    bar(25,16,ui_player_hp,100);
    snprintf(score,sizeof(score),"X%d",flow.lives);ui_text(138,16,score);
    if(ui_target>=0 || (level.enabled && level.boss==1)) {
        int target=level.enabled && level.boss==1?LEVEL_BOSS_SLOT:ui_target;
        int boss=level_is_boss(target),galsia=(target%2)==0;
        image(galsia?HUD_GALSIA:HUD_DONOVAN,300,9,28,-1);
        ui_text(26,27,boss?"CAPTAIN":galsia?"GALSIA":"DONOVAN");bar(25,35,boss?(unsigned)(g->enemies[target].hp>0?g->enemies[target].hp:0):ui_enemy_hp,boss?LEVEL_BOSS_HP:40);
    }
    image(HUD_BARRA,24,25,47,-1);
    if(g->moves.charge)image(HUD_BARRA_AZUL,24,26,48,104*g->moves.charge/100);
    ui_text(138,47,g->moves.charge==100?"OK":"SP");
    ui_text(224,7,"TIME");
    image(HUD_FUENTE,248+(int)ui_timer/10,224,17,-1);
    image(HUD_FUENTE,248+(int)ui_timer%10,240,17,-1);
    if(error)ui_text(180,112,"SELFTEST ERROR");
    else if(flow.state==FLOW_CONTINUE) {
        ui_text(202,98,"CONTINUE");snprintf(score,sizeof(score),"%02d",(flow.timer+29)/30);ui_text(232,118,score);
        snprintf(score,sizeof(score),"CREDITS %d",flow.credits);ui_text(198,136,score);
        ui_text(158,154,"START OR CROSS");ui_text(174,174,"CIRCLE TO END");
    } else if(flow.state==FLOW_GAMEOVER || flow.state==FLOW_CLEAR) {
        ui_text(196,106,flow.state==FLOW_CLEAR?(level.enabled?"STAGE CLEAR":"ARENA CLEAR"):"GAME OVER");
        snprintf(score,sizeof(score),"SCORE %07u",value);ui_text(160,132,score);
        ui_text(166,160,"START TO TITLE");
    } else if(g->paused) {ui_text(220,112,"PAUSE");ui_text(178,130,"START TO RESUME");}
    else if(flow.state==FLOW_RESPAWN)ui_text(220,112,"READY");
    else if(g->player.hp<=0)ui_text(232,112,"KO");
    else if(flow.notice>0)ui_text(220,70,"READY");
}
void ui_end(void) {
    if(count)sceGuDrawArray(GU_SPRITES,GU_TEXTURE_16BIT|GU_VERTEX_16BIT|GU_TRANSFORM_2D,count,0,vertices);
    ui_draw_count=1;
}

