---
name: add-biquad-filter
description: This skill should be used when, while editing a Verilog/SystemVerilog file, the user asks to add or insert a filter into an existing module - e.g. "add a lowpass filter in this module that filters x and returns y", "mete un notch a esta señal", "filter this input with a bandpass". It designs the biquad with filter2rtl, places the RTL and wires a ready-to-synthesize instance into the target module, adapting widths, fixed-point format and the valid handshake to the surrounding code.
version: 1.0.0
---

# Add a biquad filter into an existing Verilog module

Use this skill to take a filter request expressed against existing RTL ("filter
this input, give me this filtered output") and turn it into a working,
synthesizable instance wired into the user's module. The filter math is handled
by the `filter2rtl` generator in this repository; this skill owns the
*integration* — reading the host module, choosing matching parameters, and
cabling the instance.

## When this applies

The user is editing Verilog and asks to add/insert a filter referencing a
concrete input signal and a desired output signal inside a specific module.
If they only want a standalone `biquad.v` with no host module, just run the
generator (MCP tool `generate_biquad_rtl` or `make TYPE=...`) — no integration
needed.

## Inputs to collect (infer from the code first, ask only if missing)

1. **Filter spec**: type (`lowpass`/`highpass`/`bandpass`/`notch`), cutoff/center
   frequency, sampling frequency `fs`, and `Q`. If the user gives fc in Hz, you
   need `fs`; if they give a normalized `fc/fs` (0–0.5), `fs=1.0`. Default
   `Q = 0.70710678` (Butterworth) unless they want a sharper/resonant response.
2. **Target module**: which module, which input signal feeds the filter, and the
   name of the filtered output signal the user expects.

## Inspect the host module before generating

Read the target module and extract, so the instance actually fits:

- **Clock / reset**: the generated module uses `aclk` and active-low synchronous
  `aresetn`. Map them to the host's clock and reset. Per the workspace Verilog
  rules, resets are synchronous — never add the reset to a sensitivity list.
- **Input width and fixed-point format**: set the generator's `--data-width` to
  the host signal's width and `--frac-width` to its number of fractional bits
  (its Q format). Matching these avoids a format mismatch at the boundary.
- **Sample cadence / valid handshake**: find out whether a new sample arrives
  every clock (continuous stream) or is qualified by a `*_valid`/strobe signal.

## Generate the RTL

Prefer the MCP tool when available:

- `generate_biquad_rtl(filter_type, fc, fs, q, data_width, frac_width)` → returns
  the Verilog source.
- `characterize_biquad(...)` first if you want to confirm the poles/zeros,
  −3 dB point and DC/Nyquist gain before committing.

CLI fallback from the repo root:

```sh
make TYPE=<type> FC=<fc> FS=<fs> Q=<q> DATA_WIDTH=<w> FRAC_WIDTH=<f>
```

Save the module as a real file in the project's `rtl/` directory (e.g.
`rtl/biquad_<tag>.v`). The generator always names the module `biquad`; if the
host already has a `biquad` or you are adding more than one filter, **rename the
module** (and the file) to a unique name like `biquad_<signal>` to avoid a name
clash, and use that name in the instance.

## Wire the instance — adapt to the target module

This is the core of the skill: the instance must match the host, not the other
way around. Insert a `u_<name>`-prefixed instance and adapt as follows:

- **Clock/reset**: connect `.aclk` and `.aresetn` to the host's clock and reset.
  If the host reset is active-high, invert it through a declared wire (no inline
  `wire foo = ~rst;` — declare then `assign`).
- **Valid handshake**:
  - If the host has a sample-valid/strobe for the input, wire it to `.x_valid`
    and use the module's `.y_valid` to qualify the filtered output downstream.
  - If the input is a continuous one-sample-per-clock stream with no valid, tie
    `.x_valid` high through a declared `1'b1` wire so the filter advances every
    clock; the user's output is then `.y` directly.
- **Width / Q alignment**: if the host signal width differs from what you
  generated, bridge it with explicit declared wires and `assign`s
  (sign-extension or truncation), keeping the Q point aligned. Do not rely on
  implicit width changes in the port map.
- Connect `.x` to the requested input and route `.y` (and `.y_valid` if used) to
  the output signal the user named, declaring any needed wires.

## Respect the workspace Verilog style

When editing the host file and emitting the instance, follow the project rules:

- `aclk` / `resetn` naming, **synchronous** resets only (`always @(posedge aclk)`).
- Non-blocking `<=` in sequential blocks, blocking `=` in combinational.
- No inline `wire foo = expr;` — declare, then `assign` separately.
- Comments use `/* ... */`, never `//`. 2-space indentation, no tabs.
- `end` on its own line; `else`/`else if` on the next line after `end`.
- Instances use the `u_` prefix; constants/FSM states are `localparam` UPPER_CASE.

## Finish

Briefly tell the user what was added: the filter spec realized (with the measured
−3 dB / center and gains from `characterize_biquad`), the file written, how the
valid handshake was resolved, and any width/Q bridging you inserted. If the host
context was ambiguous (e.g. no clear sample rate or valid), state the assumption
you made so they can correct it.
