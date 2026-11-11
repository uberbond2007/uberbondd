#pragma once
#include "esp_camera.h"
typedef size_t (*jpg_out_cb)(void* arg, size_t index, const void* data, size_t len);
bool frame2jpg_cb(camera_fb_t* fb, uint8_t quality, jpg_out_cb cb, void* arg);
