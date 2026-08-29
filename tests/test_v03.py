from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from nvlx.config import DEFAULT
from nvlx.initramfs import initramfs_plan
from nvlx.prime import prime_report
from nvlx.report import sanitize_text
from nvlx.repository import driver_branch, repository_plan

class InitramfsTests(unittest.TestCase):
    def test_ubuntu_plan(self):
        with patch('nvlx.initramfs.shutil.which', side_effect=lambda x: f'/usr/bin/{x}'):
            p=initramfs_plan('6.8.0',{'ID':'ubuntu','VERSION_ID':'24.04'})
        self.assertEqual(p.command,('update-initramfs','-u','-k','6.8.0'))
    def test_rhel_plan(self):
        with patch('nvlx.initramfs.shutil.which', side_effect=lambda x: f'/usr/bin/{x}'):
            p=initramfs_plan('6.12.0',{'ID':'rhel','VERSION_ID':'10'})
        self.assertEqual(p.command[0],'dracut')

class RepositoryTests(unittest.TestCase):
    def test_branch(self): self.assertEqual(driver_branch('610.57.04'),'610')
    def test_apt_pinning(self):
        p=repository_plan(DEFAULT,{'ID':'ubuntu','VERSION_ID':'24.04'})
        self.assertIn('nvidia-driver-pinning-610',p.commands[0])

class PrimeTests(unittest.TestCase):
    def test_hybrid_topology(self):
        with TemporaryDirectory() as tmp, patch('nvlx.prime._providers',return_value=()):
            root=Path(tmp)
            for name,vendor,device in [('0000:00:02.0','0x8086','0x1234'),('0000:01:00.0','0x10de','0x2684')]:
                d=root/name; d.mkdir(); (d/'vendor').write_text(vendor); (d/'device').write_text(device); (d/'class').write_text('0x030000'); (d/'subsystem_vendor').write_text('0x0000'); (d/'subsystem_device').write_text('0x0000')
            self.assertTrue(prime_report(root).hybrid)

class ReportTests(unittest.TestCase):
    def test_sanitizes_home_and_secret(self):
        text=sanitize_text('token=abc123 path=/home/dominic/log.txt')
        self.assertNotIn('abc123',text); self.assertIn('/home/<user>',text)

if __name__=='__main__': unittest.main()
