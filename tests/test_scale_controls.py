"""Hardware-free regressions for Eventlet contention and sample encoding."""
import ast
from pathlib import Path
import subprocess
import sys

SOURCE = Path(__file__).resolve().parents[1] / 'TLB_MODBUS.py'


def definitions(names):
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    return ast.Module(body=[n for n in tree.body
                           if isinstance(n, ast.FunctionDef) and n.name in names],
                      type_ignores=[])


def calibration():
    env = {'TLBCalibrationError': RuntimeError, 'getUnit': lambda: 'g'}
    exec(compile(definitions({'_sample_counts', '_weight_decimal_scale'}),
                 str(SOURCE), 'exec'), env)
    encode = env['_sample_counts']
    assert encode(1000, 0.5) == 10000
    assert encode(1000, 0.2) == 10000
    env['getUnit'] = lambda: 'kg'
    assert encode(1000, 0.0005) == 10000
    env['getUnit'] = lambda: 'N'
    try:
        encode(1000, 0.5)
    except RuntimeError:
        pass
    else:
        raise AssertionError('Unsupported calibration unit accepted')


def contention():
    # Reproduce production: native lock created BEFORE monkey_patch.
    from threading import Lock
    lock = Lock()
    import eventlet
    eventlet.monkey_patch()
    import time
    from contextlib import contextmanager
    env = {'_lock': lock, 'time': time, 'contextmanager': contextmanager,
           'RETRIES': 0, 'RETRY_DELAY': 0.001, 'TLBCommunicationError': RuntimeError}
    exec(compile(definitions({'_serial_transaction_lock', '_transact'}),
                 str(SOURCE), 'exec'), env)
    active, done, heartbeat = [], [], []

    def serial_io(label):
        assert not active, 'Concurrent access to serial port'
        active.append(label)
        eventlet.sleep(0.05)
        active.pop()
        done.append(label)

    reader = eventlet.spawn(env['_transact'], 'read', serial_io, 'read')
    eventlet.sleep(0.005)
    writer = eventlet.spawn(env['_transact'], 'tare', serial_io, 'tare')
    eventlet.spawn_after(0.01, heartbeat.append, 'HTTP responsive')
    reader.wait()
    writer.wait()
    assert done == ['read', 'tare']
    assert heartbeat == ['HTTP responsive']
    try:
        env['_transact']('failure', lambda: (_ for _ in ()).throw(IOError('timeout')))
    except RuntimeError:
        pass
    assert lock.acquire(blocking=False), 'Lock leaked after exception'
    lock.release()


if __name__ == '__main__':
    if '--child' in sys.argv:
        contention()
    else:
        calibration()
        # A native-lock deadlock prevents even Eventlet timeouts; use an OS timeout.
        subprocess.run([sys.executable, __file__, '--child'], check=True, timeout=10)
        print('PASS: 1kg encoding, unit conversion, concurrent read/tare, heartbeat, lock release')
