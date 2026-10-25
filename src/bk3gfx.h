#ifndef BK3GFX_H
#define BK3GFX_H
#include <stdint.h>
typedef struct {uint16_t page,u,v,w,h;int16_t px,py;} Bk3GfxPose;
typedef struct {uint32_t address;uint16_t pose;uint8_t flip,hurt,collision,damage;} Bk3GfxRecord;
typedef struct {uint16_t id,start,count;uint32_t first;} Bk3GfxActor;
typedef struct {unsigned ready,error,pages,bytes,lookups,missing,draws;} Bk3GfxStats;
extern Bk3GfxStats bk3gfx_stats;
extern unsigned bk3gfx_preview_id;
int bk3gfx_init(const char *path);
int bk3gfx_selftest(void);
const Bk3GfxRecord *bk3gfx_record(unsigned id,unsigned address);
const signed char *bk3gfx_box(unsigned id,unsigned index,int hurt);
int bk3gfx_draw(unsigned id,unsigned address,int x,int y,int facing);
int bk3gfx_preview(unsigned slot,int x,int y,int facing);
#endif
