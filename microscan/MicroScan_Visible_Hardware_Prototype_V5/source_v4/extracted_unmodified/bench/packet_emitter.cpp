/* Portable C++ reference for the V3 camera UART frame encoder. This is a
 * PROTOCOL test fixture, not firmware built or flashed for ESP32 hardware. */
#include <cstdint>
#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <vector>

static uint32_t crc32_bytes(const uint8_t *bytes, size_t n) {
  uint32_t crc = 0xFFFFFFFFUL;
  for (size_t i=0; i<n; ++i) {
    crc ^= bytes[i];
    for (int bit=0; bit<8; ++bit) crc = (crc >> 1) ^ ((crc & 1) ? 0xEDB88320UL : 0);
  }
  return ~crc;
}
static void write16(uint16_t n) {
  std::putchar(uint8_t(n & 255)); std::putchar(uint8_t((n >> 8) & 255));
}
static void write32(uint32_t n) {
  for (int i=0; i<4; ++i) std::putchar(uint8_t((n >> (8*i)) & 255));
}
int main(int argc, char** argv) {
  if (argc!=4) { std::fprintf(stderr, "usage: packet_emitter file.jpg width height\n"); return 2; }
  std::ifstream f(argv[1], std::ios::binary);
  if (!f) return 3;
  std::vector<uint8_t> bytes((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
  unsigned long w=std::strtoul(argv[2],nullptr,10), h=std::strtoul(argv[3],nullptr,10);
  if (bytes.size()<2 || bytes.size()>10000000 || w==0 || h==0 || w>5000 || h>5000) return 4;
  std::fwrite("MSJ1",1,4,stdout);
  write32(uint32_t(bytes.size())); write16(uint16_t(w)); write16(uint16_t(h));
  write32(crc32_bytes(bytes.data(),bytes.size()));
  std::fwrite(bytes.data(),1,bytes.size(),stdout);
  return std::ferror(stdout)?5:0;
}
