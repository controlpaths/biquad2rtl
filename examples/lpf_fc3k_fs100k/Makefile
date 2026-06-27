IVL ?= iverilog
VVP ?= vvp

MGR_TOP = lpf_fc3k_fs100k_tb
MGR_OUT = lpf_fc3k_fs100k_tb.out
MGR_VCD = data.vcd
MGR_CSV = filter_log.csv
MGR_SRC = ./biquad.v ./lpf_fc3k_fs100k_tb.v

.PHONY: all run_manager clean

all: run_manager

$(MGR_OUT): $(MGR_SRC)
	$(IVL) -g2012 -s $(MGR_TOP) -o $(MGR_OUT) $(MGR_SRC)

run_manager: $(MGR_OUT)
	$(VVP) $(MGR_OUT)

clean:
	rm -f $(MGR_OUT) $(MGR_VCD) $(MGR_CSV)