// DESKTOP MOCK of the few Arduino calls the firmware uses. Test fixture, not firmware.
#pragma once
#ifndef MICROSCAN_HOST_MOCK
#define MICROSCAN_HOST_MOCK 1
#endif
#include <cstdint>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdarg>
#include <string>
#include <vector>

#define HIGH 1
#define LOW 0
#define OUTPUT 3

namespace mock {
extern std::vector<std::string> events;      // ordered log of every hardware-facing call
extern std::vector<uint8_t> serial_out;      // bytes the firmware wrote to the UART
extern std::string serial_in;                // bytes waiting for the firmware to read
extern int gpio_level[40];
extern bool readback_stuck_low;              // fault injection: latch never reads HIGH
extern int readback_drop_after_fb;           // fault injection: latch drops after N fb_get calls
extern bool psram;
void log(const std::string& e);
}

class String {
 public:
  String() {}
  String(const char* s) : s_(s) {}
  void trim() {
    size_t a = s_.find_first_not_of(" \t\r\n");
    size_t b = s_.find_last_not_of(" \t\r\n");
    s_ = (a == std::string::npos) ? std::string() : s_.substr(a, b - a + 1);
  }
  size_t length() const { return s_.size(); }
  bool operator==(const char* o) const { return s_ == o; }
  String& operator+=(char c) { s_ += c; return *this; }
  String& operator=(const char* o) { s_ = o; return *this; }
 private:
  std::string s_;
};

class MockSerial {
 public:
  void begin(unsigned long baud) { mock::log("SERIAL_BEGIN " + std::to_string(baud)); }
  size_t write(uint8_t b) { mock::serial_out.push_back(b); mock::log("SERIAL_WRITE 1"); return 1; }
  size_t write(const uint8_t* p, size_t n) {
    mock::serial_out.insert(mock::serial_out.end(), p, p + n);
    mock::log("SERIAL_WRITE " + std::to_string(n));
    return n;
  }
  void println(const char* s) {
    std::string t = std::string(s) + "\r\n";
    mock::serial_out.insert(mock::serial_out.end(), t.begin(), t.end());
    mock::log(std::string("SERIAL_TEXT ") + s);
  }
  void printf(const char* fmt, ...) {
    char buf[512];
    va_list ap; va_start(ap, fmt); vsnprintf(buf, sizeof buf, fmt, ap); va_end(ap);
    std::string t(buf);
    mock::serial_out.insert(mock::serial_out.end(), t.begin(), t.end());
    mock::log("SERIAL_TEXT " + t.substr(0, t.find('\n')));
  }
  int available() { return int(mock::serial_in.size()); }
  int read() { if (mock::serial_in.empty()) return -1; char c = mock::serial_in[0]; mock::serial_in.erase(0, 1); return (unsigned char)c; }
  void flush() { mock::log("SERIAL_FLUSH"); }
};
extern MockSerial Serial;

void pinMode(int pin, int mode);
void digitalWrite(int pin, int level);
int digitalRead(int pin);
void delay(uint32_t ms);
bool psramFound();
void* ps_malloc(size_t n);
