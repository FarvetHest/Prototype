#include <pspkernel.h>
#include <pspaudio.h>
#include <string.h>
#include "sfx.h"
#include "music.h"
#include "sfx_data.h"
#define BLOCK 512
#define QUEUE 16
typedef struct { unsigned id; int pan; } Event;
typedef struct { int cursor,gain,pan,active,clip; } Voice;
volatile SfxStats sfx_stats;
unsigned sfx_test_hashes[8];
short __attribute__((aligned(64))) sfx_pcm[2][BLOCK*2];
static Event queue[QUEUE];
static volatile unsigned head,tail;
static volatile int running,paused,reset_requested;
static int thread_id=-1;
static unsigned previous_tick=~0u,previous_id;
static int clip(unsigned id){return id==0x20a?5:id==0x20b?6:id==0x217?7:id==0x26?1:id==0x21?2:id==0x32?3:id==0x346?4:0;}
static int mix(Voice *v,short *out,int frames){int f,i,peak=0;
 for(f=0;f<frames;++f){int left=0,right=0,n=0;
  for(i=0;i<4;++i)if(v[i].active){int sample=sfx_clips[v[i].clip].pcm[v[i].cursor]*v[i].gain/256;
   left+=sample*(256-v[i].pan)/256;right+=sample*v[i].pan/256;++n;
   if(++v[i].cursor>=sfx_clips[v[i].clip].frames)v[i].active=0;
  }
  if(n>1){left/=n;right/=n;}
  if(left>32767 || left< -32768 || right>32767 || right< -32768)++sfx_stats.clipped;
  if(left>32767)left=32767;
  if(left< -32768)left=-32768;
  if(right>32767)right=32767;
  if(right< -32768)right=-32768;
  out[f*2]=(short)left;out[f*2+1]=(short)right;
  if(left<0)left=-left;
  if(right<0)right=-right;
  if(left>peak)peak=left;
  if(right>peak)peak=right;
 }
 return peak;
}
void sfx_emit(unsigned id,unsigned tick,int pan){unsigned next;
 if(sfx_stats.status!=1 || (previous_tick==tick && previous_id==id && id<0x200))return;
 next=(head+1)&(QUEUE-1);if(next==tail){++sfx_stats.dropped;return;}
 if(pan<64)pan=64;
 if(pan>192)pan=192;
 queue[head]=(Event){id,pan};__asm__ volatile("sync":::"memory");head=next;
 previous_tick=tick;previous_id=id;++sfx_stats.enqueued;music_duck(id==0x20a || id==0x20b || id==0x217?1200000:180000);
}
static int worker(SceSize size,void *arg){Voice voices[4]={{0}};int channel,index=0;
 (void)size;(void)arg;
 channel=sceAudioChReserve(PSP_AUDIO_NEXT_CHANNEL,BLOCK,PSP_AUDIO_FORMAT_STEREO);
 if(channel<0){sfx_stats.status=-1;sfx_stats.error=channel;return 0;}sfx_stats.status=1;
 while(running){int i,n=0,result,peak;
  if(reset_requested){tail=head;memset(voices,0,sizeof(voices));reset_requested=0;}
  if(!paused){
   while(tail!=head){Event e;int slot=0;__asm__ volatile("sync":::"memory");e=queue[tail];tail=(tail+1)&(QUEUE-1);
    for(i=0;i<4;++i){if(!voices[i].active){slot=i;break;}if(voices[i].cursor>voices[slot].cursor)slot=i;}
    voices[slot]=(Voice){0,256,e.pan,1,clip(e.id)};++sfx_stats.played;sfx_stats.last_id=e.id;sfx_stats.last_clip=clip(e.id);++sfx_stats.clip_counts[clip(e.id)];
   }
   peak=mix(voices,sfx_pcm[index],BLOCK);if((unsigned)peak>sfx_stats.peak)sfx_stats.peak=peak;
  }else{memset(sfx_pcm[index],0,sizeof(sfx_pcm[index]));++sfx_stats.paused_blocks;}
  for(i=0;i<4;++i)n+=voices[i].active;
  sfx_stats.active=n;if((unsigned)n>sfx_stats.max_active)sfx_stats.max_active=n;
  sceKernelDcacheWritebackRange(sfx_pcm[index],sizeof(sfx_pcm[index]));
  result=sceAudioOutputPannedBlocking(channel,0x8000,0x8000,sfx_pcm[index]);
  if(result<0){sfx_stats.status=-1;sfx_stats.error=result;break;}++sfx_stats.blocks;index^=1;
 }
 {unsigned wait=0;while(sceAudioGetChannelRestLen(channel)>0 && wait++<200)sceKernelDelayThread(1000);}
 sceAudioChRelease(channel);if(sfx_stats.status>=0)sfx_stats.status=0;return 0;
}
void sfx_start(void){memset((void *)&sfx_stats,0,sizeof(sfx_stats));head=tail=0;running=1;paused=reset_requested=0;previous_tick=~0u;
 thread_id=sceKernelCreateThread("Combat SFX",worker,0x19,16*1024,PSP_THREAD_ATTR_USER,0);
 if(thread_id<0){sfx_stats.status=-1;sfx_stats.error=thread_id;return;}
 {int result=sceKernelStartThread(thread_id,0,0);if(result<0){sfx_stats.status=-1;sfx_stats.error=result;sceKernelDeleteThread(thread_id);thread_id=-1;}}
}
void sfx_pause(int value){paused=value;}
void sfx_reset(void){reset_requested=1;previous_tick=~0u;}
void sfx_stop(void){SceUInt timeout=2000000;running=0;if(thread_id>=0 && sceKernelWaitThreadEnd(thread_id,&timeout)>=0){sceKernelDeleteThread(thread_id);thread_id=-1;}}
int sfx_selftest(void){Voice v[4]={{0}};short pcm[BLOCK*2];int i,peak;
 v[0]=(Voice){0,256,128,1,0};peak=mix(v,pcm,BLOCK);if(peak<=0 || peak>14000 || v[0].cursor!=BLOCK)return 901;
 for(i=0;i<BLOCK;++i)if(pcm[i*2]!=pcm[i*2+1])return 902;
 memset(v,0,sizeof(v));mix(v,pcm,BLOCK);for(i=0;i<BLOCK*2;++i)if(pcm[i])return 903;
 for(i=0;i<4;++i){v[i]=(Voice){0,256,64,1,0};}
 peak=mix(v,pcm,BLOCK);if(peak>32767 || sfx_stats.clipped)return 904;
 for(i=0;i<4;++i){v[i]=(Voice){SFX_FRAMES-1,256,128,1,0};}
 mix(v,pcm,1);for(i=0;i<4;++i)if(v[i].active)return 905;
 for(i=0;i<SFX_CLIP_COUNT;++i){int j;unsigned hash=2166136261u;memset(v,0,sizeof(v));v[0]=(Voice){0,256,128,1,i};mix(v,pcm,BLOCK);
  for(j=0;j<BLOCK*2;++j){hash^=(unsigned short)pcm[j];hash*=16777619u;}sfx_test_hashes[i]=hash;
  for(j=0;j<i;++j)if(sfx_test_hashes[j]==hash)return 906;
  v[0]=(Voice){sfx_clips[i].frames-1,256,128,1,i};mix(v,pcm,1);if(v[0].active)return 907;
 }
 return 0;
}
