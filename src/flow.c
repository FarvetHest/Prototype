#include "flow.h"
#include "game.h"
#include <string.h>
void flow_init(Flow *f){memset(f,0,sizeof(*f));f->state=FLOW_TITLE;f->lives=3;f->credits=2;}
void flow_new(Flow *f){f->state=FLOW_PLAY;f->lives=3;f->credits=2;f->timer=0;f->notice=60;f->score=0;f->request=FLOW_RESET_NEW;++f->runs;}
void flow_button(Flow *f,int confirm,int cancel){
 if(f->state==FLOW_TITLE && confirm)flow_new(f);
 else if(f->state==FLOW_CONTINUE){
  if(cancel){f->state=FLOW_GAMEOVER;f->timer=0;}
  else if(confirm && f->credits>0){--f->credits;f->lives=3;f->state=FLOW_PLAY;f->notice=60;f->request=FLOW_RESET_LIFE;}
 }else if((f->state==FLOW_GAMEOVER || f->state==FLOW_CLEAR) && confirm){f->state=FLOW_TITLE;f->request=0;f->timer=0;}
}
void flow_tick(Flow *f,const Game *g,unsigned score){
 f->score=score;if(score>f->best)f->best=score;
 if(f->state==FLOW_PLAY){
  if(g->paused)return;
  if(f->notice>0)--f->notice;
  if(g->player.hp<=0){
   if(!g->physics.body[0].phase){--f->lives;
    if(f->lives>0){f->state=FLOW_RESPAWN;f->timer=45;}
    else if(f->credits>0){f->state=FLOW_CONTINUE;f->timer=300;}
    else f->state=FLOW_GAMEOVER;
   }
  }else if(g->won)f->state=FLOW_CLEAR;
 }else if(f->state==FLOW_RESPAWN){
  if(--f->timer<=0){f->state=FLOW_PLAY;f->notice=60;f->request=FLOW_RESET_LIFE;}
 }else if(f->state==FLOW_CONTINUE && --f->timer<=0){f->state=FLOW_GAMEOVER;f->timer=0;}
}
int flow_selftest(void){Flow f;Game g;int i;
 flow_init(&f);if(f.state!=FLOW_TITLE || f.lives!=3 || f.credits!=2)return 1001;
 flow_button(&f,1,0);if(f.state!=FLOW_PLAY || f.request!=FLOW_RESET_NEW || f.runs!=1)return 1002;
 game_reset(&g);f.request=0;g.player.hp=0;g.physics.body[0].phase=BODY_FLIGHT;flow_tick(&f,&g,123);if(f.lives!=3 || f.state!=FLOW_PLAY)return 1003;
 g.physics.body[0].phase=0;flow_tick(&f,&g,123);if(f.lives!=2 || f.state!=FLOW_RESPAWN || f.timer!=45)return 1004;
 for(i=0;i<45;++i){flow_tick(&f,&g,123);}if(f.lives!=2 || f.request!=FLOW_RESET_LIFE)return 1005;
 game_respawn(&g);if(g.player.hp!=100 || g.physics.body[0].inv!=120 || g.ticks)return 1006;
 f.lives=1;f.request=0;g.player.hp=0;flow_tick(&f,&g,500);if(f.state!=FLOW_CONTINUE || f.timer!=300 || f.best!=500)return 1007;
 flow_button(&f,1,0);if(f.lives!=3 || f.credits!=1 || f.score!=500 || f.request!=FLOW_RESET_LIFE)return 1008;
 f.state=FLOW_CONTINUE;f.timer=1;flow_tick(&f,&g,500);if(f.state!=FLOW_GAMEOVER)return 1009;
 flow_button(&f,1,0);if(f.state!=FLOW_TITLE || f.best!=500)return 1010;
 flow_button(&f,1,0);if(f.score || f.best!=500 || f.runs!=2)return 1011;
 game_reset(&g);g.won=1;flow_tick(&f,&g,900);if(f.state!=FLOW_CLEAR || f.best!=900)return 1012;
 f.state=FLOW_CONTINUE;flow_button(&f,0,1);if(f.state!=FLOW_GAMEOVER)return 1013;
 game_reset(&g);g.enemies[0].hp=17;g.enemies[1].x=180;g.ticks=200;game_respawn(&g);if(g.enemies[0].hp!=17 || g.enemies[1].x!=180)return 1014;
 f.state=FLOW_PLAY;f.lives=1;f.credits=0;g.player.hp=0;g.physics.body[0].phase=0;flow_tick(&f,&g,900);if(f.state!=FLOW_GAMEOVER)return 1015;
 return 0;
}
