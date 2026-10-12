import_device ph1_35p.db -package PH1P35MDG324 -speed 3
open_project camera_to_dsi_display.prj -noanalyze
puts "=========== HELP ROUTE ==========="
catch {help route} msg ; puts $msg
puts "=========== HELP PLACE ==========="
catch {help place} msg ; puts $msg
puts "=========== HELP OPT_ROUTE ==========="
catch {help opt_route} msg ; puts $msg
puts "=========== HELP SET_PARAM ==========="
catch {help set_param} msg ; puts $msg
puts "=========== PARAM ROUTE ==========="
catch {report_param -step route} msg ; puts $msg
puts "=========== PARAM PLACE ==========="
catch {report_param -step place} msg ; puts $msg
puts "=========== PROBE DONE ==========="
