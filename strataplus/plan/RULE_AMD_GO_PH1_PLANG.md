# Soglie GO su AMD per P-H1 v2 e P-LANG v2, taglio di H-LANG(2) e nota sugli hash

Autore: Strata Lead, 2026-10-27. Regole fissate prima di qualsiasi misura su AMD. Questo file non si modifica: una correzione va in un file nuovo.

## Regole comuni (da AMD_PROTOCOL.md di Bench)
- Passo zero: patch e controllo si linkano sulla macchina di misura; si registrano la versione di ROCm e lo sha256 dei binari. Se il controllo non si linka, la sessione si ferma.
- Il tok/s che decide si misura con `STRATA_SERVE_TRACE` spento in entrambi i bracci. I dati per round vengono da run separate con il trace acceso in entrambi i bracci; l'overhead del trace si riporta ma non decide.
- Coppie alternate, IC95 bootstrap sulle richieste. Il percorso (serial o pipeline T) si registra per round.
- Output greedy identico al controllo nel 100% dei prompt. Basta un prompt diverso per fermare tutto (NO-GO e indagine).

## P-H1 v2 (strataplus-H1-arbiter-v2.patch, e7b9b48c…)
- Bracci: build `h1` contro build `ctrl` (b24c6a1d), stessi flag. Il braccio che decide gira con `STRATA_SPEC_JOINT=1 STRATA_SPEC_JOINT_DET=1`; la variante senza DET si riporta ma non decide.
- Domini: code, edit-fix, chat.
- GO se tutte vere: almeno +3% di tok/s in almeno un dominio con il limite basso dell'IC95 sopra 0; nessun dominio con stima puntuale sotto −1%; output identico.
- Pipeline T: si riportano la quota di round in pipeline e il guadagno per percorso; il GO vale sul totale.
- Il criterio della fase replay in `piano.md` resta valido solo per il replay e non sostituisce questo.

## P-LANG v2 (strataplus-LANG-knob-v2.patch, 18122e6b…, sopra H1 v2)
- Prerequisiti: GO offline di `run_hlang_editfix.json` (bbb9eb22…) e GO di P-H1 su AMD. Senza tutti e due, P-LANG non si misura.
- Calibrazione: la tabella per linguaggio si calibra solo sullo split tune (40 N) di `run_hlang_editfix.json`, con tracce AMD; poi si congela e si hasha prima di aprire l'holdout. La tabella di esempio non calibrata non si usa per decidere.
- Bracci: build `full` (H1 v2 + LANG v2) con la tabella congelata contro build `h1`, stessi flag e stessa modalità JOINT_DET. Si misura solo via serve.
- GO se tutte vere: su edit-fix, split holdout (40 N), almeno +3% di tok/s con il limite basso dell'IC95 sopra 0; su code e chat, dove `strata_lang` non si manda, stima puntuale non sotto −1%; output identico in tutti i domini.
- Nel report va scritto che H-LANG sul dominio code (solo Python) non è testato.

## Taglio del tetto H-LANG(2)
- Scout (`scout_HLANG_sota.md`, e2bdffbe…) non ha trovato nessun drafter sintattico adottabile che lasci l'output greedy identico. Anche un tetto ≥6% non avrebbe dato una patch misurabile entro il giro successivo.
- Con il cambio di passo, che chiede patch che compilano e si misurano in tok/s, ciò che non arriva a una patch si taglia. Il tetto non è mai stato misurato; la regola resta in archivio come ipotesi futura.

## Nota sugli hash di RULE_HLANG2_ceiling.md
- Lo sha256 annunciato in chat, `0e8da4750501ab9516c10f9f122f74d70af89990f2b688aef970d513db8c4c78`, vale per l'originale non pubblicato.
- La versione pubblicata nel commit 2be9e3b1 ha sha256 `f71d0b076e0a765ddcdf10dc2590a5c26328f15d24d44b4735704c640dbd67e8`. È cambiata solo la sostituzione di un nome per motivi di licenza; il contenuto della regola è invariato.

## Conteggio delle build
- Sono 10: 6 di Policy (ctrl, h1, full, fullst, ctrlst, h1st) e 4 di Scout (controllo 7dd5cf1, HFC v2, trace_ctl, trace_hfc), una alla volta, dopo la fine della finestra (a′).
