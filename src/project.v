/*
 * Copyright (c) 2024 Mohammed Abdul Mujeeb
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module mac4 (
    input  wire        clk_i,
    input  wire        rst_ni,

    input  wire [1:0]  addr_i,
    input  wire [3:0]  data_i,

    input  wire        weight_we_i,
    input  wire        sample_we_i,

    input  wire        start_i,
    input  wire        accumulate_i,
    input  wire        clear_acc_i,

    output reg  [7:0]  result_o,
    output reg         done_o,
    output reg         overflow_o
);

    // Four signed 4-bit weights
    reg signed [3:0] weights [0:3];

    // Four signed 4-bit input samples
    reg signed [3:0] samples [0:3];

    // Individual 8-bit signed products
    reg signed [7:0] product0;
    reg signed [7:0] product1;
    reg signed [7:0] product2;
    reg signed [7:0] product3;

    // MAC sum needs more than 8 bits
    reg signed [9:0] mac_sum;

    // Running accumulator
    reg signed [11:0] accumulator;

    reg signed [11:0] next_accumulator;

    integer i;

    always @(posedge clk_i or negedge rst_ni) begin

        if (!rst_ni) begin

            result_o     <= 8'd0;
            done_o       <= 1'b0;
            overflow_o   <= 1'b0;
            accumulator  <= 12'sd0;

            for (i = 0; i < 4; i = i + 1) begin
                weights[i] <= 4'sd0;
                samples[i] <= 4'sd0;
            end

        end
        else begin

            done_o <= 1'b0;

            // Load weight
            if (weight_we_i) begin
                weights[addr_i] <= $signed(data_i);
            end

            // Load sample
            if (sample_we_i) begin
                samples[addr_i] <= $signed(data_i);
            end

            // Clear accumulated result
            if (clear_acc_i) begin
                accumulator <= 12'sd0;
                result_o    <= 8'd0;
                overflow_o  <= 1'b0;
            end

            // Perform MAC operation
            if (start_i) begin

                product0 = weights[0] * samples[0];
                product1 = weights[1] * samples[1];
                product2 = weights[2] * samples[2];
                product3 = weights[3] * samples[3];

                mac_sum = product0 +
                          product1 +
                          product2 +
                          product3;

                // Either replace or accumulate
                if (accumulate_i)
                    next_accumulator = accumulator + mac_sum;
                else
                    next_accumulator = mac_sum;

                accumulator <= next_accumulator;

                // Output lower 8 bits
                result_o <= next_accumulator[7:0];

                // Detect signed 8-bit overflow
                if ((next_accumulator > 12'sd127) ||
                    (next_accumulator < -12'sd128))
                    overflow_o <= 1'b1;
                else
                    overflow_o <= 1'b0;

                done_o <= 1'b1;
            end
        end
    end

endmodule


module tt_um_4tap_mac (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path
    input  wire       ena,      // always 1 when the design is powered
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

    wire [1:0] address;
    wire [3:0] data_in;

    wire weight_we;
    wire sample_we;

    wire start;
    wire accumulate;
    wire clear_acc;

    wire [7:0] result;
    wire       done;
    wire       overflow;

    // Address
    assign address = ui_in[1:0];

    // Control signals
    assign weight_we = ui_in[2];
    assign sample_we = ui_in[3];
    assign start     = ui_in[4];

    assign accumulate = ui_in[5];
    assign clear_acc  = ui_in[6];

    // 4-bit signed data
    assign data_in = uio_in[3:0];

    mac4 u_mac (
        .clk_i         (clk),
        .rst_ni        (rst_n),

        .addr_i        (address),
        .data_i        (data_in),

        .weight_we_i   (weight_we),
        .sample_we_i   (sample_we),

        .start_i       (start),
        .accumulate_i  (accumulate),
        .clear_acc_i   (clear_acc),

        .result_o      (result),
        .done_o        (done),
        .overflow_o    (overflow)
    );

    // MAC result
    assign uo_out = result;

    // No bidirectional output drive
    assign uio_out = 8'b0;
    assign uio_oe  = 8'b0;

    // ena is intentionally unused by the original design.
    // done and overflow are internal signals and are not exposed.
    wire _unused = &{ena, 1'b0};

endmodule

`default_nettype wire
