### §10.A Mappa per alzare kVerifyMaxT a 12/16. COMPLETATA 2026-10-25 (patch a T=12)

Lettura del codice di Strata @7dd5cf1 fatta solo con rg/sed: niente build e niente esecuzioni. "V" vuol dire verificato leggendo il codice, "P" vuol dire plausibile (non compilato, non misurato). Le classi sono quelle della bozza: a = solo dimensione, b = logica o kernel, c = policy/costo, d = batch.
- Correzione al conteggio: kVerifyMaxT compare in **77 righe**, ma le occorrenze sono **82**, in 11 file sotto src e include (22 file contando sycl, serve e bench).
- La bozza segnalava falsi positivi, ora verificati:
  - s_gemv.cu `case 8`: si riferisce a code_bits, non a T (V).
  - qsa_decode_attn.cu `[8]`: sono larghezze vettoriali (V).
  - In verify.cpp L2390, `row[8]` indicizza un'altra dimensione (V).
  - copy_from_mapped_multi `n>8` (elementwise.cu L416) viene chiamato con n=7 e n=2 (mtp.cpp L1298 e L1334) (V).

#### (1) PATCH MINIMA: misurare s(12), cioè una verify da 12 righe, a single stream

**Pilotaggio consigliato, senza MTP** (V; generate.cpp):
- Comando: `--spec 12 --suffix-draft 0 --spec-oracle <continuazione> [--expert-profile/--expert-cache come al solito]`, con env `STRATA_SPEC_T_CYCLE=8,12` (o `1,…,12`) e `STRATA_VERIFY_PROFILE=1`.
- Senza `--mtp`, `use_mtp=false` (L16143) e l'MTP non viene caricato (L5472). Le righe della finestra vengono dall'oracle (L16594-16595).
- T_CYCLE accetta `1<=v<=o.spec` (L16393) e forza T a ogni round (L16553). I vettori sono dimensionati su o.spec (L16383-16385 e L16406-16407) e il primo round di ogni T, quello della cattura, è escluso (L16709). Il risultato si legge nella riga `window cost (ms/round) T8:… T12:…` (L16746-16749).
- `--suffix-draft 0` evita la clamp di L3208-3210 e il ramo sfx/policy (L16556). DraftPolicy(12) clampa da sola a 8 (draft_policy.cpp L30) senza effetti.
- Non esiste un "verify_bench": verify_parity e spec_verify_parity (kMaxT=8, L128) sono test di parità, non misure di costo.
- s(12)/s(8) = T12/T8 sulla stessa run. Nota: la misura include il costo host del round.

**Configurazione target (d′): `--spec 12 --mtp-max-t 4` (S_mtp=4) con lookup fino a 12.** Ecco cosa serve perché S=12 arrivi fino alla verify:
- **Clamp CLI** (V):
  - Con `--mtp-max-t 4` esplicito, la clamp di L3208-3210 (`spec=min(spec+2,8)`) non scatta, perché richiede mtp_max_t==0.
  - L3215-3218 (`min(...,8)`) scatta solo con `--lookup-chain>0`. Per d′ va portata a `kVerifyMaxT`, e il range di L2674 (0..7) va portato a `0..kVerifyMaxT-1` (c).
  - `--spec` (L2608) non ha un tetto superiore lì. Il limite reale è il check di verify.cpp L721-722 (`max_t>kVerifyMaxT || >cpu::MAXT`).
  - L16426: `S_mtp=min(4,12)=4`. Siccome S_mtp<o.spec, si chiama `set_max_drafts(3)` (L16427).
- **Lookup e policy** (V, c), **necessari in d′**:
  - generate.cpp L16557 (CLI) e L14897 (serve) chiamano `sfx.propose(S-1, sbuf)`. sbuf è dimensionato su o.spec/S (L16454 e L14174): OK.
  - `policy.choose` invece limita il lookup a `max_t_-1` (draft_policy.cpp L125, L131, L137) e `max_t_ = clamp(max_t,1,kMaxT=8)` (L30). **Con kMaxT=8 una finestra lookup non supera mai 8 righe.** Modifiche:
    - draft_policy.hpp L25: `kMaxT = 8` → `kMaxT = strata::kernels::kVerifyMaxT` (oppure 12).
    - Gli array `kMaxT+1` a L88, L90 e L98 scalano da soli.
    - draft_policy.cpp L13 kShape: aggiungere 4 valori, per esempio `…,3.6, 3.95, 4.3, 4.65, 5.0` (estrapolazione lineare, P). **Senza questi valori l'aggregate init mette 0.0: in cost_ms (L42-50) la riga `kShape[t]/kShape[u]` produce un costo 0, cioè r=∞, e la policy sceglie sempre T=12** (V).
  - Con T_CYCLE, la policy può comunque sovrascrivere T quando il lookup scatta (L16559-16561). Per misurare s(12) conviene quindi `--suffix-draft 0` anche in d′.
- **Buffer di finestra** (V): `window`/`outv` (L16416), `cbuf` (L16457 e L14189), `drafts`/`dprob` (L16383-16384, e DS = max(S, mtp.max_t()) a L14169-14171) sono tutti dimensionati su o.spec/S, quindi OK a 12. `win_cap = o.spec` (L16531).
  - Lato serve con S_mtp=4: dwin_s[8] (L14173) è copiato con `min(…,8)` (L14890) e usato con T_mtp-1≤3 (L15190); dp_tested/t2_rej[8] hanno le guardie `d<8` e `a<8` (L15113-15114). Restano OK.
  - PW{tok[8]} (L14248-14252) e chain_n (L14781) servono solo con `--pipeline-windows 2`, quindi vanno nella lista 2.
- **MTP in d′: NON resta intatto a 4** (V). `mtp_t = pipeline_windows>=2 ? kVerifyMaxT : o.spec` (generate.cpp L5470), quindi l'MTP viene caricato con max_t_=12 (mtp.cpp L266 accetta ≤kVerifyMaxT). In più `draft()` fa il catch-up delle righe accettate, `T=a+1` fino a 12 (mtp.cpp L1569 con STRATA_MTP_CATCHUP_ALL spento, poi capture_round(T) L1271), e prefill cattura `T=1..max_t_` (L1371 e L1497-1499). Modifiche necessarie:
  - mtp.hpp: `prefill_exec_[9]`, `prefill_dev_exec_[9]` (L242-243), `round_exec_[9]` (L249) e `round_exec_c_[9]` (L193) vanno portati a `[kVerifyMaxT+1]`, altrimenti c'è overflow dell'indice 12 (V). La distruzione usa range-for (mtp.cpp L138-144) e scala da sola.
  - mtp.cpp L396: `xq_ = native_q8_1_bytes(NH*HD, 8)` → `native_q8_1_bytes(max(NH*HD, N), T)`. Quantizza N×T righe (L905 e L935). Overflow se N·T > NH·HD·8, quindi dipende dalla geometria (V sul dimensionamento, P sul caso concreto).
  - Restano a 8 senza rischio con S_mtp≤8 e senza pipeline windows: `step_exec_[9]`, `step_exec_c_[9]` (L189 e L194, indice j<max_steps=min(max_t_-1, max_drafts_)=3, L1580), `ev_step_[8]`, `chain_tok_[8]` e `chain_prob_[8]` (L235-238, solo chain_launch con pipeline; ciclo `j<8` a L1850) (V).
- **Verifier, host** (a/b):
  - kVerifyMaxT: verify_kernels.hpp L21 `= 8` → `= 12`. È template e scala con la costante (V).
  - cpu::MAXT: cpu/expert.hpp L143 `= 8` → `= 12`, richiesto dal check di verify.cpp L721. pool.hpp L62-65 e L364-366 scalano. static_assert(MAXT*10≤128) in expert_source.cpp L4756-4759: 120 passa (V).
  - verify.hpp:
    - L536 `last_tokens_[8]` → `[kVerifyMaxT]`: è scritto per t<T a verify.cpp L2744, quindi **overflow a T=12** (V).
    - L547-549 `exec_/exec_nr_/launched_/launched_nr_[9]` e L616 `groups_[9]` → `[kVerifyMaxT+1]` (indice T, verify.cpp L1148) (V).
    - L520-524 `prof_t_sum_/prof_t_win_/rs_win_[9]` → `[kVerifyMaxT+1]` (V).
  - verify.cpp L2358 `T<=8` → `T<=kVerifyMaxT` (report profilo); L2757 `last_t_<=8` → `<=kVerifyMaxT`. Senza queste due modifiche STRATA_VERIFY_PROFILE non vede T=12 (V). L2742 `T<=8` è solo una guardia delle route stats: va bene così.
- **Kernel GPU sul percorso della verify** (b; i .cu vengono compilati anche come HIP):
  - native_mmvq.cu (V):
    - L829 `MAX_NCOLS=8` → `12`; L1800 messaggio.
    - L1511-1519 `launch_multi` (CUDA e HIP non-gfx906): aggiungere `case 9..12` (o almeno 12, se T_CYCLE usa solo 8 e 12). Registri: NCOLS somme per thread (occupancy, P).
    - **HIP gfx906**: anche `wave_launch` L1870-1879.
    - Solo CUDA: `launch_il` (L1739), nel blocco `#if !__HIPCC__` L1523-1794. `native_mmvq_il_supported` (L3230) ritorna false per ncols>8 e quindi usa il fallback: si può lasciare.
    - `native_mmvq_pair` L2844 e `il_rows_for` L3144 fanno fallback (V).
    - `q8_packed_mmvq`/`q6_packed` (L2089-2090 e L2224-2225) lanciano throw dopo validate_shape: sono opt-in (STRATA_Q8_PACKED), da lasciare spenti nella misura.
    - Alternativa sconsigliata: spezzare 8+4 al livello di entry. È bitwise uguale (commento L823-828), ma legge i pesi due volte e quindi gonfia s(12).
  - shared_expert.cu L219-220: `n_tok>8` → `>kVerifyMaxT`. Dentro usa native_mmvq con ncols=n_tok (V).
  - native_bf16.cu (router verify.cpp L1950, PLE L1272-1290, indexer L1604-1654) (V):
    - L298-300 throw `n_tok>8` → `>12`. Nello switch STRATA_MMVF_M il default `<N, 8, false>` va portato a `<N, kVerifyMaxT, false>` (registri, P).
    - L274 (`_aux`, opt-in STRATA_MMVF_ROWS) ritorna false e usa il fallback.
  - verify_kernels.cu (V):
    - gdn_conv_ab/gdn_ab_multi/gdn_state_replay usano il default `<kVerifyMaxT,false>` (L1056, L1105, L1149), quindi scalano. Rischio registri: acc[MAX_T] (L104), gv/bv/vv[MAXT] (L474) (occupancy, P).
    - resident_plan: static_assert kVerifyMaxT*10≤128 (L1281) dà 120: passa (V). Va bene solo se k≤10 (P per altri modelli).
  - s2_expert_grouped.cu L826 `GMAX=8` → `12`. È **obbligatorio**, perché static_assert(GMAX>=kVerifyMaxT) a L829 rompe la compilazione. Shared memory: xs_w 8·GMAX·NC int + xs_dh, cioè 25 KB a 8 e circa 37,5 KB a 12 (L996-997, dal commento "20 KB" + "5 KB"), sotto i 48 KB statici. Anche xs_q/hs_q[GMAX] (L860-861 e L922-923) scalano (P per FF grande).
  - fused_gr.hpp L68 `kFusedGrMaxT=8` → `kVerifyMaxT`. **fused_gr_read_multi rifiuta n_tok>kFusedGrMaxT** (fused_gr.cu L2204) e viene chiamato con n=T (verify.cpp L1368, L2270, L2288). I modelli hc lo usano (verify.cpp L737) (V).
    - Rischi: smem dinamica T·(N/S) float (L615); a 12 con N=2560 e S=2 fanno ~61 KB, al limite dei 64 KB di HIP/Turing (P).
    - persist (opt-in HIP): `n_tok>st.max_t` ritorna false e usa il fallback (L3032) (V).
  - iq_kernels.cu: `launch_mmvq_multi_nc` (L3360-3370) con default `<TY,8,false>` fa un ciclo interno su c0 a passi di NC (L1803-1808), quindi è corretto (V). Rilegge però i pesi da cache: si può aggiungere `case 12` per avere un costo fedele (P). native_gu_multi lavora a GRP_NC=4 per passata (L1859-1862): OK.
  - native_moe.cu L178-185 e verify.cpp L1144 e L2170 hanno guardie `n<=8` che portano al percorso non fuso: corretto, solo un po' più lento (V).
  - Attenzione QSA/flash: nessun tetto a T trovato con rg (P, OK).
- **CPU, se ci sono expert miss sulla CPU** (b): i kernel nativi multi-token fanno dispatch `switch(nt)` con `default: <8>`. Per nt>8 **troncano** senza errore (iq_avx2_rows.inl L546, iq_avx512.cpp L230, iq_avx1.cpp L308, nvfp4_avx2.cpp L176 e L194) oppure hanno `y[8]` senza guardia, cioè overflow (iq_avx2.cpp L557, iq_avx1.cpp L421, tq_cpu.cpp L175-176 e L217-219 con kTqMaxTokens=8 di tq_cpu.hpp L76) (V).
  - Patch minima consigliata, in un solo punto: all'inizio di `native_gu_rows` (native_expert.cpp L262) e di `native_down_rows` (L374), se `nt>8` ricorrere a blocchi di 8 token (puntatori act/ff/hq/out spostati). Ogni token resta indipendente dal gruppo (P sul bitwise).
  - q2_rows_any e i kernel bf16/q5_1/q8_0 fanno già tiling (V). Il router CPU tronca a 8 in modo sicuro (expert_source.cpp L3048) (V).
  - In alternativa: un `--expert-cache` abbastanza grande da avere zero miss CPU nella misura.

#### (2) PATCH COMPLETA a T=12 (in aggiunta alla 1)
- **Batch e multi-slot** (d, V):
  - verify.hpp L378 `brow_[8]`, L384 `last_rows_[8]`, L413 `b_out_[8]`, L420 `last_pos_b_[8]` → `[kVerifyMaxT]` (scritti per t<S a verify.cpp L3504, L3764 e L3767).
  - verify.cpp L3774-3775 e L3950-3951 `int rows[8]` con `t<8` troncano: portare a kVerifyMaxT.
  - L1512 e L3562 `<=8` (opt-in GDN groups).
  - generate.cpp: slots_in_windows L5323-5342, kHistSlots L8948, L9016-9168, L11321, L11521-11528, L11749-11760 (scalano con kVerifyMaxT, ma vanno ricontrollati per memoria, P).
- **Pipeline windows** (V): generate.cpp L14248-14252 `PW{tok[8],prob[8]}` → `[kVerifyMaxT]`; L14781 e L14810 `chain_n = kVerifyMaxT-1`. mtp.hpp `ev_step_[8]`, `chain_tok_[8]`, `chain_prob_[8]` (L235-238) → `[kVerifyMaxT]`; `step_exec_[9]` e `step_exec_c_[9]` → `[kVerifyMaxT+1]`; mtp.cpp L1850 `j<8` → `j<kVerifyMaxT`. Con la pipeline mtp_t=kVerifyMaxT, quindi chain_n_ arriva a 11: **overflow a T=12** (V).
- **MTP con S_mtp>8**: le stesse modifiche ai grafi step. h_force_ e n_force≤16 (mtp.cpp L1778) restano OK.
- **Policy** (c): kShape misurata su T 9..12 (bench/results) al posto dell'estrapolazione. STRATA_SPEC_COST_TABLE e `double ms[DraftPolicy::kMaxT]` (generate.cpp L16400-16402 e L16432-16437) scalano. Clamp lookup-chain e il default di --suffix-draft (L3208-3218) diventano `kVerifyMaxT` invece di 8.
- **Statistiche serve**: dwin_s[8] (L14173), t2_rej/t2_hit e dp_tested/dp_ok[8] (L14187-14188) → `[kVerifyMaxT]` se S_mtp>8. Oggi hanno guardie, quindi è solo telemetria troncata.
- **GEMV completi**: native_mmvq tutti i `case 9..12` (IL CUDA L1739, packed L2089 e L2224, pair L2844, interleave L2966, L3144, L3230), q8_sm60.cuh L121 (solo CUDA, fallback), dflash2.cu L719 (`--draft dflash2`), iq_kernels `case 12`, native_moe combine `n_tok<=8` (L180) per la fusione.
- **CPU completa**: casi template 9..12 (oppure tiling a 4) in iq_avx2_rows.inl, iq_avx512.cpp, iq_avx1.cpp, nvfp4_avx2.cpp; `y[8]` → `y[MAXT]` in iq_avx2.cpp L557 e iq_avx1.cpp L421; kTqMaxTokens=12 (tq_cpu.hpp L76) con le sue matrici L175-219. Router AVX1 kq_avx1.cpp L49 `acc[8]` (protetto da L3048). peer/remote CAP MAXT*10 (peer_experts.cpp L29, remote_experts.cpp L21 e L271) scalano (P).
- **Parità e test**: spec_verify_parity L128 kMaxT=8, gdn_parity e resident_plan_parity (kVerifyMaxT), native_expert_bench NTOK=8, fused_gr_bench TM.
- **16 rispetto a 12** (P): resident_plan con 160>128 entry richiede un redesign (più di 4 warp, s_ids); GMAX=16 porta la smem MoE a ~50 KB, oltre i 48 KB statici; fused_gr a ~82 KB, oltre i 64 KB HIP.
