# Vivado source-list helper for the PL-only eDRAM test platform.
#
# Typical project-mode usage:
#   source src/vivado/sources.tcl
#   edram_vivado::add_rtl_sources
#
# Typical non-project usage:
#   source src/vivado/sources.tcl
#   edram_vivado::read_rtl_sources

namespace eval edram_vivado {
  variable script_dir [file dirname [file normalize [info script]]]
  variable rtl_sources [list \
    src/rtl/edram_pkg.sv \
    src/rtl/uart_baud_gen.sv \
    src/rtl/uart_rx.sv \
    src/rtl/uart_tx.sv \
    src/rtl/uart_frame_parser.sv \
    src/rtl/uart_resp_encoder.sv \
    src/rtl/edram_output_snapshot.sv \
    src/rtl/cmd_dispatcher.sv \
    src/rtl/edram_ctrl_fsm.sv \
    src/rtl/edram_pl_top.sv \
    src/rtl/pl_clk_diff_to_single.sv \
    src/rtl/edram_pl_board_top.sv \
  ]

  proc default_repo_root {} {
    variable script_dir
    return [file normalize [file join $script_dir ../..]]
  }

  proc resolve_rtl_sources {{repo_root ""}} {
    variable rtl_sources

    if {$repo_root eq ""} {
      set repo_root [default_repo_root]
    }

    set resolved_sources [list]
    foreach source_file $rtl_sources {
      lappend resolved_sources [file normalize [file join $repo_root $source_file]]
    }
    return $resolved_sources
  }

  proc assert_files_exist {source_files} {
    foreach source_file $source_files {
      if {![file exists $source_file]} {
        return -code error "Required RTL source not found: $source_file"
      }
    }
  }

  proc get_file_objects {source_files} {
    set file_objects [list]
    foreach source_file $source_files {
      set matches [get_files -quiet $source_file]
      if {[llength $matches] == 0} {
        return -code error "Vivado did not add RTL source: $source_file"
      }
      foreach match $matches {
        lappend file_objects $match
      }
    }
    return $file_objects
  }

  proc add_rtl_sources {{repo_root ""}} {
    set resolved_sources [resolve_rtl_sources $repo_root]
    assert_files_exist $resolved_sources
    add_files -fileset sources_1 -norecurse $resolved_sources
    set_property file_type SystemVerilog [get_file_objects $resolved_sources]
    update_compile_order -fileset sources_1
  }

  proc read_rtl_sources {{repo_root ""}} {
    set resolved_sources [resolve_rtl_sources $repo_root]
    assert_files_exist $resolved_sources
    foreach source_file $resolved_sources {
      read_verilog -sv $source_file
    }
  }
}
