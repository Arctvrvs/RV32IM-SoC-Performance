#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace rv32im {

class Memory {
public:
    explicit Memory(std::size_t size_bytes = 1024 * 1024);

    std::size_t size() const { return bytes_.size(); }

    std::uint8_t read8(std::uint32_t addr) const;
    std::uint16_t read16(std::uint32_t addr) const;
    std::uint32_t read32(std::uint32_t addr) const;

    void write8(std::uint32_t addr, std::uint8_t value);
    void write16(std::uint32_t addr, std::uint16_t value);
    void write32(std::uint32_t addr, std::uint32_t value);

    // Supports a simple readmemh-style file:
    //   00500093
    //   00700113
    // and optional word-address directives such as @00000100.
    void load_hex_words(const std::string& path, std::uint32_t base_addr = 0);

private:
    void check_range(std::uint32_t addr, std::size_t width) const;
    std::vector<std::uint8_t> bytes_;
};

} // namespace rv32im
