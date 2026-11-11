/* Desktop harness: runs the REAL firmware source (src/main.cpp) against a mock HAL and records the
 * order of every indicator, camera and UART event. It proves ordering logic only - not hardware.
 * usage: harness <scenario> <jpeg-file> <width> <height> <serial-out.bin>   (event log -> stdout) */
#include "Arduino.h"
#include "esp_camera.h"
#include "img_converters.h"
#include <fstream>
#include <iterator>
#include <iostream>

namespace mock {
std::vector<std::string> events;
std::vector<uint8_t> serial_out;
std::string serial_in;
int gpio_level[40] = {0};
bool readback_stuck_low = false;
int readback_drop_after_fb = -1;
bool psram = true;
bool sensor_has_jpeg = true;
bool fb_fail = false;
bool init_not_found = false;
bool encode_fail = false;
int fb_gets = 0;
std::vector<uint8_t> jpeg;
std::vector<uint8_t> raw;
size_t width = 0, height = 0;
pixformat_t active = PIXFORMAT_JPEG;
camera_fb_t fb;
sensor_t sensor;
void log(const std::string& e) { events.push_back(e); }
}
MockSerial Serial;
void pinMode(int pin, int mode) { mock::log("PINMODE " + std::to_string(pin) + " " + std::to_string(mode)); }
void digitalWrite(int pin, int level) { mock::gpio_level[pin] = level; mock::log("GPIO" + std::to_string(pin) + "=" + std::to_string(level)); }
int digitalRead(int pin) {
  if (mock::readback_stuck_low) return LOW;
  if (mock::readback_drop_after_fb >= 0 && mock::fb_gets >= mock::readback_drop_after_fb) return LOW;
  return mock::gpio_level[pin];
}
void delay(uint32_t ms) { mock::log("DELAY " + std::to_string(ms)); }
bool psramFound() { return mock::psram; }
void* ps_malloc(size_t n) { mock::log("PS_MALLOC " + std::to_string(n)); return malloc(n); }
esp_err_t esp_camera_init(const camera_config_t* cfg) {
  mock::log(std::string("CAM_INIT ") + (cfg->pixel_format == PIXFORMAT_JPEG ? "JPEG" : "RGB565"));
  if (mock::init_not_found) return ESP_ERR_NOT_FOUND;
  if (cfg->pixel_format == PIXFORMAT_JPEG && !mock::sensor_has_jpeg) return ESP_ERR_NOT_SUPPORTED;
  mock::active = cfg->pixel_format;
  return ESP_OK;
}
esp_err_t esp_camera_deinit() { mock::log("CAM_DEINIT"); return ESP_OK; }
camera_fb_t* esp_camera_fb_get() {
  ++mock::fb_gets;
  mock::log("FB_GET indicator=" + std::to_string(mock::gpio_level[4]));
  if (mock::fb_fail) return nullptr;
  mock::fb.width = mock::width; mock::fb.height = mock::height; mock::fb.format = mock::active;
  if (mock::active == PIXFORMAT_JPEG) { mock::fb.buf = mock::jpeg.data(); mock::fb.len = mock::jpeg.size(); }
  else { mock::raw.assign(mock::width * mock::height * 2, 0x55); mock::fb.buf = mock::raw.data(); mock::fb.len = mock::raw.size(); }
  return &mock::fb;
}
void esp_camera_fb_return(camera_fb_t*) { mock::log("FB_RETURN"); }
sensor_t* esp_camera_sensor_get() { mock::sensor.id.PID = mock::sensor_has_jpeg ? 0x26 : 0x2145; return &mock::sensor; }
bool frame2jpg_cb(camera_fb_t*, uint8_t, jpg_out_cb cb, void* arg) {
  mock::log("SOFT_JPEG_ENCODE indicator=" + std::to_string(mock::gpio_level[4]));
  if (mock::encode_fail) return false;
  size_t i = 0;
  while (i < mock::jpeg.size()) {  // the real encoder also emits in pieces
    size_t n = std::min<size_t>(700, mock::jpeg.size() - i);
    if (cb(arg, i, mock::jpeg.data() + i, n) != n) return false;
    i += n;
  }
  return true;
}

#include "../src/main.cpp"

int main(int argc, char** argv) {
  if (argc != 6) { std::fprintf(stderr, "usage: harness scenario jpeg w h out.bin\n"); return 2; }
  const std::string sc = argv[1];
  std::ifstream f(argv[2], std::ios::binary);
  mock::jpeg.assign(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
  mock::width = std::strtoul(argv[3], nullptr, 10);
  mock::height = std::strtoul(argv[4], nullptr, 10);
  std::string input = "CAPTURE\n";
  if (sc == "ov2640_capture") {}
  else if (sc == "gc2145_capture") mock::sensor_has_jpeg = false;
  else if (sc == "gc2145_no_psram") { mock::sensor_has_jpeg = false; mock::psram = false; }
  else if (sc == "gc2145_encode_fail") { mock::sensor_has_jpeg = false; mock::encode_fail = true; }
  else if (sc == "indicator_stuck_low") mock::readback_stuck_low = true;
  else if (sc == "indicator_drops_midway") mock::readback_drop_after_fb = 2;
  else if (sc == "camera_fb_fail") mock::fb_fail = true;
  else if (sc == "camera_not_found") mock::init_not_found = true;
  else if (sc == "bringup_locked") g_capture_locked = true;
  else if (sc == "unknown_command") input = "capture\nSTREAM\nCAPTUREX\nXCAPTURE\nCAPTURE NOW\n";
  else if (sc == "no_command") input = "";
  else if (sc == "lamptest") input = "LAMPTEST\n";
  else if (sc == "info") input = "INFO\n";
  else if (sc == "two_requests") input = "CAPTURE\nCAPTURE\n";
  else { std::fprintf(stderr, "unknown scenario\n"); return 2; }
  setup();
  mock::log("---SETUP_DONE");
  mock::serial_in = input;
  for (int i = 0; i < 50; ++i) loop();   // many idle loop() passes: nothing may fire by itself
  std::ofstream out(argv[5], std::ios::binary);
  out.write(reinterpret_cast<const char*>(mock::serial_out.data()), std::streamsize(mock::serial_out.size()));
  for (auto& e : mock::events) std::cout << e << "\n";
  return 0;
}
