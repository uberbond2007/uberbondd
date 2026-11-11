import pathlib, sys, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ReleaseChecks(unittest.TestCase):
 def test_stl_step_exists(self):
  for ext in ['stl','step']:
   for stem in ['Open_Camera_Carrier_V2','Adjustable_Edge_Retainer_V2']:
    self.assertTrue((ROOT/'cad'/f'{stem}.{ext}').stat().st_size>1000)
 def test_wiring_source_exists(self):
  self.assertIn('5V', (ROOT/'docs'/'FIT_AND_ELECTRICAL_GATES.md').read_text())
 def test_not_covert_firmware(self):
  text=(ROOT/'firmware'/'VISIBLE_USB_CAMERA_DIAGNOSTIC.ino').read_text()
  self.assertNotIn('#include <WiFi.h>',text)
  self.assertIn('MICROSCAN_BOARD_PINS_VERIFIED 0',text)
  self.assertIn('MICROSCAN_VISIBLE_INDICATOR_VERIFIED 0',text)
  self.assertIn('CAPTURE_INDICATOR_GPIO',text)
  self.assertIn('if(line=="CAPTURE")',text)
 def test_report_references_unverified(self):
  text=(ROOT/'docs'/'V3_COMPLETION_REPORT.md').read_text()
  for word in ['NOT BUILT','NOT COMPILED','NOT FLASHED','NOT TESTED']:
   self.assertIn(word,text)
if __name__=='__main__':unittest.main()
