.section .rodata
.balign 16
.global sprite_atlas
.type sprite_atlas, @object
sprite_atlas:
.incbin "assets/sprites.t8"
.size sprite_atlas, . - sprite_atlas
