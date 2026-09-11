"""Apply the weight-read decimal fix to an installed FFA, without hardware IO."""
import ast
import sys
from datetime import datetime
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "/app/TLB_MODBUS.py")
source = path.read_text(encoding="utf-8")
if "def _weight_decimal_scale(" in source:
    raise SystemExit("Correctif deja present; aucun changement")

helper = '''def _weight_decimal_scale(division):
    """Restore display decimals without multiplying by the resolution step."""
    from decimal import Decimal

    value = Decimal(str(division))
    if not value.is_finite() or value <= 0:
        raise ValueError("Invalid weight division")
    return 10.0 ** min(0, value.normalize().as_tuple().exponent)


'''
replacements = {
    "def _snapshot(is_belly=False):": helper + "def _snapshot(is_belly=False):",
    'round(net * division, 4)': 'round(net * _weight_decimal_scale(division), 4)',
    'round(gross * division, 4)': 'round(gross * _weight_decimal_scale(division), 4)',
    'round(_apply_sign(high, low, False) * division, 4)':
        'round(_apply_sign(high, low, False) * _weight_decimal_scale(division), 4)',
}
updated = source
for old, new in replacements.items():
    if updated.count(old) != 1:
        raise SystemExit("Version inattendue; aucun changement: " + old)
    updated = updated.replace(old, new)
ast.parse(updated)
namespace = {}
exec(helper, namespace)
scale = namespace["_weight_decimal_scale"]
assert round(10000 * scale(0.5), 4) == 1000.0
assert round(-25 * scale(0.5), 4) == -2.5
assert scale(5.0) == 1.0
assert scale(0.02) == 0.01
backup = path.with_name(path.name + ".backup-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
backup.write_bytes(path.read_bytes())
temporary = path.with_name(path.name + ".decimal-fix.tmp")
temporary.write_text(updated, encoding="utf-8")
temporary.replace(path)
print("Correctif applique. Sauvegarde :", backup)
