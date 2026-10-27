# diag_fa_off_tm0 — previsione pre-registrata (proxy CPU, non AMD, llama.cpp non Strata)

Scritta e hashata: 2026-10-27 15:17:24 CET, prima di qualunque processo llama della run -fa off (che parte solo dopo la fine della run tiled in corso).

Testo di Lead (15:16 CET):

«Con GGML_CPU_TILED_MM=0 e -fa off, A1 e B1 sono identici su tutti e 20 i prompt divergenti, e A1 coincide con il greedy puro su tutti i 90 prompt.»

- Binario: proxy/llama_spec_trace.v14.nollamafile, sha256 e030ec13f9e077c746ca3b7694d8639fc04eeed944daa00022220728bca06c5e
- -fa: common/arg.cpp:1766-1778 di /workspace/llama.cpp (on|off|auto; off -> LLAMA_FLASH_ATTN_TYPE_DISABLED); default AUTO (common/common.h:506), risolto da probe in src/llama-context.cpp:659-662.
  Il tracer passa gli argomenti non suoi a common_params_parse (proxy/llama_spec_trace_v14.cpp:97,104). Accettazione da --help verificata prima del lancio (vedi env_info_fa0).
- Annotato prima del lancio (dalle tracce v3 già esistenti): n_kv alla prima differenza A1/B1 = prompt_tokens + pos:
  mtbench-105: 222 + 100 = 322; mtbench-136: 272 + 30 = 302 (con le posizioni di Policy 75 e 24: 297 e 296). Tutti < 512.
- I tempi non valgono: CPU condivisa (build di Scout/Policy in parallelo).
