"""biquad.py - RTL templates for the designed second-order IIR (biquad) filter.

This module holds the parametrizable Verilog template for the biquad (Direct
Form I, fixed-point Q(frac_width), widths and coefficients as non-overridable
localparams) plus a matching instantiation-template renderer.

The coefficient generator ``biquad2rtl.py`` imports :func:`render` and
:func:`render_instantiation`, fills them with the coefficients and the
characteristics it computes, and writes the final Verilog files.

Running this file directly renders the currently designed lowpass filter and
works as a quick self-check.
"""

from string import Template

DATA_WIDTH = 32  # sample and coefficient width in bits
FRAC_WIDTH = 20  # number of fractional bits (Q format)
MODULE_NAME = "biquad"

# Verilog module template. Only ``${name}`` placeholders are substituted; the
# literal braces of Verilog concatenations (e.g. {data_width{1'b0}}) are kept.
TEMPLATE = Template("""/**
  Module name: biquad
  Author: biquad2rtl
  Date: 
  Description: Second-order IIR filter (biquad), Direct Form I. Fixed-point arithmetic in Q(frac_width). Widths and coefficients are fixed localparams (not overridable from above). Configured as a ${data_width}-bit Q${frac_width} ${filter_type} section (b=${b_real_list}, a=${a_real_list}).
  Version: 1.0
  History:
    1.0 - Module created
**/

module biquad (
  input wire aclk,
  input wire aresetn,

  /* input sample channel */
  input wire x_valid,
  input wire signed [${msb}:0] x,

  /* output sample channel */
  output reg y_valid,
  output reg signed [${msb}:0] y
);

  localparam [31:0] data_width = ${data_width}; /* sample and coefficient width in bits */
  localparam [31:0] frac_width = ${frac_width}; /* number of fractional bits (Q format) */

${filter_doc}
  localparam signed [data_width-1:0] coeff_b0 = ${coeff_b0_lit}; /* b0 = ${b0_real} in Q${frac_width} */
  localparam signed [data_width-1:0] coeff_b1 = ${coeff_b1_lit}; /* b1 = ${b1_real} in Q${frac_width} */
  localparam signed [data_width-1:0] coeff_b2 = ${coeff_b2_lit}; /* b2 = ${b2_real} in Q${frac_width} */
  localparam signed [data_width-1:0] coeff_a1 = ${coeff_a1_lit}; /* a1 = ${a1_real} in Q${frac_width} */
  localparam signed [data_width-1:0] coeff_a2 = ${coeff_a2_lit}; /* a2 = ${a2_real} in Q${frac_width} */

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
""")

# Instantiation template: the characteristics comment followed by a ready-to-wire
# instance of the generated module.
INSTANTIATION_TEMPLATE = Template("""/**
  Module name: ${module_name}_instantiation_template
  Author: PTrujillo
  Date: Jun26
  Description: Instantiation template for the generated ${module_name} module. Copy this instance into your design and connect the ports to your clock, synchronous reset and sample streams. Coefficients and widths are fixed inside the module.
  Version: 1.0
**/

${filter_doc}
${module_name} u_${module_name} (
  .aclk(aclk), /* clock */
  .aresetn(aresetn), /* synchronous active-low reset */
  .x_valid(x_valid), /* input sample valid */
  .x(x), /* input sample, signed [${msb}:0] Q${frac_width} */
  .y_valid(y_valid), /* output sample valid */
  .y(y) /* output sample, signed [${msb}:0] Q${frac_width} */
);
""")


def quantize(value, frac_width=FRAC_WIDTH, data_width=DATA_WIDTH):
    """Quantize a real coefficient to a signed Q(frac_width) integer.

    Rounds to nearest and checks that the result fits in a signed
    ``data_width``-bit word, matching the RTL coefficient storage.
    """
    q = int(round(value * (1 << frac_width)))
    lo = -(1 << (data_width - 1))
    hi = (1 << (data_width - 1)) - 1
    if not (lo <= q <= hi):
        raise ValueError(
            f"coefficient {value} -> {q} does not fit in signed Q{frac_width} "
            f"({data_width} bits, range [{lo}, {hi}])"
        )
    return q


def _coeff_literal(value, frac_width, data_width):
    """Return the Verilog sized literal for a coefficient, e.g. -32'sd314573."""
    q = quantize(value, frac_width, data_width)
    if q < 0:
        return f"-{data_width}'sd{-q}"
    return f"{data_width}'sd{q}"


def _real_list(values):
    """Format a coefficient list as it appears in the documentation comment."""
    return "[" + ", ".join(f"{v:g}" for v in values) + "]"


def _build_context(b, a, *, filter_type, fc_norm, q_factor,
                   zeros_note="", poles_note="", rolloff_note="",
                   dc_gain_db="0 dB", nyquist_gain_note="", q_note="",
                   data_width=DATA_WIDTH, frac_width=FRAC_WIDTH):
    """Assemble the substitution context shared by both templates."""
    b0, b1, b2 = b
    _a0, a1, a2 = a  # a0 assumed 1.0, not stored in RTL
    return {
        "data_width": data_width,
        "msb": data_width - 1,
        "frac_width": frac_width,
        "int_bits": data_width - 1 - frac_width,
        "inv_fc": f"{1 / fc_norm:.1f}",
        "filter_type": filter_type,
        "b_real_list": _real_list(b),
        "a_real_list": _real_list(a),
        "zeros_note": zeros_note,
        "poles_note": poles_note,
        "rolloff_note": rolloff_note,
        "dc_gain_db": dc_gain_db,
        "nyquist_gain_note": nyquist_gain_note,
        "fc_norm": f"{fc_norm:.4g}",
        "q_factor": f"{q_factor:.4g}",
        "q_note": q_note,
        "coeff_b0_lit": _coeff_literal(b0, frac_width, data_width),
        "coeff_b1_lit": _coeff_literal(b1, frac_width, data_width),
        "coeff_b2_lit": _coeff_literal(b2, frac_width, data_width),
        "coeff_a1_lit": _coeff_literal(a1, frac_width, data_width),
        "coeff_a2_lit": _coeff_literal(a2, frac_width, data_width),
        "b0_real": f"{b0:g}",
        "b1_real": f"{b1:g}",
        "b2_real": f"{b2:g}",
        "a1_real": f"{a1:g}",
        "a2_real": f"{a2:g}",
    }


def _filter_doc(indent, ctx):
    """Render the multi-line filter-characteristics comment at a given indent.

    ``indent`` prefixes every line; continuation lines are aligned relative to it
    (used at 2 spaces inside the module, at 0 in the instantiation template).
    """
    pad3 = indent + "   "
    pad5 = indent + "     "
    return "\n".join([
        f"{indent}/* Implemented filter: 2nd-order (biquad) IIR {ctx['filter_type']}, Direct Form I.",
        f"{pad3}Transfer function: H(z) = (b0 + b1*z^-1 + b2*z^-2) / (1 + a1*z^-1 + a2*z^-2)",
        f"{pad5}numerator   b = {ctx['b_real_list']}  -> {ctx['zeros_note']}",
        f"{pad5}denominator a = {ctx['a_real_list']}  -> {ctx['poles_note']}",
        f"{pad3}Characteristics (frequencies normalized to the sampling rate fs):",
        f"{pad5}- type:            {ctx['filter_type']}, {ctx['rolloff_note']}",
        f"{pad5}- DC gain:         {ctx['dc_gain_db']}; gain at Nyquist (fs/2): {ctx['nyquist_gain_note']}",
        f"{pad5}- cutoff (-3 dB):  fc ~= {ctx['fc_norm']}*fs (about fs/{ctx['inv_fc']})",
        f"{pad5}- quality factor:  Q ~= {ctx['q_factor']}{ctx['q_note']}",
        f"{pad3}Coefficients are stored as {ctx['data_width']}-bit signed Q{ctx['frac_width']} fixed point (1 sign, {ctx['int_bits']} integer, {ctx['frac_width']} fractional bits):",
        f"{pad5}real_value = q{ctx['frac_width']}_value / 2^{ctx['frac_width']}. */",
    ])


def render(b, a, **kwargs):
    """Render the complete biquad.v Verilog source.

    ``b``/``a`` are the numerator/denominator coefficients (a0 assumed 1.0). The
    keyword arguments describe the design for the documentation comment; see
    :func:`_build_context`.
    """
    ctx = _build_context(b, a, **kwargs)
    ctx["filter_doc"] = _filter_doc("  ", ctx)
    return TEMPLATE.substitute(ctx)


def render_instantiation(b, a, *, module_name=MODULE_NAME, **kwargs):
    """Render the instantiation template (characteristics comment + instance)."""
    ctx = _build_context(b, a, **kwargs)
    return INSTANTIATION_TEMPLATE.substitute(
        module_name=module_name,
        msb=ctx["msb"],
        frac_width=ctx["frac_width"],
        filter_doc=_filter_doc("", ctx),
    )


# Characteristics of a sample lowpass filter, so `python3 biquad.py` renders a
# complete module as a quick self-check.
DESIGN = {
    "b": [0.2, 0.4, 0.2],
    "a": [1, -0.3, 0.1],
    "filter_type": "lowpass",
    "fc_norm": 0.174,
    "q_factor": 0.68,
    "zeros_note": "double zero at z = -1 (Nyquist)",
    "poles_note": "poles at 0.15 +/- j0.2784 (radius 0.316)",
    "rolloff_note": "monotonic roll-off (no resonant peak)",
    "dc_gain_db": "0 dB",
    "nyquist_gain_note": "-inf (full attenuation)",
    "q_note": " (below the Butterworth value 0.707, so slightly overdamped)",
}


if __name__ == "__main__":
    print(render(**DESIGN), end="")
