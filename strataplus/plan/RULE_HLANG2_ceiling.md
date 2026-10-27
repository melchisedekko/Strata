# Regola GO — H-LANG (2), tetto offline del drafting sintattico
Fissata da Strata Lead il 2026-10-26 prima di aprire qualsiasi dato. Riferimento: scout_HLANG_sota.md (e2bdffbe…), sezione B.

1. Domini: code (HumanEval) e edit-fix (HumanEvalFix, 5 linguaggi non Python), quando le tracce esistono. Dataset di edit con licenza non pubblicabile: solo in locale, solo aggregati, fuori dalla decisione. Chat esclusa.
2. Token forzato: alla posizione i, dato il prefisso di riferimento (solo causale), la continuazione sintattica ammessa è unica a livello di caratteri E la stringa forzata si tokenizza col tokenizer del modello esattamente nei token di riferimento. Se lo strumento non lo sa decidere, il token NON è forzato.
3. Tetto per round: token aggiuntivi oltre max(acc_mtp, acc_lookup), presi solo come catena contigua di token forzati che parte dal primo token rifiutato, con T totale ≤ 8 (kMaxT). Drafting a costo zero.
4. Metrica: guadagno di tok/s stimati con s(T)=1+rho(T-1), rho piatto 0.196 e ripido 0.538, rispetto alla choose attuale replayata, somma su somma per dominio.
5. GO alla fase successiva (prototipo di fonte) solo se il tetto è >= 6% in almeno un dominio con ENTRAMBI i rho. Motivo: una fonte reale cattura solo una parte del tetto e a valle vale la soglia del 3%. Sotto 6% con almeno un rho: H-LANG (2) si chiude.
6. Gira dopo la (a′), annunciato in cpu_busy_*.log, nice 19. Run file hashato prima, che cita questo file per sha256.
