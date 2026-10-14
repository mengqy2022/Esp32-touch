from types import SimpleNamespace
import unittest
from dashboard_agent import matching_port


class DiscoveryTests(unittest.TestCase):
    def port(self, name='COM5', vid=0x1A86, pid=0x7523, location='1-2', serial_number=''):
        return SimpleNamespace(device=name, vid=vid, pid=pid, location=location, serial_number=serial_number)

    def test_absent_and_unrelated_devices(self):
        config={'vid':0x1A86,'pid':0x7523,'device':'COM5','location':'1-2'}
        self.assertIsNone(matching_port([],config))
        self.assertIsNone(matching_port([self.port(vid=0x10C4)],config))

    def test_com_number_can_change(self):
        self.assertEqual(matching_port([self.port(name='COM8',location='1-4')],{'vid':0x1A86,'pid':0x7523,'device':'COM5'}),'COM8')

    def test_multiple_bridges_need_identity(self):
        ports=[self.port('COM7',location='1-3'),self.port('COM8',location='1-2')]
        config={'vid':0x1A86,'pid':0x7523,'location':'1-2'}
        self.assertEqual(matching_port(ports,config),'COM8')
        self.assertIsNone(matching_port(ports,{'vid':0x1A86,'pid':0x7523}))

    def test_serial_identity(self):
        ports=[self.port(serial_number='wrong'),self.port('COM8',serial_number='target')]
        self.assertEqual(matching_port(ports,{'vid':0x1A86,'pid':0x7523,'serial_number':'target'}),'COM8')


if __name__=='__main__':
    unittest.main()
