#ifndef LITE_FX_H
#define LITE_FX_H
/* BK3 impact presentation: ScreenShake mode 1 (sub_339AE), hit sparks and landing dust (sub_30B6).
   All timers are 60 Hz source frames; fx_tick runs once per combat_tick. */
typedef struct { int active,idx,count,x,y,flip; } FxSlot; /* idx/count = source bytes $62/$63 */
typedef struct { int shake_on,shake_n,shake_pos,shake_prev,shake_view; FxSlot slot[5]; } Fx;
typedef struct { int x,y,w,h; unsigned color; } FxSpan;
struct Game;
void fx_tick(struct Game *g);
void fx_shake(struct Game *g);
int fx_shake_y(const struct Game *g);
void fx_note_attack_top(int y);
void fx_spark(struct Game *g,int from,int victim);
void fx_dust(struct Game *g,int body);
int fx_spans(const struct Game *g,FxSpan *out,int max);
int fx_selftest(void);
#endif
