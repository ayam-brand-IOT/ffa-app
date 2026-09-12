"""Patch sample encoding only; no hardware imports or Modbus writes."""
import ast
import sys
from datetime import datetime
from pathlib import Path

p = Path(sys.argv[1] if len(sys.argv) > 1 else '/app/TLB_MODBUS.py')
text = p.read_text(encoding='utf-8')
old = 'counts = int(round(sample_grams / division))'
new = '''unit = getUnit()
    if unit not in ("g", "kg"):
        raise TLBCalibrationError("Calibration requires g or kg")
    sample = sample_grams if unit == "g" else sample_grams / 1000.0
    counts = int(round(sample / _weight_decimal_scale(division)))'''
nodes = {n.name: n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}
if '_weight_decimal_scale' not in nodes:
    raise SystemExit('Installer le correctif de lecture en premier')
node = nodes.get('_sample_counts')
if node is None or text.count(old) != 1 or old not in ast.get_source_segment(text, node):
    raise SystemExit('Version differente ou deja corrigee; aucun changement')
updated = text.replace(old, new)
tree = ast.parse(updated)
subset = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                         and n.name in ('_sample_counts', '_weight_decimal_scale')],
                    type_ignores=[])
env = {'TLBCalibrationError': RuntimeError, 'getUnit': lambda: 'g'}
exec(compile(subset, str(p), 'exec'), env)
assert env['_sample_counts'](1000, 0.5) == 10000
env['getUnit'] = lambda: 'kg'
assert env['_sample_counts'](1000, 0.0005) == 10000
backup = p.with_name(p.name + '.backup-calibration-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
backup.write_bytes(p.read_bytes())
tmp = p.with_name(p.name + '.calibration-fix.tmp')
tmp.write_text(updated, encoding='utf-8')
tmp.replace(p)
print('Calibration corrigee : 1000 g -> 10000. Sauvegarde :', backup)
