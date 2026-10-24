"""Build using an existing PSPSDK installation, without global PATH changes."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pspdev', type=Path, default=os.environ.get('PSPDEV'))
    args = ap.parse_args()
    sdk = args.pspdev
    if sdk is None:
        cc = shutil.which('psp-gcc')
        if cc:
            sdk = Path(cc).resolve().parent.parent
    if sdk is None:
        ap.error('Set PSPDEV or supply --pspdev PATH to an existing PSPSDK toolchain')
    sdk = sdk.resolve()
    out = ROOT / 'build'
    out.mkdir(exist_ok=True)
    env = os.environ.copy()
    env['PATH'] = str(sdk/'bin') + os.pathsep + env['PATH']
    env['PSPDEV'] = sdk.as_posix()
    suffix = '.exe' if os.name == 'nt' else ''
    log = []
    def run(name, *argv):
        cmd = [str(sdk/'bin'/(name+suffix)), *map(str, argv)]
        p = subprocess.run(cmd, cwd=ROOT, env=env, text=True, errors='replace',
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log.append(' '.join(cmd)+'\n'+p.stdout)
        (out/'build.log').write_text('\n'.join(log), encoding='utf-8')
        print(p.stdout, end='')
        if p.returncode:
            raise SystemExit(p.returncode)
    run('psp-gcc', '--version')
    common = ['-O2','-G0','-std=gnu99','-Wall','-Wextra','-Werror',
              '-ffunction-sections','-fdata-sections','-D_PSP_FW_VERSION=600',
              '-I'+(sdk/'psp/sdk/include').as_posix(),'-I'+(sdk/'psp/include').as_posix(),'-Isrc']
    for name in ('main','level','held','flow','game','machine','death','bk3','combat','rules','impact','enemy','variety','reactions','sfx','ai','physics','sprites','stage','music','ui'):
        run('psp-gcc', *common, '-c', 'src/'+name+'.c','-o',(out/(name+'.o')).as_posix())
    run('psp-gcc','-G0','-c','src/sprite_atlas.S','-o',(out/'sprite_atlas.o').as_posix())
    run('psp-gcc','-G0','-c','src/stage_texture.S','-o',(out/'stage_texture.o').as_posix())
    run('psp-gcc','-G0','-c','src/hud_texture.S','-o',(out/'hud_texture.o').as_posix())
    elf = out/'sorr-lite.elf'
    run('psp-gcc','-G0','-L'+(sdk/'psp/lib').as_posix(),'-L'+(sdk/'psp/sdk/lib').as_posix(),
        '-specs='+(sdk/'psp/sdk/lib/prxspecs').as_posix(),
        '-Wl,-q,-T'+(sdk/'psp/sdk/lib/linkfile.prx').as_posix(),
        '-Wl,-zmax-page-size=128','-Wl,--gc-sections','-Wl,-Map='+ (out/'sorr-lite.map').as_posix(),
        '-o',elf.as_posix(),(out/'main.o').as_posix(),(out/'level.o').as_posix(),(out/'held.o').as_posix(),(out/'flow.o').as_posix(),(out/'game.o').as_posix(),(out/'machine.o').as_posix(),(out/'death.o').as_posix(),(out/'bk3.o').as_posix(),(out/'combat.o').as_posix(),(out/'physics.o').as_posix(),(out/'rules.o').as_posix(),(out/'impact.o').as_posix(),(out/'enemy.o').as_posix(),(out/'variety.o').as_posix(),(out/'reactions.o').as_posix(),(out/'sfx.o').as_posix(),(out/'ai.o').as_posix(),
        (out/'sprites.o').as_posix(),(out/'sprite_atlas.o').as_posix(),
        (out/'stage.o').as_posix(),(out/'music.o').as_posix(),(out/'stage_texture.o').as_posix(),
        (out/'ui.o').as_posix(),(out/'hud_texture.o').as_posix(),
        (sdk/'psp/sdk/lib/prxexports.o').as_posix(),'-lpspaudio','-lpspgu','-lpsppower','-lpspdisplay',
        '-lpspge','-lpspctrl','-lm')
    run('psp-fixup-imports',elf)
    run('psp-prxgen',elf,out/'sorr-lite.prx')
    run('mksfoex','-d','MEMSIZE=0','-s','DISC_ID=SORL00022','SoRR PSP Lite v0.22',out/'PARAM.SFO')
    run('pack-pbp',out/'EBOOT.PBP',out/'PARAM.SFO',*(['NULL']*5),out/'sorr-lite.prx','NULL')
    run('psp-size',elf)
    pbp=out/'EBOOT.PBP'
    (out/'SHA256.txt').write_text(hashlib.sha256(pbp.read_bytes()).hexdigest()+'  EBOOT.PBP\n')
    import shutil
    if (ROOT/'music.wav').exists(): shutil.copy2(ROOT/'music.wav',out/'music.wav')
    print('Built:',pbp)

if __name__ == '__main__':
    main()
