#ifndef LITE_MUSIC_H
#define LITE_MUSIC_H
typedef struct {
    int status,error;
    unsigned blocks,frames,loops,max_decode_us,late_blocks,rate,total_frames,seek_done,paused_blocks,muted_blocks;
} MusicStats;
extern volatile MusicStats music_stats;
extern volatile int music_seek_target;
extern volatile int music_muted;
void music_start(void);
void music_pause(int paused);
void music_restart(void);
void music_toggle_mute(void);
void music_stop(void);
#endif
