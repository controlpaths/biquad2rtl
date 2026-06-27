#!/usr/bin/env python3
"""plot_log.py - plot the testbench filter log.

Reads ``filter_log.csv`` (columns: time_ns, x, y) produced by
``bpf_fc25k_fs1m_tb.v`` and draws the input and output samples on a wide
figure so all 3000 points are clearly visible.

Examples
--------
    python3 plot_log.py
    python3 plot_log.py --csv filter_log.csv --out filter_log.png
"""

import argparse

import numpy as np
import matplotlib.pyplot as plt


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
    sample = np.arange(data["x"].size)

    fig, ax = plt.subplots(figsize=(24, 6))
    ax.plot(sample, data["x"], label="x (input)", linewidth=0.8, color="tab:blue")
    ax.plot(sample, data["y"], label="y (output)", linewidth=1.2, color="tab:red")

    ax.set_title("Biquad bandpass fc = 25 kHz, fs = 1 MHz, Q = 20 - input vs output")
    ax.set_xlabel("sample")
    ax.set_ylabel("amplitude")
    ax.set_xlim(sample[0], sample[-1])
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()

    fig.savefig(args.out, dpi=120)
    print(f"saved {args.out} ({sample.size} samples)")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
