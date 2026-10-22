.section .rodata
.balign 16
.global stage_texture
.type stage_texture, @object
stage_texture:
.incbin "assets/stage.rgb565"
.size stage_texture, . - stage_texture
