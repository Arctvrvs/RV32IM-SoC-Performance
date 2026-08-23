#include "rv32im/Memory.hpp"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace rv32im {

Memory::Memory(std::size_t size_bytes) : bytes_(size_bytes, 0) {}

void Memory::check_range(std::uint32_t addr, std::size_t width) const {
    if (static_cast<std::uint64_t>(addr) + width > bytes_.size()) {
        std::ostringstream oss;
        oss << "Memory access out of range: addr=0x" << std::hex << addr
            << " width=" << std::dec << width
            << " memory_size=" << bytes_.size();
        throw std::out_of_range(oss.str());
    }
}

std::uint8_t Memory::read8(std::uint32_t addr) const {
    check_range(addr, 1);
    return bytes_[addr];
}

std::uint16_t Memory::read16(std::uint32_t addr) const {
    check_range(addr, 2);
    return static_cast<std::uint16_t>(bytes_[addr]) |
           (static_cast<std::uint16_t>(bytes_[addr + 1]) << 8u);
}

std::uint32_t Memory::read32(std::uint32_t addr) const {
    check_range(addr, 4);
    return static_cast<std::uint32_t>(bytes_[addr]) |
           (static_cast<std::uint32_t>(bytes_[addr + 1]) << 8u) |
           (static_cast<std::uint32_t>(bytes_[addr + 2]) << 16u) |
           (static_cast<std::uint32_t>(bytes_[addr + 3]) << 24u);
}

void Memory::write8(std::uint32_t addr, std::uint8_t value) {
    check_range(addr, 1);
    bytes_[addr] = value;
}

void Memory::write16(std::uint32_t addr, std::uint16_t value) {
    check_range(addr, 2);
    bytes_[addr] = static_cast<std::uint8_t>(value & 0xffu);
    bytes_[addr + 1] = static_cast<std::uint8_t>((value >> 8u) & 0xffu);
}

void Memory::write32(std::uint32_t addr, std::uint32_t value) {
    check_range(addr, 4);
    bytes_[addr] = static_cast<std::uint8_t>(value & 0xffu);
    bytes_[addr + 1] = static_cast<std::uint8_t>((value >> 8u) & 0xffu);
    bytes_[addr + 2] = static_cast<std::uint8_t>((value >> 16u) & 0xffu);
    bytes_[addr + 3] = static_cast<std::uint8_t>((value >> 24u) & 0xffu);
}

static std::string strip_comment(std::string line) {
    const auto slash = line.find("//");
    const auto hash = line.find('#');
    const auto semi = line.find(';');
    auto cut = line.size();
    if (slash != std::string::npos) cut = std::min(cut, slash);
    if (hash != std::string::npos) cut = std::min(cut, hash);
    if (semi != std::string::npos) cut = std::min(cut, semi);
    line.resize(cut);
    return line;
}

void Memory::load_hex_words(const std::string& path, std::uint32_t base_addr) {
    std::ifstream in(path);
    if (!in) {
        throw std::runtime_error("Could not open hex program: " + path);
    }

    std::uint32_t addr = base_addr;
    std::string line;
    std::size_t line_no = 0;

    while (std::getline(in, line)) {
        ++line_no;
        line = strip_comment(line);
        std::istringstream iss(line);
        std::string token;

        while (iss >> token) {
            if (token.empty()) continue;

            if (token[0] == '@') {
                const auto word_index = static_cast<std::uint32_t>(std::stoul(token.substr(1), nullptr, 16));
                addr = base_addr + word_index * 4u;
                continue;
            }

            if (token.rfind("0x", 0) == 0 || token.rfind("0X", 0) == 0) {
                token = token.substr(2);
            }

            try {
                const auto word = static_cast<std::uint32_t>(std::stoul(token, nullptr, 16));
                write32(addr, word);
                addr += 4u;
            } catch (const std::exception&) {
                std::ostringstream oss;
                oss << "Invalid hex token at " << path << ':' << line_no << ": " << token;
                throw std::runtime_error(oss.str());
            }
        }
    }
}

} // namespace rv32im
