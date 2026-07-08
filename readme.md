# filter2rtl

Generate synthesizable Verilog for a **second-order IIR filter** (biquad) from a
short filter specification. The tool designs the filter from a type, a
cutoff/center frequency and a quality factor, characterizes the resulting
transfer function, quantizes the coefficients to fixed-point, and fills a Verilog
template to emit a ready-to-simulate RTL module.

For each run it also prints a verbose report (filter type, coefficients,
characteristics, quantization error), saves a Bode plot comparing the
continuous, discrete and quantized responses, and writes a module instantiation
template. Everything is stored under `output/`.

A second-order IIR section (biquad) implements the difference equation:

```
y[n] = b0*x[n] + b1*x[n-1] + b2*x[n-2] - a1*y[n-1] - a2*y[n-2]
```

The `bX` (feed-forward) and `aX` (feed-back) coefficients are computed from the
requested specification (RBJ Audio EQ Cookbook formulas), then rounded to the
nearest value representable in `Q(frac_width)` fixed-point and baked into the
module as non-overridable `localparam`s.

## Project layout

```
filter2rtl/
├── biquad.py        # Verilog module template (string.Template) + render()
├── biquad2rtl.py    # CLI: design, characterize, quantize, generate biquad.v
├── mcp/
│   ├── mcp_server.py  # MCP server exposing the generator as tools
│   └── .mcp.json      # sample MCP client configuration
├── .claude/skills/add-biquad-filter/  # Claude Code skill: integrate a filter into existing RTL
├── requirements.txt # Python dependencies (numpy, scipy, matplotlib, mcp)
├── Makefile         # creates the venv, installs deps and runs the generator
├── install.sh       # registers the MCP server and links the skill user-wide
├── output/          # generated artifacts (created at runtime, git-ignored)
└── readme.md
```

- **`biquad.py`** holds the parametric biquad and instantiation `string.Template`s,
  plus the `render()`/`render_instantiation()` helpers and the fixed-point
  `quantize()` routine. Running it directly (`python3 biquad.py`) prints the
  currently configured filter.
- **`biquad2rtl.py`** parses the arguments, designs the filter, characterizes it
  with `numpy`/`scipy` (poles, zeros, -3 dB cutoff, DC/Nyquist gain), reports the
  quantization error and writes the artifacts.

Each run writes to `output/`:

- `biquad.v` — the synthesizable module with quantized coefficients.
- `biquad_instantiation_template.v` — a ready-to-wire instance, preceded by a
  comment describing the filter characteristics.
- `biquad_bode.png` — magnitude/phase Bode plot overlaying the continuous
  (analog prototype), discrete (float) and discrete quantized responses.

## Usage

The `Makefile` creates a Python virtual environment (if missing), installs the
dependencies and runs the generator inside it:

```
make
```

This produces `output/biquad.v` with the default specification (Butterworth
lowpass at `fc = 0.1*fs`). Override any parameter on the command line:

```
make TYPE=highpass FC=2000 FS=48000 Q=1.0
make TYPE=bandpass FC=0.15 Q=5 DATA_WIDTH=24 FRAC_WIDTH=18
```

| Variable     | Meaning                                                     | Default      |
|--------------|-------------------------------------------------------------|--------------|
| `TYPE`       | `lowpass`, `highpass`, `bandpass` or `notch`                | `lowpass`    |
| `FC`         | Cutoff/center frequency (in `fs` units, or in Hz with `FS`) | `0.1`        |
| `FS`         | Sampling frequency (1.0 keeps `FC` normalized)              | `1.0`        |
| `Q`          | Quality factor                                              | `0.70710678` |
| `DATA_WIDTH` | Sample/coefficient width in bits                            | `32`         |
| `FRAC_WIDTH` | Number of fractional bits (Q format)                        | `20`         |
| `OUT`        | Output Verilog file                                         | `output/biquad.v` |

Other targets:

- `make venv` — only create the environment and install dependencies.
- `make clean` — remove the generated RTL.
- `make distclean` — remove the RTL and the virtual environment.

### Running the generator directly

If you prefer not to use the `Makefile`, create the virtual environment and
install the dependencies by hand:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> On Windows use `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

With the environment active, run the generator directly:

```
python3 biquad2rtl.py --type lowpass --fc 0.1 --q 0.70710678
python3 biquad2rtl.py --type highpass --fc 2000 --fs 48000 --q 0.8 --print
```

`--print` writes only the RTL to stdout (no report, plot or files); `--no-plot`
skips the Bode plot. Run `deactivate` to leave the
virtual environment.

## MCP server

`mcp/mcp_server.py` exposes the generator over the [Model Context Protocol](https://modelcontextprotocol.io)
so an AI assistant can design filters on demand. It provides two tools:

- **`generate_biquad_rtl`** — design the filter and return the Verilog source.
- **`characterize_biquad`** — return the coefficients (float and quantized),
  poles/zeros, -3 dB cutoff and DC/Nyquist gain, without emitting RTL.

Both accept `filter_type`, `fc`, `fs`, `q`, `data_width` and `frac_width`, with
the same defaults as the CLI.

Run it over stdio (the environment is created/installed automatically):

```
make mcp
```

To register it with an MCP client, point the client at the virtual-environment
Python and `mcp/mcp_server.py`. `mcp/.mcp.json` is a sample configuration with
paths relative to the project root:

```json
{
  "mcpServers": {
    "filter2rtl": {
      "command": ".venv/bin/python",
      "args": ["mcp/mcp_server.py"]
    }
  }
}
```

Claude Code auto-discovers a `.mcp.json` at the **project root**, so copy this
file there (`cp mcp/.mcp.json .mcp.json`) to enable it. For clients that need
absolute paths (e.g. Claude Desktop), replace them with the full paths to
`.venv/bin/python` and `mcp/mcp_server.py`. Run `make venv` once beforehand so
the environment exists.

## Claude Code skill

The repository also ships a Claude Code skill, `add-biquad-filter`
(`.claude/skills/add-biquad-filter/SKILL.md`), that goes one step beyond
generating a standalone module: it **integrates** a filter into an existing
Verilog/SystemVerilog file. When, while editing RTL, you ask something like
"add a lowpass that filters `x` and returns `y` in this module", the skill:

- reads the host module and infers the filter spec, the input/output signals,
  and the surrounding clock/reset and sample cadence;
- generates the biquad through the MCP tools (or the CLI as a fallback), matching
  the host's `--data-width` and `--frac-width` (Q format);
- saves the RTL into the project's `rtl/` directory, renaming the module when
  needed to avoid a name clash;
- wires a `u_`-prefixed instance into the module, adapting the clock/reset, the
  `x_valid`/`y_valid` handshake (or tying valid high for a continuous stream) and
  any width/Q bridging, following the workspace Verilog style.

If you only need a standalone `biquad.v`, keep using the CLI or the MCP tools
directly — the skill is for the in-place integration case.

## Using the skill and MCP server from any project

The steps above enable both only while Claude Code runs inside this
repository. To use `add-biquad-filter` and the `filter2rtl` MCP server while
editing RTL in *any* project, register them once in your personal Claude Code
installation.

### Quick install

`install.sh` automates both steps below (venv, `claude mcp add`, and the
skill symlink):

```sh
./install.sh                # registers the MCP server with --scope user
./install.sh --scope project  # registers it for the current project instead
```

It is idempotent — safe to re-run after a `git pull`, and it won't overwrite
an existing skill symlink that points somewhere else. Requires the `claude`
CLI in `PATH`.

### MCP server (user-wide)

```sh
make venv   # make sure .venv exists first
claude mcp add filter2rtl --scope user \
  -- /path/to/biquad2rtl/.venv/bin/python /path/to/biquad2rtl/mcp/mcp_server.py
```

Replace `/path/to/biquad2rtl` with the absolute path to this repository, then
check it with `claude mcp list`. Use `--scope project` instead of `--scope
user` to enable it only for the project you're currently in (equivalent to
copying `mcp/.mcp.json` to that project's root).

### Skill (user-wide)

```sh
mkdir -p ~/.claude/skills
ln -s /path/to/biquad2rtl/.claude/skills/add-biquad-filter ~/.claude/skills/add-biquad-filter
```

Using a symlink (instead of copying the folder) means `git pull` in this repo
keeps the installed skill up to date automatically, with no manual re-copy
step. Claude Code picks up user-level skills from `~/.claude/skills/` on the
next session, no restart needed. Keep the MCP server registered as above so
the skill calls `generate_biquad_rtl`/`characterize_biquad` directly instead
of falling back to the CLI.

## Generated module

The generated module follows the workspace RTL conventions: synchronous reset
(`aresetn`, active-low), single clock (`aclk`), non-blocking assignments in the
sequential block, and a multiply-accumulate datapath sized with guard bits to
avoid overflow. Widths and coefficients are fixed `localparam`s, so the module is
not parameterizable from above — regenerate it to change the filter.

## Requirements

- Python 3.10+ with `numpy`, `scipy`, `matplotlib` and `mcp` (installed
  automatically into `.venv`).
