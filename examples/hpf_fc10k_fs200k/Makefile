IVL ?= iverilog
VVP ?= vvp

MGR_TOP = hpf_fc10k_fs200k_tb
MGR_OUT = hpf_fc10k_fs200k_tb.out
MGR_VCD = data.vcd
MGR_CSV = filter_log.csv
MGR_SRC = ./biquad.v ./hpf_fc10k_fs200k_tb.v

.PHONY: all run_manager clean

all: run_manager

$(MGR_OUT): $(MGR_SRC)
	$(IVL) -g2012 -s $(MGR_TOP) -o $(MGR_OUT) $(MGR_SRC)

run_manager: $(MGR_OUT)
	$(VVP) $(MGR_OUT)

clean:
	rm -f $(MGR_OUT) $(MGR_VCD) $(MGR_CSV)
