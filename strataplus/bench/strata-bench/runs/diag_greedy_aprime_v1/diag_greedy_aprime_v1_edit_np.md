# diag_greedy_aprime v1 — aggregati edit (<ET>), senza id. proxy CPU, non AMD, llama.cpp non Strata

Sottoinsieme edit della diagnosi: 8 prompt = 7 divergenti A1/B1 nella run (a') v3 + 1 di controllo. Sorgenti: tm0_report_<ET>.json, diag_report_<ET>.json (file locali).

| misura | valore |
|---|---|
| v3: A1 = B1 sui 7 divergenti | 0/7 (per costruzione) |
| v3: prima differenza di output sul round con T=8 (round che contiene il token) | 1/7 (gli altri 6: T=4 contro T=4 o T=6) |
| v3: almeno un round T=8 di A1 prima della prima differenza di output | 7/7 |
| ripetibilità: A1 rilanciato 2 volte, B1 rilanciato 2 volte | 8/8 output e 265/265, 284/284 round con vmargin bit-identici |
| greedy puro batch 1 (base_r1 = base_r2 = TF3) | 8/8 output, 1024/1024 round identici |
| v3: A1 = greedy puro (base_r1) sui 7 | 1/7 |
| gap top1-top2 alla prima divergenza v3, A1:B1 (n=19 valori) | <0.05: 6; 0.05-0.5: 13; >=0.5: 0; max 0.36271 |
| gap B1:greedy (n=21) | max 0.44916, >=0.5: 0 |
| token emesso diverso dal top-1 / violazioni criterio BUG | 0 / 0 |
| GGML_CPU_TILED_MM=0: A1 = B1 sui 7 divergenti | **6/7** (1 residuo: pos 69, T=4 contro T=4, celle 390/391, gap 0.09228 contro 0.0462, ciascun braccio emette il proprio top-1) |
| GGML_CPU_TILED_MM=0: A1 = B1 sugli 8 | 7/8 |
| GGML_CPU_TILED_MM=0: A1 = greedy puro *già generato* (base_r1, tiled attivo) sui 7 | 3/7 |
| greedy puro con TILED_MM=0 (edit) | non generato (budget) |
| celle KV occupate alla prima differenza v3 (kv_pos) | 300-705 (tutte > 256, quindi n_kv dedotta 512 o 768 con pad 256; dedotta, non misurata) |
