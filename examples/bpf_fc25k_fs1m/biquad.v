/**
  Module name: biquad
  Author: filter2rtl
  Date: 
  Description: Second-order IIR filter (biquad), Direct Form I. Fixed-point arithmetic in Q(frac_width). Widths and coefficients are fixed localparams (not overridable from above). Configured as a 32-bit Q20 bandpass section (b=[0.00389563, 0, -0.00389563], a=[1, -1.96768, 0.992209]).
  Version: 1.0
  History:
    1.0 - Module created
**/

module biquad (
  input wire aclk,
  input wire aresetn,

  /* input sample channel */
  input wire x_valid,
  input wire signed [31:0] x,

  /* output sample channel */
  output reg y_valid,
  output reg signed [31:0] y
);

  localparam [31:0] data_width = 32; /* sample and coefficient width in bits */
  localparam [31:0] frac_width = 20; /* number of fractional bits (Q format) */

  /* Implemented filter: 2nd-order (biquad) IIR bandpass, Direct Form I.
     Transfer function: H(z) = (b0 + b1*z^-1 + b2*z^-2) / (1 + a1*z^-1 + a2*z^-2)
       numerator   b = [0.00389563, 0, -0.00389563]  -> zeros at z = -1 and z = 1
       denominator a = [1, -1.96768, 0.992209]  -> poles at 0.9838 +/- j0.1558 (radius 0.9961)
     Characteristics (frequencies normalized to the sampling rate fs):
       - type:            bandpass, pass-band centered at fc, attenuating both DC and Nyquist
       - DC gain:         -inf (full attenuation); gain at Nyquist (fs/2): -inf (full attenuation)
       - cutoff (-3 dB):  fc ~= 0.025*fs (about fs/40.0)
       - quality factor:  Q ~= 20 (above the Butterworth value 0.707, so it shows a resonant peak)
     Coefficients are stored as 32-bit signed Q20 fixed point (1 sign, 11 integer, 20 fractional bits):
       real_value = q20_value / 2^20. */
  localparam signed [data_width-1:0] coeff_b0 = 32'sd4085; /* b0 = 0.00389563 in Q20 */
  localparam signed [data_width-1:0] coeff_b1 = 32'sd0; /* b1 = 0 in Q20 */
  localparam signed [data_width-1:0] coeff_b2 = -32'sd4085; /* b2 = -0.00389563 in Q20 */
  localparam signed [data_width-1:0] coeff_a1 = -32'sd2063263; /* a1 = -1.96768 in Q20 */
  localparam signed [data_width-1:0] coeff_a2 = 32'sd1040406; /* a2 = 0.992209 in Q20 */

  localparam [31:0] PROD_WIDTH = 2*data_width; /* width of a coefficient times sample product */
  localparam [31:0] ACC_WIDTH = (2*data_width) + 3; /* accumulator width: product plus 3 guard bits */

  reg signed [data_width-1:0] x_reg1; /* x[n-1] */
  reg signed [data_width-1:0] x_reg2; /* x[n-2] */
  reg signed [data_width-1:0] y_reg1; /* y[n-1] */
  reg signed [data_width-1:0] y_reg2; /* y[n-2] */

  wire signed [PROD_WIDTH-1:0] prod_b0;
  wire signed [PROD_WIDTH-1:0] prod_b1;
  wire signed [PROD_WIDTH-1:0] prod_b2;
  wire signed [PROD_WIDTH-1:0] prod_a1;
  wire signed [PROD_WIDTH-1:0] prod_a2;
  wire signed [ACC_WIDTH-1:0] acc;
  wire signed [ACC_WIDTH-1:0] y_scaled;
  wire signed [data_width-1:0] y_next;

  always @(posedge aclk) begin
    if (!aresetn) begin
      x_reg1 <= {data_width{1'b0}};
      x_reg2 <= {data_width{1'b0}};
      y_reg1 <= {data_width{1'b0}};
      y_reg2 <= {data_width{1'b0}};
      y <= {data_width{1'b0}};
      y_valid <= 1'b0;
    end
    else begin
      if (x_valid) begin
        x_reg1 <= x;
        x_reg2 <= x_reg1;
        y_reg1 <= y_next;
        y_reg2 <= y_reg1;
        y <= y_next;
        y_valid <= 1'b1;
      end
      else begin
        y_valid <= 1'b0;
      end
    end
  end

  /* feed-forward and feed-back products */
  assign prod_b0 = coeff_b0 * x;
  assign prod_b1 = coeff_b1 * x_reg1;
  assign prod_b2 = coeff_b2 * x_reg2;
  assign prod_a1 = coeff_a1 * y_reg1;
  assign prod_a2 = coeff_a2 * y_reg2;

  /* y[n] = b0*x[n] + b1*x[n-1] + b2*x[n-2] - a1*y[n-1] - a2*y[n-2] */
  assign acc = prod_b0 + prod_b1 + prod_b2 - prod_a1 - prod_a2;

  /* rescale from Q(2*frac_width) back to Q(frac_width) and truncate to data_width */
  assign y_scaled = acc >>> frac_width;
  assign y_next = y_scaled[data_width-1:0];

endmodule
