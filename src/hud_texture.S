.section .rodata
.balign 16
.global hud_texture
.type hud_texture, @object
hud_texture:
.incbin "assets/hud.rgba"
.size hud_texture, . - hud_texture
