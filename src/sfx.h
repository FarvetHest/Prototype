#ifndef LITE_SFX_H
#define LITE_SFX_H
typedef struct { int status,error; unsigned enqueued,played,active,max_active,dropped,clipped,blocks,paused_blocks,peak,last_id; } SfxStats;
extern volatile SfxStats sfx_stats;
void sfx_start(void);
void sfx_emit(unsigned id,unsigned tick,int pan);
void sfx_pause(int paused);
void sfx_reset(void);
void sfx_stop(void);
int sfx_selftest(void);
#endif
