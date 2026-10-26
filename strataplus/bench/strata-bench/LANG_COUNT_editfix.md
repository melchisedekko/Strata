# LANG_COUNT edit-fix — HumanEvalFix (bigcode/humanevalpack @9a41762f), proxy CPU, non AMD

Creato il 2026-10-26 19:58:08 CET.
- Lingua presa solo dal prefisso `task_id` `<Lang>/<N>`, cioè dai metadati del dataset.
- Nessuna traccia, nessun output del modello.
- Dominio 'edit-fix', separato da edit/edit_np e **mai sommato**.
- Lo split tune/holdout lo fa Policy.
- Licenza MIT (card alla revisione 9a41762f73a8cb23bb5811b73d5aab164efcf378). Python escluso (non scaricato).

| config | prefisso ID | item | N distinti | N min–max | ID anomali | sha256 parquet |
|---|---|---|---|---|---|---|
| js | JavaScript | 164 | 164 | 0–163 | 0 | 52d6aada9ff62c22ba139aaa64431cca461fbca3cb0625521a988ffeef250855 |
| java | Java | 164 | 164 | 0–163 | 0 | 0be942d715894e3b350149f1cde6593e95eda495aa4bd1750f09428c0b3e3e9c |
| go | Go | 164 | 164 | 0–163 | 0 | 5cbb0e8152b5c9d2b595a1fa9d540c87cde7a306e9fc7f63febe24825bc20c74 |
| cpp | CPP | 164 | 164 | 0–163 | 0 | fd2eed15063bf883952fb3b0a23a372eeaa9b9e58932a496667a0c2595145779 |
| rust | Rust | 164 | 164 | 0–163 | 0 | 02570ed6a11d8801d26a9aae0db87cdc0fc6f4a7eb68adb3a9e37fb4f752da57 |

Totale item (5 linguaggi): 820.

**N presenti in tutti e 5 i linguaggi:** 164.
Elenco completo nel .json (`N_in_all_5`). Compresso: 0–163 (contigui)
