`default_nettype none
`timescale 1ns / 1ps

/*
 * This testbench instantiates the Tiny Tapeout top-level module
 * and provides convenient signals for the Cocotb test.
 */
module tb ();

  // Dump the signals to a FST file.
  initial begin
    $dumpfile("tb.fst");
    $dumpvars(0, tb);
    #1;
  end

  // Tiny Tapeout interface signals
  reg clk;
  reg rst_n;
  reg ena;
  reg [7:0] ui_in;
  reg [7:0] uio_in;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;

  // Instantiate the participant's Tiny Tapeout top module
  tt_um_4tap_mac user_project (
      .ui_in  (ui_in),
      .uo_out (uo_out),
      .uio_in (uio_in),
      .uio_out(uio_out),
      .uio_oe (uio_oe),
      .ena    (ena),
      .clk    (clk),
      .rst_n  (rst_n)
  );

endmodule

`default_nettype wire
