/* Development executor of the original BK3 object handlers. The native game
 * still owns its actors; this isolated RAM bank is used to verify the port on
 * MIPS before replacing any live combat routines. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "bk3vm.h"
#include "bk3vm_data.h"
#include "vendor/musashi/m68k.h"
#define IMAGE_BYTES 0x300000u
#define RETURN_PC 0x2ffff0u
static unsigned char *program;
static unsigned char memory[65536] __attribute__((aligned(16)));
static unsigned call_instructions,call_done;
Bk3VmStats bk3vm_stats;
static void fault(unsigned address,int write){
 if(write)++bk3vm_stats.writes;else ++bk3vm_stats.reads;
 if(!bk3vm_stats.fault_address)bk3vm_stats.fault_address=address;
}
unsigned int m68k_read_memory_8(unsigned a){
 a&=0xffffffu;
 if(a<IMAGE_BYTES)return program[a];
 if(a>=0xff0000u)return memory[a&65535];
 fault(a,0);return 0;
}
unsigned int m68k_read_memory_16(unsigned a){return m68k_read_memory_8(a)*256u+m68k_read_memory_8(a+1);}
unsigned int m68k_read_memory_32(unsigned a){return m68k_read_memory_16(a)*65536u+m68k_read_memory_16(a+2);}
void m68k_write_memory_8(unsigned a,unsigned v){a&=0xffffffu;if(a>=0xff0000u)memory[a&65535]=(unsigned char)v;else fault(a,1);}
void m68k_write_memory_16(unsigned a,unsigned v){m68k_write_memory_8(a,v>>8);m68k_write_memory_8(a+1,v);}
void m68k_write_memory_32(unsigned a,unsigned v){m68k_write_memory_16(a,v>>16);m68k_write_memory_16(a+2,v);}
void m68k_write_memory_32_pd(unsigned a,unsigned v){m68k_write_memory_32(a,v);}
static void instruction(unsigned pc){
 bk3vm_stats.pc=pc;++call_instructions;
 if(pc==RETURN_PC){call_done=1;m68k_end_timeslice();}
 else if(call_instructions>20000 || pc==0 || pc==0x200){call_done=2;m68k_end_timeslice();}
}
static unsigned le32(const unsigned char *p){return p[0]|(unsigned)p[1]<<8|(unsigned)p[2]<<16|(unsigned)p[3]<<24;}
int bk3vm_init(const char *path){
 unsigned char h[12];unsigned i,hash=2166136261u;FILE *f;
 const unsigned hooks[]={BK3VM_PlaySound,BK3VM_GetArt,BK3VM_PlayRoutine,
  BK3VM_Chk_CharacterCollision,BK3VM_Chk_EnemyCollision};
 memset(&bk3vm_stats,0,sizeof(bk3vm_stats));
 f=fopen(path,"rb");if(!f){bk3vm_stats.error=2601;return 0;}
 if(fread(h,1,12,f)!=12 || memcmp(h,"BKA1",4) || le32(h+4)!=IMAGE_BYTES){fclose(f);bk3vm_stats.error=2602;return 0;}
 if(!program)program=malloc(IMAGE_BYTES);
 if(!program){fclose(f);bk3vm_stats.error=2603;return 0;}
 if(fread(program,1,IMAGE_BYTES,f)!=IMAGE_BYTES || fgetc(f)!=EOF){fclose(f);bk3vm_stats.error=2604;return 0;}
 fclose(f);
 for(i=0;i<IMAGE_BYTES;++i)hash=(hash^program[i])*16777619u;
 if(hash!=le32(h+8)){bk3vm_stats.error=2605;return 0;}
 for(i=0;i<sizeof(hooks)/sizeof(*hooks);++i){program[hooks[i]]=0x4e;program[hooks[i]+1]=0x75;}
 program[RETURN_PC]=0x4e;program[RETURN_PC+1]=0x71;
 m68k_init();m68k_set_cpu_type(M68K_CPU_TYPE_68000);m68k_set_instr_hook_callback(instruction);
 bk3vm_stats.ready=1;return 1;
}
static unsigned word(unsigned o){return memory[o]*256u+memory[o+1];}
const signed char *bk3vm_collision_box(unsigned id,unsigned index,int hurt){
 unsigned ptr,table=hurt?BK3VM_Data_Hit_Collision:BK3VM_Data_Atk_Collision;
 if(!bk3vm_stats.ready || !index || index>255 || (id&1) || id>=306)return 0;
 ptr=m68k_read_memory_32(table+id*2u)+index*8u;
 return ptr<IMAGE_BYTES-8?(const signed char *)(program+ptr):0;
}
static void putword(unsigned o,unsigned v){memory[o]=v>>8;memory[o+1]=v;}
static int32_t lng(unsigned o){return (int32_t)((unsigned)word(o)*65536u+word(o+2));}
static void putlong(unsigned o,int32_t v){putword(o,(uint32_t)v>>16);putword(o+2,(unsigned)v);}
static int call(unsigned entry){
 unsigned i;
 call_instructions=call_done=0;
 for(i=M68K_REG_D0;i<=M68K_REG_A6;++i)m68k_set_reg((m68k_register_t)i,0);
 /* Registers supplied by LoadEnemyObj for the E200 slot. */
 m68k_set_reg(M68K_REG_D0,word(0xe20c)*2u);
 m68k_set_reg(M68K_REG_D7,4);m68k_set_reg(M68K_REG_A1,entry);
 m68k_set_reg(M68K_REG_SR,0x2700);m68k_set_reg(M68K_REG_SP,0xfffd00);
 m68k_write_memory_32(0xfffd00,RETURN_PC);
 m68k_set_reg(M68K_REG_A0,0xffe200);m68k_set_reg(M68K_REG_PC,entry);
 m68k_execute(200000);
 bk3vm_stats.instructions+=call_instructions;
 if(call_instructions>bk3vm_stats.max_instructions)bk3vm_stats.max_instructions=call_instructions;
 return call_done==1 && !bk3vm_stats.reads && !bk3vm_stats.writes;
}
int bk3vm_probe(unsigned id,unsigned ticks){
 unsigned i;
 if(!bk3vm_stats.ready)return 2606;
 if(id<14 || id>76 || (id&1) || !ticks || ticks>3600)return 2607;
 bk3vm_stats.id=id;bk3vm_stats.ticks=0;bk3vm_stats.instructions=0;
 bk3vm_stats.max_instructions=bk3vm_stats.reads=bk3vm_stats.writes=bk3vm_stats.fault_address=0;
 memset(memory,0,sizeof(memory));
 putword(0xdf00,2);putword(0xdf0c,6);putword(0xdf40,128);putword(0xdf44,188);
 putword(0xdf28,112);putword(0xdf2a,144);putword(0xdf2c,108);putword(0xdf2e,188);
 memory[0xdf58]=128;memory[0xdf6c]=100;
 putword(0xe200,0x14);putword(0xe20c,id);putword(0xe240,280);putword(0xe244,188);
 putword(0xe230,8);putword(0xf7c0,56);putword(0xf7c2,96);
 memory[0xe258]=128;memory[0xe26c]=80;memory[0xe2df]=5;
 memory[0xe21e]=16;putword(0xe210,65535);putword(0xf60e,0xace1);
 for(i=0;i<ticks;++i){
  int64_t x,y;
  putword(0xf624,0);putword(0xf608,i);putlong(0xe250,0);putlong(0xe254,0);
  if(!call(bk3vm_entries[(id-14)/2]))return bk3vm_stats.error=2608;
  if(!i){putword(0xe200,2);memory[0xe258]=128;memory[0xe21e]|=16;putword(0xe2ce,7);}
  x=(int64_t)lng(0xe240)+lng(0xe250);y=(int64_t)lng(0xe244)+lng(0xe254);
  if(x<20*65536)x=20*65536;
  if(x>460*65536)x=460*65536;
  if(y<172*65536)y=172*65536;
  if(y>210*65536)y=210*65536;
  putlong(0xe240,(int32_t)x);putlong(0xe244,(int32_t)y);++bk3vm_stats.ticks;
 }
 bk3vm_stats.end_x=lng(0xe240);bk3vm_stats.end_y=lng(0xe244);
 bk3vm_stats.mode=word(0xe200);bk3vm_stats.animation=word(0xe20e);
 ++bk3vm_stats.completed;bk3vm_stats.error=0;return 0;
}
int bk3vm_selftest(void){unsigned id;int result;
 if(!bk3vm_stats.ready)return 0; /* Development bank is optional in a legacy run. */
 for(id=14;id<=76;id+=2){result=bk3vm_probe(id,240);if(result)return result;}
 bk3vm_stats.passed=32;return 0;
}
void bk3vm_debug_tick(void){
 unsigned id=bk3vm_stats.requested_id,ticks=bk3vm_stats.requested_ticks;
 if(id){bk3vm_stats.requested_id=0;bk3vm_stats.requested_ticks=0;bk3vm_stats.error=bk3vm_probe(id,ticks);}
}
