#ifndef BK3VM_H
#define BK3VM_H
#ifdef _WIN32
#define BK3VM_PUBLIC __declspec(dllexport)
#else
#define BK3VM_PUBLIC
#endif
/* Original AI execution probe. Does not yet drive the native game actors. */
typedef struct {
 unsigned ready,error,id,ticks,instructions,max_instructions,reads,writes;
 unsigned pc,fault_address,completed,passed,requested_id,requested_ticks;
 int end_x,end_y;unsigned mode,animation;
} Bk3VmStats;
extern BK3VM_PUBLIC Bk3VmStats bk3vm_stats;
BK3VM_PUBLIC int bk3vm_init(const char *path);
BK3VM_PUBLIC int bk3vm_probe(unsigned id,unsigned ticks);
BK3VM_PUBLIC int bk3vm_selftest(void);
BK3VM_PUBLIC void bk3vm_debug_tick(void);
BK3VM_PUBLIC const signed char *bk3vm_collision_box(unsigned id,unsigned index,int hurt);
#endif
