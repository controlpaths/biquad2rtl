`timescale 1ns/1ns

`define DATA_WIDTH 32
`define FRAC_WIDTH 20
`define CLK_CYCLE 4
`define TSAMPLE 10*`CLK_CYCLE /* sampling period; not tied to fs, the discretized filter only keeps the fs/fc relation */

module ai_test_tb ();


  reg aclk;
  reg aresetn;

  /* FP signal: composite of five harmonics at 10k/20k/30k/35k/40k Hz, fs = 1 Msps */
  real fs;
  real amp;
  real angle_h1, angle_h2, angle_h3, angle_h4, angle_h5;
  real finc_h1, finc_h2, finc_h3, finc_h4, finc_h5;
  real signal;

  /* Quantized & discretized signal */
  reg [`DATA_WIDTH-1:0] signal_reg;
  reg dvalid;
  wire y_valid;
  wire [`DATA_WIDTH-1:0] y;

  /* csv logging */
  integer csv_fd;
  reg logging;


  /* clock generation */
  initial begin
    aclk <= 0;
    forever begin
      #(`CLK_CYCLE/2); /* This delay depends on the clock frecuency, so it is unrelevant for this simulation */
      aclk <= ~aclk;
    end
  end

  /* DUT: no filter has been generated for this signal yet. Once one is added
     here (e.g. with the add-biquad-filter skill or the biquad2rtl MCP tools)
     it should consume signal_reg/dvalid and drive y/y_valid instead of this
     passthrough. */
  // Insert filter here
  assign y = signal_reg;
  assign y_valid = dvalid;

  /* log input and output to the csv once per sample while enabled */
  always @(posedge aclk)
    if (logging && dvalid)
      $fwrite(csv_fd, "%0d,%f,%f\n", $time, $itor($signed(signal_reg))/(2.0**`FRAC_WIDTH), $itor($signed(y))/(2.0**`FRAC_WIDTH));

  /* ---------------- helper tasks ---------------- */

  /* create the csv log file, write the header and enable logging */
  task open_csv;
    begin
      csv_fd = $fopen("filter_log.csv", "w");
      $fwrite(csv_fd, "time_ns,x,y\n");
      logging = 1'b1;
    end
  endtask

  /* stop logging and close the csv log file */
  task close_csv;
    begin
      logging = 1'b0;
      $fclose(csv_fd);
    end
  endtask

  /* drive n samples of the composite 10k/20k/30k/35k/40k signal */
  task drive_composite(input integer n);
    integer i;
    begin
      for (i = 0; i<n; i=i+1) begin
        angle_h1 = angle_h1 + finc_h1;
        angle_h2 = angle_h2 + finc_h2;
        angle_h3 = angle_h3 + finc_h3;
        angle_h4 = angle_h4 + finc_h4;
        angle_h5 = angle_h5 + finc_h5;
        #(`TSAMPLE); /* this delay don't have to be consistent with the sampling frequency because
                  the discretized filter only satisfy the relation between fs and fc */
        signal = amp * ($sin(angle_h1) + $sin(angle_h2) + $sin(angle_h3) + $sin(angle_h4) + $sin(angle_h5));
        signal_reg = signal * 2**(`FRAC_WIDTH);
        dvalid = 1'b1;
        #(`CLK_CYCLE);
        dvalid = 1'b0;
      end
    end
  endtask

  /* ---------------- test ---------------- */

  task test1;
    /* composite signal: 10kHz, 20kHz, 30kHz, 35kHz and 40kHz harmonics, fs = 1Msps */
    begin
      $display("Test 1: Composite signal with harmonics at 10k/20k/30k/35k/40k Hz, fs = 1Msps");
      $display("Expected output: bandpass filtered, only the 35kHz harmonic passes (fc = 35kHz, fs = 1Msps, Q = 20)");
      drive_composite(8192);
    end
  endtask

  /* ---------------- main ---------------- */
  initial begin
    $dumpfile ("data.vcd"); // Change filename as appropriate.
    $dumpvars();

    /* signal generation defaults */
    fs = 1000000;
    amp = 1.0/5.0;
    angle_h1 = 0; finc_h1 = 2*3.141459*10000/fs;
    angle_h2 = 0; finc_h2 = 2*3.141459*20000/fs;
    angle_h3 = 0; finc_h3 = 2*3.141459*30000/fs;
    angle_h4 = 0; finc_h4 = 2*3.141459*35000/fs;
    angle_h5 = 0; finc_h5 = 2*3.141459*40000/fs;
    dvalid = 1'b0;
    logging = 1'b0;

    aresetn <= 1'b0; /* system reset */
    #(5*`CLK_CYCLE);
    aresetn <= 1'b1; /* release reset */

    open_csv();
    test1();
    close_csv();

    #(50*`CLK_CYCLE);
    $finish();
  end

endmodule
