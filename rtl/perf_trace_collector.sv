// Retirement trace collector with cache-stall de-duplication.
//
// rv32im_pipeline intentionally holds MEM/WB stable while a cache miss stalls
// the pipe so forwarding remains valid. During those held cycles the DUT marks
// trace_writeback_cycle_status as TRACE_MEMSTALL (32). Those cycles are NOT new
// architectural retirements, so this collector suppresses them.

module perf_trace_collector #(
    parameter string TRACE_FILE = "results/rtl_trace.csv",
    parameter logic [31:0] TRACE_MEMSTALL = 32'd32
) (
    input  logic        clk,
    input  logic        reset,
    input  logic        trace_writeback_valid,
    input  logic [31:0] trace_writeback_pc,
    input  logic [31:0] trace_writeback_insn,
    input  logic [31:0] trace_writeback_cycle_status,
    input  logic [4:0]  trace_writeback_rd,
    input  logic [31:0] trace_writeback_wdata,
    input  logic        trace_writeback_reg_write
);

    integer fd;
    longint unsigned cycle;
    longint unsigned retired;
    string trace_path;

    initial begin
        if (!$value$plusargs("TRACE_FILE=%s", trace_path)) begin
            trace_path = TRACE_FILE;
        end
        fd = $fopen(trace_path, "w");
        if (fd == 0) $fatal(1, "Could not open RTL trace file: %s", trace_path);
        $fdisplay(fd,
            "cycle,retired,pc,insn,rd,wdata,reg_write,mem_addr,mem_read,mem_write");
    end

    always_ff @(posedge clk) begin
        if (reset) begin
            cycle <= 0;
            retired <= 0;
        end else begin
            cycle <= cycle + 1;
            if (trace_writeback_valid &&
                (trace_writeback_cycle_status != TRACE_MEMSTALL)) begin
                retired <= retired + 1;
                $fdisplay(fd,
                    "%0d,%0d,0x%08x,0x%08x,%0d,0x%08x,%0d,0x00000000,0,0",
                    cycle + 1,
                    retired + 1,
                    trace_writeback_pc,
                    trace_writeback_insn,
                    trace_writeback_rd,
                    trace_writeback_wdata,
                    trace_writeback_reg_write);
                $fflush(fd);
            end
        end
    end

    final begin
        if (fd != 0) $fclose(fd);
    end
endmodule
