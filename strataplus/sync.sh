#!/usr/bin/env bash
# Strata+ research backup -> fork PUBBLICO melchisedekko/Strata, SOLO branch `strataplus-research`.
# Idempotente: ricopia le sorgenti inventariate, rigenera manifest/patch/bundle, scansiona segreti,
# committa solo se ci sono cambiamenti e fa push di strataplus-research, strataplus-policy-local e strataplus-pt12-measure.
# Il token viene letto SOLO da $GITHUB_TOKEN a runtime (mai scritto su file, config o URL).
# Uso:   bash /workspace/strataplus-backup/sync.sh          (NOPUSH=1 per non fare push)
set -euo pipefail
set +x
umask 022
export LC_ALL=C

REPO=/workspace/strataplus-backup
BR=strataplus-research
BASE=7dd5cf18e68c639a8773e096c5c79f971ea2a9f5          # upstream Niko1221/Strata main usato dal team
REMOTE_URL=https://github.com/melchisedekko/Strata.git
D=$REPO/strataplus
MAXSIZE=50M
SRC_GIT=/workspace/strata-src
BRANCHES=(strataplus-policy-local strataplus-pt12-measure)
NOPUSH=${NOPUSH:-0}
RUNLOG=$REPO/.sync_runs.log          # escluso dal repo (.git/info/exclude)
GITLEAKS=$(command -v gitleaks || echo /home/box/.local/bin/gitleaks)
ALLOW=$D/SECRET_SCAN_ALLOWLIST.txt   # "sha256  path" di falsi positivi verificati a mano
SELF=sync.sh                         # questo script (contiene le regex di scansione): non scansionato
T0=$(date '+%Y-%m-%d %H:%M:%S')

cd "$REPO"
[ "$(git rev-parse --abbrev-ref HEAD)" = "$BR" ] || { echo "ERRORE: $REPO non e' sul branch $BR" >&2; exit 1; }
command -v rsync >/dev/null || { echo "ERRORE: rsync mancante" >&2; exit 1; }

EXC=(--exclude='.venv/' --exclude='venv/' --exclude='__pycache__/' --exclude='*.pyc' --exclude='.cache/'
     --exclude='*.gguf' --exclude='*.safetensors' --exclude='*.bin' --exclude='*.pt' --exclude='*.pth'
     --exclude='*.o' --exclude='*.so' --exclude='*.a' --exclude='build/' --exclude='build-*/' --exclude='.git/'
     --exclude='node_modules/' --exclude='*.whl')

# ---- esclusioni per licenza (LICENSE_INVENTORY.md sha256 2e160c96f86ca192a52a4935fa6c609e854137ccd9b08452d7eac91acfd1dc11, 2026-10-26) ----
# Stessa lista di strataplus/.gitignore. Percorsi relativi a strataplus/; m() li traduce in exclude rsync ancorati
# alla sorgente della cartella di destinazione. Con m 1 (--delete-excluded) eventuali copie vengono anche cancellate.
LIC_LIST=$(cat <<'LICEOF'
bench/e1/policy/results/e1_per_request.csv
bench/strata-bench/datasets/subset_ids.json
bench/traces/raw/v11_holdout/
logs/tmp_scratch/annt/
logs/tmp_scratch/cv12t/
logs/tmp_scratch/v11p/
policy/strata-policy/replay/results/v2/split_c/
bench/strata-bench/datasets/agent_turns_bench.jsonl
bench/strata-bench/datasets/edit_np.jsonl
bench/strata-bench/datasets/check_v12.jsonl
bench/strata-bench/datasets/check_v12_ids.json
bench/strata-bench/datasets/diag_prompts.jsonl
bench/strata-bench/datasets/diag_ref.tsv
bench/strata-bench/datasets/holdout_90.jsonl
bench/strata-bench/datasets/holdout_ids.json
bench/strata-bench/datasets/p4_prompts.jsonl
bench/strata-bench/datasets/proxy_30.jsonl
bench/strata-bench/datasets/sessions_all.jsonl
bench/strata-bench/smoke/p2.jsonl
bench/strata-bench/smoke/s2.requests.jsonl
bench/strata-bench/smoke/s2.rounds.jsonl
bench/strata-bench/smoke_mtp/e_base_mtp.err
bench/strata-bench/smoke_mtp/e_base_mtp.jsonl
bench/strata-bench/smoke_mtp/e_live_combo.err
bench/strata-bench/smoke_mtp/e_live_combo.jsonl
bench/strata-bench/smoke_mtp/e_live_lookup.err
bench/strata-bench/smoke_mtp/e_live_lookup.jsonl
bench/strata-bench/smoke_mtp/e_live_mtp.err
bench/strata-bench/smoke_mtp/e_live_mtp.jsonl
bench/strata-bench/smoke_mtp/p4.err
bench/strata-bench/smoke_mtp/p4.jsonl
bench/traces/CRITICAL.md
bench/traces/GREEDY_DIAG.md
bench/traces/SUMMARY.md
bench/traces/base_r0.jsonl
bench/traces/base_r1.jsonl
bench/traces/base_r2.jsonl
bench/traces/check_v12/check_v12.jsonl
bench/traces/check_v12/check_v12_divergence.json
bench/traces/check_v12/check_v12_ids.json
bench/traces/check_v12/check_v12_licenses.json
bench/traces/check_v12/check_v12_live_combo.jsonl
bench/traces/check_v12/check_v12_live_lookup.jsonl
bench/traces/check_v12/check_v12_live_mtp_k3.jsonl
bench/traces/check_v12/check_v12_tf_d7.jsonl
bench/traces/check_v12_eos_clamped_recalc.json
bench/traces/docs_prev/GREEDY_DIAG.md.pre_0738
bench/traces/docs_prev/GREEDY_DIAG.md.pre_0810
bench/traces/docs_prev/SUMMARY.md.pre_0738
bench/traces/greedy_diag.json
bench/traces/holdout_lookup_v12/holdout_90.jsonl
bench/traces/holdout_lookup_v12/holdout_lookup_v12_n12.jsonl
bench/traces/holdout_lookup_v12/holdout_lookup_v12_n16.jsonl
bench/traces/holdout_lookup_v12/holdout_lookup_v12_n7.jsonl
bench/traces/holdout_lookup_v12/holdout_lookup_v12_summary.json
bench/traces/holdout_lookup_v12/ref_holdout_tf.tsv
bench/traces/holdout_lookup_v12_ERRATA.md
bench/traces/live_combo_k3_r0.jsonl
bench/traces/live_combo_k3_r1.jsonl
bench/traces/live_combo_k3_r2.jsonl
bench/traces/live_lookup_r0.jsonl
bench/traces/live_lookup_r1.jsonl
bench/traces/live_lookup_r2.jsonl
bench/traces/live_mtp_k1_r0.jsonl
bench/traces/live_mtp_k2_r0.jsonl
bench/traces/live_mtp_k3_r0.jsonl
bench/traces/live_mtp_k3_r1.jsonl
bench/traces/live_mtp_k3_r2.jsonl
bench/traces/live_mtp_k5_r0.jsonl
bench/traces/live_mtp_k7_r0.jsonl
bench/traces/raw/base_r0.err
bench/traces/raw/base_r0.jsonl
bench/traces/raw/base_r1.err
bench/traces/raw/base_r1.jsonl
bench/traces/raw/base_r2.err
bench/traces/raw/base_r2.jsonl
bench/traces/raw/check_v12/check_v12_live_combo.err
bench/traces/raw/check_v12/check_v12_live_combo.jsonl
bench/traces/raw/check_v12/check_v12_live_lookup.err
bench/traces/raw/check_v12/check_v12_live_lookup.jsonl
bench/traces/raw/check_v12/check_v12_live_mtp_k3.err
bench/traces/raw/check_v12/check_v12_live_mtp_k3.jsonl
bench/traces/raw/check_v12/check_v12_tf_d7.err
bench/traces/raw/check_v12/check_v12_tf_d7.jsonl
bench/traces/raw/check_v12/ref_tf.tsv
bench/traces/raw/diag_yright.err
bench/traces/raw/diag_yright.jsonl
bench/traces/raw/diag_ywrong.err
bench/traces/raw/diag_ywrong.jsonl
bench/traces/raw/holdout_lookup_v12/holdout_lookup_v12_n12.err
bench/traces/raw/holdout_lookup_v12/holdout_lookup_v12_n12.jsonl
bench/traces/raw/holdout_lookup_v12/holdout_lookup_v12_n16.err
bench/traces/raw/holdout_lookup_v12/holdout_lookup_v12_n16.jsonl
bench/traces/raw/holdout_lookup_v12/holdout_lookup_v12_n7.err
bench/traces/raw/holdout_lookup_v12/holdout_lookup_v12_n7.jsonl
bench/traces/raw/holdout_lookup_v12/ref_holdout_tf.tsv
bench/traces/raw/live_combo_k3_r0.err
bench/traces/raw/live_combo_k3_r0.jsonl
bench/traces/raw/live_combo_k3_r1.err
bench/traces/raw/live_combo_k3_r1.jsonl
bench/traces/raw/live_combo_k3_r2.err
bench/traces/raw/live_combo_k3_r2.jsonl
bench/traces/raw/live_lookup_r0.err
bench/traces/raw/live_lookup_r0.jsonl
bench/traces/raw/live_lookup_r1.err
bench/traces/raw/live_lookup_r1.jsonl
bench/traces/raw/live_lookup_r2.err
bench/traces/raw/live_lookup_r2.jsonl
bench/traces/raw/live_mtp_k1_r0.err
bench/traces/raw/live_mtp_k1_r0.jsonl
bench/traces/raw/live_mtp_k2_r0.err
bench/traces/raw/live_mtp_k2_r0.jsonl
bench/traces/raw/live_mtp_k3_r0.err
bench/traces/raw/live_mtp_k3_r0.jsonl
bench/traces/raw/live_mtp_k3_r1.err
bench/traces/raw/live_mtp_k3_r1.jsonl
bench/traces/raw/live_mtp_k3_r2.err
bench/traces/raw/live_mtp_k3_r2.jsonl
bench/traces/raw/live_mtp_k5_r0.err
bench/traces/raw/live_mtp_k5_r0.jsonl
bench/traces/raw/live_mtp_k7_r0.err
bench/traces/raw/live_mtp_k7_r0.jsonl
bench/traces/raw/p4_08b_q4km.err
bench/traces/raw/p4_08b_q4km.jsonl
bench/traces/raw/p4_08b_q8.err
bench/traces/raw/p4_08b_q8.jsonl
bench/traces/raw/p4_2b_q4km.err
bench/traces/raw/p4_2b_q4km.jsonl
bench/traces/raw/tf_d7.err
bench/traces/raw/tf_d7.jsonl
bench/traces/raw/v11/abl_llamafile_off_base.err
bench/traces/raw/v11/abl_llamafile_off_base.jsonl
bench/traces/raw/v11/abl_llamafile_off_ref.tsv
bench/traces/raw/v11/abl_llamafile_off_ywrong_T2.err
bench/traces/raw/v11/abl_llamafile_off_ywrong_T2.jsonl
bench/traces/raw/v11/abl_llamafile_on_base.err
bench/traces/raw/v11/abl_llamafile_on_base.jsonl
bench/traces/raw/v11/abl_llamafile_on_ref.tsv
bench/traces/raw/v11/abl_llamafile_on_ywrong_T2.err
bench/traces/raw/v11/abl_llamafile_on_ywrong_T2.jsonl
bench/traces/raw/v11/agent_turns_bench_base.err
bench/traces/raw/v11/agent_turns_bench_base.jsonl
bench/traces/raw/v11/agent_turns_bench_live_combo.err
bench/traces/raw/v11/agent_turns_bench_live_combo.jsonl
bench/traces/raw/v11/agent_turns_bench_live_lookup.err
bench/traces/raw/v11/agent_turns_bench_live_lookup.jsonl
bench/traces/raw/v11/agent_turns_bench_live_mtp_k3.err
bench/traces/raw/v11/agent_turns_bench_live_mtp_k3.jsonl
bench/traces/raw/v11/agent_turns_bench_tf_d7.err
bench/traces/raw/v11/agent_turns_bench_tf_d7.jsonl
bench/traces/raw/v11/base_p30.err
bench/traces/raw/v11/base_p30.jsonl
bench/traces/raw/v11/campaign.log
bench/traces/raw/v11/diag_yright_T2.err
bench/traces/raw/v11/diag_yright_T2.jsonl
bench/traces/raw/v11/diag_yright_T4.err
bench/traces/raw/v11/diag_yright_T4.jsonl
bench/traces/raw/v11/diag_yright_T8.err
bench/traces/raw/v11/diag_yright_T8.jsonl
bench/traces/raw/v11/diag_ywrong_T2.err
bench/traces/raw/v11/diag_ywrong_T2.jsonl
bench/traces/raw/v11/diag_ywrong_T4.err
bench/traces/raw/v11/diag_ywrong_T4.jsonl
bench/traces/raw/v11/diag_ywrong_T8.err
bench/traces/raw/v11/diag_ywrong_T8.jsonl
bench/traces/raw/v11/divergence_tune_p30.json
bench/traces/raw/v11/knee/invalid/knee_q4km_ctrl_ub256.err
bench/traces/raw/v11/knee/invalid/knee_q4km_ctrl_ub256.jsonl
bench/traces/raw/v11/knee/invalid/knee_q4km_llamafile_off_b7.err
bench/traces/raw/v11/knee/invalid/knee_q4km_llamafile_off_b7.jsonl
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b4.err
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b4.jsonl
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b4_a1.err
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b4_a1.jsonl
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b4_a2.err
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b4_a2.jsonl
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b4_a3.err
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b4_a3.jsonl
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b5.err
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b5.jsonl
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b5_a1.err
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b5_a1.jsonl
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b5_a2.err
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b5_a2.jsonl
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b5_a3.err
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b5_a3.jsonl
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b8.err
bench/traces/raw/v11/knee/invalid/knee_q4km_main_b8.jsonl
bench/traces/raw/v11/knee/knee_q4km_ctrl_t8.err
bench/traces/raw/v11/knee/knee_q4km_ctrl_t8.jsonl
bench/traces/raw/v11/knee/knee_q4km_ctrl_ub256.err
bench/traces/raw/v11/knee/knee_q4km_ctrl_ub256.jsonl
bench/traces/raw/v11/knee/knee_q4km_llamafile_off_b2.err
bench/traces/raw/v11/knee/knee_q4km_llamafile_off_b2.jsonl
bench/traces/raw/v11/knee/knee_q4km_llamafile_off_b3.err
bench/traces/raw/v11/knee/knee_q4km_llamafile_off_b3.jsonl
bench/traces/raw/v11/knee/knee_q4km_llamafile_off_b6.err
bench/traces/raw/v11/knee/knee_q4km_llamafile_off_b6.jsonl
bench/traces/raw/v11/knee/knee_q4km_llamafile_off_b7.err
bench/traces/raw/v11/knee/knee_q4km_llamafile_off_b7.jsonl
bench/traces/raw/v11/knee/knee_q4km_main_b1.err
bench/traces/raw/v11/knee/knee_q4km_main_b1.jsonl
bench/traces/raw/v11/knee/knee_q4km_main_b4.err
bench/traces/raw/v11/knee/knee_q4km_main_b4.jsonl
bench/traces/raw/v11/knee/knee_q4km_main_b5.err
bench/traces/raw/v11/knee/knee_q4km_main_b5.jsonl
bench/traces/raw/v11/knee/knee_q4km_main_b8.err
bench/traces/raw/v11/knee/knee_q4km_main_b8.jsonl
bench/traces/raw/v11/knee/knee_q8_ctrl_t8.err
bench/traces/raw/v11/knee/knee_q8_ctrl_t8.jsonl
bench/traces/raw/v11/knee/knee_q8_ctrl_ub256.err
bench/traces/raw/v11/knee/knee_q8_ctrl_ub256.jsonl
bench/traces/raw/v11/knee/knee_q8_llamafile_off_b2.err
bench/traces/raw/v11/knee/knee_q8_llamafile_off_b2.jsonl
bench/traces/raw/v11/knee/knee_q8_llamafile_off_b3.err
bench/traces/raw/v11/knee/knee_q8_llamafile_off_b3.jsonl
bench/traces/raw/v11/knee/knee_q8_llamafile_off_b6.err
bench/traces/raw/v11/knee/knee_q8_llamafile_off_b6.jsonl
bench/traces/raw/v11/knee/knee_q8_llamafile_off_b7.err
bench/traces/raw/v11/knee/knee_q8_llamafile_off_b7.jsonl
bench/traces/raw/v11/knee/knee_q8_main_b1.err
bench/traces/raw/v11/knee/knee_q8_main_b1.jsonl
bench/traces/raw/v11/knee/knee_q8_main_b4.err
bench/traces/raw/v11/knee/knee_q8_main_b4.jsonl
bench/traces/raw/v11/knee/knee_q8_main_b5.err
bench/traces/raw/v11/knee/knee_q8_main_b5.jsonl
bench/traces/raw/v11/knee/knee_q8_main_b8.err
bench/traces/raw/v11/knee/knee_q8_main_b8.jsonl
bench/traces/raw/v11/live_combo_p30.err
bench/traces/raw/v11/live_combo_p30.jsonl
bench/traces/raw/v11/live_lookup_p30.err
bench/traces/raw/v11/live_lookup_p30.jsonl
bench/traces/raw/v11/live_mtp_k3_p30.err
bench/traces/raw/v11/live_mtp_k3_p30.jsonl
bench/traces/raw/v11/p4_2b_q4km.err
bench/traces/raw/v11/p4_2b_q4km.jsonl
bench/traces/raw/v11/p4_2b_q4km_r2.err
bench/traces/raw/v11/p4_2b_q4km_r2.jsonl
bench/traces/raw/v11/p4_2b_q8.err
bench/traces/raw/v11/p4_2b_q8.jsonl
bench/traces/raw/v11/ref_base.tsv
bench/traces/raw/v11/tf_d7_p30.err
bench/traces/raw/v11/tf_d7_p30.jsonl
bench/traces/summary.json
bench/traces/tf_d7.jsonl
bench/traces/v1.1/agent_turns_bench_base.jsonl
bench/traces/v1.1/agent_turns_bench_live_combo.jsonl
bench/traces/v1.1/agent_turns_bench_live_lookup.jsonl
bench/traces/v1.1/agent_turns_bench_live_mtp_k3.jsonl
bench/traces/v1.1/agent_turns_bench_tf_d7.jsonl
bench/traces/v1.1/base_p30.jsonl
bench/traces/v1.1/diag_yright_T2.jsonl
bench/traces/v1.1/diag_yright_T4.jsonl
bench/traces/v1.1/diag_yright_T8.jsonl
bench/traces/v1.1/diag_ywrong_T2.jsonl
bench/traces/v1.1/diag_ywrong_T4.jsonl
bench/traces/v1.1/diag_ywrong_T8.jsonl
bench/traces/v1.1/holdout_edit_tf_d7.jsonl
bench/traces/v1.1/live_combo_p30.jsonl
bench/traces/v1.1/live_lookup_p30.jsonl
bench/traces/v1.1/live_mtp_k3_p30.jsonl
bench/traces/v1.1/tf_d7_p30.jsonl
logs/tmp_scratch/div_p30.json
logs/tmp_scratch/div_test.json
logs/tmp_scratch/jg/split_h_decay.json
logs/tmp_scratch/jg/split_h_prefix.json
logs/tmp_scratch/lic_test.json
logs/tmp_scratch/smk/live.err
logs/tmp_scratch/smk/live.jsonl
logs/tmp_scratch/smk/p.jsonl
logs/tmp_scratch/sum.txt
policy/strata-policy/replay/frozen_params.json
policy/strata-policy/replay/frozen_params_v2.json
policy/strata-policy/replay/frozen_params_v3_PREPARED_NOT_FROZEN.json
policy/strata-policy/replay/results/v2/_obsolete_decay/split_h_decay.json
policy/strata-policy/replay/results/v2/lookup_only_replay/lookup_only_replay.json
policy/strata-policy/replay/results/v2/lookup_prefix_replay/REPORT.md
policy/strata-policy/replay/results/v2/lookup_prefix_replay/diag_stdout.txt
policy/strata-policy/replay/results/v2/lookup_prefix_replay/lookup_prefix_diag.json
policy/strata-policy/replay/results/v2/lookup_prefix_replay/lookup_prefix_replay.json
policy/strata-policy/replay/results/v2/split_h/split_h.json
logs/tmp_scratch/gen/
policy/strata-policy/replay/run_hca.json
bench/traces/mtp_cap_prefix_check.json
bench/strata-bench/runs/live_combo_aprime_holdout.md
logs/tmp_scratch/mcp_test.json
logs/tmp_scratch/order.txt
logs/tmp_scratch/c0.json
logs/tmp_scratch/c1.json
logs/tmp_scratch/hfcards/
LICEOF
)
# pattern generici (anche per file futuri): edit_np e artefatti H-CA/classificatore; il codice *.py resta
# dati GREZZI di terzi (regola del 2026-10-26 20:05 CET, LICENSE_INVENTORY.md sez. 7): mai sul fork
RAW_EXC=(--exclude='*.[pP][aA][rR][qQ][uU][eE][tT]' --exclude='*.[aA][rR][rR][oO][wW]' --exclude='[tT][oO][kK][eE][nN][iI][zZ][eE][rR]*.json'
  --exclude='*[hH][fF][-_][cC][aA][rR][dD]*' --exclude='[nN][fF][eE]_*.jsonl'
  --exclude='*[nN][oO][fF][uU][nN][eE][vV][aA][lL]*')
# cartelle di download dei dataset in bench/strata-bench/datasets/*/: solo note/hash/log del team (dopo LIC_EXC)
DS_ALLOW=(--include='/datasets/*/LICENSE_NOTE*.md' --include='/datasets/*/SHA256SUMS' --include='/datasets/*/*.sha256' --include='/datasets/*/*.log'
  --exclude='/datasets/*/**')
LIC_EXC=(--exclude='*[cC][aA][nN][iI][tT][eE][dD][iI][tT]*' --exclude='*[cC][aA][nN]_[iI][tT]_[eE][dD][iI][tT]*'
         --include='/replay/results/v2/hca/hca_results.json' --include='/replay/results/v2/hca/REPORT.md' --exclude='/replay/results/v2/hca/*'
         --exclude='*[hH][cC][aA]*.npz' --exclude='*[hH][cC][aA]*.npy' --exclude='*[hH][cC][aA]*.pkl' --exclude='*[hH][cC][aA]*.joblib'
         --exclude='*[hH][cC][aA]*.pt' --exclude='*[hH][cC][aA]*.safetensors' --exclude='*[hH][cC][aA]*fitted*'
         --exclude='*[hH][-_][cC][aA]*.npz' --exclude='*[hH][-_][cC][aA]*.npy' --exclude='*[hH][-_][cC][aA]*.pkl' --exclude='*[hH][-_][cC][aA]*.joblib' --exclude='*[hH][-_][cC][aA]*.pt' --exclude='*[hH][-_][cC][aA]*.safetensors' --exclude='*[hH][-_][cC][aA]*fitted*'
         --include='*[cC][lL][aA][sS][sS][iI][fF][iI][eE][rR]*.py' --exclude='*[cC][lL][aA][sS][sS][iI][fF][iI][eE][rR]*.*')
# solo per logs/tmp_scratch (da /tmp): smoke/probe H-CA esclusi, il codice resta
LIC_EXC_TMP=(--include='*[hH][cC][aA]*.py' --include='*[hH][-_][cC][aA]*.py' --exclude='*[hH][cC][aA]*' --exclude='*[hH][-_][cC][aA]*')

TMPD=$(mktemp -d); trap 'rm -rf "$TMPD"' EXIT
: > "$TMPD/large.txt"

# m <delete:0|1> <dest-subdir> <src...> [-- rsync-extra-args...]
m() {
  local del=$1 dest=$2; shift 2
  local srcs=() extra=()
  while [ $# -gt 0 ] && [ "$1" != "--" ]; do [ -e "$1" ] && srcs+=("$1"); shift; done
  [ "${1:-}" = "--" ] && { shift; extra=("$@"); }
  [ ${#srcs[@]} -eq 0 ] && return 0
  mkdir -p "$D/$dest"
  local dflags=(); [ "$del" = 1 ] && dflags=(--delete --delete-excluded)
  local lic=() e
  while IFS= read -r e; do [ -n "$e" ] && [ "${e#"$dest"/}" != "$e" ] && lic+=(--exclude="/${e#"$dest"/}"); done <<< "$LIC_LIST"
  [ "$dest" = logs/tmp_scratch ] && lic+=("${LIC_EXC_TMP[@]}")
  lic+=("${RAW_EXC[@]}" "${LIC_EXC[@]}")
  [ "$dest" = bench/strata-bench ] && lic+=("${DS_ALLOW[@]}")
  rsync -a "${dflags[@]}" --max-size=$MAXSIZE "${EXC[@]}" "${lic[@]}" "${extra[@]}" "${srcs[@]}" "$D/$dest/"
  # file oltre il limite: solo elenco (path, size, sha256)
  rsync -a -n --min-size=$MAXSIZE --out-format='%n' "${EXC[@]}" "${lic[@]}" "${extra[@]}" "${srcs[@]}" "$D/$dest/" 2>/dev/null \
    | grep -v '/$' | while read -r rel; do
        for s in "${srcs[@]}"; do
          local cand
          if [ -d "$s" ]; then cand="${s%/}/$rel"; [ "${s: -1}" = "/" ] || cand="$(dirname "$s")/$rel"; else cand="$(dirname "$s")/$rel"; fi
          if [ -f "$cand" ]; then printf '%s\t%s\t%s\n' "$cand" "$(stat -c %s "$cand")" "$(sha256sum "$cand" | cut -d' ' -f1)" >> "$TMPD/large.txt"; break; fi
        done
      done || true
  return 0
}

# ---- plan ----
m 0 plan /workspace/strata-plus/piano.md /workspace/strata-plus/log_format.md
# (plan/PLAN_PAGE.md = export manuale della Page, non toccato dallo script)

# ---- policy ----
m 1 policy/strata-policy /workspace/strata-policy/ -- --exclude='/patchwork/' --exclude='/pt12_worktree/' --exclude='/patches/'

# ---- scout ----
m 0 scout/strata-plus /workspace/strata-plus/scout.md /workspace/strata-plus/scout_greedy_rho.md /workspace/strata-plus/scout_patch_support.md
m 1 scout/scout /workspace/scout/ -- --exclude='/Strata/' --exclude='/llama.cpp/' --exclude='/colibri/' --exclude='/HIP-CPU/' \
     --exclude='/arctic/' --exclude='/sglang/' --exclude='/vllm/'
m 0 scout/refs /workspace/issues1.txt /workspace/prs.txt /workspace/q2b_index.json /workspace/ggufhdr.py

# ---- bench ----
m 1 bench/strata-bench /workspace/strata-bench/ -- --exclude='/models/' --exclude='/logs/' --exclude='/patches/' \
     --exclude='/build-strata-cpu/' --exclude='/proxy/llama_spec_trace' --exclude='/proxy/llama_spec_trace.new' \
     --exclude='/datasets/specbench.jsonl'
m 1 bench/traces /workspace/strata-plus/traces/
m 1 bench/e1 /workspace/strata-plus/e1/ -- --exclude='/policy/data/'

# ---- logs ----
m 1 logs/strata-bench /workspace/strata-bench/logs/
m 0 logs/cpu_busy /workspace/strata-plus/cpu_busy_*.log /workspace/cpu_busy_*.log
# scratch volatile in /tmp (whitelist; senza --delete per non perdere nulla se /tmp viene svuotato)
m 0 logs/tmp_scratch /tmp/ -- --exclude='/sand-*' --exclude='/gl*.json' --exclude='/g1.json' --exclude='/jg/apply/' --exclude='/jg/apply6/' \
     --include='/annt/***' --include='/av12/***' --include='/cv12t/***' --include='/gen/***' --include='/s10/***' \
     --include='/smk/***' --include='/v11p/***' --include='/jg/***' \
     --include='/*.py' --include='/*.md' --include='/*.json' --include='/*.jsonl' --include='/*.txt' --include='/*.diff' \
     --include='/*.cu' --include='/*.cpp' --include='/*.jinja' --include='/*.bak*' --include='/*.err' --include='/*.out' \
     --include='/tf_p4.log' --exclude='*'

# ---- patches ----
m 1 patches/strata-policy /workspace/strata-policy/patches/
m 1 patches/bench /workspace/strata-bench/patches/
for b in "${BRANCHES[@]}"; do
  out=$D/patches/branches/$b
  head=$(git -C "$SRC_GIT" rev-parse -q --verify "refs/heads/$b" || true)
  [ -z "$head" ] && { echo "AVVISO: branch $b non trovato in $SRC_GIT, conservo la copia esistente"; continue; }
  if [ "$(cat "$out/HEAD" 2>/dev/null)" != "$head" ]; then
    rm -rf "$out"; mkdir -p "$out/format-patch"
    git -C "$SRC_GIT" format-patch -q --zero-commit -o "$out/format-patch" "$BASE..$head"
    git -C "$SRC_GIT" bundle create -q "$out/$b.bundle" "$BASE..refs/heads/$b"
    if [ "$(stat -c %s "$out/$b.bundle")" -gt 52428800 ]; then
      printf '%s\t%s\t%s\n' "(bundle) $b.bundle" "$(stat -c %s "$out/$b.bundle")" "$(sha256sum "$out/$b.bundle" | cut -d' ' -f1)" >> "$TMPD/large.txt"
      rm -f "$out/$b.bundle"
    fi
    git -C "$SRC_GIT" log --format='%H %ad %an%n    %s' --date=iso "$BASE..$head" > "$out/LOG.txt"
    echo "$head" > "$out/HEAD"
  fi
done
mkdir -p "$D/patches/llama.cpp"
if [ -d /workspace/llama.cpp/.git ]; then
  { echo "# llama.cpp working tree diff (non committato) su $(git -C /workspace/llama.cpp rev-parse HEAD)"; \
    git -C /workspace/llama.cpp diff; } > "$TMPD/llama.diff"
  cmp -s "$TMPD/llama.diff" "$D/patches/llama.cpp/worktree_uncommitted.diff" || cp "$TMPD/llama.diff" "$D/patches/llama.cpp/worktree_uncommitted.diff"
fi

# ---- rimozione binari ELF (output di build) ----
python3 - "$D" "$TMPD/elf.txt" <<'PY'
import os,sys
root,outp=sys.argv[1],sys.argv[2]; out=[]
for dp,dn,fn in os.walk(root):
    for f in fn:
        p=os.path.join(dp,f)
        if os.path.islink(p): continue
        try:
            with open(p,'rb') as h:
                if h.read(4)==b'\x7fELF': out.append(os.path.relpath(p,root)); os.remove(p)
        except OSError: pass
open(outp,'w').write(''.join(sorted(x+'\n' for x in out)))
PY

# ---- controllo licenze: niente che strataplus/.gitignore escluda (git add -f lo aggiungerebbe comunque) ----
: > "$TMPD/lic.txt"
if [ -f "$D/.gitignore" ]; then
  LICG=$(mktemp -d -p "$TMPD"); git init -q "$LICG"; mkdir -p "$LICG/strataplus"; cp "$D/.gitignore" "$LICG/strataplus/.gitignore"
  ( cd "$D" && find . -type f ! -name .gitignore -printf 'strataplus/%P\n' ) \
    | git -C "$LICG" check-ignore --no-index --stdin > "$TMPD/lic.txt" || true
  # controllo sul contenuto: qualsiasi file (anche nuovo, con nome qualsiasi) che contiene ID edit_np resta fuori
  grep -rlIiE 'edit_np[-_][0-9]+' "$D" 2>/dev/null | sed "s|^$D/|strataplus/|" >> "$TMPD/lic.txt" || true
  # quarantena (2026-10-26): file di dati NUOVI (non in HEAD) sotto datasets/, *.jsonl di tmp_scratch, parquet/arrow ovunque:
  # restano fuori finche' qualcuno non li rivede e ne mette lo sha256 in REVIEWED (sotto). I file gia' tracciati passano.
  REVIEWED=$(cat <<'REVEOF'
18288525fff122efc9790efbeadcbf810ae5c650149833ea5cb8a141efdba84e  bench/strata-bench/datasets/holdout_90_codechat.jsonl
89c28ff8fc0a74d20074c83226f4637955235f43dbf52caa73c9153d79724684  bench/strata-bench/datasets/proxy_30_codechat.jsonl
ea8e2f340aecd87511fd0de5627f74975bb772024aa0b65535ab14fa4d1869c0  bench/strata-bench/datasets/commitpackft_selection_manifest.csv
584a98a9e12aa762b2b8a4d4cfa3313fb4df4a3169e7d89d2bcc6d43ef5fd20d  bench/strata-bench/datasets/commitpackft_selection_counts.json
77247b1da5c174548fc5ef6ef9227d22ebbedfe1a66ecbd3c5bc3e806bf3d7c1  bench/strata-bench/datasets/commitpackft_fc56fe33/raw_files.sha256
9789d77fcf5c6ac140936905105d3db74e2845a66aeddf4e3583f227d12ef90a  bench/strata-bench/datasets/commitpackft_fc56fe33/select_run.log
a6ceeb5a076d7f3c1e93134566e926121c4cfb4ee998caed27932417a883e2e2  bench/strata-bench/datasets/humanevalfix_9a41762f/LICENSE_NOTE.md
3341a36cd081b49247dc60691025f548bf120f6dbb9b54122a0688c377f8d0b7  bench/strata-bench/datasets/humanevalfix_9a41762f/SHA256SUMS
7949ed6b9e5b22d7ad6b8397f409a4b66b43c83b4d4de3760a9a1653c6c83145  logs/tmp_scratch/a.jsonl
5a26280967ad5b7652f2baa320a8b6f5cf722ea030444e69a72f25922d03491f  bench/strata-bench/datasets/commitpackft_fc56fe33/selected_files.sha256
7bb6353c855cba4ee9cb77c75e3070395c2c28d4e7d2e7b99f96cb700fc26ee2  bench/strata-bench/datasets/commitpackft_selection.sha256
5e6f30651d22cfd5214ffda2d824db02d83dcf7033931dd3315480b80634c777  bench/strata-bench/datasets/commitpackft_selection_README.md
REVEOF
)
  : > "$TMPD/quar.txt"
  ( cd "$D" && { find bench/strata-bench/datasets -type f 2>/dev/null; find logs/tmp_scratch -maxdepth 1 -type f -name '*.jsonl' 2>/dev/null
      find . -type f \( -iname '*.parquet' -o -iname '*.arrow' \) -printf '%P\n'; } | sort -u ) | while IFS= read -r p; do
    grep -qxF "strataplus/$p" "$TMPD/lic.txt" && continue
    git -C "$REPO" cat-file -e "HEAD:strataplus/$p" 2>/dev/null && continue
    printf '%s\n' "$REVIEWED" | grep -qxF "$(sha256sum "$D/$p" | cut -d' ' -f1)  $p" && continue
    echo "strataplus/$p"
  done > "$TMPD/quar.txt"
  [ -s "$TMPD/quar.txt" ] && echo "AVVISO: $(wc -l < "$TMPD/quar.txt") file di dati nuovi in quarantena (non pubblicati, da revisionare)"
  cat "$TMPD/quar.txt" >> "$TMPD/lic.txt"
  sort -u -o "$TMPD/lic.txt" "$TMPD/lic.txt"
  while read -r f; do [ -n "$f" ] && rm -f "$REPO/$f"; done < "$TMPD/lic.txt"
  [ -s "$TMPD/lic.txt" ] && echo "AVVISO: $(wc -l < "$TMPD/lic.txt") file esclusi per licenza rimossi dalla copia (non pubblicati)"
else
  echo "ERRORE: $D/.gitignore mancante (esclusioni per licenza)" >&2; exit 4
fi

# ---- scansione segreti (repo PUBBLICO): file sospetti rimossi dallo staging ----
: > "$TMPD/hits.txt"
RX='(ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,}|ghs_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|hf_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[abprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{32,}|aws_secret_access_key|AIza[0-9A-Za-z_-]{35})'
grep -rlE -I "$RX" "$D" 2>/dev/null | sed "s|^$D/||" >> "$TMPD/hits.txt" || true
# il token reale non deve mai comparire (anche se allowlisted)
: > "$TMPD/tok.txt"
if [ -n "${GITHUB_TOKEN:-}" ]; then grep -rlF -- "$GITHUB_TOKEN" "$D" 2>/dev/null | sed "s|^$D/||" > "$TMPD/tok.txt" || true; fi
if [ -x "$GITLEAKS" ]; then
  "$GITLEAKS" dir "$D" --redact --no-banner -l error -f json -r "$TMPD/gl.json" >/dev/null 2>&1 || true
  [ -s "$TMPD/gl.json" ] && python3 -c 'import json,sys;[print(x["File"]) for x in json.load(open(sys.argv[1]))]' "$TMPD/gl.json" \
     | sed "s|^$D/||" >> "$TMPD/hits.txt" || true
  [ -s "$TMPD/gl.json" ] && cp "$TMPD/gl.json" "$REPO/.last_gitleaks.json"   # redatto, fuori dal repo
else
  echo "AVVISO: gitleaks non disponibile, solo scansione regex"
fi
sort -u "$TMPD/hits.txt" | grep -vxF "$SELF" > "$TMPD/hits2.txt" || true
: > "$TMPD/secret.txt"
while read -r f; do
  [ -z "$f" ] && continue
  [ -f "$D/$f" ] || continue
  if [ -f "$ALLOW" ] && grep -qxF "$(sha256sum "$D/$f" | cut -d' ' -f1)  $f" "$ALLOW"; then continue; fi
  echo "$f" >> "$TMPD/secret.txt"
done < "$TMPD/hits2.txt"
cat "$TMPD/tok.txt" >> "$TMPD/secret.txt"
sort -u -o "$TMPD/secret.txt" "$TMPD/secret.txt"
while read -r f; do [ -n "$f" ] && [ "$f" != "$SELF" ] && rm -f "$D/$f"; done < "$TMPD/secret.txt"
if grep -qxF "$SELF" "$TMPD/tok.txt"; then echo "ERRORE: il token compare in sync.sh!" >&2; exit 3; fi

# ---- SKIPPED.md + MANIFEST ----
{
  echo "# File esclusi dal backup (generato da sync.sh)"
  echo
  echo "## File > $MAXSIZE (non committati): path, byte, sha256"
  sort -u "$TMPD/large.txt" | sed 's/^/    /'
  echo
  echo "## Binari ELF rimossi (output di build, ricostruibili)"
  sed 's/^/    /' "$TMPD/elf.txt"
  echo
  echo "## Esclusi dalla scansione segreti (contenuto sospetto, NON pubblicato)"
  sed 's/^/    /' "$TMPD/secret.txt"
  echo
  cat <<'SKEOF'
## Esclusi per licenza (decisione del proprietario, 2026-10-26)

Riferimento: `LICENSE_INVENTORY.md` (sha256 2e160c96f86ca192a52a4935fa6c609e854137ccd9b08452d7eac91acfd1dc11,
CSV sha256 80bf8ba8dee7e440ae614a88bca642813ed36fd527b09d23295ecf92604f2acc), sezione 4, più il controllo del 2026-10-26.
Elenco esatto dei percorsi: `strataplus/.gitignore` (stessa lista negli exclude rsync di `sync.sh`).
Questi file sono stati tolti dalla testa di `strataplus-research` il 2026-10-26 ma **restano nei commit precedenti**
(la riscrittura della storia non è ancora autorizzata). Vedi `ERRATA_LICENZE.md`.

| Categoria | File | Motivo |
|---|---|---|
| Dati derivati da edit_np (testi, prompt tokenizzati, ID, metriche per richiesta) | 289 (par. 4b) | licenza in conflitto: card HF @<revisione non pubblicata> "MIT" contro LICENSE GitHub edit_np una licenza con una clausola che vieta l'uso come dati di training |
| `bench/e1/policy/results/e1_per_request.csv` | 1 (par. 4a) | ID e metriche per richiesta di Dolly (CC-BY-SA-3.0, share-alike) e MBPP (CC-BY-4.0, attribuzione), più edit_np |
| `bench/strata-bench/datasets/subset_ids.json` | 1 (par. 4a) | 26 ID Spec-Bench (dati da fonti con licenze miste, non verificate) più edit_np |
| `logs/tmp_scratch/gen/gen.py` | 1 (trovato il 2026-10-26, fuori dal par. 4) | contiene 2 ID edit_np e la diagnosi per richiesta del dominio edit |
| Artefatti H-CA stimati su edit_np: `policy/strata-policy/replay/results/v2/hca/` tranne `hca_results.json` e `REPORT.md` (aggregati, pubblicati), quindi anche `edit_np_fitted/`; `replay/run_hca.json`; smoke/probe H-CA da /tmp; pesi/feature di classificatori; qualsiasi nome con "edit_np" (es. `lang_inventory_edit_np/`) | pattern, anche per file futuri | uso solo locale; si pubblicano gli aggregati, i run file addendum e il codice (`hca*.py`) |
| File con ID edit_np nel contenuto (`edit_np-N`), qualunque nome; per ora `bench/traces/mtp_cap_prefix_check.json`, `bench/strata-bench/runs/live_combo_aprime_holdout.md`, `logs/tmp_scratch/mcp_test.json`, `logs/tmp_scratch/order.txt` (mai pubblicati) | controllo sul contenuto in `sync.sh` | ID e metriche per richiesta |
| `bench/strata-bench/datasets/specbench.jsonl` | regola già esistente | Spec-Bench, licenze miste |
| `bench/e1/policy/data/` | regola già esistente | Dolly, MBPP, edit_np, HumanEval in parquet e tokenizer Qwen |

Totale tolto dalla testa il 2026-10-26: 292 file (291 del par. 4 + `gen.py`).

## Dati grezzi di terzi (regola del proprietario, 2026-10-26 20:05 CET)

"Tutto quello che il team produce va nel backup, ma il contenuto grezzo di dataset di terzi no."
Riferimento: `LICENSE_INVENTORY.md` sezione 7 (sha256 29bfb7c43a13614a1c01f8239dec019e9cae7dc0957549b60b98649c8d53e0c1).
Mai pubblicati (non sono mai arrivati sul fork).

| Esclusi | Motivo |
|---|---|
| `bench/strata-bench/datasets/humanevalfix_9a41762f/` tranne `LICENSE_NOTE.md`, `SHA256SUMS` (parquet per linguaggio, card HF) | dataset grezzo bigcode/humanevalpack, riscaricabile dal pin 9a41762f |
| `bench/strata-bench/datasets/commitpackft_fc56fe33/` tranne `raw_files.sha256`, `select_run.log` (`raw/`, `selected/`, `tokenizer/`, card HF) | dataset grezzo bigcode/commitpackft (licenze per repo miste), riscaricabile dal pin fc56fe33 |
| qualsiasi altra cartella `datasets/*/`: solo `LICENSE_NOTE*.md`, `SHA256SUMS`, `*.sha256`, `*.log` | regola per download futuri |
| `*.parquet`, `*.arrow`, `tokenizer*.json`, `*hf_card*`/`*hf-card*` ovunque | formati di dataset/tokenizer e card HF di terzi |
| `logs/tmp_scratch/nfe_*.jsonl`, `*nofuneval*` | NoFunEval: codice di terzi (repo GitHub, PIE/CodeNet, CodeQL), licenze non verificate |
| `logs/tmp_scratch/hfcards/` | copie di card HF di terzi |
| `logs/tmp_scratch/c0.json`, `c1.json` | dump API HF (commit dei repo bigcode, utenti), non prodotti dal team |
| quarantena: file NUOVI sotto `datasets/`, `*.jsonl` nuovi in `tmp_scratch/`, parquet/arrow | fuori finche' non revisionati (sha256 in `REVIEWED` in `sync.sh`) |

Pubblicati dopo revisione: `holdout_90_codechat.jsonl`, `proxy_30_codechat.jsonl` (solo HumanEval MIT + MT-Bench Apache-2.0, nessuna riga
edit_np), `commitpackft_selection_manifest.csv` e `commitpackft_selection_counts.json` (solo ID, licenza dichiarata e conteggi, nessun codice).
SKEOF
  if [ -s "$TMPD/lic.txt" ]; then
    echo
    echo "### Rimossi in questo sync dal controllo licenze/quarantena"
    sed 's/^/    /' "$TMPD/lic.txt"
  fi
} > "$D/SKIPPED.md"
( cd "$D" && find . -type f ! -name MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256 )

# ---- commit (solo se cambia qualcosa) ----
git add -A -f -- strataplus   # -f: il .gitignore upstream ignora *.log e logs/
git ls-files -z -- strataplus | xargs -0 grep -lIiE 'edit_np[-_][0-9]+' > "$TMPD/lic_id.txt" 2>/dev/null || true
if { [ -n "${LICG:-}" ] && git ls-files -- strataplus | git -C "$LICG" check-ignore --no-index --stdin > "$TMPD/lic_idx.txt"; } || { cat "$TMPD/lic_id.txt" >> "$TMPD/lic_idx.txt"; [ -s "$TMPD/lic_id.txt" ]; }; then
  echo "ERRORE: file esclusi per licenza nell'indice:" >&2; cat "$TMPD/lic_idx.txt" >&2
  git reset -q -- strataplus; exit 4
fi
if git diff --cached --quiet; then
  echo "Nessun cambiamento da committare."
else
  git -c user.name="Strata+ backup (melchisedekko)" -c user.email="10241980+melchisedekko@users.noreply.github.com" \
      commit -q -m "strataplus backup: sync $(TZ=Europe/Rome date '+%Y-%m-%d %H:%M %Z')"
  echo "Commit: $(git rev-parse --short HEAD)"
fi

# ---- branch delle patch: import dal repo sorgente + scansione segreti dei commit ----
# I branch vengono pubblicati così come sono (nessun merge: P6 e P-T12 confliggono in generate.cpp).
PUSH_REFS=("refs/heads/$BR:refs/heads/$BR")
for b in "${BRANCHES[@]}"; do
  git -C "$SRC_GIT" rev-parse -q --verify "refs/heads/$b" >/dev/null || { echo "AVVISO: $b assente in $SRC_GIT, salto"; continue; }
  # fast-forward soltanto: se il branch sorgente è stato riscritto, fetch fallisce e il branch non viene pubblicato
  if ! git fetch -q "$SRC_GIT" "refs/heads/$b:refs/heads/$b" 2>"$TMPD/fetch_$b.log"; then
    echo "AVVISO: $b non è fast-forward rispetto alla copia locale, non pubblicato (vedi sotto)"; cat "$TMPD/fetch_$b.log"; continue
  fi
  bad=0
  git log -p --format= "$BASE..refs/heads/$b" | grep -qE "$RX" && bad=1
  [ -n "${GITHUB_TOKEN:-}" ] && git log -p --format= "$BASE..refs/heads/$b" | grep -qF -- "$GITHUB_TOKEN" && bad=1
  if [ -x "$GITLEAKS" ]; then
    "$GITLEAKS" git . --log-opts="$BASE..refs/heads/$b" --redact --no-banner -l error -f json -r "$TMPD/glb_$b.json" >/dev/null 2>&1 || true
    [ -s "$TMPD/glb_$b.json" ] && [ "$(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1]))))' "$TMPD/glb_$b.json")" != 0 ] && bad=1
  fi
  if [ "$bad" = 1 ]; then echo "AVVISO: possibili segreti nei commit di $b: NON pubblicato"; continue; fi
  PUSH_REFS+=("refs/heads/$b:refs/heads/$b")
done

# ---- push di strataplus-research + branch delle patch sul fork (mai force, mai il default branch) ----
if [ "$NOPUSH" != 1 ]; then
  [ -n "${GITHUB_TOKEN:-}" ] || { echo "ERRORE: GITHUB_TOKEN non impostato" >&2; exit 1; }
  AUTH=$(printf 'x-access-token:%s' "$GITHUB_TOKEN" | base64 -w0)
  GIT_TERMINAL_PROMPT=0 GIT_CONFIG_COUNT=2 \
    GIT_CONFIG_KEY_0=credential.helper GIT_CONFIG_VALUE_0= \
    GIT_CONFIG_KEY_1=http.https://github.com/.extraHeader GIT_CONFIG_VALUE_1="Authorization: Basic $AUTH" \
    git push -q "$REMOTE_URL" "${PUSH_REFS[@]}" > "$TMPD/push.log" 2>&1 && prc=0 || prc=$?
  unset AUTH
  grep -v -i authorization "$TMPD/push.log" || true
  [ "$prc" = 0 ] || { echo "ERRORE: push fallito (rc=$prc)" >&2; exit "$prc"; }
  echo "Push OK: ${PUSH_REFS[*]%%:*} -> $REMOTE_URL"
fi
echo "$T0 | $(date '+%Y-%m-%d %H:%M:%S') | sync.sh HEAD=$(git rev-parse --short HEAD)" >> "$RUNLOG"
echo "OK: HEAD $(git rev-parse HEAD)"
