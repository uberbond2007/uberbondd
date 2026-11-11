/* MicroScan V3 OPEN / USB-TETHERED laboratory camera diagnostic.
 * No wireless services, no background capture, no covert trigger.
 * Operator must explicitly send CAPTURE over the wired serial link.
 * Capture indicator must be electrically identified and tested first.
 * RHYX-M21/AI-Thinker pin similarity is THIRD-PARTY REPORTED, NOT manufacturer-proven.
 * Fails compile until board pin mapping AND capture LED are personally verified.
 * No physical RHYX board has been tested by the author.
 */
#include <Arduino.h>
#include <esp_camera.h>

// BLOCKER: set to 1 only after physical board pin mapping has been independently verified.
#define MICROSCAN_BOARD_PINS_VERIFIED 0
// BLOCKER: set to 1 only after physical flash/status LED GPIO4 is verified visible during exposure.
#define MICROSCAN_VISIBLE_INDICATOR_VERIFIED 0
#if MICROSCAN_BOARD_PINS_VERIFIED != 1
  #error "RHYX board camera pin map unverified; refuse hardware build."
#endif
#if MICROSCAN_VISIBLE_INDICATOR_VERIFIED != 1
  #error "Visible capture indicator GPIO unverified; refuse hardware build."
#endif

// Provisional AI-Thinker pin map, based on Espressif camera_pins.h.
#define CAM_PWDN 32
#define CAM_RESET -1
#define CAM_XCLK 0
#define CAM_SIOD 26
#define CAM_SIOC 27
#define CAM_Y9 35
#define CAM_Y8 34
#define CAM_Y7 39
#define CAM_Y6 36
#define CAM_Y5 21
#define CAM_Y4 19
#define CAM_Y3 18
#define CAM_Y2 5
#define CAM_VSYNC 25
#define CAM_HREF 23
#define CAM_PCLK 22
#define CAPTURE_INDICATOR_GPIO 4 // Provisional: only valid after physical inspection.

static void write_le16(uint16_t n) {
  Serial.write(uint8_t(n & 255));
  Serial.write(uint8_t((n >> 8) & 255));
}
static void write_le32(uint32_t n) {
  for (int k=0; k<4; ++k) Serial.write(uint8_t((n >> (8*k)) & 255));
}
static uint32_t crc32_bytes(const uint8_t *bytes, size_t n) {
  uint32_t crc = 0xFFFFFFFFUL;
  for(size_t i = 0; i < n; ++i) {
    crc ^= bytes[i];
    for(int bit=0; bit<8; ++bit) crc = (crc>>1) ^ ((crc&1)?0xEDB88320UL:0);
  }
  return ~crc;
}
static bool initialized=false;
static void capture_explicit() {
  if(!initialized) { Serial.println("ERROR camera not ready"); return; }
  // On verified boards, flash light communicates active capture and aids document illumination.
  digitalWrite(CAPTURE_INDICATOR_GPIO, HIGH);
  delay(90);
  camera_fb_t *fb = esp_camera_fb_get();
  if(!fb) {
    digitalWrite(CAPTURE_INDICATOR_GPIO, LOW);
    Serial.println("ERROR camera capture failed");
    return;
  }
  // Wire format: MSJ1, uint32 length, uint16 width, uint16 height, uint32 CRC32, raw JPEG.
  const uint32_t checksum = crc32_bytes(fb->buf, fb->len);
  Serial.write(reinterpret_cast<const uint8_t*>("MSJ1"),4);
  write_le32(uint32_t(fb->len));
  write_le16(uint16_t(fb->width));
  write_le16(uint16_t(fb->height));
  write_le32(checksum);
  Serial.write(fb->buf,fb->len);
  Serial.flush();
  esp_camera_fb_return(fb);
  digitalWrite(CAPTURE_INDICATOR_GPIO, LOW);
}
void setup() {
  Serial.begin(115200);
  pinMode(CAPTURE_INDICATOR_GPIO,OUTPUT);
  digitalWrite(CAPTURE_INDICATOR_GPIO,LOW);
  camera_config_t cfg = {};
  cfg.ledc_channel=LEDC_CHANNEL_0;
  cfg.ledc_timer=LEDC_TIMER_0;
  cfg.pin_d0=CAM_Y2; cfg.pin_d1=CAM_Y3; cfg.pin_d2=CAM_Y4; cfg.pin_d3=CAM_Y5;
  cfg.pin_d4=CAM_Y6; cfg.pin_d5=CAM_Y7; cfg.pin_d6=CAM_Y8; cfg.pin_d7=CAM_Y9;
  cfg.pin_xclk=CAM_XCLK; cfg.pin_pclk=CAM_PCLK;
  cfg.pin_vsync=CAM_VSYNC; cfg.pin_href=CAM_HREF;
  cfg.pin_sccb_sda=CAM_SIOD; cfg.pin_sccb_scl=CAM_SIOC;
  cfg.pin_pwdn=CAM_PWDN; cfg.pin_reset=CAM_RESET;
  cfg.xclk_freq_hz=20000000;
  cfg.pixel_format=PIXFORMAT_JPEG;
  cfg.jpeg_quality=12;
  cfg.fb_count=1;
  cfg.grab_mode=CAMERA_GRAB_WHEN_EMPTY;
  cfg.fb_location=psramFound() ? CAMERA_FB_IN_PSRAM:CAMERA_FB_IN_DRAM;
  cfg.frame_size=psramFound() ? FRAMESIZE_UXGA:FRAMESIZE_VGA;
  const esp_err_t status=esp_camera_init(&cfg);
  initialized=(status==ESP_OK);
  if(initialized) Serial.println("MICROSCAN_VISIBLE_USB_READY; type CAPTURE and newline");
  else Serial.printf("ERROR camera init 0x%x\n",unsigned(status));
}
void loop() {
  static String line;
  while(Serial.available()>0) {
    const char c = char(Serial.read());
    if(c=='\n' || c=='\r') {
      line.trim();
      if(line=="CAPTURE") capture_explicit();
      else if(line.length()) Serial.println("ERROR unknown operator command");
      line="";
    } else if(line.length()<32 && c>=32 && c<=126) line+=c;
  }
}
