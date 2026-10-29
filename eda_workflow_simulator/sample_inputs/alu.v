/* EDUCATIONAL SAMPLE: a small ALU that instantiates the counter module
   (as a stand-in for a "cycle counter") to show elaboration. */
module counter (
    input  wire       clk,
    input  wire       rst_n,
    output reg  [7:0] count
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) count <= 8'd0;
        else        count <= count + 8'd1;
    end
endmodule

module alu (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] a,
    input  wire [7:0] b,
    input  wire [1:0] op,
    output wire [7:0] result,
    output wire [7:0] cycles
);
    counter cycle_counter (.clk(clk), .rst_n(rst_n), .count(cycles));

    assign result = (op == 2'b00) ? a + b :
                    (op == 2'b01) ? a - b :
                    (op == 2'b10) ? a & b :
                                    a | b;
endmodule
