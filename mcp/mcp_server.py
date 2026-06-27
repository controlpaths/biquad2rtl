#!/usr/bin/env python3
"""MCP server exposing the filter2rtl biquad generator as tools.

It lets an MCP client (e.g. Claude Code / Claude Desktop) design a second-order
IIR (biquad) filter and obtain the synthesizable Verilog, or just inspect the
coefficients and characteristics, without having to run the CLI by hand.

Run it over stdio with:

    python3 mcp/mcp_server.py
"""

import os
import sys
from typing import Annotated, Literal

from pydantic import Field
from mcp.server.fastmcp import FastMCP

# biquad.py and biquad2rtl.py live in the project root, one level up.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import biquad
import biquad2rtl

mcp = FastMCP("filter2rtl")

FilterType = Literal["lowpass", "highpass", "bandpass", "notch"]
_BUTTERWORTH_Q = float(biquad2rtl.BUTTERWORTH_Q)

# Shared parameter annotations, kept identical across the tools.
TypeArg = Annotated[FilterType, Field(description="Filter type.")]
FcArg = Annotated[float, Field(gt=0, description=(
    "Cutoff frequency for lowpass/highpass, or center frequency for "
    "bandpass/notch. Given in fs units, or in Hz when fs is also provided."))]
FsArg = Annotated[float, Field(gt=0, description=(
    "Sampling frequency. Leave at 1.0 to interpret fc as normalized (fc/fs). "
    "The design requires 0 < fc/fs < 0.5."))]
QArg = Annotated[float, Field(gt=0, description=(
    "Quality factor. 0.7071 (1/sqrt(2)) gives a Butterworth/maximally-flat "
    "response; higher values sharpen the response and add a resonant peak."))]
DataWidthArg = Annotated[int, Field(ge=4, le=64, description=(
    "Sample and coefficient width in bits."))]
FracWidthArg = Annotated[int, Field(ge=0, description=(
    "Number of fractional bits (Q format). Must be smaller than data_width."))]


def _fc_norm(fc: float, fs: float) -> float:
    fc_norm = fc / fs
    if not 0.0 < fc_norm < 0.5:
        raise ValueError(
            f"fc/fs = {fc_norm:g} is out of range; it must satisfy 0 < fc/fs < 0.5"
        )
    return fc_norm


def _check_widths(data_width: int, frac_width: int) -> None:
    if frac_width >= data_width:
        raise ValueError(
            f"frac_width ({frac_width}) must be smaller than data_width ({data_width})"
        )


@mcp.tool()
def generate_biquad_rtl(
    filter_type: TypeArg,
    fc: FcArg,
    fs: FsArg = 1.0,
    q: QArg = _BUTTERWORTH_Q,
    data_width: DataWidthArg = biquad.DATA_WIDTH,
    frac_width: FracWidthArg = biquad.FRAC_WIDTH,
) -> str:
    """Design a 2nd-order IIR (biquad) filter and return synthesizable Verilog.

    The module implements the Direct Form I difference equation with the
    coefficients baked in as fixed-point Q(frac_width) localparams. Returns the
    complete biquad.v source as text (save it wherever you need it).
    """
    fc_norm = _fc_norm(fc, fs)
    _check_widths(data_width, frac_width)
    return biquad2rtl.generate(filter_type, fc_norm, q, data_width, frac_width)


@mcp.tool()
def characterize_biquad(
    filter_type: TypeArg,
    fc: FcArg,
    fs: FsArg = 1.0,
    q: QArg = _BUTTERWORTH_Q,
    data_width: DataWidthArg = biquad.DATA_WIDTH,
    frac_width: FracWidthArg = biquad.FRAC_WIDTH,
) -> dict:
    """Design the filter and report its coefficients and characteristics.

    Use this to inspect a design (float and quantized coefficients, poles/zeros,
    -3 dB cutoff, DC/Nyquist gain) before generating the RTL.
    """
    fc_norm = _fc_norm(fc, fs)
    _check_widths(data_width, frac_width)

    b, a = biquad2rtl.design_coefficients(filter_type, fc_norm, q)
    doc = biquad2rtl.characterize(b, a, filter_type, fc_norm, q)

    scale = float(1 << frac_width)
    b_q = [biquad.quantize(c, frac_width, data_width) for c in b]
    a_q = [biquad.quantize(c, frac_width, data_width) for c in a[1:]]  # a0 = 1 is implicit

    return {
        "filter_type": filter_type,
        "fc_norm_requested": fc_norm,
        "fc_norm_measured": doc["fc_norm"],
        "q": q,
        "data_width": data_width,
        "frac_width": frac_width,
        "coefficients_float": {"b": b, "a": a},
        "coefficients_q": {"b": b_q, "a1": a_q[0], "a2": a_q[1]},
        "coefficients_realized": {
            "b": [v / scale for v in b_q],
            "a": [1.0] + [v / scale for v in a_q],
        },
        "dc_gain": doc["dc_gain_db"],
        "nyquist_gain": doc["nyquist_gain_note"],
        "zeros": doc["zeros_note"],
        "poles": doc["poles_note"],
        "response": doc["rolloff_note"],
    }


if __name__ == "__main__":
    mcp.run()
