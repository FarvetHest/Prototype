#include <pspkernel.h>
#include <pspdisplay.h>
#include <pspctrl.h>
#include <pspgu.h>
#include <psppower.h>
#include <pspiofilemgr.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "game.h"
#include "sprites.h"
#include "stage.h"
#include "music.h"
#include "sfx.h"
#include "ui.h"
#include "flow.h"
#include "held.h"
#include "level.h"

PSP_MODULE_INFO("SoRR PSP Lite", 0, 0, 21);
PSP_MAIN_THREAD_ATTR(PSP_THREAD_ATTR_USER);
PSP_MAIN_THREAD_STACK_SIZE_KB(128);
PSP_HEAP_SIZE_KB(4096);

#define RGB(r,g,b) (0xff000000u | ((b)<<16) | ((g)<<8) | (r))
#define WHITE RGB(224,224,208)
static unsigned int __attribute__((aligned(16))) commands[65536];
static volatile int running = 1;
Flow flow;
Game game; /* Kept as a symbol for emulator inspection. */
unsigned int frame_count, logic_count, dropped_ticks;
unsigned int presented_buffer = 0x04000000u;
int selftest_result;
typedef struct { unsigned color; short x,y,z,pad; } Vertex;
/* Reserve vertex storage inside the uncached GU list, then submit one batch. */
#define MAX_VERTICES 8192
static Vertex *vertices;
static unsigned vertex_count, batch_start;
typedef struct { float fps, logic_hz, logic_ms, render_ms; unsigned drops, music_blocks, music_late, music_decode_us; } Sample;
static Sample samples[900], hud;
static unsigned sample_count;
unsigned show_perf;
static unsigned save_notice_until;
static int save_status; /* 1 saved, -1 failed, 0 not requested */

static int exit_callback(int a, int b, void *c) {
    (void)a; (void)b; (void)c; running = 0; return 0;
}
static int callbacks(SceSize args, void *argp) {
    int cb; (void)args; (void)argp;
    cb = sceKernelCreateCallback("Exit", exit_callback, 0);
    if (cb >= 0) sceKernelRegisterExitCallback(cb);
    sceKernelSleepThreadCB(); return 0;
}
static void rect(int x, int y, int w, int h, unsigned color) {
    Vertex *v;
    if (w <= 0 || h <= 0) return;
    if (vertex_count + 2 > MAX_VERTICES) return;
    v = vertices + vertex_count; vertex_count += 2;
    v[0] = (Vertex){color, x*2, y*2, 0, 0};
    v[1] = (Vertex){color, (x+w)*2, (y+h)*2, 0, 0};
}
/* Original 3x5 glyphs; drawn entirely by the GE, no framebuffer text writes. */
static unsigned glyph(char c) {
    static const char chars[] = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.-:/";
    static const unsigned short bits[] = {
        0x7b6f,0x2492,0x73e7,0x73cf,0x5bc9,0x79cf,0x79ef,0x7249,0x7bef,0x7bcf,
        0x2bed,0x6bae,0x7927,0x6b6e,0x79e7,0x79e4,0x796f,0x5bed,0x7497,
        0x124e,0x5bad,0x4927,0x5fed,0x5f6d,0x7b6f,0x7be4,0x7b7b,0x7bad,
        0x79cf,0x7492,0x5b6f,0x5b6a,0x5bfd,0x5aad,0x5a92,0x72a7,
        0x0002,0x01c0,0x0410,0x12a4
    };
    const char *p = strchr(chars, c);
    return p && c ? bits[p-chars] : 0;
}
static void text(int x, int y, const char *s, unsigned color) {
    for (; *s; ++s, x += 4) {
        unsigned b = glyph(*s); int row, col;
        for (row=0; row<5; ++row) for (col=0; col<3; ++col)
            if (b & (1u << (14-row*3-col))) rect(x+col,y+row,1,1,color);
    }
}
static void init_gu(void) {
    sceGuInit(); sceGuStart(GU_DIRECT, commands);
    /* Two RGB565 buffers, 512 stride, 272 rows: 557056 bytes VRAM. */
    sceGuDrawBuffer(GU_PSM_5650, (void *)0, 512);
    sceGuDispBuffer(480, 272, (void *)(512*272*2), 512);
    sceGuOffset(2048-240, 2048-136); sceGuViewport(2048,2048,480,272);
    sceGuScissor(0,0,480,272); sceGuEnable(GU_SCISSOR_TEST);
    sceGuDisable(GU_DEPTH_TEST); sceGuDisable(GU_CULL_FACE);
    sceGuDisable(GU_TEXTURE_2D); sceGuDisable(GU_BLEND);
    sceGuShadeModel(GU_FLAT); sceGuClearColor(RGB(0,0,0));
    sceGuFinish(); sceGuSync(0,0);
    sceDisplayWaitVblankStart(); sceGuDisplay(GU_TRUE);
}
static void flush_rects(void) {
    unsigned count=vertex_count-batch_start;
    if(!count) return;
    sceGuDisable(GU_TEXTURE_2D);sceGuDisable(GU_ALPHA_TEST);sceGuDisable(GU_BLEND);
    sceGuDrawArray(GU_SPRITES,GU_COLOR_8888|GU_VERTEX_16BIT|GU_TRANSFORM_2D,count,0,vertices+batch_start);
    batch_start=vertex_count;
}
static void render(void) {
    int i,j,order[5]={0,1,2,3,4}; char line[64];
    Actor *actors[5] = {&game.player,&game.enemies[0],&game.enemies[1],&game.enemies[2],&game.enemies[3]};
    sceGuStart(GU_DIRECT,commands); sceGuClear(GU_COLOR_BUFFER_BIT);
    vertices = (Vertex *)sceGuGetMemory(MAX_VERTICES * sizeof(Vertex)); vertex_count = batch_start = 0;
    stage_draw();
    ui_begin();ui_food();ui_end();
    for(i=1;i<5;++i) { int k=order[i]; j=i; while(j && actors[order[j-1]]->y>actors[k]->y) {order[j]=order[j-1]; --j;} order[j]=k; }
    for(i=0;i<5;++i) if(!i || !level.enabled || (level.slots&(1<<(i-1))))rect((int)actors[i]->x-7,stage_foot_y(actors[i]->y)/2-1,14,2,RGB(24,24,32));
    flush_rects();
    sprites_begin();
    for(i=0;i<5;++i) { j=order[i];if(!j || !level.enabled || (level.slots&(1<<(j-1))))sprites_draw(actors[j],j); }
    if(flow.state==FLOW_TITLE || flow.state>=FLOW_CONTINUE) {
        rect(40,44,160,56,RGB(8,12,24));flush_rects();
    }
    ui_begin();ui_draw(&game,selftest_result);
    if(frame_count<save_notice_until) ui_text(340,8,save_status>0?"CSV SAVED":"CSV ERROR");
    if(music_stats.status<0)ui_text(320,26,"MUSIC ERROR");
    else if(music_muted)ui_text(328,26,"MUSIC OFF");
    ui_end();
    if(level.enabled && level.go && flow.state==FLOW_PLAY && !game.paused && ((level.timer/15)&1)==0){
        int bob=level_go_bob(&level); /* arrow slides sideways so "go on" reads as motion, not just a blink */
        rect(207+bob,43,14,4,RGB(255,224,32));for(i=0;i<7;++i)rect(219+i+bob,38+i,1,14-i*2,RGB(255,224,32));
    }
    /* Blinds transition (no alpha blending needed): fade-in at the start of a run, fade-out at the exit. */
    if(flow.state==FLOW_PLAY && level_fade(&level)>0){
        int y,bar=level_fade(&level);
        for(y=0;y<136;y+=8)rect(0,y,240,bar,RGB(0,0,0));
    }
    if(show_perf) {
        rect(0,123,240,13,RGB(0,0,0));
        snprintf(line,sizeof(line),"FPS %.1f LOG %.1f",hud.fps,hud.logic_hz);text(3,124,line,WHITE);
        snprintf(line,sizeof(line),"L %.2f R %.2f MS D %u",hud.logic_ms,hud.render_ms,hud.drops);text(3,131,line,WHITE);
    }
    flush_rects();
    sprites_end();
    sceGuFinish(); sceGuSync(GU_SYNC_FINISH,GU_SYNC_WHAT_DONE);
}
static void save_profile(void) {
    unsigned i; int failed=0;
    FILE *f = fopen("lite-profile.csv","w");
    if (!f) {save_status=-1; return;}
    if (fprintf(f,"# SoRR PSP Lite v0.21; selftest=%d; cpu_mhz=%d; samples=%u; capacity=900; music_status=%d; music_error=%d; rate=%u; loops=%u\n", selftest_result,scePowerGetCpuClockFrequencyInt(),sample_count,music_stats.status,music_stats.error,music_stats.rate,music_stats.loops)<0) failed=1;
    if (fprintf(f,"sample,fps,logic_hz,logic_ms,render_sync_ms,dropped_ticks_total,music_blocks,music_late,music_decode_max_ms\n")<0) failed=1;
    for(i=0;i<sample_count;++i) {
        Sample *s=&samples[i];
        if (fprintf(f,"%u,%.3f,%.3f,%.4f,%.4f,%u,%u,%u,%.4f\n",i,s->fps,s->logic_hz,s->logic_ms,s->render_ms,s->drops,s->music_blocks,s->music_late,s->music_decode_us/1000.0)<0) failed=1;
    }
    if(fclose(f)) failed=1;
    save_status=failed?-1:1;
}
static void apply_flow_request(void) {
    if(flow.request==FLOW_RESET_NEW) {
        game_reset(&game);level_start(&level,&game);sprites_reset(&game);ui_reset(&game);
        music_restart();sfx_reset();show_perf=0;
    } else if(flow.request==FLOW_RESET_LIFE) {
        game_respawn(&game);level_cancel_pickup(&level);sprites_reset(&game);ui_reset(&game);
        ui_score=flow.score;sfx_reset();
    }
    if(flow.request)held_reset();
    flow.request=FLOW_RESET_NONE;
}
int main(void) {
    SceCtrlData pad; unsigned previous=0, pending=0, last_vblank;
    uint64_t prev, window, accum=0, logic_us=0, render_us=0;
    unsigned nf=0,nl=0; int th;
    th=sceKernelCreateThread("callbacks",callbacks,0x11,0x1000,PSP_THREAD_ATTR_USER,0);
    if(th>=0) sceKernelStartThread(th,0,0);
    scePowerSetClockFrequency(333,333,166);
    sceCtrlSetSamplingCycle(0); sceCtrlSetSamplingMode(PSP_CTRL_MODE_ANALOG);
    selftest_result=game_selftest(); if(!selftest_result)selftest_result=sprites_selftest(); if(!selftest_result)selftest_result=flow_selftest(); if(!selftest_result)selftest_result=held_selftest(); if(!selftest_result)selftest_result=level_selftest(); if(!selftest_result)selftest_result=level_boss_selftest(); if(!selftest_result)selftest_result=level_entry_selftest(); flow_init(&flow); game_reset(&game); init_gu(); sprites_init(&game); stage_init(); ui_init(&game); music_start();sfx_start();
    prev=sceKernelGetSystemTimeWide()-TICK_US; window=prev; last_vblank=sceDisplayGetVcount();
    while(running) {
        uint64_t now=sceKernelGetSystemTimeWide(), delta=now-prev, a,b;
        unsigned edges, steps=0; Input in;
        prev=now;
        /* Bound catch-up to three steps, report discarded simulation time. */
        if(delta > 3*TICK_US) { dropped_ticks+=(unsigned)((delta-3*TICK_US)/TICK_US); delta=3*TICK_US; }
        accum+=delta;
        memset(&pad,0,sizeof(pad)); pad.Lx=pad.Ly=128; sceCtrlPeekBufferPositive(&pad,1);
        edges=pad.Buttons & ~previous; previous=pad.Buttons;
        {
            int menu=flow.state==FLOW_TITLE || flow.state>=FLOW_CONTINUE;
            if(menu) {
                flow_button(&flow,(edges&(PSP_CTRL_START|PSP_CTRL_CROSS))!=0,(edges&PSP_CTRL_CIRCLE)!=0);
                pending=0;apply_flow_request();
            } else if(flow.state==FLOW_PLAY && (edges&PSP_CTRL_START)) {
                game.paused=!game.paused;pending=0;held_reset();
            }
            if((pad.Buttons&(PSP_CTRL_LTRIGGER|PSP_CTRL_RTRIGGER))==(PSP_CTRL_LTRIGGER|PSP_CTRL_RTRIGGER) &&
               (edges&(PSP_CTRL_LTRIGGER|PSP_CTRL_RTRIGGER))) {
                flow_new(&flow);apply_flow_request();pending=0;menu=1;
            }
            if(!menu && flow.state==FLOW_PLAY && (edges&PSP_CTRL_CIRCLE))show_perf=!show_perf;
            music_pause(game.paused);sfx_pause(game.paused);
            if((edges&PSP_CTRL_TRIANGLE) && (pad.Buttons&PSP_CTRL_LTRIGGER))music_toggle_mute();
            if(!menu && flow.state==FLOW_PLAY && !game.paused) {
                pending|=edges&(PSP_CTRL_SQUARE|PSP_CTRL_CROSS);
                if(!(pad.Buttons&PSP_CTRL_LTRIGGER))pending|=edges&PSP_CTRL_TRIANGLE;
            }
        }
        in.x=(pad.Lx<96 || pad.Lx>160)?((int)pad.Lx-128)/128.0f:0;
        in.y=(pad.Ly<96 || pad.Ly>160)?((int)pad.Ly-128)/128.0f:0;
        if(pad.Buttons & (PSP_CTRL_LEFT|PSP_CTRL_RIGHT)) in.x=((pad.Buttons&PSP_CTRL_RIGHT)?1:0)-((pad.Buttons&PSP_CTRL_LEFT)?1:0);
        if(pad.Buttons & (PSP_CTRL_UP|PSP_CTRL_DOWN)) in.y=((pad.Buttons&PSP_CTRL_DOWN)?1:0)-((pad.Buttons&PSP_CTRL_UP)?1:0);
        a=sceKernelGetSystemTimeWide();
        while(accum>=TICK_US && steps<3) {
            in.attack=(pending & PSP_CTRL_SQUARE)?((pad.Buttons&PSP_CTRL_RTRIGGER)?2:1):0; in.jump=(pending & PSP_CTRL_CROSS)!=0; in.special=(pending & PSP_CTRL_TRIANGLE)!=0; pending=0;
            if(!selftest_result) {
                if(flow.state==FLOW_PLAY) { if(level_pickup_button(&level,&game,in.attack,in.jump,in.special)){held_reset();in=(Input){0};}
                    else in.attack=held_tick(&game,(pad.Buttons&PSP_CTRL_SQUARE)!=0,in.attack,(pad.Buttons&PSP_CTRL_RTRIGGER)!=0);
                    game_step(&game,in);ui_step(&game);
                    level_step(&level,&game);
                    if(level.spawn_mask){ui_spawn_enemies(&game,level.spawn_mask);sprites_spawn_enemies(&game,level.spawn_mask);level.spawn_mask=0;}
                    sprites_step(&game);ui_health_sync(&game); }
                if(flow.state!=FLOW_PLAY)held_reset();
                flow_tick(&flow,&game,ui_score);apply_flow_request();
            }
            accum-=TICK_US; ++steps; ++logic_count; ++nl;
        }
        b=sceKernelGetSystemTimeWide(); logic_us+=b-a;
        render(); a=sceKernelGetSystemTimeWide(); render_us+=a-b;
        /* Anchor to the previous presentation; GPU time consumes the same budget. */
        while(running && (unsigned)(sceDisplayGetVcount()-last_vblank)<2) sceDisplayWaitVblankStartCB();
        if(!running) break;
        { unsigned next=(unsigned)sceGuSwapBuffers();
          presented_buffer=0x04000000u+(next==0?512*272*2:0); }
        last_vblank=sceDisplayGetVcount(); ++frame_count; ++nf;
        now=sceKernelGetSystemTimeWide();
        if(now-window>=1000000) {
            double seconds=(now-window)/1000000.0;
            hud=(Sample){nf/seconds,nl/seconds,nl?logic_us/(1000.0*nl):0,nf?render_us/(1000.0*nf):0,dropped_ticks,music_stats.blocks,music_stats.late_blocks,music_stats.max_decode_us};
            if(sample_count<900) samples[sample_count++]=hud;
            window=now; nf=nl=0; logic_us=render_us=0;
        }
        if(edges & PSP_CTRL_SELECT) {
            save_profile(); save_notice_until=frame_count+90; /* Deliberate I/O excluded from subsequent timing. */
            prev=sceKernelGetSystemTimeWide(); accum=0;
            window=prev; nf=nl=0; logic_us=render_us=0;
            last_vblank=sceDisplayGetVcount();
        }
    }
    save_profile();sfx_stop(); music_stop(); sceGuTerm(); sceKernelExitGame(); return 0;
}
