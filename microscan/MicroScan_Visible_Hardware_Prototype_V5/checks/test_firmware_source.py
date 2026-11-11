"""Deterministic checks on the firmware SOURCE TEXT. Text checks are not compilation and not hardware."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / 'firmware' / 'microscan_hw818_candidate'
SRC = (FW / 'src' / 'main.cpp').read_text()
CODE = re.sub(r'//[^\n]*', '', re.sub(r'/\*.*?\*/', '', SRC, flags=re.S))   # comments stripped
V4 = (ROOT / 'source_v4' / 'extracted_unmodified' / 'firmware' / 'VISIBLE_USB_CAMERA_DIAGNOSTIC.ino').read_text()


class Source(unittest.TestCase):
    def test_both_v4_gates_are_still_zero_and_hard_coded(self):
        self.assertRegex(CODE, r'#define MICROSCAN_BOARD_PINS_VERIFIED 0\n')
        self.assertRegex(CODE, r'#define MICROSCAN_VISIBLE_INDICATOR_VERIFIED 0\n')
        for name in ('MICROSCAN_BOARD_PINS_VERIFIED', 'MICROSCAN_VISIBLE_INDICATOR_VERIFIED'):
            self.assertNotRegex(CODE, r'#ifndef\s+' + name, f'{name} must not be overridable from the command line')
            self.assertEqual(len(re.findall(r'#define\s+' + name + r'\b', CODE)), 1)

    def test_gate_errors_present(self):
        self.assertIn('#error "HW-818 camera pin map unverified; refuse capture-capable build."', CODE)
        self.assertIn('#error "Visible capture indicator unverified; refuse capture-capable build."', CODE)
        self.assertIn('#error "MICROSCAN_HOST_MOCK must never be defined in an ESP32 build."', CODE)
        self.assertIn('#error "Bring-up (capture-locked) mode is only for boards whose gates are still 0."', CODE)

    def test_build_config_cannot_define_the_gates(self):
        ini = (FW / 'platformio.ini').read_text()
        self.assertNotIn('MICROSCAN_BOARD_PINS_VERIFIED', ini)
        self.assertNotIn('MICROSCAN_VISIBLE_INDICATOR_VERIFIED', ini)
        self.assertNotIn('MICROSCAN_HOST_MOCK', ini)
        self.assertNotIn('upload_port', ini)
        self.assertNotIn('lib_deps', ini, 'no third-party libraries are pulled')

    def test_no_radio_storage_or_network_code(self):
        for banned in ('WiFi', 'wifi', 'Bluetooth', 'BLEDevice', 'NimBLE', 'esp_bt', 'esp_now', 'HTTP', 'httpd', 'SD_MMC', 'SD.h', 'SPIFFS', 'LittleFS',
                       'ArduinoOTA', 'Update.h', 'socket', 'mqtt', 'esp_sleep', 'attachInterrupt', 'touchRead', 'xTaskCreate',
                       'Ticker', 'hw_timer', 'timerBegin'):
            self.assertNotIn(banned, CODE, f'{banned} found in firmware code')
        includes = re.findall(r'#include\s*[<"]([^>"]+)[>"]', CODE)
        self.assertEqual(includes, ['Arduino.h', 'esp_camera.h', 'img_converters.h'])

    def test_single_guarded_frame_grab(self):
        self.assertEqual(CODE.count('esp_camera_fb_get('), 1)
        m = re.search(r'static camera_fb_t\* guarded_fb_get\(const IndicatorScope& indicator\) \{(.*?)\n\}', CODE, re.S)
        self.assertIsNotNone(m)
        body = m.group(1)
        self.assertLess(body.index('if (!indicator.lit()) return nullptr;'), body.index('esp_camera_fb_get()'))

    def test_indicator_is_only_switched_off_by_scope_exit_or_setup(self):
        lows = [m.start() for m in re.finditer(r'digitalWrite\(CAPTURE_INDICATOR_GPIO, LOW\)', CODE)]
        self.assertEqual(len(lows), 2)
        self.assertIn('~IndicatorScope() { digitalWrite(CAPTURE_INDICATOR_GPIO, LOW); }', CODE)
        setup = re.search(r'void setup\(\) \{(.*?)\n\}', CODE, re.S).group(1)
        self.assertIn('digitalWrite(CAPTURE_INDICATOR_GPIO, LOW);', setup)
        self.assertEqual(len(re.findall(r'digitalWrite\(CAPTURE_INDICATOR_GPIO, HIGH\)', CODE)), 1)

    def test_no_preprocessor_switch_around_the_interlock(self):
        start = CODE.index('class IndicatorScope')
        end = CODE.index('static void write_le16')
        self.assertNotIn('#if', CODE[start:end])
        cap = re.search(r'static void capture_explicit\(\) \{(.*?)\n\}\n', CODE, re.S).group(1)
        self.assertNotIn('#if', cap)
        self.assertNotIn('#define', cap)
        self.assertNotRegex(CODE, r'#define\s+(digitalWrite|digitalRead|esp_camera_fb_get|HIGH|LOW)\b')
        self.assertNotRegex(CODE, r'#undef')

    def test_capture_holds_scope_before_any_camera_or_uart_payload_use(self):
        cap = re.search(r'static void capture_explicit\(\) \{(.*?)\n\}\n', CODE, re.S).group(1)
        scope = cap.index('IndicatorScope indicator;')
        for token in ('guarded_fb_get(', 'frame2jpg_cb(', 'Serial.write('):
            self.assertGreater(cap.index(token), scope, token)
        self.assertLess(cap.index('if (g_capture_locked)'), scope)
        self.assertEqual(CODE.count('capture_explicit();'), 1, 'exactly one call site')
        self.assertIn('if (line == "CAPTURE") capture_explicit();', CODE)

    def test_loop_has_no_autonomous_trigger(self):
        loop = re.search(r'void loop\(\) \{(.*?)\n\}', CODE, re.S).group(1)
        for banned in ('millis', 'delay', 'digitalRead', 'analogRead'):
            self.assertNotIn(banned, loop)

    def test_wire_format_and_crc_unchanged_from_v4(self):
        def crc_fn(text):
            m = re.search(r'static uint32_t crc32_bytes\(.*?\n\}', text, re.S)
            return re.sub(r'\s+', '', m.group(0))
        self.assertEqual(crc_fn(SRC), crc_fn(V4))
        self.assertIn('"MSJ1"', CODE)
        order = [CODE.index(t) for t in ('write_le32(uint32_t(jpeg_len));', 'write_le16(uint16_t(fb->width));',
                                         'write_le16(uint16_t(fb->height));', 'write_le32(checksum);', 'Serial.write(jpeg, jpeg_len);')]
        self.assertEqual(order, sorted(order))

    def test_pin_map_equals_espressif_ai_thinker_and_v4(self):
        expect = {'PWDN': 32, 'RESET': -1, 'XCLK': 0, 'SIOD': 26, 'SIOC': 27, 'Y9': 35, 'Y8': 34, 'Y7': 39, 'Y6': 36,
                  'Y5': 21, 'Y4': 19, 'Y3': 18, 'Y2': 5, 'VSYNC': 25, 'HREF': 23, 'PCLK': 22}
        for text in (CODE, V4):
            got = {k: int(v) for k, v in re.findall(r'#define CAM_(\w+) (-?\d+)', text)}
            self.assertEqual(got, expect)
        self.assertRegex(CODE, r'#define CAPTURE_INDICATOR_GPIO 4\b')

    def test_baud_is_restricted(self):
        self.assertIn('static_assert(MICROSCAN_BAUD == 115200 || MICROSCAN_BAUD == 230400 || MICROSCAN_BAUD == 460800 ||', CODE)

    def test_v4_firmware_is_preserved_unmodified(self):
        self.assertIn('#define MICROSCAN_BOARD_PINS_VERIFIED 0', V4)
        self.assertIn('#define MICROSCAN_VISIBLE_INDICATOR_VERIFIED 0', V4)


if __name__ == '__main__':
    unittest.main()
