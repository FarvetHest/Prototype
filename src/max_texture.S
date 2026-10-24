.section .rodata
.balign 16
.global max_atlas
.type max_atlas, @object
max_atlas:
.incbin "assets/max.t8"
.size max_atlas, . - max_atlas
