# Vivado project-mode flow for the PL-only eDRAM test platform.
#
# GUI usage:
#   Vivado -> Tools -> Run Tcl Script -> select this file
#
# Tcl console examples:
#   set ::EDRAM_VIVADO_STAGES {project sources constraints simulate}
#   set ::EDRAM_VIVADO_RECREATE 0
#   source /path/to/src/vivado/run_project_mode.tcl
#
# Environment variables with the same names are also supported:
#   EDRAM_VIVADO_STAGES="project,sources,constraints,synth,impl,bitstream"
#   EDRAM_VIVADO_PROJECT_DIR="/tmp/edram_fpga_test_platform"
#   EDRAM_VIVADO_RECREATE=1
#   EDRAM_VIVADO_JOBS=4
#   EDRAM_VIVADO_VALIDATE_ONLY=1

namespace eval edram_project {
  variable default_stages {project sources constraints simulate synth impl bitstream}
  variable stage_order {project sources constraints simulate synth impl bitstream}

  variable script_path ""
  variable script_dir ""
  variable repo_root ""
  variable config_path ""
  variable sources_tcl_path ""
  variable xdc_path ""
  variable sim_tb_path ""

  variable project_name ""
  variable part ""
  variable top ""
  variable default_library ""
  variable target_language ""
  variable project_dir ""
  variable stages {}
  variable recreate 1
  variable jobs 4
  variable validate_only 0
}

proc edram_project::log {message} {
  puts "[clock format [clock seconds] -format {%Y-%m-%d %H:%M:%S}] edram_vivado: $message"
}

proc edram_project::fail {message} {
  return -code error "edram_vivado: $message"
}

proc edram_project::norm_join {args} {
  return [file normalize [file join {*}$args]]
}

proc edram_project::read_text {path} {
  set channel [open $path r]
  set data [read $channel]
  close $channel
  return $data
}

proc edram_project::get_option {name default_value} {
  set global_name "::EDRAM_VIVADO_${name}"
  if {[uplevel #0 [list info exists $global_name]]} {
    return [uplevel #0 [list set $global_name]]
  }

  set env_name "EDRAM_VIVADO_${name}"
  if {[info exists ::env($env_name)]} {
    return $::env($env_name)
  }

  return $default_value
}

proc edram_project::to_bool {value option_name} {
  switch -nocase -- [string trim $value] {
    1 - true - yes - y - on {
      return 1
    }
    0 - false - no - n - off {
      return 0
    }
    default {
      fail "Invalid boolean for ${option_name}: $value"
    }
  }
}

proc edram_project::normalize_stage {stage} {
  set stage [string tolower [string trim $stage]]
  switch -exact -- $stage {
    all - full {
      return all
    }
    project - create - create_project {
      return project
    }
    sources - source - add_sources {
      return sources
    }
    constraints - constrs - add_constraints {
      return constraints
    }
    simulate - simulation - sim {
      return simulate
    }
    synth - synthesis - synthesize {
      return synth
    }
    impl - implement - implementation {
      return impl
    }
    bitstream - write_bitstream - bit {
      return bitstream
    }
    default {
      fail "Unknown stage '$stage'. Supported stages: all, project, sources, constraints, simulate, synth, impl, bitstream"
    }
  }
}

proc edram_project::parse_stage_list {raw_stages} {
  variable default_stages
  variable stage_order

  set tokens {}
  foreach item $raw_stages {
    foreach token [split [string map {"," " "} $item]] {
      if {[string trim $token] ne ""} {
        lappend tokens $token
      }
    }
  }

  if {[llength $tokens] == 0} {
    return $default_stages
  }

  set requested {}
  foreach token $tokens {
    set normalized [normalize_stage $token]
    if {$normalized eq "all"} {
      return $default_stages
    }
    if {[lsearch -exact $requested $normalized] < 0} {
      lappend requested $normalized
    }
  }

  set ordered {}
  foreach stage $stage_order {
    if {[lsearch -exact $requested $stage] >= 0} {
      lappend ordered $stage
    }
  }

  if {[llength $ordered] == 0} {
    fail "No supported stages selected"
  }
  return $ordered
}

proc edram_project::stage_enabled {stage} {
  variable stages
  return [expr {[lsearch -exact $stages $stage] >= 0}]
}

proc edram_project::json_project_string {json key} {
  set project_index [string first "\"project\"" $json]
  if {$project_index < 0} {
    fail "config.json does not contain a project object"
  }

  set open_brace [string first "{" $json $project_index]
  set close_brace [string first "}" $json $open_brace]
  if {$open_brace < 0 || $close_brace < 0 || $close_brace <= $open_brace} {
    fail "config.json project object is malformed"
  }

  set project_block [string range $json $open_brace $close_brace]
  set key_token "\"$key\""
  set key_index [string first $key_token $project_block]
  if {$key_index < 0} {
    fail "config.json project.$key is missing or is not a string"
  }

  set colon_index [string first ":" $project_block $key_index]
  set value_start [string first "\"" $project_block $colon_index]
  set value_end [string first "\"" $project_block [expr {$value_start + 1}]]
  if {$colon_index < 0 || $value_start < 0 || $value_end < 0} {
    fail "config.json project.$key is missing or is not a string"
  }

  set value [string range $project_block [expr {$value_start + 1}] [expr {$value_end - 1}]]
  return $value
}

proc edram_project::vivado_target_language {configured_language} {
  switch -nocase -- $configured_language {
    systemverilog - verilog {
      return Verilog
    }
    vhdl {
      return VHDL
    }
    default {
      return $configured_language
    }
  }
}

proc edram_project::init_paths {} {
  variable script_path
  variable script_dir
  variable repo_root
  variable config_path
  variable sources_tcl_path
  variable xdc_path
  variable sim_tb_path

  set script_path [file normalize [info script]]
  if {$script_path eq ""} {
    fail "Unable to determine script path; source this file or run it through Vivado Run Tcl Script"
  }

  set script_dir [file dirname $script_path]
  set repo_root [norm_join $script_dir ../..]
  set config_path [norm_join $repo_root src vivado config.json]
  set sources_tcl_path [norm_join $repo_root src vivado sources.tcl]
  set xdc_path [norm_join $repo_root src vivado edram_pl_board.xdc]
  set sim_tb_path [norm_join $repo_root sim tb edram_pl_board_top_vivado_tb.sv]
}

proc edram_project::load_project_config {} {
  variable repo_root
  variable config_path
  variable project_name
  variable part
  variable top
  variable default_library
  variable target_language
  variable project_dir
  variable stages
  variable recreate
  variable jobs
  variable validate_only

  if {![file exists $config_path]} {
    fail "Required file not found: $config_path"
  }

  set json [read_text $config_path]
  set project_name [json_project_string $json name]
  set part [json_project_string $json part]
  set top [json_project_string $json top]
  set default_library [json_project_string $json default_library]
  set target_language [json_project_string $json target_language]

  set project_dir_override [string trim [get_option PROJECT_DIR ""]]
  if {$project_dir_override eq ""} {
    set project_dir [norm_join $repo_root build vivado $project_name]
  } elseif {[file pathtype $project_dir_override] eq "relative"} {
    set project_dir [norm_join $repo_root $project_dir_override]
  } else {
    set project_dir [file normalize $project_dir_override]
  }

  set stages [parse_stage_list [get_option STAGES "all"]]
  set recreate [to_bool [get_option RECREATE 1] RECREATE]
  set validate_only [to_bool [get_option VALIDATE_ONLY 0] VALIDATE_ONLY]

  set jobs_value [string trim [get_option JOBS 4]]
  if {![string is integer -strict $jobs_value] || $jobs_value < 1} {
    fail "EDRAM_VIVADO_JOBS must be a positive integer"
  }
  set jobs $jobs_value
}

proc edram_project::assert_file_exists {path label} {
  if {![file exists $path]} {
    fail "Required $label not found: $path"
  }
}

proc edram_project::validate_required_files {} {
  variable config_path
  variable sources_tcl_path
  variable xdc_path
  variable sim_tb_path

  assert_file_exists $config_path "config JSON"
  assert_file_exists $sources_tcl_path "Vivado source helper"
  assert_file_exists $xdc_path "board XDC"
  if {[stage_enabled simulate]} {
    assert_file_exists $sim_tb_path "Vivado simulation testbench"
  }
}

proc edram_project::in_vivado {} {
  return [expr {
    [llength [info commands create_project]] > 0 &&
    [llength [info commands launch_runs]] > 0
  }]
}

proc edram_project::has_open_project {} {
  if {[catch {current_project} current] || $current eq ""} {
    return 0
  }
  return 1
}

proc edram_project::project_xpr_path {} {
  variable project_dir
  variable project_name
  return [norm_join $project_dir "${project_name}.xpr"]
}

proc edram_project::safe_delete_project_dir {} {
  variable project_dir
  variable repo_root

  set normalized_project_dir [file normalize $project_dir]
  set normalized_repo_root [file normalize $repo_root]

  if {$normalized_project_dir eq "/" ||
      $normalized_project_dir eq $normalized_repo_root ||
      [string length $normalized_project_dir] < 8} {
    fail "Refusing to delete unsafe project directory: $normalized_project_dir"
  }

  if {[file exists $normalized_project_dir]} {
    log "Deleting generated project directory: $normalized_project_dir"
    file delete -force $normalized_project_dir
  }
}

proc edram_project::configure_project_properties {} {
  variable part
  variable default_library
  variable target_language

  set vivado_language [vivado_target_language $target_language]
  set_property part $part [current_project]
  set_property target_language $vivado_language [current_project]
  set_property default_lib $default_library [current_project]

  if {![string equal -nocase $target_language $vivado_language]} {
    log "Mapped config target_language '$target_language' to Vivado project target_language '$vivado_language'"
  }
}

proc edram_project::prepare_project {} {
  variable project_name
  variable part
  variable project_dir
  variable recreate

  set xpr_path [project_xpr_path]

  if {[has_open_project]} {
    log "Closing currently open Vivado project"
    close_project
  }

  if {$recreate} {
    safe_delete_project_dir
  }

  if {[file exists $xpr_path]} {
    log "Opening existing Vivado project: $xpr_path"
    open_project $xpr_path
  } else {
    log "Creating Vivado project '$project_name' at $project_dir"
    file mkdir [file dirname $project_dir]
    create_project $project_name $project_dir -part $part -force
  }

  configure_project_properties
}

proc edram_project::ensure_project_open {} {
  if {[has_open_project]} {
    return
  }

  set xpr_path [project_xpr_path]
  if {[file exists $xpr_path]} {
    log "Opening Vivado project: $xpr_path"
    open_project $xpr_path
    configure_project_properties
    return
  }

  fail "No Vivado project is open and $xpr_path does not exist. Include the 'project' stage or create the project first."
}

proc edram_project::remove_files_if_present {paths} {
  if {[llength $paths] == 0} {
    return
  }

  set existing [list]
  foreach path $paths {
    set matches [get_files -quiet $path]
    foreach match $matches {
      if {[lsearch -exact $existing $match] < 0} {
        lappend existing $match
      }
    }
  }

  if {[llength $existing] > 0} {
    remove_files $existing
  }
}

proc edram_project::configure_sources {} {
  variable repo_root
  variable sources_tcl_path
  variable top

  ensure_project_open

  log "Adding RTL sources through $sources_tcl_path"
  source $sources_tcl_path
  if {[llength [info commands edram_vivado::add_rtl_sources]] == 0} {
    fail "sources.tcl did not define edram_vivado::add_rtl_sources"
  }

  remove_files_if_present [edram_vivado::resolve_rtl_sources $repo_root]
  edram_vivado::add_rtl_sources $repo_root
  set_property top $top [get_filesets sources_1]
  update_compile_order -fileset sources_1
  log "Configured sources_1 top: $top"
}

proc edram_project::configure_constraints {} {
  variable xdc_path

  ensure_project_open

  log "Adding board constraints: $xdc_path"
  remove_files_if_present [list $xdc_path]
  add_files -fileset constrs_1 -norecurse $xdc_path
  set xdc_file [get_files $xdc_path]
  set_property used_in_synthesis true $xdc_file
  set_property used_in_implementation true $xdc_file
  log "Configured constrs_1 XDC: $xdc_path"
}

proc edram_project::configure_simulation {} {
  variable sim_tb_path

  ensure_project_open

  log "Adding Vivado xsim smoke testbench: $sim_tb_path"
  remove_files_if_present [list $sim_tb_path]
  add_files -fileset sim_1 -norecurse $sim_tb_path
  set sim_tb_file [get_files $sim_tb_path]
  set_property file_type SystemVerilog $sim_tb_file
  set_property top edram_pl_board_top_vivado_tb [get_filesets sim_1]
  update_compile_order -fileset sim_1
  log "Configured sim_1 top: edram_pl_board_top_vivado_tb"
}

proc edram_project::run_simulation {} {
  ensure_project_open
  configure_simulation

  log "Launching Vivado behavioral simulation"
  set failed [catch {
    launch_simulation -simset sim_1 -mode behavioral
    run all
  } result]
  catch {close_sim}
  if {$failed} {
    fail "Simulation failed: $result"
  }
  log "Vivado simulation completed"
}

proc edram_project::check_run_completed {run_name stage_name} {
  set run_obj [get_runs $run_name]
  set progress [get_property PROGRESS $run_obj]
  set status [get_property STATUS $run_obj]

  if {[regexp -nocase {fail|error|cancel} $status]} {
    fail "$stage_name failed: $status"
  }
  if {$progress ne "100%"} {
    fail "$stage_name did not complete; progress=$progress status=$status"
  }

  log "$stage_name completed: $status"
}

proc edram_project::run_synthesis {} {
  variable jobs

  ensure_project_open

  log "Launching synth_1 with $jobs job(s)"
  catch {reset_run synth_1}
  launch_runs synth_1 -jobs $jobs
  wait_on_run synth_1
  check_run_completed synth_1 "Synthesis"
}

proc edram_project::run_implementation {include_bitstream} {
  variable jobs

  ensure_project_open

  catch {reset_run impl_1}
  if {$include_bitstream} {
    log "Launching impl_1 through write_bitstream with $jobs job(s)"
    launch_runs impl_1 -to_step write_bitstream -jobs $jobs
  } else {
    log "Launching impl_1 with $jobs job(s)"
    launch_runs impl_1 -jobs $jobs
  }

  wait_on_run impl_1
  if {$include_bitstream} {
    check_run_completed impl_1 "Implementation and bitstream generation"
  } else {
    check_run_completed impl_1 "Implementation"
  }
}

proc edram_project::locate_bitstream {} {
  variable project_dir
  variable project_name
  variable top

  ensure_project_open

  set candidates {}
  if {![catch {get_property DIRECTORY [get_runs impl_1]} run_dir] && $run_dir ne ""} {
    set candidates [concat $candidates [glob -nocomplain -directory $run_dir *.bit]]
  }

  set default_impl_dir [norm_join $project_dir "${project_name}.runs" impl_1]
  set candidates [concat $candidates [glob -nocomplain -directory $default_impl_dir *.bit]]

  set preferred [norm_join $default_impl_dir "${top}.bit"]
  if {[file exists $preferred]} {
    log "Generated bitstream: $preferred"
    return $preferred
  }

  if {[llength $candidates] == 0} {
    fail "Bitstream file was not found under impl_1"
  }

  set bit_path [file normalize [lindex [lsort -unique $candidates] 0]]
  log "Generated bitstream: $bit_path"
  return $bit_path
}

proc edram_project::print_configuration_summary {} {
  variable project_name
  variable part
  variable top
  variable default_library
  variable target_language
  variable project_dir
  variable stages
  variable recreate
  variable jobs

  log "Project: $project_name"
  log "Part: $part"
  log "Top: $top"
  log "Default library: $default_library"
  log "Configured target language: $target_language"
  log "Project directory: $project_dir"
  log "Recreate generated project: $recreate"
  log "Jobs: $jobs"
  log "Stages: $stages"
}

proc edram_project::run_flow {} {
  variable project_dir

  if {[stage_enabled project]} {
    prepare_project
  } elseif {[llength [lrange $::edram_project::stages 1 end]] > 0} {
    ensure_project_open
  }

  if {[stage_enabled sources]} {
    configure_sources
  }
  if {[stage_enabled constraints]} {
    configure_constraints
  }
  if {[stage_enabled simulate]} {
    run_simulation
  }
  if {[stage_enabled synth]} {
    run_synthesis
  }
  if {[stage_enabled impl] || [stage_enabled bitstream]} {
    run_implementation [stage_enabled bitstream]
  }
  if {[stage_enabled bitstream]} {
    locate_bitstream
  }

  log "Vivado project flow complete: $project_dir"
}

proc edram_project::run {} {
  variable validate_only

  init_paths
  load_project_config
  validate_required_files
  print_configuration_summary

  if {$validate_only} {
    log "Static Tcl/config/path validation complete; Vivado flow was not run"
    return
  }

  if {![in_vivado]} {
    fail "This script must run inside Vivado. For non-Vivado static checks, set EDRAM_VIVADO_VALIDATE_ONLY=1."
  }

  run_flow
}

set edram_project_auto_run [edram_project::to_bool [edram_project::get_option AUTO_RUN 1] AUTO_RUN]
if {$edram_project_auto_run} {
  edram_project::run
}
unset edram_project_auto_run
