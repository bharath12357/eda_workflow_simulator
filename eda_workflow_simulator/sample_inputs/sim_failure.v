// EDUCATIONAL SAMPLE: the marker below makes the simulated test fail.
module parity (
    input  wire [7:0] data,
    output wire       odd
);
    assign odd = ^data;   // SIM_FAIL
endmodule
