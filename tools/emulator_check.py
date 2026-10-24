"""Run against the Lite EBOOT in PPSSPP with its local remote debugger enabled.
Requires: python -m pip install websocket-client
Combat tests intentionally arrange actors through debugger memory writes.
"""
import argparse, os, subprocess, time, json, struct, base64, zlib, hashlib, math
from pathlib import Path
import websocket
ap=argparse.ArgumentParser()
ap.add_argument('--pspdev',type=Path,default=os.environ.get('PSPDEV'))
ap.add_argument('--url',default='ws://127.0.0.1:19876/debugger')
ap.add_argument('--soak-seconds',type=int,default=0)
args=ap.parse_args()
if not args.pspdev: ap.error('Set PSPDEV or supply --pspdev')
project=Path(__file__).resolve().parents[1]
artifacts=project/'test-results'
artifacts.mkdir(exist_ok=True)
class PSP:
    def __init__(self):
        self.ws=websocket.create_connection(args.url,subprotocols=['debugger.ppsspp.org'],timeout=15,suppress_origin=True)
        self.req('version',name='Lite integration tests',version='1')
        status=self.req('game.status');deadline=time.monotonic()+15
        while not status.get('game') and time.monotonic()<deadline:
            time.sleep(.1);status=self.req('game.status')
        if (status.get('game')or{}).get('id')!='SORL00020':
            raise RuntimeError('Load SoRR PSP Lite EBOOT first; refusing to modify another game')
        nm=args.pspdev/'bin'/('psp-nm.exe' if os.name=='nt' else 'psp-nm')
        raw=subprocess.check_output([str(nm),'-n',str(project/'build/sorr-lite.elf')],text=True)
        self.symbols={a[2]:int(a[0],16)+0x08804000 for l in raw.splitlines() if len(a:=l.split())==3 and all(c in '0123456789abcdefABCDEF' for c in a[0])}
    def req(self,event,**params):
        self.ws.send(json.dumps(dict(event=event,ticket=event,**params)))
        while True:
            r=json.loads(self.ws.recv())
            if r.get('ticket')==event or r.get('event')==event:
                if r.get('event')=='error':raise RuntimeError(r)
                return r
    def read(self,addr,size):return base64.b64decode(self.req('memory.read',address=addr,size=size)['base64'])
    def u32(self,s):return struct.unpack('<I',self.read(self.symbols[s],4))[0]
    def send(self,**buttons):return self.req('input.buttons.send',buttons=buttons)
    def close(self):self.ws.close()
p=PSP()
# Trace arrays are populated during startup selftests, before the first GU frame.
ready_deadline=time.monotonic()+15
while p.u32('frame_count')<2:
    if time.monotonic()>ready_deadline:raise RuntimeError('PSP startup did not reach rendering')
    time.sleep(.1)
checks={}
def state():
    raw=p.read(p.symbols['game'],192)
    return dict(player=list(struct.unpack_from('<2f7i',raw)), enemies=[list(struct.unpack_from('<2f7i',raw,36*(i+1))) for i in range(4)], ticks=struct.unpack_from('<I',raw,180)[0],paused=struct.unpack_from('<i',raw,184)[0],won=struct.unpack_from('<i',raw,188)[0])
def button(name,t=0.18):
    p.send(**{name:True});time.sleep(t);p.send(**{name:False});time.sleep(0.1)
def reset():
    p.send(ltrigger=True,rtrigger=True);time.sleep(0.15);p.send(ltrigger=False,rtrigger=False);time.sleep(0.12)
    p.req('memory.write_u32',address=p.symbols['level'],value=0)
    p.req('memory.write',address=p.symbols['level']+132,base64=base64.b64encode(bytes(96)).decode())
    # The stream opens with two actors; isolated legacy combat scenarios need four.
    for i in range(4):
        p.req('memory.write',address=p.symbols['game']+36*(i+1),base64=base64.b64encode(struct.pack('<2f7i',144.+i*23.,79.+i*12.,40,-1,20+i*9,0,0,0,0)).decode())
def frames():return list(struct.unpack('<5I',p.read(p.symbols['actor_frames'],20)))
def moves():return list(struct.unpack('<34i',p.read(p.symbols['game']+192,136)))

def music():return list(struct.unpack('<2i10I',p.read(p.symbols['music_stats'],48)))
def screenshot(path):
    p.req('cpu.stepping')
    try:
        raw=p.read(p.u32('presented_buffer'),512*272*2)
        rows=[]
        for y in range(272):
            row=bytearray(b'\0')
            for x in range(480):
                v=struct.unpack_from('<H',raw,y*1024+x*2)[0]
                row.extend(((v&31)*255//31,((v>>5)&63)*255//63,((v>>11)&31)*255//31))
            rows.append(row)
        def chunk(k,d): return struct.pack('>I',len(d))+k+d+struct.pack('>I',zlib.crc32(k+d))
        path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',480,272,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b''))
    finally:p.req('cpu.resume')
def arrange(hp,player_hp=100,attack=0,x=82.0,one=False,freeze_one=False):
    p.req('cpu.stepping')
    a=p.symbols['game']
    def put(off,fmt,*v):p.req('memory.write',address=a+off,base64=base64.b64encode(struct.pack(fmt,*v)).decode())
    try:
        put(0,'<2f7i',64.,100.,player_hp,1,0,0,0,0,0)
        for i in range(4):put(36*(i+1),'<2f7i',x if not one or i==0 else 220.,100. if not one or i==0 else 120.,hp,-1,100,0,attack,0,0)
        put(184,'<2i',0,0);put(328,'<184s',bytes(184))
        cb=bytearray(288);struct.pack_into('<i',cb,12,-1);struct.pack_into('<i',cb,40,112);struct.pack_into('<I',cb,56,0xace1)
        for i in range(4):
            struct.pack_into('<i',cb,64+i*56+4,10000);struct.pack_into('<i',cb,64+i*56+16,5);struct.pack_into('<i',cb,64+i*56+32,1)
            if attack:
                struct.pack_into('<i',cb,64+i*56,9);struct.pack_into('<i',cb,64+i*56+20,3 if i%2 else 2);struct.pack_into('<i',cb,64+i*56+24,4)
            elif not one or i:put(36*(i+1)+20,'<i',10000)
        put(512,'<288s',cb);put(800,'<284s',bytes(284))
        rules=bytearray(404)
        for j in range(5):struct.pack_into('<12i',rules,j*48,6 if not j else 14 if j%2 else 16,128,0,0,0,0,8,0,-1,-1,0,1)
        for j in range(4):struct.pack_into('<10i',rules,240+j*40,0x1a if attack else 2,0,-1,0,0,0,0,0,0,0)
        put(1084,'<404s',rules);put(1488,'<176s',bytes(176))
        if freeze_one:put(1492,'<i',10000)
        raw=bytearray(136);struct.pack_into('<i',raw,52,100);struct.pack_into('<i',raw,64,-1)
        p.req('memory.write',address=a+192,base64=base64.b64encode(raw).decode())
    finally:p.req('cpu.resume')
try:
    checks['selftest']=p.u32('selftest_result')==0
    assert checks['selftest'], ('MIPS selftest',p.u32('selftest_result'))
    trace=list(struct.iter_unpack('<4i',p.read(p.symbols['bk3_jump_trace'],48*16)))
    ref=json.loads((project/'assets/bk3-reference.json').read_text())
    velocity=ref['jump_longs'][3]-2**32;height=0;expected=[]
    # Init_Jump stores 4; the next four Obj_Jumping calls return before integration.
    for tick in range(43):
        if tick>=5:height+=velocity;velocity+=0x4000
        expected.append(height)
    checks['jump_trace_matches_68000_equations']=[row[0]for row in trace[:43]]==expected
    punch=list(struct.iter_unpack('<4i',p.read(p.symbols['bk3_punch_trace'],8*16)))
    checks['punch_timing_matches_rom_table']=punch[:4]==[(1,0,0,1),(80,2,5,1),(80,2,5,1),(80,2,5,1)]

    # Read traces produced by the actual MIPS C routines before GU startup.
    special=list(struct.iter_unpack('<5i',p.read(p.symbols['bk3_special_trace'],160*20)))
    fwd=ref['scripts']['special2']['frames'];expected=[];z=0;vz=-4*65536;landed=0;tick=0
    for frame,f in enumerate(fwd):
        for sub in range(f['ticks']):
            if len(fwd)-frame<=4 and not landed:
                z+=vz;vz+=16384
                if z>=0 and vz>=0:z=0;landed=1
            expected.append((z,vz,landed,frame,9))
    checks['dragon_smash_trace_matches_source']=special[:len(expected)]==expected
    checks['dragon_smash_peak_34_pixels']=min(x[0]for x in special)==-34*65536
    victims=list(struct.iter_unpack('<4i',p.read(p.symbols['physics_victim_trace'],2*40*16)))
    checks['front_victim_independent_release']=next(i+1 for i,x in enumerate(victims[:40])if x[0]==2)==26
    checks['back_victim_independent_release']=next(i+1 for i,x in enumerate(victims[40:])if x[0]==2)==29
    checks['throw_damage_waits_for_ground']=all(x[3]==40 for x in victims[:26]) and all(x[3]==40 for x in victims[40:69]) and victims[70][3]==26
    fall=list(struct.iter_unpack('<4i',p.read(p.symbols['physics_fall_trace'],128*16)))
    z=0;vz=-343040;expected_fall=[]
    while True:
        z+=vz;vz+=16384
        if z>=0 and vz>=0:break
        expected_fall.append((z,vz))
    checks['knockdown_trace_matches_source']=[x[:2]for x in fall[:len(expected_fall)]]==expected_fall
    impact=len(expected_fall);checks['ground_bounce_ffffffff']=fall[impact][:3]==(-1,-114688,3)
    checks['getup_finishes']=fall[-1][2]==0
    (artifacts/'physics-traces.json').write_text(json.dumps(dict(special=special,victims=victims,fall=fall),indent=2))
    reset();a=state();checks['restart']=a['player'][2]==100 and all(e[2]==40 for e in a['enemies'])
    checks['hud_reset']=p.u32('ui_score')==0 and p.u32('ui_player_hp')==100 and p.u32('ui_timer')==99 and p.u32('show_perf')==0
    hud_manifest=json.loads((project/'assets/hud-manifest.json').read_text())
    checks['hud_upload']=hashlib.sha256(p.read(0x04148000,256*256*4)).hexdigest()==hud_manifest['texture_sha256']
    manifest=json.loads((project/'assets/manifest.json').read_text())
    checks['atlas_upload']=p.read(0x04088000,512*512*3)==(project/'assets/sprites.t8').read_bytes()[:512*512*3] and p.read(p.symbols['sprite_atlas']+512*512*3,512*512)==(project/'assets/sprites.t8').read_bytes()[512*512*3:]
    stage=json.loads((project/'assets/stage-manifest.json').read_text())
    checks['stage_RAM_source']=hashlib.sha256(p.read(p.symbols['stage_texture'],512*256*2)).hexdigest()==stage['first_page_sha256'] and p.u32('stage_draw_count')==1
    checks['music_source']=hashlib.sha256((project/'build/music.wav').read_bytes()).hexdigest()==json.loads((project/'assets/music-manifest.json').read_text())['wav_sha256']
    audio_start=music();time.sleep(0.3);audio_next=music()
    checks['music_streaming']=audio_next[0]==1 and audio_next[1]==0 and audio_next[2]>audio_start[2] and audio_next[7]==44100
    arrange(40,x=220.);idle=[]
    for _ in range(8):idle.append(frames()[0]);time.sleep(0.08)
    checks['idle_animation']=len(set(idle))>1 and set(idle)<=set(range(1,5))
    button('start'); a=state();time.sleep(0.5);b=state()
    checks['pause']=a['paused']==b['paused']==1 and a['ticks']==b['ticks']
    paused_timer=p.u32('ui_timer');time.sleep(0.1);checks['timer_pause']=p.u32('ui_timer')==paused_timer
    screenshot(artifacts/'lite-pause.png')
    paused_frames=frames();time.sleep(0.2);checks['animation_pause']=frames()==paused_frames
    paused_audio=music();time.sleep(0.2);later_audio=music()
    checks['music_pause']=later_audio[3]==paused_audio[3] and later_audio[10]>paused_audio[10]
    button('start');arrange(40,x=220.);a=state();p.send(right=True);walk=[]
    for _ in range(5):time.sleep(0.08);walk.append(frames()[0])
    p.send(right=False);time.sleep(0.1);b=state()
    checks['movement']=b['player'][0]>a['player'][0]+10 and b['ticks']>a['ticks']
    checks['walk_animation']=len(set(walk)&set(range(5,11)))>1
    arrange(40,x=220.0) # Isolate the jump from enemies: low takeoff is now vulnerable.
    button('cross',0.05);checks['jump']=state()['player'][7]>0 and frames()[0] in (60,12,13)
    screenshot(artifacts/'lite-jump.png')
    arrange(40);p.send(square=True);time.sleep(0.035)
    checks['attack_animation']=frames()[0] in (1,80)
    screenshot(artifacts/'lite-attack.png');p.send(square=False);time.sleep(0.17);a=state()
    checks['one_hit_per_attack']=all(e[2]==38 for e in a['enemies'])
    checks['hud_enemy_hp']=p.u32('ui_enemy_hp')==38 and p.u32('ui_target')==3
    checks['hud_score']=p.u32('ui_score')>=40
    arrange(2);button('square');time.sleep(1.6);a=state()
    checks['four_enemy_victory']=a['won']==1 and all(e[2]==0 for e in a['enemies'])
    time.sleep(0.4);enemy_ref=json.loads((project/'assets/enemy-rom-match.json').read_text());checks['fall_animation']=frames()[1:]==[enemy_ref[k]['floor']['frames'][0]['fpg']for k in ['garcia','donovan','garcia','donovan']]
    screenshot(artifacts/'lite-victory.png')
    reset();arrange(40,1,10);time.sleep(0.4);a=state()
    checks['game_over']=a['player'][2]==0
    checks['hud_player_hp']=p.u32('ui_player_hp')==0
    reset();time.sleep(1.2);button('left',0.15);screenshot(artifacts/'lite-mirrored.png')
    reset();time.sleep(1.2);screenshot(artifacts/'lite-preview.png')
    checks['timer_advances']=p.u32('ui_timer')<99
    button('circle');checks['diagnostics_toggle_on']=p.u32('show_perf')==1
    screenshot(artifacts/'lite-profile.png')
    button('circle');checks['diagnostics_toggle_off']=p.u32('show_perf')==0
    p.send(ltrigger=True);button('triangle');p.send(ltrigger=False);checks['music_mute']=p.u32('music_muted')==1 and music()[11]>0
    p.send(ltrigger=True);button('triangle');p.send(ltrigger=False);checks['music_unmute']=p.u32('music_muted')==0 and music()[0]==1
    before_loop=music()
    # Ask the audio worker to seek near EOF, then exercise its real wrap path.
    p.req('memory.write_u32',address=p.symbols['music_seek_target'],value=before_loop[8]-1000)
    for _ in range(30):
        if music()[4]>before_loop[4]:break
        time.sleep(0.05)
    checks['music_loop']=music()[4]>before_loop[4] and music()[0]==1
    # Check the PCM itself against the reference file, not merely nonzero samples.
    import wave
    with wave.open(str(project/'music.wav'),'rb') as w:
        reference=w.readframes(w.getnframes())
    p.req('cpu.stepping')
    try:
        raw=p.read(p.symbols['music_pcm'],16384)
        starts=struct.unpack('<2i',p.read(p.symbols['music_buffer_start'],8))
    finally:p.req('cpu.resume')
    exact=[]
    for i,start in enumerate(starts):
        off=start*4;n=8192
        expected=(reference[off:]+reference)[:n] if off+n>len(reference) else reference[off:off+n]
        exact.append(start>=0 and raw[i*n:(i+1)*n]==expected)
    checks['audio_buffers_exact_reference']=all(exact)
    pcm=struct.unpack('<8192h',raw);pcm_rms=math.sqrt(sum(v*v for v in pcm)/len(pcm))
    checks['decoded_audio_non_silent']=pcm_rms>30
    # Enter the last tick of the countdown; the actual C logic performs timeout.
    reset();p.req('cpu.stepping')
    p.req('memory.write_u32',address=p.symbols['game']+180,value=99*30-1)
    p.req('cpu.resume');time.sleep(0.15)
    checks['timer_expiry']=state()['player'][2]==0 and p.u32('ui_timer')==0
    screenshot(artifacts/'lite-time-over.png');reset()
    # SoR3-style controls are exercised through actual controller input.
    reset();p.send(right=True);time.sleep(0.06);p.send(right=False);time.sleep(0.06);p.send(right=True);time.sleep(0.12)
    checks['double_tap_run']=moves()[0]==1
    screenshot(artifacts/'lite-run.png');p.send(right=False);time.sleep(0.1)
    checks['run_release']=moves()[0]==0
    reset();p.send(down=True);time.sleep(0.06);p.send(down=False);time.sleep(0.06);p.send(down=True);time.sleep(0.1)
    checks['double_tap_roll']=moves()[1]>0 and moves()[19]>0
    screenshot(artifacts/'lite-roll.png');p.send(down=False)
    # Original four-part sequence: 52,52,54,56, including whiffs.
    reset();arrange(40)
    for _ in range(3):
        p.send(square=True);time.sleep(.04);p.send(square=False);time.sleep(.22)
    p.send(square=True);time.sleep(.20)
    checks['four_part_combo']=moves()[9]==4 and state()['enemies'][0][2]<40
    screenshot(artifacts/'lite-combo.png');p.send(square=False)
    reset();arrange(40);p.send(cross=True,square=True);time.sleep(.25)
    checks['jump_kick']=moves()[12]==2 and state()['enemies'][0][2]<40
    screenshot(artifacts/'lite-jump-kick.png');p.send(cross=False,square=False)
    reset();arrange(40,x=100.0);p.send(right=True);time.sleep(.06);p.send(right=False);time.sleep(.06)
    p.send(right=True,square=True);time.sleep(.35)
    checks['blitz_attack']=moves()[12]==3 and state()['enemies'][0][2]<40
    screenshot(artifacts/'lite-blitz.png');p.send(right=False,square=False)
    # BK3 special scripts: damage comes from active ROM rectangles, not one flat hit.
    reset();arrange(40);p.send(triangle=True);time.sleep(.15)
    checks['full_charge_special']=moves()[13]==0 and moves()[14]>0 and state()['player'][2]==100 and state()['enemies'][0][2]==32
    checks['neutral_special_original_frames']=frames()[0] in range(24,32)
    screenshot(artifacts/'lite-special.png');p.send(triangle=False);time.sleep(.6)
    before_hp=state()['player'][2];p.send(triangle=True);time.sleep(.1)
    checks['special_cost_deferred']=state()['player'][2]==before_hp
    p.send(triangle=False);time.sleep(.8)
    checks['early_special_costs_hp']=state()['player'][2]<before_hp
    reset();arrange(100);p.send(right=True,triangle=True);time.sleep(.2)
    checks['forward_special']=moves()[15]==1 and state()['enemies'][0][2]<100 and frames()[0] in range(34,44)
    screenshot(artifacts/'lite-forward-special.png');p.send(right=False,triangle=False)
    time.sleep(2.5);checks['special_finishes']=moves()[14]==0 and moves()[19]==0
    # Set held target and let real controller actions run. Debug arrangement avoids AI racing setup.
    def hold(back=False,hits=0):
        reset();arrange(100,x=80.,one=True);p.req('cpu.stepping')
        def write(off,value):p.req('memory.write_u32',address=p.symbols['game']+off,value=value&0xffffffff)
        write(512,1);write(524,0);write(528,int(back));write(532,hits);write(256,0)
        write(512+64,0);write(512+68,10000)
        write(1084+4,160);write(1084+36,1);write(1084+48+4,144);write(1084+48+32,0);write(1084+240,14 if back else 12)
        p.req('cpu.resume');time.sleep(.06)
    reset();arrange(40,x=70.,one=True,freeze_one=True);p.send(right=True);time.sleep(.12);p.send(right=False)
    checks['automatic_grab']=moves()[16]==0
    checks['grab_repositions_player_not_victim']=abs(state()['enemies'][0][0]-70.)<.01 and state()['player'][0]<60
    screenshot(artifacts/'lite-grab.png')
    hold();p.send(right=True,square=True);time.sleep(.08);p.send(right=False,square=False)
    checks['grab_knee']=state()['enemies'][0][2]==98 and moves()[16]==0 and frames()[0]==72
    time.sleep(.3);checks['knee_retains_hold']=moves()[16]==0
    hold(hits=2);p.send(right=True,square=True);time.sleep(.3);p.send(right=False,square=False)
    checks['third_knee_knocks_down']=state()['enemies'][0][2]<=96 and moves()[20]>0
    hold();button('square',.05);time.sleep(.25)
    checks['neutral_grab_headbutt']=state()['enemies'][0][2]==92 and moves()[16]==-1
    hold();p.send(left=True,square=True);time.sleep(.25)
    checks['front_throw_windup']=moves()[16]==0 and frames()[0] in (153,154,155)
    time.sleep(.3)
    checks['front_throw_release']=moves()[16]==-1 and state()['enemies'][0][2]==100 and moves()[24]>0
    checks['throw_recovery_preserved']=frames()[0]==156
    screenshot(artifacts/'lite-throw.png');p.send(left=False,square=False)
    time.sleep(1.6);checks['throw_lands']=moves()[24]==0 and state()['enemies'][0][2]==88
    hold(back=True);p.send(square=True);time.sleep(.55)
    lift=struct.unpack('<f',p.read(p.symbols['game']+328,4))[0]
    checks['axel_backthrow_physical_lift']=lift>0
    screenshot(artifacts/'lite-backthrow.png');p.send(square=False);time.sleep(.65)
    checks['back_throw_damage']=state()['enemies'][0][2]==86 and moves()[16]==-1
    hold();before=state()['player'][0];p.send(cross=True);time.sleep(.13)
    checks['vault_animation']=frames()[0] in range(900,905)
    screenshot(artifacts/'lite-vault.png');p.send(cross=False);time.sleep(.6)
    checks['vault_retains_grab']=moves()[16]==0 and state()['player'][0]>before+15 and state()['player'][3]==-1
    hold();p.send(left=True);time.sleep(.5);p.send(left=False)
    checks['grab_direction_escape']=moves()[16]==-1
    # Thrown-body collision: place a second target in the outgoing path, then let physics run.
    hold();p.req('cpu.stepping')
    p.req('memory.write',address=p.symbols['game']+72,base64=base64.b64encode(struct.pack('<2f',15.,100.)).decode());p.req('cpu.resume')
    p.send(left=True,square=True);time.sleep(.7);p.send(left=False,square=False)
    checks['thrown_body_damage_16']=state()['enemies'][1][2]==84
    # Enemy active attack rectangle/timer executes on the emulated MIPS CPU.
    reset();arrange(40,100,10,x=82.);time.sleep(.12)
    checks['enemy_jab_damage_1']=state()['player'][2]==99
    reset();arrange(40,100,10,x=140.);time.sleep(.12)
    checks['enemy_jab_misses_outside_rect']=state()['player'][2]==100
    # Donovan selects the anti-air branch at level 5, after ROM wait interval / 2.
    reset();arrange(40,x=220.);p.send(cross=True);time.sleep(.18);p.send(cross=False)
    p.req('cpu.stepping')
    p.req('memory.write',address=p.symbols['game']+72,base64=base64.b64encode(struct.pack('<2f7i',82.,100.,40,-1,0,0,0,0,0)).decode())
    p.req('memory.write_u32',address=p.symbols['game']+512+64+56,value=7)
    p.req('cpu.resume');time.sleep(.04)
    cb=p.read(p.symbols['game']+512,288);brain=struct.unpack_from('<14i',cb,64+56)
    checks['donovan_anti_air_selection']=brain[0]==10 or struct.unpack('<i',p.read(p.symbols['game']+1084+240+40,4))[0]==0x1c
    screenshot(artifacts/'lite-donovan-uppercut.png')
    # Both jab chains must use the follow-up states instead of returning to idle.
    for family,index in [('garcia',0),('donovan',1)]:
        reset();arrange(100,x=220.);p.req('cpu.stepping')
        a=p.symbols['game'];brain=a+512+64+index*56
        p.req('memory.write',address=a+36*(index+1),base64=base64.b64encode(struct.pack('<2f7i',82.,100.,100,-1,0,0,0,0,0)).decode())
        for off,value in [(0,9),(4,10000),(20,5),(24,1),(28,0)]:p.req('memory.write_u32',address=brain+off,value=value)
        p.req('memory.write_u32',address=a+1084+240+index*40,value=0x1a)
        p.req('cpu.resume');time.sleep(.06)
        ai=list(struct.unpack('<14i',p.read(brain,56)))
        checks[family+'_jab_completion_preserves_ce']=ai[0]==9 and struct.unpack('<i',p.read(a+1084+240+index*40,4))[0]==2
    # A second vault releases the held opponent (Obj_Vault $99 bit 0).
    hold();button('cross',.05);time.sleep(.5);button('cross',.05);time.sleep(.5)
    checks['second_vault_releases']=moves()[16]==-1

    reset()
    for second in range(args.soak_seconds):
        if second%8==0:reset()
        time.sleep(1)
    button('select');csv=project/'build/lite-profile.csv'
    checks['csv']=csv.exists() and 'selftest=0' in csv.read_text() and len(csv.read_text().splitlines())>4
    checks['bounded_sprite_draws']=p.u32('sprite_draw_count')==5 and p.u32('sprite_slice_count')<=15
    checks['all_selected_frames_exist']=p.u32('missing_sprite_frames')==0
    checks['single_hud_batch']=p.u32('ui_draw_count')==1
    profile_intervals=max(0,len(csv.read_text().splitlines())-2)
    result={'checks':checks,'bk3_jump_trace':trace,'physics_trace_file':'physics-traces.json','bk3_punch_trace':punch,'eboot_sha256':hashlib.sha256((project/'build/EBOOT.PBP').read_bytes()).hexdigest(),'profile_intervals':profile_intervals,'soak_seconds':args.soak_seconds,'idle_frames_seen':idle,'walk_frames_seen':walk,'state':state(),'music_stats':music(),'mechanics':moves(),'decoded_pcm_rms':pcm_rms,'sprite_draws':p.u32('sprite_draw_count'),'sprite_slices':p.u32('sprite_slice_count'),'frames':p.u32('frame_count'),'logic_count':p.u32('logic_count'),'dropped_ticks':p.u32('dropped_ticks'),'note':'Emulator checks only. Combat edge cases use debugger-arranged actor positions/HP. EOF loop check seeks near the end via the audio worker, then lets the PCM stream wrap normally. Controller traces compare source equations/tables, not execution of the ROM. Screenshots read the completed presented VRAM buffer; use PPSSPP software renderer.'}
    (artifacts/'lite-emulator-tests.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    assert all(checks.values())
finally:p.close()
