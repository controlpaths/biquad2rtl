`timescale 1ns/1ns

`define DATA_WIDTH 32
`define FRAC_WIDTH 20
`define CLK_CYCLE 4
`define TSAMPLE 10*`CLK_CYCLE /* sampling period; not tied to fs, the discretized filter only keeps the fs/fc relation */

module bpf_fc25k_fs1m_tb ();


  reg aclk;
  reg aresetn;

  /* FP signal */
  real angle;
  real signal;
  real fs;
  real f0;
  real nsamples;
  real angle_increment;

  /* Quantized & discretized signal */
  reg [`DATA_WIDTH-1:0] signal_reg;
  reg dvalid;
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

  /* DUT */
  biquad u_biquad (
  .aclk(aclk), /* clock */
  .aresetn(aresetn), /* synchronous active-low reset */
  .x_valid(dvalid), /* input sample valid */
  .x(signal_reg), /* input sample, signed [19:0] Q15 */
  .y_valid(y_valid), /* output sample valid */
  .y(y) /* output sample, signed [19:0] Q15 */
  );

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

  /* update the sinusoid frequency and recompute the angle increment */
  task set_freq(input real new_f0);
    begin
      f0 = new_f0;
      nsamples = fs/f0; /* samples per period */
      angle_increment = 2*3.141459/nsamples;
    end
  endtask

  /* drive n sine samples at the current frequency */
  task drive_sine(input integer n);
    integer i;
    begin
      for (i = 0; i<n; i=i+1) begin
        angle = angle + angle_increment;
        #(`TSAMPLE); /* this delay don't have to be consistent with the sampling frequency because
                  the discretized filter only satisfy the relation between fs and fc */
        signal = $sin(angle) * 2**(`FRAC_WIDTH);
        signal_reg = signal;
        dvalid = 1'b1;
        #(`CLK_CYCLE);
        dvalid = 1'b0;
      end
    end
  endtask

  /* ---------------- tests ---------------- */

  task test1;
    /* near-band tone: f0 = 22kHz, off the 25kHz pass-band, should be rejected */
    begin
      $display("Test 1: Sinusoidal signal with f0 = 22kHz and fs = 1MHz");
      $display("Expected output: tone rejected (off the 25kHz pass-band)");
      set_freq(22000);
      drive_sine(1000);
    end
  endtask

  task test2;
    /* pass-band tone: f0 = 25kHz, at the band center, should pass */
    begin
      $display("Test 2: Sinusoidal signal with f0 = 25kHz and fs = 1MHz");
      $display("Expected output: tone passes (at the 25kHz pass-band center)");
      set_freq(25000);
      drive_sine(1000);
    end
  endtask

  task test3;
    /* near-band tone: f0 = 27kHz, off the 25kHz pass-band, should be rejected */
    begin
      $display("Test 3: Sinusoidal signal with f0 = 27kHz and fs = 1MHz");
      $display("Expected output: tone rejected (off the 25kHz pass-band)");
      set_freq(27000);
      drive_sine(1000);
    end
  endtask

  /* ---------------- main ---------------- */
  initial begin
    $dumpfile ("data.vcd"); // Change filename as appropriate.
    $dumpvars();

    /* signal generation defaults */
    fs = 1000000;
    angle = 0;
    dvalid = 1'b0;
    logging = 1'b0;

    aresetn <= 1'b0; /* system reset */
    #(5*`CLK_CYCLE);
    aresetn <= 1'b1; /* release reset */

    open_csv();
    test1();
    test2();
    test3();
    close_csv();

    #(50*`CLK_CYCLE);
    $finish();
  end

endmodule
