// DESKTOP MOCK of the esp32-camera API surface used by the firmware. Test fixture only.
#pragma once
#include <cstdint>
#include <cstddef>
typedef int esp_err_t;
#define ESP_OK 0
#define ESP_FAIL -1
#define ESP_ERR_NOT_SUPPORTED 0x106
#define ESP_ERR_NOT_FOUND 0x105
typedef enum { PIXFORMAT_RGB565, PIXFORMAT_YUV422, PIXFORMAT_GRAYSCALE, PIXFORMAT_JPEG } pixformat_t;
typedef enum { FRAMESIZE_QVGA, FRAMESIZE_VGA, FRAMESIZE_SVGA, FRAMESIZE_XGA, FRAMESIZE_UXGA } framesize_t;
typedef enum { CAMERA_FB_IN_PSRAM, CAMERA_FB_IN_DRAM } camera_fb_location_t;
typedef enum { CAMERA_GRAB_WHEN_EMPTY, CAMERA_GRAB_LATEST } camera_grab_mode_t;
#define LEDC_CHANNEL_0 0
#define LEDC_TIMER_0 0
typedef struct {
  int pin_pwdn, pin_reset, pin_xclk, pin_sccb_sda, pin_sccb_scl;
  int pin_d7, pin_d6, pin_d5, pin_d4, pin_d3, pin_d2, pin_d1, pin_d0, pin_vsync, pin_href, pin_pclk;
  int xclk_freq_hz, ledc_timer, ledc_channel;
  pixformat_t pixel_format; framesize_t frame_size; int jpeg_quality; size_t fb_count;
  camera_fb_location_t fb_location; camera_grab_mode_t grab_mode;
} camera_config_t;
typedef struct { uint8_t* buf; size_t len; size_t width; size_t height; pixformat_t format; } camera_fb_t;
typedef struct { uint8_t MIDH, MIDL; uint16_t PID; uint8_t VER; } sensor_id_t;
typedef struct { sensor_id_t id; } sensor_t;
esp_err_t esp_camera_init(const camera_config_t* cfg);
esp_err_t esp_camera_deinit();
camera_fb_t* esp_camera_fb_get();
void esp_camera_fb_return(camera_fb_t* fb);
sensor_t* esp_camera_sensor_get();
