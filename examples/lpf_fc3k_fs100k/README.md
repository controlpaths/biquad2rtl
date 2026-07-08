# Example: low-pass biquad, fc = 3 kHz, fs = 100 kHz

End-to-end example of the `biquad2rtl` flow: generate the RTL for a Butterworth
low-pass biquad, simulate it with a sine sweep, log the input/output samples to a
CSV and plot the result.

The filter is a second-order low-pass with a -3 dB cutoff at **3 kHz** for a
sampling rate of **100 kHz**, in `Q12.20` fixed-point (`DATA_WIDTH = 32`,
`FRAC_WIDTH = 20`).

## Files

| File | Tracked | Description |
|---|---|---|
| `lpf_fc3k_fs100k_tb.v` | yes | Testbench: sine generator + CSV logger + three tone tests |
| `Makefile` | yes | Builds and runs the simulation with `iverilog`/`vvp` |
| `plot_log.py` | yes | Reads the CSV log and renders a wide input/output plot |
| `biquad.v` | no | Generated RTL (copied from `output/`) |
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
make TYPE=lowpass FC=3000 FS=100000 DATA_WIDTH=32 FRAC_WIDTH=20
```

This creates the virtual environment (if missing), designs the filter and writes
the artifacts to `output/` (`biquad.v`, `biquad_instantiation_template.v` and
`biquad_bode.png`).

### 2. Copy the RTL into this example

```sh
cp output/biquad.v examples/lpf_fc3k_fs100k/biquad.v
```

### 3. Run the simulation

```sh
cd examples/lpf_fc3k_fs100k
make
```

This compiles `biquad.v` + `lpf_fc3k_fs100k_tb.v` with `iverilog -g2012`, runs the
three tone tests (1 kHz, 3 kHz and 8 kHz, 500 samples each) and writes
`data.vcd` and `filter_log.csv`.

### 4. Plot the log

```sh
python3 plot_log.py
```

Reads `filter_log.csv` and saves `filter_log.png` (a wide figure with all 1500
samples). Use `--show` for an interactive window or `--out <file>` to change the
output name.

## What to expect

The testbench drives three sinusoids through the filter and the plot shows the
low-pass response clearly:

- **1 kHz** (below fc) - output tracks the input at full amplitude.
- **3 kHz** (at fc) - output attenuated by roughly -3 dB.
- **8 kHz** (above fc) - output strongly attenuated.

Each `test_xx` task sets its frequency with `set_freq()` and injects samples with
`drive_sine()`, so you can add more tones or change frequencies without touching
the generator.

## Clean up

```sh
make clean
```

Removes the simulation binary, `data.vcd`, `filter_log.csv` and `filter_log.png`.
