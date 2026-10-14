"""Exercise the real OS lock across processes, without API calls."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import benchmark as b


class LockTests(unittest.TestCase):
    def contender(self, path):
        return subprocess.run(
            [sys.executable, '-c',
             'import sys; sys.path.insert(0, sys.argv[1]); import benchmark as b; '
             'lock = b.exclusive_lock(sys.argv[2]); lock.__enter__(); lock.__exit__(None, None, None)',
             str(b.ROOT / 'scripts'), str(path)],
            capture_output=True, text=True, timeout=10)

    def test_competing_process_and_release_after_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'budget.lock'
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                with b.exclusive_lock(path):
                    result = self.contender(path)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('SetupError', result.stderr)
                    raise RuntimeError('interrupted')
            result = self.contender(path)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
