# diag_tiled_mm0 — previsione pre-registrata (proxy CPU, non AMD, llama.cpp non Strata)

Scritta e hashata: 2026-10-27 15:11:37 CET, prima di qualunque processo llama di questa prova.

Testo di Lead (approvato alle 15:11 CET):

«Previsione: con GGML_CPU_TILED_MM=0, A1 e B1 diventano identici sui 20 prompt divergenti (13 code/chat e 7 edit), e A1 coincide con il greedy puro. Se resta anche una sola divergenza, la causa del percorso tiled non è dimostrata.»

- Binario: proxy/llama_spec_trace.v14.nollamafile, sha256 e030ec13f9e077c746ca3b7694d8639fc04eeed944daa00022220728bca06c5e
- libggml-cpu: /workspace/llama.cpp/build-nollamafile/bin/libggml-cpu.so.0.27.0, sha256 31e0c41168c05450f378dde3f223a671f5d13781988409c2f1a8bf80fb738f96 (contiene la stringa GGML_CPU_TILED_MM)
- Sorgente: /workspace/llama.cpp/ggml/src/ggml-cpu/tiled/tiled.cpp, sha256 a5d92ce8f617696778e225de6658180649143fec3792c5cfef84170641f2d06e, commit llama.cpp d327bf1f0780f87b8c01b367b61853b0c291d7c4
  - L572-581 ggml_tiled_matmul_enabled(): getenv("GGML_CPU_TILED_MM"); enabled = env == NULL || atoi(env) != 0. Con valore 0 => disabilitato (una sola lettura, std::call_once).
  - L607 e L648: if (!ggml_tiled_matmul_enabled()) -> ritorno false, si torna al mul_mat vec_dot standard (ggml-cpu.c:1269).
  - L1202-1205 ggml_tiled_min_batch: percorso tiled solo con rows >= 8 (o FORCE). Tipi Q4_K/Q5_K/Q6_K inclusi (L617-619, L1171-1175).
- Nomi bracci come nello script v3: A1 = --live-src aprime (S=8), B1 = --live-src default_a (S=6). Greedy puro = --mode base (batch 1).
- I tempi di questa finestra non valgono: CPU condivisa.
