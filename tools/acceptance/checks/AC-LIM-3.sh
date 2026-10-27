$GEN synth-entries 1048576 "$W/ok.chst" && expect_exit 0 $CHST verify "$W/ok.chst"
$GEN synth-entries 1048577 "$W/over.chst" && expect_exit 8 $CHST verify "$W/over.chst"
