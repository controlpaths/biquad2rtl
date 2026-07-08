# Example: bandpass biquad, fc = 25 kHz, fs = 1 MHz, Q = 20

End-to-end example of the `biquad2rtl` flow: generate the RTL for a bandpass
biquad, simulate it with a set of tones around the pass-band, log the
input/output samples to a CSV and plot the result.

The filter is a second-order bandpass centered at **25 kHz** for a sampling rate
of **1 MHz**, with a quality factor **Q = 20** (narrow pass-band), in `Q12.20`
fixed-point (`DATA_WIDTH = 32`, `FRAC_WIDTH = 20`).

It is the exact counterpart of the [notch example](../notch_fc25k_fs1m/): same
center frequency, sampling rate and Q, but the opposite response. Where the
notch rejects the 25 kHz band and passes everything else, this bandpass passes
the 25 kHz band and rejects everything else.

## Files

| File | Tracked | Description |
|---|---|---|
| `bpf_fc25k_fs1m_tb.v` | yes | Testbench: sine generator + CSV logger + three tone tests |
| `Makefile` | yes | Builds and runs the simulation with `iverilog`/`vvp` |
| `plot_log.py` | yes | Reads the CSV log and renders a wide input/output plot |
| `biquad.v` | yes | Generated RTL (copied from `output/`) |
| `data.vcd` | no | Simulation waveform |
| `filter_log.csv` | no | Per-sample input/output log |
| `filter_log.png` | no | Plot produced by `plot_log.py` |

## Requirements

- **Icarus Verilog** (`iverilog` + `vvp`) to compile and run the testbench. On
  Debian/Ubuntu: `sudo apt install iverilog`.
- **Python 3** with `numpy` and `matplotlib` for `plot_log.py`. The repository
  `Makefile` installs them into a virtual environment when generating the filter
  (see step 1), or install them manually with `pip install numpy matplotlib`.

## Recreate the example

All commands are relative to the repository root unless noted otherwise.

### 1. Generate the filter RTL

```sh
make TYPE=bandpass FC=25000 FS=1000000 DATA_WIDTH=32 FRAC_WIDTH=20 Q=20
```

This creates the virtual environment (if missing), designs the filter and writes
the artifacts to `output/` (`biquad.v`, `biquad_instantiation_template.v` and
`biquad_bode.png`).

### 2. Copy the RTL into this example

```sh
cp output/biquad.v examples/bpf_fc25k_fs1m/biquad.v
```

### 3. Run the simulation

```sh
cd examples/bpf_fc25k_fs1m
make
```

This compiles `biquad.v` + `bpf_fc25k_fs1m_tb.v` with `iverilog -g2012`, runs
the three tone tests (22 kHz, 25 kHz and 27 kHz, 1000 samples each) and writes
`data.vcd` and `filter_log.csv`.

### 4. Plot the log

```sh
python3 plot_log.py
```

Reads `filter_log.csv` and saves `filter_log.png` (a wide figure with all 3000
samples). Use `--show` for an interactive window or `--out <file>` to change the
output name.

## What to expect

The testbench drives three sinusoids through the filter and the plot shows the
bandpass response clearly — the mirror image of the notch:

- **22 kHz** (off the pass-band) - output strongly attenuated.
- **25 kHz** (at the band center) - output tracks the input at full amplitude.
- **27 kHz** (off the pass-band) - output strongly attenuated again.

With Q = 20 the pass-band is narrow, so the 22 kHz and 27 kHz tones, only a few
kHz away from the center, are already noticeably attenuated.

Each `test_xx` task sets its frequency with `set_freq()` and injects samples with
`drive_sine()`, so you can add more tones or change frequencies without touching
the generator.

## Clean up

```sh
make clean
```

Removes the simulation binary, `data.vcd`, `filter_log.csv` and `filter_log.png`.
