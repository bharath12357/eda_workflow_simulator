// EDUCATIONAL SAMPLE: instantiates 'fast_multiplier' which is never defined
// -> elaboration fails.
module top (
    input  wire       clk,
    input  wire [7:0] x,
    input  wire [7:0] y,
    output wire [15:0] product
);
    fast_multiplier u_mul (.a(x), .b(y), .p(product));
endmodule
