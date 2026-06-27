# Example: high-pass biquad, fc = 10 kHz, fs = 200 kHz, Q = 3 (Q5.10)

End-to-end example of the `filter2rtl` flow: generate the RTL for a high-pass
biquad, simulate it with a sine sweep, log the input/output samples to a CSV and
plot the result.

The filter is a second-order high-pass with a cutoff at **10 kHz** for a
sampling rate of **200 kHz**, with a quality factor **Q = 3**, in `Q5.10`
fixed-point (`DATA_WIDTH = 16`, `FRAC_WIDTH = 10`). The fractional point is at
bit 10 (instead of the usual 14) to leave 5 integer bits of headroom for the
Q = 3 resonant peak around the cutoff.

## Files

| File | Tracked | Description |
|---|---|---|
| `hpf_fc10k_fs200k_tb.v` | yes | Testbench: sine generator + CSV logger + three tone tests |
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
make TYPE=highpass FC=10000 FS=200000 DATA_WIDTH=16 FRAC_WIDTH=10 Q=3
```

This creates the virtual environment (if missing), designs the filter and writes
the artifacts to `output/` (`biquad.v`, `biquad_instantiation_template.v` and
`biquad_bode.png`).

### 2. Copy the RTL into this example

```sh
cp output/biquad.v examples/hpf_fc10k_fs200k/biquad.v
```

### 3. Run the simulation

```sh
cd examples/hpf_fc10k_fs200k
make
```

This compiles `biquad.v` + `hpf_fc10k_fs200k_tb.v` with `iverilog -g2012`, runs
the three tone tests (1 kHz, 10 kHz and 20 kHz, 1000 samples each) and writes
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
high-pass response clearly:

- **1 kHz** (below fc) - output strongly attenuated.
- **10 kHz** (at fc) - output attenuated by roughly -3 dB.
- **20 kHz** (above fc) - output tracks the input at full amplitude.

Each `test_xx` task sets its frequency with `set_freq()` and injects samples with
`drive_sine()`, so you can add more tones or change frequencies without touching
the generator.

## Clean up

```sh
make clean
```

Removes the simulation binary, `data.vcd`, `filter_log.csv` and `filter_log.png`.
