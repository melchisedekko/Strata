# STATUS P6 — NON ACCENDERE (decisione Strata Lead, 25/10/2026 04:58 CET)
- P6 (commit 079ecdd generate.cpp hook, e467f6e docs; branch locale strataplus-policy-local) **resta solo in locale e NON va acceso** (STRATA_SPEC_JOINT=1 da non usare).
- Motivo: il hook P6 non salta né interrompe il draft MTP (commento del hook: "It does not yet skip or stop the MTP draft itself, so the draft
  time a skip/stop would save is not saved here"), quindi il risparmio di draft contato dal replay ORIG non esiste nel motore.
  Con il costo fedele "catena intera" (M-full, holdout v1.1, banda ρ 0,06–0,15, 15 celle/dominio) A vs SPEC_COST è negativo:
  code −5,8% [−8,8;−2,8] W15/15, edit −6,7% [−10,4;+0,7] W14/15, chat −7,8% [−12,1;−4,4] W15/15 (mediana [min;max] fra celle, tok/s STIMATI,
  fonte results/v2/holdout_v11_costvariants/REPORT.md). Variante esatta P6 + min_p 0,5 (draft = min(3,1+run)) non simulata.
- P7 e P6b: **NO-GO in questo giro**. Nessuna patch del gate proposta.
- La chain_rule (M-real: draft = max(d,1), il test di valore del gate come chain_rule con attesa host per passo, mtp.cpp L1658-1708)
  resta **candidata per il giro GPU**, da misurare con l'attesa host reale e con le mtp_p vere del draft layer di Strata
  (le mtp_p del replay vengono dal proxy llama.cpp 2B). Stato compilazione P6 invariato: sintassi OK su HIP 5.7.1 e CUDA, link e ramo HIP≥7 non verificati.
