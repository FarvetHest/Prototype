TARGET = sorr-lite
OBJS = src/main.o src/fx.o src/level.o src/held.o src/flow.o src/game.o src/machine.o src/death.o src/bk3.o src/combat.o src/sfx.o src/enemy.o src/variety.o src/reactions.o src/impact.o src/rules.o src/ai.o src/physics.o src/sprites.o src/sprite_atlas.o src/max_texture.o src/stage.o src/stage_texture.o src/music.o src/ui.o src/hud_texture.o
INCDIR = src
CFLAGS = -O2 -G0 -std=gnu99 -Wall -Wextra -Werror -ffunction-sections -fdata-sections
CXXFLAGS = $(CFLAGS)
ASFLAGS = $(CFLAGS)
BUILD_PRX = 1
PSP_LARGE_MEMORY = 0
LIBS = -lpspaudio -lpspgu -lpsppower -lm
LDFLAGS = -Wl,--gc-sections
EXTRA_TARGETS = EBOOT.PBP
PSP_EBOOT_TITLE = SoRR PSP Lite v0.23
SFOFLAGS = -s DISC_ID=SORL00023
PSPSDK := $(shell psp-config --pspsdk-path)
include $(PSPSDK)/lib/build.mak

src/sprite_atlas.o: assets/sprites.t8
src/sprites.o: src/sprite_data.h src/sprites.h src/game.h
src/main.o: src/game.h src/sprites.h
src/game.o: src/game.h

src/stage_texture.o: assets/stage.t8
src/stage.o: src/stage.h
src/music.o: src/music.h
src/sprites.o: src/stage.h
src/main.o: src/stage.h src/music.h

src/ui.o: src/ui.h src/hud_data.h src/game.h
src/hud_texture.o: assets/hud.rgba
src/main.o: src/ui.h

src/bk3.o: src/bk3.h src/bk3_data.h src/game.h src/stage.h
src/game.o: src/bk3.h

src/fx.o: src/fx.h src/fx_data.h src/game.h
src/combat.o: src/combat.h src/combat_data.h src/bk3_data.h src/game.h

src/physics.o: src/physics.h src/physics_data.h src/game.h

src/main.o src/game.o src/machine.o src/death.o src/bk3.o src/combat.o src/sprites.o src/ui.o: src/physics.h src/combat.h

$(OBJS): src/rules.h

$(OBJS): src/impact.h

$(OBJS): src/enemy.h
src/enemy.o: src/enemy_data.h

src/sfx.o: src/sfx.h src/sfx_data.h

src/main.o src/flow.o src/ui.o: src/flow.h

src/main.o src/held.o: src/held.h

src/main.o src/ui.o src/level.o src/stage.o: src/level.h

src/ai.o src/sprites.o: src/level.h

src/combat.o: src/level.h

src/variety.o: src/variety_data.h src/bk3_data.h src/combat_data.h src/physics_data.h

src/reactions.o src/variety.o: src/reaction_data.h

src/machine.o: src/machine_data.h src/machine.h
$(OBJS): src/machine.h

$(OBJS): src/death.h

src/max_texture.o: assets/max.t8
