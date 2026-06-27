#!/usr/bin/env python3
"""biquad2rtl.py - generate a fixed-point biquad RTL from a filter specification.

Given a filter type, a cutoff/center frequency and a quality factor, this script
computes the biquad coefficients (RBJ Audio EQ Cookbook formulas), characterizes
the resulting transfer function (poles, zeros, -3 dB cutoff, DC/Nyquist gain),
quantizes the coefficients to fixed-point and fills the templates from
``biquad.py`` to produce the Verilog.

When writing to disk (the default) it also reports the design verbosely, saves a
Bode plot comparing the continuous, discrete and quantized responses, and emits
an instantiation-template module. Everything lands in the output folder.

Examples
--------
    # Butterworth lowpass at fc = 0.1*fs
    python3 biquad2rtl.py --type lowpass --fc 0.1 --q 0.70710678

    # highpass at 2 kHz with fs = 48 kHz, RTL preview only
    python3 biquad2rtl.py --type highpass --fc 2000 --fs 48000 --q 0.8 --print
"""

import argparse
import os

import numpy as np
from scipy.signal import freqz, freqs

import biquad

BUTTERWORTH_Q = 1.0 / np.sqrt(2.0)  # 0.70710678..., maximally flat
FILTER_TYPES = ("lowpass", "highpass", "bandpass", "notch")


# --------------------------------------------------------------------------- #
# Filter design
# --------------------------------------------------------------------------- #
def design_coefficients(filter_type, fc_norm, q):
    """Return (b, a) biquad coefficients using the RBJ cookbook formulas.

    fc_norm is the cutoff/center frequency normalized to fs (0 < fc_norm < 0.5).
    The denominator is normalized so a0 = 1, matching the RTL difference equation
    y[n] = b0*x[n] + b1*x[n-1] + b2*x[n-2] - a1*y[n-1] - a2*y[n-2].
    """
    w0 = 2.0 * np.pi * fc_norm
    cos_w0 = np.cos(w0)
    sin_w0 = np.sin(w0)
    alpha = sin_w0 / (2.0 * q)

    if filter_type == "lowpass":
        b = [(1 - cos_w0) / 2, 1 - cos_w0, (1 - cos_w0) / 2]
    elif filter_type == "highpass":
        b = [(1 + cos_w0) / 2, -(1 + cos_w0), (1 + cos_w0) / 2]
    elif filter_type == "bandpass":  # constant 0 dB peak gain
        b = [alpha, 0.0, -alpha]
    elif filter_type == "notch":
        b = [1.0, -2 * cos_w0, 1.0]
    else:
        raise ValueError(f"unknown filter type: {filter_type}")

    a = [1 + alpha, -2 * cos_w0, 1 - alpha]

    a0 = a[0]
    b = [c / a0 for c in b]
    a = [c / a0 for c in a]
    return b, a


def analog_prototype(filter_type, fc_hz, q):
    """Return the continuous-time (s-domain) prototype coefficients (b_s, a_s)."""
    w0 = 2.0 * np.pi * fc_hz
    a_s = [1.0, w0 / q, w0 ** 2]
    if filter_type == "lowpass":
        b_s = [0.0, 0.0, w0 ** 2]
    elif filter_type == "highpass":
        b_s = [1.0, 0.0, 0.0]
    elif filter_type == "bandpass":
        b_s = [0.0, w0 / q, 0.0]
    elif filter_type == "notch":
        b_s = [1.0, 0.0, w0 ** 2]
    else:
        raise ValueError(f"unknown filter type: {filter_type}")
    return b_s, a_s


def realized_coefficients(b, a, frac_width, data_width):
    """Quantize then de-quantize the coefficients to their realized values."""
    scale = float(1 << frac_width)
    b_r = [biquad.quantize(c, frac_width, data_width) / scale for c in b]
    a_r = [1.0] + [biquad.quantize(c, frac_width, data_width) / scale for c in a[1:]]
    return b_r, a_r


# --------------------------------------------------------------------------- #
# Characterization
# --------------------------------------------------------------------------- #
def _mag(b, a, w):
    """Magnitude of H(e^jw) at the given angular frequencies (rad/sample)."""
    _, h = freqz(b, a, worN=w)
    return np.abs(h)


def _gain_text(linear):
    """Human-readable gain from a linear magnitude."""
    if linear < 1e-6:
        return "-inf (full attenuation)"
    db = 20.0 * np.log10(linear)
    if abs(db) < 0.05:
        return "0 dB"
    return f"{db:+.1f} dB"


def _fmt_root(z):
    """Format a single root, real or complex."""
    if abs(z.imag) < 1e-9:
        return f"z = {z.real:.4g}"
    sign = "+" if z.imag >= 0 else "-"
    return f"{z.real:.4g} {sign} j{abs(z.imag):.4g}"


def _describe_roots(coeffs, name):
    """Describe the roots (poles/zeros) of a 2nd-order polynomial."""
    roots = list(np.roots(coeffs))
    if len(roots) == 2 and abs(roots[0] - roots[1]) < 1e-6:
        return f"double {name} at {_fmt_root(roots[0])}"
    if len(roots) == 2 and abs(roots[0].imag) > 1e-9:
        r = abs(roots[0])
        return f"{name}s at {roots[0].real:.4g} +/- j{abs(roots[0].imag):.4g} (radius {r:.4g})"
    return f"{name}s at " + " and ".join(_fmt_root(r) for r in roots)


def _measure_cutoff(b, a, filter_type, design_fc):
    """Measure the -3 dB cutoff (relative to the passband peak) of the design.

    Returns the cutoff frequency normalized to fs. For band-pass/notch the design
    center frequency is reported, since a single -3 dB number is not meaningful.
    """
    if filter_type in ("bandpass", "notch"):
        return design_fc

    w = np.linspace(1e-6, np.pi - 1e-6, 2_000_001)
    mag = _mag(b, a, w)
    half_power = mag.max() / np.sqrt(2.0)
    crossings = np.where(np.diff(np.signbit(mag - half_power)))[0]
    if len(crossings) == 0:
        return design_fc
    # lowpass: first crossing going down; highpass: first crossing going up
    return float(w[crossings[0]] / (2.0 * np.pi))


def characterize(b, a, filter_type, design_fc, q):
    """Compute the documentation fields for a designed biquad."""
    dc_gain = abs(sum(b) / sum(a))
    nyq_gain = abs((b[0] - b[1] + b[2]) / (a[0] - a[1] + a[2]))
    fc_meas = _measure_cutoff(b, a, filter_type, design_fc)

    if abs(q - BUTTERWORTH_Q) < 1e-3:
        q_note = " (Butterworth, maximally flat)"
    elif q < BUTTERWORTH_Q:
        q_note = " (below the Butterworth value 0.707, so slightly overdamped)"
    else:
        q_note = " (above the Butterworth value 0.707, so it shows a resonant peak)"

    if filter_type in ("lowpass", "highpass"):
        rolloff = ("with a resonant peak" if q > BUTTERWORTH_Q
                   else "monotonic roll-off (no resonant peak)")
    elif filter_type == "bandpass":
        rolloff = "pass-band centered at fc, attenuating both DC and Nyquist"
    else:  # notch
        rolloff = "rejects a narrow band around fc, unity gain elsewhere"

    return {
        "fc_norm": fc_meas,
        "q_factor": q,
        "q_note": q_note,
        "zeros_note": _describe_roots(b, "zero"),
        "poles_note": _describe_roots(a, "pole"),
        "rolloff_note": rolloff,
        "dc_gain_db": _gain_text(dc_gain),
        "nyquist_gain_note": _gain_text(nyq_gain),
    }


def quantization_error(b, a, b_r, a_r, n=4096):
    """Compare the float design against the quantized one over the spectrum."""
    w = np.linspace(1e-4, np.pi - 1e-4, n)
    mag = 20.0 * np.log10(np.maximum(_mag(b, a, w), 1e-12))
    mag_q = 20.0 * np.log10(np.maximum(_mag(b_r, a_r, w), 1e-12))
    err = mag_q - mag
    i = int(np.argmax(np.abs(err)))
    return {
        "max_db": float(abs(err[i])),
        "at_fnorm": float(w[i] / (2.0 * np.pi)),
        "rms_db": float(np.sqrt(np.mean(err ** 2))),
    }


# --------------------------------------------------------------------------- #
# RTL generation (pure; reused by the MCP server)
# --------------------------------------------------------------------------- #
def generate(filter_type, fc_norm, q, data_width, frac_width):
    """Design the filter and return the complete biquad.v source string."""
    b, a = design_coefficients(filter_type, fc_norm, q)
    doc = characterize(b, a, filter_type, fc_norm, q)
    return biquad.render(b, a, filter_type=filter_type,
                         data_width=data_width, frac_width=frac_width, **doc)


# --------------------------------------------------------------------------- #
# Plotting and reporting (CLI side effects)
# --------------------------------------------------------------------------- #
def write_bode_plot(filter_type, b, a, b_r, a_r, fc_norm, q, fs, path, n=2048):
    """Save a Bode plot comparing continuous, discrete and quantized responses.

    Uses a non-interactive backend, so the figure is written to disk and never
    displayed (the script does not block).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    normalized = abs(fs - 1.0) < 1e-12
    f = np.logspace(np.log10(fs / 2 * 1e-3), np.log10(fs / 2 * 0.999), n)

    _, h_s = freqs(*analog_prototype(filter_type, fc_norm * fs, q), worN=2 * np.pi * f)
    _, h_d = freqz(b, a, worN=2 * np.pi * f / fs)
    _, h_q = freqz(b_r, a_r, worN=2 * np.pi * f / fs)

    def db(h):
        return 20.0 * np.log10(np.maximum(np.abs(h), 1e-12))

    def deg(h):
        return np.degrees(np.unwrap(np.angle(h)))

    x = f / fs if normalized else f
    xlabel = "Frequency (f / fs)" if normalized else "Frequency (Hz)"

    fig, (ax_mag, ax_ph) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    ax_mag.semilogx(x, db(h_s), "--", label="continuous (analog prototype)")
    ax_mag.semilogx(x, db(h_d), "-", label="discrete (float coeffs)")
    ax_mag.semilogx(x, db(h_q), ":", label="discrete (quantized coeffs)")
    ax_mag.set_ylabel("Magnitude (dB)")
    ax_mag.set_title(f"Biquad {filter_type} - fc={fc_norm:g}*fs, Q={q:g}")
    ax_mag.grid(True, which="both", alpha=0.3)
    ax_mag.legend(loc="best", fontsize=8)

    ax_ph.semilogx(x, deg(h_s), "--")
    ax_ph.semilogx(x, deg(h_d), "-")
    ax_ph.semilogx(x, deg(h_q), ":")
    ax_ph.set_ylabel("Phase (deg)")
    ax_ph.set_xlabel(xlabel)
    ax_ph.grid(True, which="both", alpha=0.3)

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def report(filter_type, fc_norm, fs, q, data_width, frac_width,
           b, a, b_r, a_r, doc, qerr, outputs):
    """Print a verbose summary of the design to stdout."""
    scale = 1 << frac_width
    fc_hz = fc_norm * fs

    print("filter2rtl - biquad design")
    print(f"  type:    {filter_type}")
    if abs(fs - 1.0) < 1e-12:
        print(f"  fc:      {fc_norm:g}*fs (normalized)")
    else:
        print(f"  fc:      {fc_hz:g} Hz  (fs = {fs:g} Hz, fc/fs = {fc_norm:g})")
    print(f"  Q:       {q:g}")
    print(f"  format:  Q{frac_width} ({data_width}-bit signed)")

    names = ["b0", "b1", "b2", "a1", "a2"]
    floats = [b[0], b[1], b[2], a[1], a[2]]
    quants = [biquad.quantize(c, frac_width, data_width) for c in floats]
    reals = [b_r[0], b_r[1], b_r[2], a_r[1], a_r[2]]
    print("\ncoefficients (float -> Q-integer -> realized):")
    print(f"  {'coef':<4} {'float':>14} {'Q'+str(frac_width):>12} {'realized':>14} {'abs error':>12}")
    for name, fv, qv, rv in zip(names, floats, quants, reals):
        print(f"  {name:<4} {fv:>14.8f} {qv:>12d} {rv:>14.8f} {rv - fv:>12.2e}")

    print("\ncharacteristics:")
    print(f"  -3 dB cutoff:  {doc['fc_norm']:g}*fs")
    print(f"  DC gain:       {doc['dc_gain_db']}")
    print(f"  Nyquist gain:  {doc['nyquist_gain_note']}")
    print(f"  zeros:         {doc['zeros_note']}")
    print(f"  poles:         {doc['poles_note']}")

    print("\nquantization error (quantized vs float response):")
    print(f"  max |magnitude| deviation: {qerr['max_db']:.4f} dB at f/fs = {qerr['at_fnorm']:.4f}")
    print(f"  RMS magnitude deviation:   {qerr['rms_db']:.4f} dB")

    print("\noutputs:")
    for path in outputs:
        print(f"  {path}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args():
    here = os.path.dirname(os.path.abspath(__file__))
    default_out = os.path.join(here, "output", "biquad.v")

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--type", required=True, choices=FILTER_TYPES,
                        help="filter type")
    parser.add_argument("--fc", required=True, type=float,
                        help="cutoff/center frequency (in fs units, or in Hz with --fs)")
    parser.add_argument("--fs", type=float, default=1.0,
                        help="sampling frequency (default 1.0, so --fc is normalized)")
    parser.add_argument("--q", type=float, default=BUTTERWORTH_Q,
                        help="quality factor (default 0.70710678, Butterworth)")
    parser.add_argument("--data-width", type=int, default=biquad.DATA_WIDTH,
                        help=f"sample/coefficient width in bits (default {biquad.DATA_WIDTH})")
    parser.add_argument("--frac-width", type=int, default=biquad.FRAC_WIDTH,
                        help=f"number of fractional bits, Q format (default {biquad.FRAC_WIDTH})")
    parser.add_argument("--output", default=default_out,
                        help="output Verilog file (default output/biquad.v)")
    parser.add_argument("--no-plot", action="store_true",
                        help="skip the Bode plot generation")
    parser.add_argument("--print", dest="to_stdout", action="store_true",
                        help="print the RTL to stdout instead of writing the files")
    return parser.parse_args()


def main():
    args = parse_args()

    fc_norm = args.fc / args.fs
    if not 0.0 < fc_norm < 0.5:
        raise SystemExit(
            f"fc/fs = {fc_norm:g} is out of range; it must satisfy 0 < fc/fs < 0.5"
        )
    if args.q <= 0.0:
        raise SystemExit("Q must be positive")
    if args.frac_width >= args.data_width:
        raise SystemExit("frac-width must be smaller than data-width")

    b, a = design_coefficients(args.type, fc_norm, args.q)
    doc = characterize(b, a, args.type, fc_norm, args.q)
    rtl = biquad.render(b, a, filter_type=args.type,
                        data_width=args.data_width, frac_width=args.frac_width, **doc)

    if args.to_stdout:
        print(rtl, end="")
        return

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    module = biquad.MODULE_NAME
    inst_path = os.path.join(out_dir, f"{module}_instantiation_template.v")
    bode_path = os.path.join(out_dir, f"{module}_bode.png")

    # RTL module
    with open(args.output, "w") as f:
        f.write(rtl)

    # instantiation template
    inst = biquad.render_instantiation(
        b, a, module_name=module, filter_type=args.type,
        data_width=args.data_width, frac_width=args.frac_width, **doc)
    with open(inst_path, "w") as f:
        f.write(inst)

    outputs = [args.output, inst_path]

    # Bode plot
    b_r, a_r = realized_coefficients(b, a, args.frac_width, args.data_width)
    if not args.no_plot:
        try:
            write_bode_plot(args.type, b, a, b_r, a_r, fc_norm, args.q, args.fs, bode_path)
            outputs.append(bode_path)
        except ImportError:
            print("warning: matplotlib not available, skipping the Bode plot")

    qerr = quantization_error(b, a, b_r, a_r)
    report(args.type, fc_norm, args.fs, args.q, args.data_width, args.frac_width,
           b, a, b_r, a_r, doc, qerr, outputs)


if __name__ == "__main__":
    main()
