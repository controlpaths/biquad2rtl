/**
  Module name: biquad_instantiation_template
  Author: PTrujillo
  Date: Jun26
  Description: Instantiation template for the generated biquad module. Copy this instance into your design and connect the ports to your clock, synchronous reset and sample streams. Coefficients and widths are fixed inside the module.
  Version: 1.0
**/

/* Implemented filter: 2nd-order (biquad) IIR lowpass, Direct Form I.
   Transfer function: H(z) = (b0 + b1*z^-1 + b2*z^-2) / (1 + a1*z^-1 + a2*z^-2)
     numerator   b = [0.00782021, 0.0156404, 0.00782021]  -> double zero at z = -1
     denominator a = [1, -1.73473, 0.766007]  -> poles at 0.8674 +/- j0.117 (radius 0.8752)
   Characteristics (frequencies normalized to the sampling rate fs):
     - type:            lowpass, monotonic roll-off (no resonant peak)
     - DC gain:         0 dB; gain at Nyquist (fs/2): -inf (full attenuation)
     - cutoff (-3 dB):  fc ~= 0.03*fs (about fs/33.3)
     - quality factor:  Q ~= 0.7071 (Butterworth, maximally flat)
   Coefficients are stored as 32-bit signed Q20 fixed point (1 sign, 11 integer, 20 fractional bits):
     real_value = q20_value / 2^20. */
biquad u_biquad (
  .aclk(aclk), /* clock */
  .aresetn(aresetn), /* synchronous active-low reset */
  .x_valid(x_valid), /* input sample valid */
  .x(x), /* input sample, signed [31:0] Q20 */
  .y_valid(y_valid), /* output sample valid */
  .y(y) /* output sample, signed [31:0] Q20 */
);
