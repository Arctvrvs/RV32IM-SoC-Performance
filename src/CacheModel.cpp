#include "rv32im/CacheModel.hpp"

#include <stdexcept>

namespace rv32im {

DirectMappedCacheModel::DirectMappedCacheModel(const CacheConfig& config) {
    configure(config);
}

bool DirectMappedCacheModel::is_power_of_two(std::size_t value) {
    return value != 0 && (value & (value - 1u)) == 0;
}

void DirectMappedCacheModel::configure(const CacheConfig& config) {
    if (!is_power_of_two(config.lines)) {
        throw std::invalid_argument("Cache line count must be a non-zero power of two");
    }
    if (config.line_bytes != 4) {
        throw std::invalid_argument("Current RTL cache model supports one 32-bit word (4 bytes) per line");
    }

    config_ = config;
    lines_.assign(config_.lines, Line{});
    stats_ = {};
}

void DirectMappedCacheModel::reset() {
    stats_ = {};
    for (auto& line : lines_) {
        line = {};
    }
}


bool DirectMappedCacheModel::would_hit(std::uint32_t byte_addr) const {
    if (!config_.enabled) {
        return true;
    }
    const std::uint64_t word_addr = static_cast<std::uint64_t>(byte_addr) / config_.line_bytes;
    const std::size_t index = static_cast<std::size_t>(word_addr % config_.lines);
    const std::uint64_t tag = word_addr / config_.lines;
    const auto& line = lines_[index];
    return line.valid && line.tag == tag;
}

std::uint32_t DirectMappedCacheModel::clean_miss_penalty() const {
    // RTL sequence: miss detect -> AR handshake -> LATENCY countdown ->
    // RVALID observation -> cache RESP -> CPU accepts response.
    return config_.memory_latency + 4u;
}

std::uint32_t DirectMappedCacheModel::dirty_miss_penalty() const {
    // Dirty victim performs an AXI write transaction before the normal refill.
    // The writeback path adds LATENCY+3 cycles to the clean refill path.
    return (2u * config_.memory_latency) + 7u;
}

CacheAccessResult DirectMappedCacheModel::access(std::uint32_t byte_addr, bool is_write) {
    CacheAccessResult result{};
    if (!config_.enabled) {
        result.hit = true;
        return result;
    }

    ++stats_.accesses;

    const std::uint64_t word_addr = static_cast<std::uint64_t>(byte_addr) / config_.line_bytes;
    const std::size_t index = static_cast<std::size_t>(word_addr % config_.lines);
    const std::uint64_t tag = word_addr / config_.lines;
    auto& line = lines_[index];

    if (line.valid && line.tag == tag) {
        result.hit = true;
        ++stats_.hits;
        if (is_write && config_.write_back) {
            line.dirty = true;
        }
        return result;
    }

    result.miss = true;
    ++stats_.misses;

    if (line.valid && line.dirty && config_.write_back) {
        result.writeback = true;
        ++stats_.writebacks;
        ++stats_.write_transactions;
        result.stall_cycles = dirty_miss_penalty();
    } else {
        result.stall_cycles = clean_miss_penalty();
    }

    // Both RTL caches refill one word on every miss. D-cache is write-allocate.
    ++stats_.read_transactions;
    stats_.stall_cycles += result.stall_cycles;

    line.valid = true;
    line.tag = tag;
    line.dirty = is_write && config_.write_back;

    return result;
}

} // namespace rv32im
