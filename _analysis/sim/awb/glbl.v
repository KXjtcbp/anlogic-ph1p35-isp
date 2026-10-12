// Minimal glbl stub so Anlogic's AL_MAP_* gate-level simulation models can be
// compiled in ModelSim.  al_map_basic.v:888/960 does
//     assign gsrn       = glbl.gsrn;
//     assign done_gwe   = glbl.done_gwe;
// i.e. a *hierarchical* reference to a top-level module named `glbl`.
// ModelSim does not ship one, so we supply just the two registers.
//
//   gsrn     = 0  -> global set/reset NOT asserted (no config-reset pulse)
//   done_gwe = 1  -> configuration "done, global write enable" already high
`timescale 1ps / 1ps

module glbl;
    reg gsrn     = 1'b0;
    reg done_gwe = 1'b1;
endmodule
