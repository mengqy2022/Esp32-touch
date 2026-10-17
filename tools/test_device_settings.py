import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from device_settings import load_config, save_config, driver_summary, install_signed_driver


class SettingsTests(unittest.TestCase):
    def test_legacy_combined_mode_migrates_to_codex_and_preserves_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.json'
            device = dict(vid=0x1A86, pid=0x7523, mode='manual', device='COM5')
            for source in (None, 'all', 'codex', 'claude'):
                config = dict(device=device, codex_refresh=7)
                if source is not None:
                    config['ai_source'] = source
                path.write_text(json.dumps(config), encoding='utf-8')
                migrated = load_config(path)
                self.assertEqual(migrated['ai_source'], 'claude' if source == 'claude' else 'codex')
                self.assertEqual(migrated['device'], device)
                self.assertEqual(migrated['codex_refresh'], 7)
                save_config(path, migrated)
                self.assertEqual(load_config(path), migrated)

    def test_atomic_settings_remove_goal_and_reject_invalid_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.json'
            config = dict(device=dict(vid=0x1A86, pid=0x7523), daily_goal=500, ai_source='claude')
            save_config(path, config)
            self.assertNotIn('daily_goal', load_config(path))
            self.assertEqual(load_config(path)['ai_source'], 'claude')
            for field, value in (('ai_source', 'invalid'), ('codex_refresh', 0), ('codex_refresh', float('nan'))):
                bad = dict(config, **{field: value})
                path.write_text(json.dumps(bad), encoding='utf-8')
                with self.assertRaises(ValueError):
                    load_config(path)

    def test_driver_missing_is_different_from_unplugged(self):
        self.assertIn('无法据此判断', driver_summary([]))
        self.assertIn('缺少驱动', driver_summary([dict(name='USB', code=28)]))
        self.assertIn('驱动正常', driver_summary([dict(name='CH340 COM5', code=0)]))
        self.assertIn('无法查询', driver_summary(None))

    def test_driver_requires_valid_vendor_signature_before_elevation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'CH341SER.EXE'
            path.write_bytes(b'MZtest')
            with patch('device_settings.subprocess.run') as run:
                run.return_value.returncode = 1
                run.return_value.stderr = 'Invalid signature'
                with self.assertRaises(RuntimeError):
                    install_signed_driver(path)
                script = (path.parent / 'install_wch.ps1').read_text(encoding='utf-8-sig')
                self.assertLess(script.index('Get-AuthenticodeSignature'), script.index('-Verb RunAs'))
                self.assertIn("$sig.Status -ne 'Valid'", script)


if __name__ == '__main__':
    unittest.main()
