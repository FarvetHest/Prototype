#ifndef LITE_MACHINE_H
#define LITE_MACHINE_H
#include <stdint.h>
struct Game;
/* One original machine, never a 64-KiB allocation on a PSP actor/test stack. */
extern unsigned char bk3_work_ram[65536];
typedef struct { unsigned ticks,calls,skipped,faults,order[7],count,state_calls[5],last_mode[5]; int dispatching; } Bk3MachineStats;
extern Bk3MachineStats bk3_machine_stats;
uint8_t bk3_ram8(uint32_t address);
uint16_t bk3_ram16(uint32_t address);
uint32_t bk3_ram32(uint32_t address);
int bk3_put8(uint32_t address,uint8_t value);
int bk3_put16(uint32_t address,uint16_t value);
int bk3_put32(uint32_t address,uint32_t value);
uint32_t bk3_sst_address(int actor);
const char *bk3_state_label(unsigned id,unsigned mode);
void bk3_machine_reset(struct Game *g);
void bk3_machine_step(struct Game *g,float x,float y,int attack,int jump,int special);
int bk3_machine_selftest(void);
#endif
