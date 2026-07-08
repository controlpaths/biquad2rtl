# Example: AI-assisted filter insertion, 5-harmonic signal at fs = 1 Msps

Unlike the other examples, this one does not ship with a pre-generated
`biquad.v`. It is the **starting point** for exercising the
[`add-biquad-filter` skill](../../.claude/skills/add-biquad-filter/SKILL.md)
and the `biquad2rtl` MCP server end to end: a testbench drives a signal made of
five harmonics into a placeholder "DUT" section, and you ask Claude to design
and wire the filter that lets one of them through.

The signal is the sum of five equal-amplitude tones at **10 kHz, 20 kHz,
30 kHz, 35 kHz and 40 kHz**, sampled at **fs = 1 Msps**, in the same `Q12.20`
fixed-point format (`DATA_WIDTH = 32`, `FRAC_WIDTH = 20`) used by the other
`fs = 1 MHz` examples ([bpf](../bpf_fc25k_fs1m/), [notch](../notch_fc25k_fs1m/)).

## Files

| File | Tracked | Description |
|---|---|---|
| `ai_test_tb.v` | yes | Testbench: 5-harmonic composite signal generator + CSV logger + `// Insert filter here` placeholder |
| `Makefile` | yes | Builds and runs the simulation with `iverilog`/`vvp` |
| `plot_log.py` | yes | Reads the CSV log and plots a zoomed time view plus the FFT of x and y |
| `data.vcd` | no | Simulation waveform |
| `filter_log.csv` | no | Per-sample input/output log |
| `filter_log.png` | no | Plot produced by `plot_log.py` |

## Requirements

- **Icarus Verilog** (`iverilog` + `vvp`) to compile and run the testbench. On
  Debian/Ubuntu: `sudo apt install iverilog`.
- **Python 3** with `numpy` and `matplotlib` for `plot_log.py`. The repository
  `Makefile` installs them into a virtual environment when generating a filter,
  or install them manually with `pip install numpy matplotlib`.
- Claude Code with the `biquad2rtl` MCP server and the `add-biquad-filter`
  skill available (see [Using the skill and MCP server from any
  project](../../readme.md#using-the-skill-and-mcp-server-from-any-project) in
  the repository root, or just run `../../install.sh` once).

## 1. Run the baseline simulation

No filter has been generated yet: `ai_test_tb.v` marks where it goes with a
`// Insert filter here` comment, right above a passthrough (`y = signal_reg`,
`y_valid = dvalid`). Running the baseline confirms the signal generator and
logging work before any RTL is added:

```sh
cd examples/ai_test
make
python3 plot_log.py
```

`filter_log.png` should show `x` and `y` perfectly overlapping, and the FFT
plot should show all five harmonics at roughly equal magnitude.

## 2. Ask Claude to add the filter

With the skill and MCP server registered, open `ai_test_tb.v` in Claude Code
and ask for the harmonic you want to keep, e.g.:

> Add a bandpass filter in this module that lets the 30kHz harmonic through,
> filtering `signal_reg` and returning `y`.

The skill reads the module, finds `fs = 1000000` and the `DATA_WIDTH`/
`FRAC_WIDTH` macros, generates a matching biquad (via the MCP tools or the
CLI), saves it under a `rtl/` directory, and replaces the placeholder
assigns at `// Insert filter here` with a `u_`-prefixed instance wired to
`aclk`/`aresetn`, `signal_reg`/`dvalid` and `y`/`y_valid`.

After it edits the file, add the generated RTL source to `MGR_SRC` in the
`Makefile` (e.g. `MGR_SRC = ./rtl/biquad_ai_test.v ./ai_test_tb.v`) before
re-running the simulation.

## 3. Re-run and compare

```sh
make clean
make
python3 plot_log.py
```

The FFT plot should now show the requested harmonic dominating and the other
four attenuated, while the time-domain plot shows `y` settling into a clean
single-tone sinusoid instead of tracking the composite `x`.

## Clean up

```sh
make clean
```

Removes the simulation binary, `data.vcd`, `filter_log.csv` and
`filter_log.png`. Any filter RTL added under `rtl/` is left untouched.
