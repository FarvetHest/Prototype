Obj_Barbon:	dc.l loc_15058		; DATA XREF: ROM:0000DE0Co
		dc.l loc_1572E
		dc.l Enemy_Death
		dc.l sub_E692
		dc.l Enemy_Knockout
		dc.l Enemy_ForwardGrab
		dc.l Enemy_BackwardGrab
		dc.l Enemy_ForwardThrow
		dc.l Enemy_BackwardThrow
		dc.l loc_14E16
		dc.l Enemy_Attack
		dc.l Enemy_Attack
		dc.l sub_15682
		dc.l sub_15682
		dc.l sub_1562A
		dc.l loc_156DC
		dc.l locret_1543A
		dc.l loc_1543C
		dc.l Obj_BarbonBlock
		dc.l loc_157CA
		dc.l loc_15826
		dc.l loc_15458
		dc.l sub_E63E
		dc.l sub_15882
		dc.l sub_158AA
; ---------------------------------------------------------------------------

loc_14E16:				; DATA XREF: ROM:00014DD6o
		clr.w	d0
		move.b	Enemy_AI(a2),d0
		cmpi.b	#5,d0
		bls.s	loc_14E26
		move.b	#5,d0

loc_14E26:				; CODE XREF: ROM:00014E20j
		lsl.w	#5,d0
		lea	byte_14E82(pc,d0.w),a0
		lea	EnemyMovementData(a2),a1
		moveq	#$1F,d0

loc_14E32:				; CODE XREF: ROM:00014E34j
		move.b	(a0)+,(a1)+
		dbf	d0,loc_14E32
		move.w	EnemyMode(a2),d0
		clr.w	EnemyMode(a2)
		tst.b	d0
		beq.w	loc_14F74
		subq.b	#1,d0
		beq.w	loc_14F42
		subq.b	#1,d0
		beq.w	loc_14E5E
		subq.b	#1,d0
		beq.w	loc_14F94
		subq.b	#1,d0
		beq.w	loc_14FBC

loc_14E5E:				; CODE XREF: ROM:00014E4Ej
		lea	Pal_Wayne(pc),a6
		jsr	(Update_Palette).l
		bclr	#0,$DE(a2)
		move.w	#2,0(a2)
		andi.w	#1,$E(a2)
		ori.w	#0,$E(a2)
		rts
; ---------------------------------------------------------------------------
byte_14E82:	dc.b	$F,   $A,  $14,	 $2D,  $63,    0,  $1E,	 $32,  $28,  $1E,    6,	   6,  $3C,    8,   $A,	 $50,  $14,  $28,  $32,	   6,  $32,  $3C,    5,	   6,  $1E,  $14,    8,	   6,	 4,  $20,    0,	   0; 0
		dc.b	$F,    5,  $19,	 $2D,  $63,    0,  $14,	 $3C,  $28,  $1E,    8,	  $A,  $3C,   $C,  $14,	 $50,  $28,  $28,  $32,	   8,  $32,  $50,    6,	  $E,  $1E,  $14,  $10,	 $10,  $20,  $80,    0,	   0; 32
		dc.b	$F,    5,  $1E,	 $28,  $63,    0,  $14,	 $3C,  $28,  $1E,   $A,	  $A,  $3C,   $E,  $18,	 $52,  $28,  $28,  $32,	  $A,  $32,  $50,   $A,	  $E,  $1E,  $14,  $10,	 $10,  $30,  $90,    0,	   0; 64
		dc.b	$F,    5,  $23,	 $23,  $63,    0,  $14,	 $32,  $28,  $1E,   $C,	  $C,  $3C,  $10,  $1A,	 $54,  $28,  $28,  $32,	  $C,  $32,  $50,   $E,	  $C,  $1E,  $14,  $10,	 $10,  $40,  $A0,    0,	   0; 96
		dc.b	$F,    5,  $28,	 $1E,  $63,    0,  $14,	 $28,  $28,  $1E,   $E,	  $E,  $3C,  $12,  $1C,	 $56,  $28,  $28,  $32,	  $E,  $32,  $50,  $10,	  $A,  $1E,  $14,  $14,	 $10,  $60,  $B0,    0,	   0; 128
		dc.b	$F,    5,  $28,	 $19,  $63,    0,  $14,	 $1E,  $28,  $1E,  $10,	 $10,  $3C,  $14,  $1E,	 $58,  $28,  $28,  $32,	 $10,  $32,  $50,  $12,	  $E,  $1E,  $14,  $18,	 $10,  $80,  $C0,    0,	   0; 160
; ---------------------------------------------------------------------------

loc_14F42:				; CODE XREF: ROM:00014E48j
		lea	Pal_Barbon(pc),a6
		jsr	(Update_Palette).l
		bset	#3,$DE(a2)
		bset	#2,$DE(a2)
		bclr	#7,$49(a2)
		move.w	#$2C,0(a2) ; ','
		andi.w	#1,$E(a2)
		ori.w	#$1A,$E(a2)
		bra.w	loc_15458
; ---------------------------------------------------------------------------

loc_14F74:				; CODE XREF: ROM:00014E42j
		lea	Pal_Barbon(pc),a6
		jsr	(Update_Palette).l
		move.w	#$22,0(a2) ; '"'
		andi.w	#1,$E(a2)
		ori.w	#$20,$E(a2) ; ' '
		bra.w	locret_1543A
; ---------------------------------------------------------------------------

loc_14F94:				; CODE XREF: ROM:00014E54j
		lea	Pal_Wayne(pc),a6
		jsr	(Update_Palette).l
		bclr	#0,$DE(a2)
		move.w	#$2E,0(a2) ; '.'
		andi.w	#1,$E(a2)
		ori.w	#0,$E(a2)
		jmp	sub_E63E
; ---------------------------------------------------------------------------

loc_14FBC:				; CODE XREF: ROM:00014E5Aj
		lea	Pal_Vulture(pc),a6
		jsr	(Update_Palette).l
		move.l	#$FF000000,$5E(a2)
		addi.l	#-$1000000,6(a2)
		bset	#7,$A(a2)
		move.w	#$30,0(a2) ; '0'
		andi.w	#1,$E(a2)
		ori.w	#0,$E(a2)
		bra.w	sub_15882
; ---------------------------------------------------------------------------
Pal_Barbon:	dc.w $200F		; DATA XREF: ROM:loc_14F42t
					; ROM:loc_14F74t
		dc.w  $44A,    0,  $48,	$48E, $8CE,  $22, $244,	$466, $688, $8AA, $ACC,	  $C, $24E, $48E,  $28,	$CEE; 0
Pal_Wayne:	dc.w $200F		; DATA XREF: ROM:loc_14E5Et
					; ROM:loc_14F94t
		dc.w  $44A,    0,    4,	$248, $48A,    0, $222,	$642, $844, $866, $A88,	 $8E, $6CE, $48E,  $68,	$AAC; 0
Pal_Vulture:	dc.w $200F		; DATA XREF: ROM:loc_14FBCt
		dc.w  $44A,    0, $246,	$48A, $6AE,    2,    6,	$228, $24C, $28E, $6AE,	$666, $AA8, $48E, $222,	$8EE; 0
; ---------------------------------------------------------------------------

loc_15058:				; DATA XREF: ROM:Obj_Barbono
		jsr	(Chk_Hit).l
		jsr	(Chk_Grab).l
		bsr.w	Chk_PlayerDistance_Enemy
		bcs.w	loc_150A2
		bsr.w	Update_SpriteOrientation

loc_15070:				; CODE XREF: ROM:000150A0j
		move.w	EnemyMode(a2),d4
		add.w	d4,d4
		lea	off_1507E(pc,d4.w),a1
		adda.w	(a1),a1
		jmp	(a1)
; ---------------------------------------------------------------------------
off_1507E:	dc.w loc_150D4-off_1507E ; DATA	XREF: ROM:off_1507Eo
off_15080:	dc.w loc_1514E-off_15080 ; DATA	XREF: ROM:off_15080o
off_15082:	dc.w loc_15144-off_15082 ; DATA	XREF: ROM:off_15082o
off_15084:	dc.w loc_1510A-off_15084 ; DATA	XREF: ROM:off_15084o
off_15086:	dc.w loc_150FA-off_15086 ; DATA	XREF: ROM:off_15086o
off_15088:	dc.w loc_15120-off_15088 ; DATA	XREF: ROM:off_15088o
off_1508A:	dc.w loc_15132-off_1508A ; DATA	XREF: ROM:off_1508Ao
off_1508C:	dc.w loc_15098-off_1508C ; DATA	XREF: ROM:off_1508Co
off_1508E:	dc.w loc_15180-off_1508E ; DATA	XREF: ROM:off_1508Eo
off_15090:	dc.w loc_151CC-off_15090 ; DATA	XREF: ROM:off_15090o
off_15092:	dc.w loc_1520C-off_15092 ; DATA	XREF: ROM:off_15092o
off_15094:	dc.w loc_15242-off_15094 ; DATA	XREF: ROM:off_15094o
off_15096:	dc.w loc_15174-off_15096 ; DATA	XREF: ROM:off_15096o
; ---------------------------------------------------------------------------

loc_15098:				; DATA XREF: ROM:off_1508Co
		bsr.w	Set_Enemy_Mode_5
		bsr.w	Chk_PlayerDistance_Boss
		bra.s	loc_15070
; ---------------------------------------------------------------------------

loc_150A2:				; CODE XREF: ROM:00015068j
		bsr.w	Chk_PlayerDistance_Boss
		bcs.w	loc_150D4
		bsr.w	Update_SpriteOrientation
		move.w	#2,$D0(a2)
		move.w	#$80,d0	; '�'
		bsr.w	Get_MovementMode_ID
		bcs.w	loc_150D4
		tst.w	d0
		bmi.w	loc_150D4
		move.w	d0,$D2(a2)
		move.w	#$C,$D6(a2)
		bra.w	loc_15174
; ---------------------------------------------------------------------------

loc_150D4:				; CODE XREF: ROM:000150A6j
					; ROM:000150BCj ...
		andi.w	#1,$E(a2)
		ori.w	#0,$E(a2)
		move.l	#0,$44(a2)
		move.l	#0,$40(a2)

loc_150F0:				; CODE XREF: ROM:0001517Cj
		subq.w	#1,$D0(a2)
		bmi.w	loc_15278
		rts
; ---------------------------------------------------------------------------

loc_150FA:				; DATA XREF: ROM:off_15086o
		move.w	$D4(a2),d0
		bsr.w	Update_RandomMovement
		move.w	d0,MovementMode_ID(a2) ; 0   Up
					; 1   Up-Right
					; 2   Right
					; 3   Down-Right
					; 4   Down
					; 5   Down - Left
					; 6   Left
					; 7   Up-Left
		bra.w	loc_1514E
; ---------------------------------------------------------------------------

loc_1510A:				; DATA XREF: ROM:off_15084o
		move.w	$D4(a2),d0
		bsr.w	Get_MovementMode_ID
		bcs.s	loc_150D4
		tst.w	d0
		bmi.s	loc_150D4
		move.w	d0,$D2(a2)
		bra.w	loc_1514E
; ---------------------------------------------------------------------------

loc_15120:				; DATA XREF: ROM:off_15088o
		bsr.w	Update_EnemyMovement
		bcs.s	loc_150D4
		bchg	#2,d0
		move.w	d0,$D2(a2)
		bra.w	loc_15174
; ---------------------------------------------------------------------------

loc_15132:				; DATA XREF: ROM:off_1508Ao
		bsr.w	Update_EnemyMovement
		bcs.s	loc_150D4
		add.w	$D4(a2),d0
		move.w	d0,$D2(a2)
		bra.w	loc_15174
; ---------------------------------------------------------------------------

loc_15144:				; DATA XREF: ROM:off_15082o
		bsr.w	Update_EnemyMovement
		bcs.s	loc_150D4
		move.w	d0,$D2(a2)

loc_1514E:				; CODE XREF: ROM:00015106j
					; ROM:0001511Cj
					; DATA XREF: ...
		btst	#7,$49(a0)
		beq.w	loc_15174
		move.w	d2,d0
		add.w	d3,d0
		cmpi.w	#$1E,d0
		bcs.w	loc_15278
		cmpi.w	#6,d3
		bhi.w	loc_15174
		cmpi.w	#$3C,d2	; '<'
		bcs.w	loc_15278

loc_15174:				; CODE XREF: ROM:000150D0j
					; ROM:0001512Ej ...
		move.w	#4,d3
		bsr.w	Update_EnemyMoveInertia
		bra.w	loc_150F0
; ---------------------------------------------------------------------------

loc_15180:				; DATA XREF: ROM:off_1508Eo
		cmpi.w	#7,d3
		bhi.w	loc_152BE
		cmpi.w	#$3D,d2	; '='
		bhi.w	loc_152BE
		subq.w	#1,$D0(a2)
		bpl.w	locret_151CA
		addq.w	#1,$CE(a2)
		move.w	#8,d0
		bsr.w	Get_RandomValue2
		addq.w	#4,d0
		move.w	d0,$D0(a2)
		move.w	#$16,0(a2)
		andi.w	#1,$E(a2)
		ori.w	#$3A,$E(a2) ; ':'
		move.l	#$74D,d0
		moveq	#0,d1
		jsr	PlaySound

locret_151CA:				; CODE XREF: ROM:00015194j
					; ROM:000151E0j
		rts
; ---------------------------------------------------------------------------

loc_151CC:				; DATA XREF: ROM:off_15090o
		cmpi.w	#7,d3
		bhi.w	loc_152BE
		cmpi.w	#$3D,d2	; '='
		bhi.w	loc_152BE
		subq.w	#1,$D0(a2)
		bpl.s	locret_151CA
		addq.w	#1,$CE(a2)
		clr.w	$D0(a2)
		move.w	#$16,0(a2)
		andi.w	#1,$E(a2)
		ori.w	#$3A,$E(a2) ; ':'
		move.l	#$74D,d0
		moveq	#0,d1
		jsr	PlaySound
		rts
; ---------------------------------------------------------------------------

loc_1520C:				; DATA XREF: ROM:off_15092o
		cmpi.w	#7,d3
		bhi.w	loc_152BE
		cmpi.w	#$4A,d2	; 'J'
		bhi.w	loc_152BE
		cmpi.w	#$36,d2	; '6'
		bhi.w	loc_15242
		move.w	#7,$CE(a2)
		clr.w	$D0(a2)
		move.w	#$18,0(a2)
		andi.w	#1,$E(a2)
		ori.w	#$3C,$E(a2) ; '<'
		rts
; ---------------------------------------------------------------------------

loc_15242:				; CODE XREF: ROM:00015220j
					; DATA XREF: ROM:off_15094o
		clr.w	$CE(a2)
		clr.w	$D0(a2)
		move.l	#$FFE00000,$40(a2)
		btst	#0,$F(a2)
		beq.w	loc_15264
		neg.l	$40(a2)
		bra.w	*+4

loc_15264:				; CODE XREF: ROM:00015258j
		move.w	#$1E,0(a2)
		andi.w	#1,$E(a2)
		ori.w	#$3E,$E(a2) ; '>'
		rts
; ---------------------------------------------------------------------------

loc_15278:				; CODE XREF: ROM:000150F4j
					; ROM:00015160j ...
		bsr.w	Chk_PlayerDistance_Enemy
		bcs.w	Set_Enemy_Mode_0
		cmpi.w	#$20,d0	; ' '
		bcs.w	loc_1535A
		cmpi.w	#$A0,d0	; '�'
		bhi.w	Set_Enemy_Mode_6
		cmpi.w	#7,d3
		bhi.w	loc_152BE
		cmpi.w	#$14,d2
		bcs.w	loc_1535A

loc_152A0:				; CODE XREF: ROM:00015360j
					; ROM:0001536Aj ...
		btst	#7,$49(a0)
		beq.w	loc_152BE
		cmpi.w	#$3E,d2	; '>'
		bcs.w	loc_152F6
		cmpi.w	#$4A,d2	; 'J'
		bcs.w	loc_15352
		bra.w	loc_152C4
; ---------------------------------------------------------------------------

loc_152BE:				; CODE XREF: ROM:00015184j
					; ROM:0001518Cj ...
		bsr.w	Update_EnemyMode
		rts
; ---------------------------------------------------------------------------

loc_152C4:				; CODE XREF: ROM:000152BAj
		move.w	#$C,$CE(a2)
		move.w	#$15,$D6(a2)
		cmpi.w	#1,d3
		bhi.s	loc_152DA
		move.b	($FFFFFC11).w,d1

loc_152DA:				; CODE XREF: ROM:000152D4j
		andi.w	#2,d1
		add.w	d1,d1
		move.w	d1,$D2(a2)
		move.w	#$14,d0
		bsr.w	Get_RandomValue2
		addi.w	#$F,d0
		move.w	d0,$D0(a2)
		rts
; ---------------------------------------------------------------------------

loc_152F6:				; CODE XREF: ROM:000152AEj
		btst	#2,d1
		beq.s	loc_15304
		cmpi.w	#$30,$E(a0) ; '0'
		bcc.s	loc_15320

loc_15304:				; CODE XREF: ROM:000152FAj
		tst.w	$5E(a0)
		bne.s	loc_1534A
		move.w	#8,$CE(a2)
		move.w	#4,d0
		bsr.w	Get_RandomValue2
		addq.w	#2,d0
		move.w	d0,$D0(a2)
		rts
; ---------------------------------------------------------------------------

loc_15320:				; CODE XREF: ROM:00015302j
		bset	#0,$48(a2)
		move.w	#$19,d0
		bsr.w	Get_RandomValue2
		addi.w	#$F,d0
		move.w	d0,$D0(a2)
		andi.w	#1,$E(a2)
		ori.w	#$1C,$E(a2)
		move.w	#$2A,0(a2) ; '*'
		rts
; ---------------------------------------------------------------------------

loc_1534A:				; CODE XREF: ROM:00015308j
		move.w	#$A,$CE(a2)
		rts
; ---------------------------------------------------------------------------

loc_15352:				; CODE XREF: ROM:000152B6j
		move.w	#$B,$CE(a2)
		rts
; ---------------------------------------------------------------------------

loc_1535A:				; CODE XREF: ROM:00015284j
					; ROM:0001529Cj
		btst	#7,$49(a0)
		beq.w	loc_152A0
		btst	#4,$49(a0)
		bne.w	loc_152A0
		btst	#5,$49(a0)
		bne.w	loc_152A0
		tst.w	$5E(a0)
		bne.w	loc_152A0
		bsr.w	ScrambleNo
		cmp.b	$FC(a2),d0
		bcc.w	Set_Enemy_Mode_3
		bclr	#0,$49(a0)
		btst	#0,$F(a2)
		bne.s	loc_153A0
		bset	#0,$49(a0)

loc_153A0:				; CODE XREF: ROM:00015398j
		bset	#5,$49(a2)
		bset	#4,$49(a0)
		bclr	#7,$49(a2)
		bclr	#7,$49(a0)
		move.l	a0,$86(a2)
		clr.l	$8A(a2)
		move.l	a2,$8A(a0)
		clr.l	$86(a0)
		exg	a0,a2
		andi.w	#1,$E(a2)
		ori.w	#$C,$E(a2)
		move.w	#$C,0(a2)
		exg	a0,a2
		move.w	($FFFFFC22).w,d0
		add.w	$20(a2),d0
		cmpi.w	#$38,d0	; '8'
		ble.w	loc_15406
		cmpi.w	#$108,d0
		blt.w	loc_15412
		bset	#0,$F(a2)
		addi.w	#$18,$20(a0)
		bra.w	loc_15412
; ---------------------------------------------------------------------------

loc_15406:				; CODE XREF: ROM:000153EAj
		bclr	#0,$F(a2)
		subi.w	#$18,$20(a0)

loc_15412:				; CODE XREF: ROM:000153F2j
					; ROM:00015402j
		move.w	$E(a2),d0
		andi.w	#1,d0
		eori.b	#1,d0
		andi.w	#$FFFE,$E(a0)
		or.w	d0,$E(a0)
		move.w	#$E,$D0(a2)
		clr.w	$CE(a2)
		jsr	(Chk_Grab).l
		rts
; ---------------------------------------------------------------------------

locret_1543A:				; CODE XREF: ROM:00014F90j
					; DATA XREF: ROM:00014DF2o
		rts
; ---------------------------------------------------------------------------

loc_1543C:				; DATA XREF: ROM:00014DF6o
		cmpi.w	#$630,$20(a2)
		bcc.s	loc_1544A
		addq.w	#2,$20(a2)
		rts
; ---------------------------------------------------------------------------

loc_1544A:				; CODE XREF: ROM:00015442j
		clr.w	0(a2)
		sf	$49(a2)
		sf	$1E(a2)
		rts
; ---------------------------------------------------------------------------

loc_15458:				; CODE XREF: ROM:00014F70j
					; DATA XREF: ROM:00014E06o
		cmpi.w	#$8000,($FFFFFC3C).w
		bcs.s	loc_1547E
		move.w	($FFFFFC22).w,d0
		add.w	$20(a2),d0
		cmpi.w	#$130,d0
		bgt.s	locret_154A6
		bsr.w	Chk_PlayerDistance_Boss
		bcs.w	locret_154A6
		cmpi.w	#$58,d2	; 'X'
		bhi.w	locret_154A6

loc_1547E:				; CODE XREF: ROM:0001545Ej
		andi.w	#1,$E(a2)
		ori.w	#6,$E(a2)
		move.w	#$26,0(a2) ; '&'
		clr.w	$CE(a2)
		clr.w	$D0(a2)
		move.l	#$211,d0
		moveq	#0,d1
		jsr	PlaySound

locret_154A6:				; CODE XREF: ROM:0001546Cj
					; ROM:00015472j ...
		rts
; ---------------------------------------------------------------------------

Obj_BarbonBlock:			; DATA XREF: ROM:00014DFAo
		cmpi.w	#1,$16(a2)
		bne.s	loc_154BA
		cmpi.w	#5,$18(a2)
		beq.w	loc_154E4

loc_154BA:				; CODE XREF: ROM:000154AEj
					; ROM:000154F6j ...
		btst	#0,$1E(a2)
		beq.w	locret_154E2
		andi.w	#1,$E(a2)
		ori.w	#0,$E(a2)
		move.w	#2,0(a2)
		bclr	#0,$DE(a2)
		bset	#7,$49(a2)

locret_154E2:				; CODE XREF: ROM:000154C0j
		rts
; ---------------------------------------------------------------------------

loc_154E4:				; CODE XREF: ROM:000154B6j
		jsr	sub_E390
		cmpi.w	#7,d0
		bcc.w	loc_154F8

loc_154F2:				; CODE XREF: ROM:000154FEj
		addq.w	#1,$16(a2)
		bra.s	loc_154BA
; ---------------------------------------------------------------------------

loc_154F8:				; CODE XREF: ROM:000154EEj
		jsr	Find_RAMAddr_SubItem
		bcs.w	loc_154F2
		movea.l	a0,a1
		move.w	#2,0(a1)
		move.w	#$4A,$C(a1) ; 'J'
		move.w	#$252A,$A(a1)
		move.w	#$FFFF,$10(a1)
		sf	$49(a1)
		sf	$1E(a1)
		sf	$48(a1)
		move.w	#$28,$3A(a1) ; '('
		move.l	$20(a2),$20(a1)
		move.l	$24(a2),$24(a1)
		addq.w	#1,$24(a1)
		move.l	$20(a1),2(a1)
		move.l	$24(a1),6(a1)
		clr.l	$5A(a1)
		clr.l	$5E(a1)
		movea.l	a1,a5
		lea	(DecBuffer).w,a4
		lea	word_155F2(pc),a3
		moveq	#6,d6

loc_1555E:				; CODE XREF: ROM:0001558Ej
		move.w	(a3)+,d0
		move.w	(a3)+,d1
		move.w	(a3)+,d4
		move.w	(a3)+,d5
		ext.l	d4
		ext.l	d5
		asl.l	#8,d0
		asl.l	#8,d0
		asl.l	#8,d1
		asl.l	#8,d1
		asl.l	#8,d4
		asl.l	#4,d4
		asl.l	#8,d5
		asl.l	#4,d5
		move.w	#6,d2
		sub.w	d6,d2
		move.w	#2,d3
		bsr.w	Init_BarbonTornJacket
		adda.l	#8,a4
		dbf	d6,loc_1555E
		move.b	#$FF,$1F(a1)
		bra.w	loc_154BA

; =============== S U B	R O U T	I N E =======================================


Init_BarbonTornJacket:			; CODE XREF: ROM:00015584p
		jsr	sub_E356
		move.w	#$4A,$C(a0) ; 'J'
		move.w	#$252A,$A(a0)
		move.w	#$FFFF,$10(a0)
		move.b	#$1C,$1E(a0)
		move.w	d3,0(a0)
		move.l	d4,0(a4)
		move.l	d5,4(a4)
		move.l	$20(a5),2(a0)
		move.l	$24(a5),6(a0)
		add.l	d0,2(a0)
		add.l	d1,6(a0)
		add.w	d2,d2
		move.w	d2,$E(a0)
		move.l	a0,d0
		subi.l	#$FFFFFA00,d0
		lsr.w	#5,d0
		move.b	d0,$1F(a1)
		movea.l	a0,a1
		rts
; End of function Init_BarbonTornJacket

; ---------------------------------------------------------------------------
word_155F2:	dc.w	 8,$FFBA,   $D,$FFFA; 0	; DATA XREF: ROM:00015558t
		dc.w	$A,$FFC0,  $12,	   1; 4
		dc.w	 8,$FFC6,   $B,	   4; 8
		dc.w $FFF7,$FFC5,$FFFA,	   4; 12
		dc.w $FFF7,$FFBF,$FFF3,	   2; 16
		dc.w $FFF7,$FFB9,$FFFB,$FFF9; 20
		dc.w	 6,$FFAF,$FFFA,$FFF0; 24

; =============== S U B	R O U T	I N E =======================================


sub_1562A:				; DATA XREF: ROM:00014DEAo
		jsr	(Chk_Hit).l
		jsr	(Chk_Grab).l
		cmpi.w	#3,$18(a2)
		beq.w	loc_15650

loc_15640:				; CODE XREF: sub_1562A+2Cj
					; sub_1562A+3Cj ...
		btst	#0,$1E(a2)
		bne.s	loc_1566E
		jsr	(Chk_CharacterCollision).l
		rts
; ---------------------------------------------------------------------------

loc_15650:				; CODE XREF: sub_1562A+12j
		cmpi.w	#1,$16(a2)
		bne.s	loc_15640
		move.l	#$200000,$40(a2)
		btst	#0,$F(a2)
		beq.s	loc_15640
		neg.l	$40(a2)
		bra.s	loc_15640
; ---------------------------------------------------------------------------

loc_1566E:				; CODE XREF: sub_1562A+1Cj
		andi.w	#1,$E(a2)
		ori.w	#0,$E(a2)
		move.w	#2,0(a2)
		rts
; End of function sub_1562A


; =============== S U B	R O U T	I N E =======================================


sub_15682:				; DATA XREF: ROM:00014DE2o
					; ROM:00014DE6o
		andi.w	#1,$E(a2)
		ori.w	#$30,$E(a2) ; '0'
		subq.w	#1,$D0(a2)
		bne.w	locret_156DA
		movea.l	$86(a2),a0
		bclr	#5,$49(a2)
		beq.w	loc_15700
		bclr	#4,$49(a0)
		beq.w	loc_15700
		bset	#0,$DE(a2)
		bclr	#7,$49(a2)
		bset	#7,$48(a0)
		bclr	#7,$49(a0)
		move.w	#$20,0(a2) ; ' '
		move.l	#$233,d0
		moveq	#0,d1
		jsr	PlaySound

locret_156DA:				; CODE XREF: sub_15682+10j
		rts
; ---------------------------------------------------------------------------

loc_156DC:				; DATA XREF: ROM:00014DEEo
		bclr	#7,$49(a2)
		btst	#0,$1E(a2)
		bne.w	loc_156EE
		rts
; ---------------------------------------------------------------------------

loc_156EE:				; CODE XREF: sub_15682+66j
		move.w	#$1E,$50(a2)
		bclr	#0,$DE(a2)
		eori.w	#1,$E(a2)

loc_15700:				; CODE XREF: sub_15682+1Ej
					; sub_15682+28j
		bset	#7,$49(a2)
		bclr	#4,$49(a2)
		bclr	#5,$49(a2)

loc_15712:				; CODE XREF: sub_158AA+12j
		clr.w	$CE(a2)
		clr.w	$D0(a2)
		andi.w	#1,$E(a2)
		ori.w	#0,$E(a2)
		move.w	#2,0(a2)
		rts
; End of function sub_15682

; ---------------------------------------------------------------------------

loc_1572E:				; DATA XREF: ROM:00014DB6o
		tst.b	$C0(a2)
		bne.w	loc_1574C
		btst	#4,$49(a2)
		bne.w	loc_1574C
		bsr.w	ScrambleNo
		cmp.b	$FD(a2),d0
		bcs.w	loc_157A8

loc_1574C:				; CODE XREF: ROM:00015732j
					; ROM:0001573Cj
		st	$C0(a2)
		jsr	(Chk_Hit).l
		cmpi.w	#$12,$E(a2)
		bcs.s	loc_15764
		jsr	(Chk_Grab).l

loc_15764:				; CODE XREF: ROM:0001575Cj
		btst	#7,$48(a2)
		bne.s	loc_15794
		btst	#0,$1E(a2)
		beq.s	locret_15792
		sf	$C0(a2)
		btst	#4,$49(a2)
		bne.s	loc_15794
		andi.w	#1,$E(a2)
		ori.w	#0,$E(a2)
		move.w	#2,0(a2)

locret_15792:				; CODE XREF: ROM:00015772j
		rts
; ---------------------------------------------------------------------------

loc_15794:				; CODE XREF: ROM:0001576Aj
					; ROM:0001577Ej
		andi.w	#1,$E(a2)
		ori.w	#$C,$E(a2)
		move.w	#$C,0(a2)
		rts
; ---------------------------------------------------------------------------

loc_157A8:				; CODE XREF: ROM:00015748j
		bset	#0,$48(a2)
		move.l	#$30000,$2A(a2)
		andi.w	#1,$E(a2)
		ori.w	#$1C,$E(a2)
		move.w	#$28,0(a2) ; '('
		rts
; ---------------------------------------------------------------------------

loc_157CA:				; DATA XREF: ROM:00014DFEo
		bclr	#6,$49(a2)
		btst	#0,$1E(a2)
		beq.s	loc_15800
		andi.w	#1,$E(a2)
		ori.w	#0,$E(a2)
		move.w	#2,0(a2)
		bclr	#0,$48(a2)
		move.w	#7,$CE(a2)
		clr.w	$D0(a2)
		clr.l	$2A(a2)
		rts
; ---------------------------------------------------------------------------

loc_15800:				; CODE XREF: ROM:000157D6j
		move.l	$2A(a2),$40(a2)
		subi.l	#$7000,$2A(a2)
		bpl.w	loc_15816
		clr.l	$2A(a2)

loc_15816:				; CODE XREF: ROM:0001580Ej
		btst	#0,$F(a2)
		beq.w	locret_15824
		neg.l	$40(a2)

locret_15824:				; CODE XREF: ROM:0001581Cj
		rts
; ---------------------------------------------------------------------------

loc_15826:				; DATA XREF: ROM:00014E02o
		bclr	#6,$49(a2)
		bclr	#2,$49(a2)
		bne.s	loc_15860
		subq.w	#1,$D0(a2)
		bpl.w	locret_1585E
		bclr	#0,$48(a2)
		move.w	#7,$CE(a2)
		clr.w	$D0(a2)
		andi.w	#1,$E(a2)
		ori.w	#0,$E(a2)
		move.w	#2,0(a2)

locret_1585E:				; CODE XREF: ROM:00015838j
		rts
; ---------------------------------------------------------------------------

loc_15860:				; CODE XREF: ROM:00015832j
		move.l	#$30000,$2A(a2)
		move.w	#$FFFF,$10(a2)
		andi.w	#1,$E(a2)
		ori.w	#$1C,$E(a2)
		move.w	#$28,0(a2) ; '('
		rts

; =============== S U B	R O U T	I N E =======================================


sub_15882:				; CODE XREF: ROM:00014FEEj
					; DATA XREF: ROM:00014E0Eo
		bclr	#0,$DE(a2)
		bclr	#7,$A(a2)
		move.w	#$32,0(a2) ; '2'
		andi.w	#1,$E(a2)
		ori.w	#$1E,$E(a2)
		clr.l	$2A(a2)
		clr.l	$2E(a2)
		rts
; End of function sub_15882


; =============== S U B	R O U T	I N E =======================================


sub_158AA:				; DATA XREF: ROM:00014E12o
		jsr	(Chk_Hit).l
		jsr	(Chk_Grab).l
		btst	#0,$1E(a2)
		bne.w	loc_15712
		cmpi.w	#2,$18(a2)
		bne.s	locret_158F6
		move.l	$2A(a2),$40(a2)
		move.l	$2E(a2),d0
		addi.l	#$4000,$2E(a2)
		add.l	d0,$5E(a2)
		bmi.s	locret_158F6
		clr.l	$5E(a2)
		clr.l	$40(a2)
		clr.l	$2A(a2)
		clr.l	$2E(a2)
		move.w	#1,$16(a2)

locret_158F6:				; CODE XREF: sub_158AA+1Cj
					; sub_158AA+34j
		rts
; End of function sub_158AA

; ---------------------------------------------------------------------------
