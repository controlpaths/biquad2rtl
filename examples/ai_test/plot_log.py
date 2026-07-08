#!/usr/bin/env python3
"""plot_log.py - plot the testbench filter log.

Reads ``filter_log.csv`` (columns: time_ns, x, y) produced by
``ai_test_tb.v`` and draws two views of the composite five-harmonic signal
(10k/20k/30k/35k/40k Hz, fs = 1 Msps): a zoomed time-domain segment and the
FFT magnitude spectrum of both x and y.

Examples
--------
    python3 plot_log.py
    python3 plot_log.py --csv filter_log.csv --out filter_log.png
"""

import argparse

import numpy as np
import matplotlib.pyplot as plt

FS = 1_000_000.0
HARMONICS = (10_000, 20_000, 30_000, 35_000, 40_000)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", default="filter_log.csv",
                        help="input csv log (default: filter_log.csv)")
    parser.add_argument("--out", default="filter_log.png",
                        help="output image file (default: filter_log.png)")
    parser.add_argument("--show", action="store_true",
                        help="open an interactive window instead of only saving")
    args = parser.parse_args()

    data = np.genfromtxt(args.csv, delimiter=",", names=True)
    x = data["x"]
    y = data["y"]
    sample = np.arange(x.size)

    freqs = np.fft.rfftfreq(x.size, d=1.0 / FS)
    x_mag = np.abs(np.fft.rfft(x)) / x.size
    y_mag = np.abs(np.fft.rfft(y)) / y.size

    fig, (ax_t, ax_f) = plt.subplots(2, 1, figsize=(14, 8))

    zoom = min(500, sample.size)
    ax_t.plot(sample[:zoom], x[:zoom], label="x (input)", linewidth=0.9, color="tab:blue")
    ax_t.plot(sample[:zoom], y[:zoom], label="y (output)", linewidth=0.9, color="tab:red", linestyle="--")
    ax_t.set_title(f"Composite signal: 10k/20k/30k/35k/40k Hz, fs = 1 Msps (first {zoom} samples)")
    ax_t.set_xlabel("sample")
    ax_t.set_ylabel("amplitude")
    ax_t.set_xlim(sample[0], sample[zoom - 1])
    ax_t.grid(True, alpha=0.3)
    ax_t.legend(loc="upper right")

    ax_f.plot(freqs, x_mag, label="x (input)", linewidth=1.0, color="tab:blue")
    ax_f.plot(freqs, y_mag, label="y (output)", linewidth=1.0, color="tab:red")
    for h in HARMONICS:
        ax_f.axvline(h, color="grey", linewidth=0.7, linestyle=":")
    ax_f.set_title("FFT magnitude - dotted lines mark the 5 injected harmonics")
    ax_f.set_xlabel("frequency (Hz)")
    ax_f.set_ylabel("magnitude")
    ax_f.set_xlim(0, 60_000)
    ax_f.grid(True, alpha=0.3)
    ax_f.legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(args.out, dpi=120)
    print(f"saved {args.out} ({sample.size} samples)")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
