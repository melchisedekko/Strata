set -u
cd /workspace/strata-policy/patchwork
for mode in plain san; do
  F="-std=c++20 -O1 -Iinclude"; [ $mode = san ] && F="$F -g -fsanitize=address,undefined -fno-sanitize-recover=all"
  for t in suffix_drafter_test controller_test draft_policy_test pool_source_test joint_gate_test spec_start_test; do
    if [ $t = spec_start_test ]; then SRC=src/spec/$t.cpp; else SRC="src/spec/$t.cpp src/spec/suffix_drafter.cpp src/spec/controller.cpp src/spec/draft_policy.cpp src/spec/draft_source.cpp src/spec/pool_source.cpp src/spec/joint_gate.cpp"; fi
    nice -n 19 /workspace/strata-policy/.venv/lib/python3.13/site-packages/ziglang/zig c++ $F $SRC -o /tmp/jg/fin/${t}_$mode 2>/tmp/jg/fin/${t}_$mode.build || { echo "$mode $t BUILD FAIL"; continue; }
    /tmp/jg/fin/${t}_$mode > /tmp/jg/fin/${t}_$mode.log 2>&1; rc=$?
    echo "$mode $t rc=$rc last=$(tail -1 /tmp/jg/fin/${t}_$mode.log) asan_syms=$(nm /tmp/jg/fin/${t}_$mode 2>/dev/null | grep -c __asan_report)"
  done
done
