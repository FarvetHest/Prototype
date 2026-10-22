#include <pspkernel.h>
#include <pspaudio.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "music.h"

#define BLOCK_FRAMES 2048
#define BLOCK_BYTES (BLOCK_FRAMES*4)
volatile MusicStats music_stats;
volatile int music_seek_target=-1,music_muted;
volatile int music_buffer_start[2]={-1,-1};
static volatile int playing,paused;
static int thread_id=-1;
short __attribute__((aligned(64))) music_pcm[2][BLOCK_FRAMES*2];
static char file_cache[32768];
static void fail(int code){music_stats.error=code;music_stats.status=-1;}
static unsigned le32(const unsigned char *p){return p[0]|p[1]<<8|p[2]<<16|(unsigned)p[3]<<24;}
static unsigned le16(const unsigned char *p){return p[0]|p[1]<<8;}
/* Parse RIFF chunks, including padded chunks, rather than assuming a 44-byte header. */
static int open_wave(FILE *f,long *start,unsigned *bytes){
    unsigned char h[16];int fmt=0;
    if(fread(h,1,12,f)!=12 || memcmp(h,"RIFF",4) || memcmp(h+8,"WAVE",4))return 0;
    while(fread(h,1,8,f)==8){
        unsigned n=le32(h+4);long payload=ftell(f);
        if(n>0x7fffffffu || payload<0 || payload>0x7fffffffL-(long)n-1)return 0;
        if(!memcmp(h,"fmt ",4)){
            if(n<16 || fread(h,1,16,f)!=16)return 0;
            fmt=le16(h)==1 && le16(h+2)==2 && le32(h+4)==44100 && le32(h+8)==176400 && le16(h+12)==4 && le16(h+14)==16;
        }else if(!memcmp(h,"data",4)){
            if(!fmt || !n || n%4)return 0;
            *start=payload;*bytes=n;return 1;
        }
        if(fseek(f,payload+(long)n+(n&1),SEEK_SET))return 0;
    }
    return 0;
}
static int worker(SceSize args,void *argp){
    FILE *f;int channel=-1,index=0;long start;unsigned bytes,cursor=0;
    (void)args;(void)argp;
    f=fopen("music.wav","rb");if(!f){fail(-1);return 0;}
    setvbuf(f,file_cache,_IOFBF,sizeof(file_cache));
    if(!open_wave(f,&start,&bytes)){fail(-2);goto cleanup;}
    music_stats.rate=44100;music_stats.total_frames=bytes/4;
    channel=sceAudioChReserve(PSP_AUDIO_NEXT_CHANNEL,BLOCK_FRAMES,PSP_AUDIO_FORMAT_STEREO);
    if(channel<0){fail(channel);goto cleanup;}
    music_stats.status=1;
    while(playing){
        int silent=paused,volume,result;unsigned offset=0;
        unsigned long long clock=sceKernelGetSystemTimeWide();
        music_buffer_start[index]=-1;
        if(silent){memset(music_pcm[index],0,BLOCK_BYTES);++music_stats.paused_blocks;}
        else{
            int target=music_seek_target;
            if(target>=0){
                music_seek_target=-1;
                if((unsigned)target>=music_stats.total_frames || fseek(f,start+(long)target*4,SEEK_SET)){fail(-5);break;}
                cursor=(unsigned)target*4;++music_stats.seek_done;
            }
            music_buffer_start[index]=(int)(cursor/4);
            while(offset<BLOCK_BYTES && playing){
                unsigned n=BLOCK_BYTES-offset;if(n>bytes-cursor)n=bytes-cursor;
                if(fread((char *)music_pcm[index]+offset,1,n,f)!=n){fail(-6);break;}
                offset+=n;cursor+=n;
                if(cursor==bytes){if(fseek(f,start,SEEK_SET)){fail(-7);break;}cursor=0;++music_stats.loops;}
            }
            if(music_stats.status<0 || !playing)break;
            {unsigned elapsed=(unsigned)(sceKernelGetSystemTimeWide()-clock);
             if(elapsed>music_stats.max_decode_us)music_stats.max_decode_us=elapsed;
             if(music_stats.blocks>2 && sceAudioGetChannelRestLen(channel)==0)++music_stats.late_blocks;}
        }
        /* Finish CPU writes before the system audio path consumes the buffer. */
        sceKernelDcacheWritebackRange(music_pcm[index],BLOCK_BYTES);
        volume=(silent || music_muted)?0:0x5000;
        if(music_muted)++music_stats.muted_blocks;
        result=sceAudioOutputPannedBlocking(channel,volume,volume,music_pcm[index]);
        if(result<0){fail(result);break;}
        ++music_stats.blocks;if(!silent)music_stats.frames+=BLOCK_FRAMES;
        index^=1;
    }
    if(channel>=0){unsigned waits=0;while(sceAudioGetChannelRestLen(channel)>0 && waits++<200)sceKernelDelayThread(1000);sceAudioChRelease(channel);}
cleanup:
    fclose(f);if(music_stats.status>=0)music_stats.status=0;return 0;
}
void music_start(void){
    playing=1;paused=0;music_muted=0;music_seek_target=-1;
    memset((void *)&music_stats,0,sizeof(music_stats));
    thread_id=sceKernelCreateThread("PCM music",worker,0x18,32*1024,PSP_THREAD_ATTR_USER,0);
    if(thread_id<0){fail(thread_id);return;}
    {int result=sceKernelStartThread(thread_id,0,0);if(result<0){fail(result);sceKernelDeleteThread(thread_id);thread_id=-1;}}
}
void music_pause(int value){paused=value;}
void music_restart(void){music_seek_target=0;}
void music_toggle_mute(void){music_muted=!music_muted;}
void music_stop(void){SceUInt timeout=2000000;playing=0;if(thread_id>=0 && sceKernelWaitThreadEnd(thread_id,&timeout)>=0){sceKernelDeleteThread(thread_id);thread_id=-1;}}
