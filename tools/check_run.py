"""Real-input Max running regressions in both directions, with source pixel frames."""
from pathlib import Path
source=(Path(__file__).with_name('check_max.py')).read_text()
exec(source[:source.index('\ntry:\n checks[')])
try:
 checks['native_selftests']=p.u32('selftest_result')==0
 for face,name in [(1,'right'),(-1,'left')]:
  fixture(200,220.,face);p.send(**{name:True});time.sleep(.07);p.send(**{name:False});time.sleep(.07);p.send(**{name:True});time.sleep(.12)
  checks[name+'_run_pose_and_facing']=mx()[2]==0x54 and moves()[0]==face and frames()[0]in range(1100,1106) and state()['player'][3]==face
  screenshot(artifacts/('max-run-'+name+'.png'))
  button('square',.06);checks[name+'_run_attack_is_original_slide']=mx()[1]==9 and mx()[2]==0x48
  p.send(**{name:False})
 fixture(200,220.);p.send(right=True);time.sleep(.07);p.send(right=False);time.sleep(.40);p.send(right=True);time.sleep(.10)
 checks['expired_double_tap_is_walk']=mx()[2]==2 and moves()[0]==0
 p.send(right=False)
 result=dict(checks=checks,eboot_sha256=hashlib.sha256((project/'build/EBOOT.PBP').read_bytes()).hexdigest(),note='Real button double taps, resolved run poses in both directions, source slide, expired tap window. Hardware not tested.')
 (artifacts/'max-run-tests.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert all(checks.values())
finally:p.send(left=False,right=False,square=False);p.close()
