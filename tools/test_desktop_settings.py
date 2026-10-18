import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

if sys.platform == 'win32':
    from desktop_dashboard import update_prices, choose_ai_source, control_dialog, set_device_source
    from device_settings import save_config, load_config


@unittest.skipUnless(sys.platform == 'win32', 'Windows control application')
class DesktopSettingsTests(unittest.TestCase):
    def test_portable_runtime_uses_existing_config_beside_executable(self):
        from desktop_dashboard import install_root
        import os
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'config.json').write_text('{}')
            with patch.dict(os.environ, {'ESP32_DASHBOARD_HOME': ''}), \
                 patch('sys.frozen', True, create=True), patch('sys.executable', str(root / 'ESP32TouchDashboard.exe')):
                self.assertEqual(install_root(), root)
            with patch.dict(os.environ, {'ESP32_DASHBOARD_HOME': str(root)}):
                self.assertEqual(install_root(), root.resolve())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.prices = self.root / 'codex_prices.json'

    def test_upgrade_legacy_rates_preserves_fx_and_backs_up(self):
        fields = ['input_per_million', 'cached_input_per_million', 'cache_write_input_per_million', 'output_per_million']
        old = dict(currency='USD', usd_to_cny=7.1, models={
            'gpt-6-astra': dict(short=dict(zip(fields, [10, 1, 12.5, 50])),
                                long=dict(zip(fields, [20, 2, 25, 75])))})
        self.prices.write_text(json.dumps(old), encoding='utf-8')
        update_prices(self.root)
        result = json.loads(self.prices.read_text(encoding='utf-8'))
        self.assertEqual(result['usd_to_cny'], 7.1)
        self.assertEqual(result['models']['gpt-6-astra']['short']['input_per_million'], 2)
        self.assertIn('claude-fable-5-1', result['models'])
        self.assertEqual(json.loads((self.root / 'codex_prices.before-2026-10-17.json').read_text()), old)

    def test_upgrade_custom_prices_preserved(self):
        custom = dict(currency='CNY', usd_to_cny=7, models={'custom': dict(input_per_million=1)})
        self.prices.write_text(json.dumps(custom), encoding='utf-8')
        update_prices(self.root)
        self.assertEqual(json.loads(self.prices.read_text()), custom)
        custom['currency'] = 'USD'
        custom['models']['gpt-6-astra'] = dict(input_per_million=7)
        self.prices.write_text(json.dumps(custom), encoding='utf-8')
        update_prices(self.root)
        self.assertEqual(json.loads(self.prices.read_text())['models']['gpt-6-astra'], dict(input_per_million=7))

    def test_source_selection_applies_without_changing_pause(self):
        save_config(self.root / 'config.json', dict(device=dict(vid=0x1A86, pid=0x7523)))
        (self.root / 'paused').touch()
        for action, source in ((203, 'claude'), (202, 'codex')):
            with patch('desktop_dashboard.native_command_dialog', return_value=action) as dialog, \
                 patch('desktop_dashboard.set_device_source') as select:
                choose_ai_source(self.root)
            self.assertEqual(select.call_args.args[2], source)
            self.assertEqual(load_config(self.root / 'config.json')['ai_source'], source)
            self.assertEqual([item[0] for item in dialog.call_args.args[2]], [202, 203])
            self.assertTrue((self.root / 'paused').exists())

    def test_fallback_selects_device_and_restores_pause_on_ack_or_error(self):
        marker = self.root / 'paused'
        for was_paused in (False, True):
            if was_paused:
                marker.touch()
            with patch('desktop_dashboard.is_running', return_value=False), patch('serial.Serial') as serial:
                connection = serial.return_value.__enter__.return_value
                connection.read.return_value = b'PC:AI_STATE|CLAUDE|155|20261017|3|1\n'
                set_device_source(self.root, 'COM5', 'claude')
                connection.write.assert_called_once_with(b'PC:AI|CLAUDE\nPC:AI?\n')
                self.assertEqual(marker.exists(), was_paused)
                connection.read.side_effect = OSError('Disconnected')
                with self.assertRaises(OSError):
                    set_device_source(self.root, 'COM5', 'codex')
                self.assertEqual(marker.exists(), was_paused)

    def test_fallback_without_device_retains_source_and_pause(self):
        save_config(self.root / 'config.json', dict(device=dict(vid=0x1A86, pid=0x7523), ai_source='codex'))
        with patch('desktop_dashboard.native_command_dialog', return_value=203), \
             patch('desktop_dashboard.serial.tools.list_ports.comports', return_value=[]):
            with self.assertRaises(RuntimeError):
                choose_ai_source(self.root)
        self.assertEqual(load_config(self.root / 'config.json')['ai_source'], 'codex')
        self.assertFalse((self.root / 'paused').exists())

    def test_control_exposes_all_new_actions(self):
        save_config(self.root / 'config.json', dict(device=dict(vid=0x1A86, pid=0x7523)))
        with patch('desktop_dashboard.startup_status', return_value=dict(enabled=False, paused=True)), \
             patch('desktop_dashboard.serial.tools.list_ports.comports', return_value=[]), \
             patch('desktop_dashboard.native_command_dialog', return_value=0) as dialog:
            control_dialog(self.root)
        buttons = dict(dialog.call_args.args[2])
        self.assertIn('COM', buttons[107])
        self.assertIn('CH340', buttons[108])
        self.assertIn('CLAUDE', buttons[109])


if __name__ == '__main__':
    unittest.main()
