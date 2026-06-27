# filter2rtl - generate a fixed-point biquad RTL from a filter specification.
#
# The default target creates a Python virtual environment (if missing), installs
# the dependencies from requirements.txt and runs biquad2rtl.py to emit biquad.v.

VENV   := .venv
PYTHON := $(VENV)/bin/python
PIP    := $(VENV)/bin/pip
STAMP  := $(VENV)/.installed

# Filter specification. Override on the command line, e.g.
#   make TYPE=highpass FC=2000 FS=48000 Q=1.0
#   make TYPE=bandpass FC=0.15 Q=5 DATA_WIDTH=24 FRAC_WIDTH=18
#
# FC is a built-in Make variable (Fortran compiler); drop it so our default below
# is honoured while still allowing a command-line override.
undefine FC

TYPE       ?= lowpass
FC         ?= 0.1
FS         ?= 1.0
Q          ?= 0.70710678
DATA_WIDTH ?= 32
FRAC_WIDTH ?= 20
OUT        ?= output/biquad.v

.PHONY: all generate venv mcp clean distclean

all: generate

# Create the virtual environment and install dependencies. Re-runs only when it
# is missing or when requirements.txt changes (tracked by the stamp file).
$(STAMP): requirements.txt
	python3 -m venv --system-site-packages $(VENV)
	$(PIP) install -r requirements.txt
	touch $(STAMP)

venv: $(STAMP)

# Design the filter and write the RTL using the virtual environment.
generate: $(STAMP)
	$(PYTHON) biquad2rtl.py \
	  --type $(TYPE) \
	  --fc $(FC) \
	  --fs $(FS) \
	  --q $(Q) \
	  --data-width $(DATA_WIDTH) \
	  --frac-width $(FRAC_WIDTH) \
	  --output $(OUT)

# Run the MCP server (stdio) so an MCP client can use the generator as a tool.
mcp: $(STAMP)
	$(PYTHON) mcp/mcp_server.py

# Remove the generated RTL.
clean:
	rm -f $(OUT)

# Remove the generated RTL and the virtual environment.
distclean: clean
	rm -rf $(VENV)
