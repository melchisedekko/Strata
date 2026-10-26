import { Page, Section, Text, Table, Callout, NumberedList, Rows, LinkCards, Properties, TableOfContents } from "grok/canvas";

const S = "https://github.com/Niko1221/Strata/blob/7dd5cf18e68c639a8773e096c5c79f971ea2a9f5/";
const L = "https://github.com/ggml-org/llama.cpp/blob/d327bf1f0780f87b8c01b367b61853b0c291d7c4/";
const C = "https://github.com/JustVugg/colibri/blob/e0db083cdc9e563e0766cc6fc661ef23c32298e0/";
const V = "https://github.com/vllm-project/vllm/blob/4e591657157a021cab997f911d67f50c0d18a71e/";
const G = "https://github.com/sgl-project/sglang/blob/656331295619a4d0267b40b7da0b5cd5b549fcbc/";
const A = (href: string, label: string) => <a href={href} target="_blank" rel="noreferrer">{label}</a>;
const HF = (r: string) => A("https://huggingface.co/" + r, r);

export default function Ricognizione() {
  return (
    <Page width="column" title="Strata+ — Ricognizione stato dell'arte speculative decoding"
      summary="Scout v1, 2026-10-25 (Europe/Rome). [S] = implementato in Strata, [A] = implementato altrove, [P] = solo proposto. Ogni affermazione sul codice ha un permalink al commit; ciò che manca è segnato «non trovato»."
      sources={["Strata @7dd5cf18 (MIT)", "llama.cpp @d327bf1f (MIT)", "Colibri @e0db083c (Apache-2.0)", "vLLM @4e591657 (Apache-2.0)", "SGLang @65633129 (Apache-2.0)", "Hugging Face API"]}>
      <TableOfContents items={[
        { label: "Sintesi: idee prioritarie", id: "sintesi" },
        { label: "Strata oggi", id: "strata" },
        { label: "Proxy per Strata Bench", id: "proxy" },
        { label: "Richieste di Specu", id: "specu" },
        { label: "Modello di costo", id: "costo" },
        { label: "Pool n-gram e profondità adattiva", id: "pool" },
        { label: "Tabella idee", id: "tabella" },
        { label: "Schede paper", id: "paper" },
        { label: "Non trovato / non verificato", id: "nontrovato" },
      ]} />

      <Section heading="Sintesi: idee prioritarie" id="sintesi">
        <NumberedList items={[
          "Pool n-gram persistente tra richieste come DraftSource: Strata ha già il gancio (extra_draft_sources), ma nessuna sorgente registrata e un reset a ogni richiesta. Portabile su CPU. [S] gancio / [A] llama.cpp ngram-mod, vLLM suffix, SGLang NgramCorpus.",
          "Gate congiunto fra profondità MTP e lookup, come in Colibri. Il +13% di Colibri viene dalla profondità MTP, non dal lookup. [A] Colibri / [S] parziale con STRATA_SPEC_COST=1.",
          "Stop del draft MTP per entropia o probabilità (AdaEDL/SVIP): costa poco, Strata ha già --spec-min-p. [P].",
          "Selezione full-information fra sorgenti (HedgeSpec / Not-a-Bandit, lo stesso paper), con feedback controfattuale coerente con il log v1. [P].",
          "Proxy CPU confermato: Qwen3.5-2B e Qwen3.5-0.8B con MTP nativo, GGUF unsloth -MTP con tensori nextn verificati, llama.cpp --spec-type draft-mtp (PR #22673 merged). Non ancora eseguito.",
        ]} />
      </Section>

      <Section heading="Strata oggi" id="strata">
        <Rows rows={[
          { title: "DraftPolicy::choose — MTP vs lookup per token/ms attesi", detail: "Finestra MTP fissata dal chiamante; lookup per bucket di match, con margine, probe e staleness.", meta: "src/spec/draft_policy.cpp L123-152", status: { label: "[S]", tone: "success" } },
          { title: "STRATA_SPEC_COST=1 — finestra MTP cost-aware (braccio A/B)", detail: "Costi di riga per bucket di contesto; STRATA_SPEC_COST_TABLE precarica una tabella.", meta: "generate.cpp L11179, L16400-16432", status: { label: "[S] opt-in", tone: "warning" } },
          { title: "DraftSource / extra_draft_sources — gancio per retrieval", detail: "Nessuna sorgente registrata; reset() a ogni richiesta.", meta: "draft_source.hpp L1-55; generate.cpp L1089-1095", status: { label: "[S] vuoto", tone: "warning" } },
          { title: "DFlash2 — in main dal commit 7f97c35a (21/10)", detail: "Solo build CUDA e HIP; #3322 dice che non si può selezionare insieme a MTP.", meta: "CMakeLists.txt L339-340", status: { label: "legato a HW", tone: "danger" } },
          { title: "Motore solo GPU", detail: "La scelta CPU-only non avvia i motori CUDA/HIP/SYCL; strata_spec compila invece su CPU (piano v2 §0).", meta: "docs/release-notes-0.2.2.md L60" },
        ]} />
        <Text>Link: {A(S + "src/spec/draft_policy.cpp#L123-L152", "draft_policy.cpp#L123-L152")} · {A(S + "include/strata/spec/draft_source.hpp#L1-L55", "draft_source.hpp#L1-L55")} · {A(S + "src/program/generate.cpp#L1089-L1095", "generate.cpp#L1089-L1095")} · {A(S + "CMakeLists.txt#L339-L340", "CMakeLists.txt#L339-L340")} · {A(S + "docs/release-notes-0.2.2.md#L60", "release-notes-0.2.2.md#L60")}</Text>
      </Section>

      <Section heading="Proxy per Strata Bench" id="proxy" caption="CPU, ≤ ~6 GB GGUF; RAM libera ~2,2 GB (vincolo di Strata Lead). Dimensioni lette dall'albero file su HF.">
        <Table columns={["Proxy", "Repo HF / GGUF", "Quant e dimensione", "In ~2 GB?", "Licenza"]} rows={[
          ["1. Qwen3.5-2B + MTP nativo (principale)", <span>{HF("Qwen/Qwen3.5-2B")} · {HF("unsloth/Qwen3.5-2B-MTP-GGUF")}</span>, "Q4_K_M 1,33 GB · Q6_K 1,63 · Q8_0 2,08", { text: "Q4_K_M sì; Q8_0 no", tone: "warning" }, "Apache-2.0"],
          ["2. Qwen3.5-0.8B + MTP nativo (iterazione veloce)", <span>{HF("Qwen/Qwen3.5-0.8B")} · {HF("unsloth/Qwen3.5-0.8B-MTP-GGUF")}</span>, "Q8_0 0,83 GB · Q4_K_M 0,55", { text: "Sì", tone: "success" }, "Apache-2.0"],
          ["3. Qwen3.5-4B + MTP nativo", HF("unsloth/Qwen3.5-4B-MTP-GGUF"), "Q4_K_M 2,84 GB · Q3_K_M 2,38 · UD-IQ2_M 1,94", { text: "No", tone: "danger" }, "Apache-2.0"],
          ["4. Coppia 2B (target) + 0.8B (drafter, -md)", HF("unsloth/Qwen3.5-0.8B-GGUF"), "1,33 + 0,53 GB (Q4_K_M)", { text: "Al limite", tone: "warning" }, "Apache-2.0"],
          ["5. Drafter DFlash / EAGLE-3 per Qwen3.5-4B", <span>{HF("Anbeeld/Qwen3.5-4B-DFlash-GGUF")} · {HF("yuyijiong/Qwen3.5-4B-Eagle3")}</span>, "DFlash Q4_K_M 0,38 GB · EAGLE-3 0,47 GB", { text: "No (target 4B)", tone: "danger" }, "Apache-2.0"],
        ]} />
        <Callout lead="Verifica indipendente dell'affermazione di Strata Lead: confermata (salvo esecuzione)." tone="success">
          Ho letto gli header GGUF via HTTP Range di Qwen3.5-0.8B-Q4_K_M e Qwen3.5-2B-Q4_K_M dai repo -MTP-GGUF. Risultati: arch qwen35, block_count 25, nextn_predict_layers 1, tensori blk.24.nextn.(eh_proj, enorm, hnorm, shared_head_norm), vocabolario di 248320 token (uguale a Flash-Next), general.license apache-2.0. Controllo negativo: il GGUF non-MTP ha 24 blocchi e 0 tensori nextn. Nel config HF di 0.8B e 2B c'è mtp_num_hidden_layers = 1. llama.cpp: PR #22673 merged il 2026-05-16; caricamento nextn in qwen35.cpp L114-119; draft-mtp in docs L227/L372. Non verificato a runtime: non ho eseguito llama.cpp su CPU, e la RAM oltre al file (KV, buffer) non è misurata.
        </Callout>
        <Text>Link: {A("https://github.com/ggml-org/llama.cpp/pull/22673", "llama.cpp PR #22673")} · {A(L + "src/models/qwen35.cpp#L114-L119", "qwen35.cpp#L114-L119")} · {A(L + "docs/speculative.md#L227", "docs/speculative.md#L227")} · {A(L + "common/speculative.cpp#L78", "speculative.cpp#L78")}. Scartati: MiMo-7B (vocabolario 151680; in llama.cpp c'è solo l'arch mimo2) e Qwen3-4B/0.6B (vocabolario 151936, senza MTP). Limite: i proxy sono densi, Flash-Next è MoE.</Text>
      </Section>

      <Section heading="Richieste di Specu" id="specu">
        <Rows rows={[
          { lead: "1", title: "Gate Colibri vs DraftPolicy::choose", detail: "Colibri massimizza su k anche la profondità MTP (SPEC_PROBE 16, SPEC_REFRESH 64) e sceglie il lookup tutto-o-niente. Strata riceve la finestra MTP fissa e ha margine, bucket e staleness. Il +13% di Colibri: Qwen3.8 su CPU (Ryzen 7 PRO 8700GE), 3,30 contro 2,91 tok/s, 2,74 token/forward; viene dalla profondità MTP, «lookup never chosen». Run singolo, nessuno script di riproduzione trovato." },
          { lead: "2", title: "llama.cpp: più --spec-type, mtp + eagle3", detail: "La lista separata da virgole è accettata, ma si combina con un fallback a priorità fissa (il primo impl che produce un draft vince), non con una scelta cost-aware. C'è un solo ctx_dft, quindi mtp ed eagle3 non funzionano come drafter indipendenti. Dedotto dal codice, non eseguito." },
          { lead: "3", title: "Strata #1161, PR #1426 / #3322 / #3457", detail: "#1161 chiusa not_planned il 13/10 (pulizia del tracker). #1426 chiusa senza merge il 19/10 (reset 0.2.0-beta). #3322 aperta: DFlash2 non si combina con MTP; +29,05% code short su 4070 Ti SUPER. #3457 aperta (Metal). DFlash2 è già in main (7f97c35a)." },
          { lead: "4", title: "Pool n-gram persistente", detail: "Vedi la sezione Pool: gancio presente in Strata, implementazioni in llama.cpp, vLLM e SGLang." },
        ]} />
        <Text>Link: {A(C + "c/spec_draft.h#L129-L160", "colibri spec_draft.h#L129-L160")} · {A(C + "c/qwen38_core.h#L3883-L3893", "qwen38_core.h#L3883-L3893")} · {A(C + "docs/speculative.md#L187-L198", "colibri docs#L187-L198")} · {A(L + "common/speculative.cpp#L2806-L2818", "llama.cpp priorità L2806-2818")} · {A(L + "common/speculative.cpp#L2975-L3063", "fallback L2975-3063")} · {A(L + "common/speculative.cpp#L2704-L2762", "ctx_dft unico L2704-2762")} · {A("https://github.com/Niko1221/Strata/issues/1161", "#1161")} · {A("https://github.com/Niko1221/Strata/pull/1426", "#1426")} · {A("https://github.com/Niko1221/Strata/pull/3322", "#3322")} · {A("https://github.com/Niko1221/Strata/pull/3457", "#3457")}</Text>
      </Section>

      <Section heading="Modello di costo" id="costo" caption="s(T) = c_verify(T)/c_verify(1); ρ_mtp e ρ_lu sono rapporti rispetto al forward del target (piano v2 §4).">
        <Table columns={["Parametro", "Valore", "Condizioni", "Fonte"]} rows={[
          ["s(T) pubblico per Qwen-Next", { text: "non trovato", tone: "danger" }, "—", "—"],
          ["s(T) componente CPU degli expert", "1; 1,75; 2,4; 3,05 (T=1..4)", "Flash-Next in Strata, «measured on decode traces», hardware non indicato", A(S + "include/strata/core/verify.hpp#L10-L11", "verify.hpp#L10-L11")],
          ["ρ_mtp pubblico", { text: "non trovato", tone: "danger" }, "—", "—"],
          ["ρ_lu ngram-mod", "durate b/g/a 0,149 / 0,347 / 0,005 ms su 810 chiamate", "esempio nella doc; modello e hardware non indicati", A(L + "docs/speculative.md#L434", "llama.cpp docs#L434")],
          ["ρ_lu ngram-map-k", "2,234 / 1,427 / 0,016 ms", "come sopra", A(L + "docs/speculative.md#L438", "docs#L438")],
          ["ρ_lu suffix tree", "~20 µs per token", "SuffixDecoding, su CPU", A("https://arxiv.org/abs/2411.04975", "arXiv:2411.04975")],
          ["Accettazione MTP di Flash-Next", "0,89 / 0,86 / 0,85 (passi 1-3)", "greedy, tools/mtp_probe.py", A(S + "include/strata/core/mtp.hpp#L3-L5", "mtp.hpp#L3-L5")],
          ["Token per pass in Strata", "2,4-3,2 (MTP fino a 3 draft)", "Flash-Next", A(S + "docs/DETAILS.md#L2303-L2306", "DETAILS.md#L2303-L2306")],
          ["Accettazione MTP di DeepSeek-V3", "85-90% sul 2° token; ~1,8× TPS", "sezione non verificata", A("https://arxiv.org/abs/2412.19437", "arXiv:2412.19437")],
          ["Accettazione MTP di MiMo-7B", "~90% con 1 layer", "sezione non verificata", A("https://arxiv.org/abs/2505.07608", "arXiv:2505.07608")],
          ["DFlash2 vs MTP", "+29,05% code short; +14,84% a 256K", "RTX 4070 Ti SUPER, Flash-Next", A("https://github.com/Niko1221/Strata/pull/3322", "Strata #3322")],
        ]} />
        <Callout lead="Costi nel codice di Strata: stima/obiettivo nel codice, non misura pubblica." tone="warning">
          kShape s(T) = 1; 1,35; 1,7; 2,05; 2,45; 2,85; 3,25; 3,6, con il riferimento a bench/results/2026-09-27-spec/window-cost. CostModel: dense_ms = 11,0 ms, etichettato «plan P3 target»; dense_ratio e distinct_ratio dalle directory 2026-09-23-mmvq-multi e -spec-economics; mtp_draft_ms 1,2 → ρ_mtp ≈ 0,059; lookup_draft_ms 0,01 → ρ_lu ≈ 0,0005. Il rapporto è un mio calcolo da step_ms(0) = 20,51 ms. Nessuna delle directory 2026-09-23-* né 2026-09-27-spec è nel repo. B-flat e B-lin sono ipotesi.
        </Callout>
        <Text>Link: {A(S + "src/spec/draft_policy.cpp#L10-L13", "draft_policy.cpp#L10-L13")} · {A(S + "include/strata/spec/controller.hpp#L12-L34", "controller.hpp#L12-L34")} · {A(S + "src/spec/controller.cpp#L8-L18", "controller.cpp#L8-L18")} · {A(S + "src/program/generate.cpp#L3205-L3207", "generate.cpp#L3205-L3207 (+6-11% sulle edit)")} · {A(S + "include/strata/spec/draft_policy.hpp#L51-L62", "draft_policy.hpp#L51-L62")}</Text>
      </Section>

      <Section heading="Pool n-gram e profondità adattiva" id="pool">
        <Table columns={["Meccanismo", "Persistenza", "Dove", "Stato"]} rows={[
          ["Strata DraftSource", "nessuna (reset a ogni richiesta)", A(S + "src/spec/draft_source.cpp#L13-L34", "draft_source.cpp#L13-L34"), "[S] gancio vuoto"],
          ["llama.cpp ngram-mod (#19164)", "tra richieste, in RAM", A(L + "docs/speculative.md#L162-L197", "docs#L162-L197"), "[A]"],
          ["llama.cpp ngram-cache (#5479)", "su file (-lcs/-lcd)", A(L + "common/ngram-cache.h#L84-L101", "ngram-cache.h#L84-L101"), "[A]"],
          ["vLLM SuffixDecoding", "albero globale in RAM", A(V + "vllm/v1/spec_decode/suffix_decoding.py#L9-L102", "suffix_decoding.py#L9-L102"), "[A]"],
          ["SGLang NgramCorpus + corpora SAM", "tra richieste; corpus esterno", A(G + "python/sglang/srt/speculative/ngram_worker.py#L114-L123", "ngram_worker.py#L114-L123"), "[A]"],
          ["SGLang adaptive steps (EMA)", "profondità per batch", A(G + "python/sglang/srt/speculative/adaptive_spec_params.py#L153-L262", "adaptive_spec_params.py#L153-L262"), "[A] solo EAGLE"],
          ["AdaEDL / SVIP / AdaEAGLE / LTD / HedgeSpec", "profondità o selezione adattiva", "vedi Schede paper", "[P]"],
        ]} />
      </Section>

      <Section heading="Tabella idee" id="tabella">
        <Table columns={["Idea", "Fonte", "Licenza", "Hardware", "Stato", "Sforzo", "Prossimo passo"]} rows={[
          ["Pool persistente come DraftSource", A(S + "include/strata/spec/draft_source.hpp#L1-L55", "draft_source.hpp#L1-L55"), "MIT", { text: "portabile", tone: "success" }, "[S] gancio / [A]", "medio", "replay su tracce multi-turno 2B"],
          ["Gate congiunto profondità MTP + lookup", A(C + "c/spec_draft.h#L129-L160", "colibri spec_draft.h"), "Apache-2.0", { text: "portabile", tone: "success" }, "[A] / [S] parziale", "basso-medio", "oracolo O_DP sul replay"],
          ["Stop per entropia (AdaEDL/SVIP)", A("https://arxiv.org/abs/2411.18462", "SVIP"), "MIT (SVIP)", { text: "portabile", tone: "success" }, "[P]", "basso", "loggare le prob MTP"],
          ["Selezione full-information (HedgeSpec)", A("https://arxiv.org/abs/2510.20064", "arXiv:2510.20064"), "Apache-2.0", { text: "portabile", tone: "success" }, "[P]", "medio", "valutazione controfattuale"],
          ["DFlash2 come sorgente", A(S + "CMakeLists.txt#L339-L340", "CMakeLists#L339-L340"), "Apache-2.0", { text: "legato a HW (CUDA/HIP)", tone: "danger" }, "[S]", "—", "fuori ambito CPU"],
        ]} />
      </Section>

      <Section heading="Schede paper" id="paper">
        <LinkCards links={[
          { title: "SuffixDecoding — codice Apache-2.0 (ArcticInference)", site: "arXiv:2411.04975", href: "https://arxiv.org/abs/2411.04975" },
          { title: "AdaEDL — stop per entropia; codice non trovato", site: "arXiv:2410.18351", href: "https://arxiv.org/abs/2410.18351" },
          { title: "SVIP — EMNLP 2025; codice MIT", site: "arXiv:2411.18462", href: "https://arxiv.org/abs/2411.18462" },
          { title: "AdaEAGLE — LDLP; codice non trovato", site: "arXiv:2412.18910", href: "https://arxiv.org/abs/2412.18910" },
          { title: "Learning to Draft — ICLR 2026; Apache-2.0", site: "arXiv:2603.01639", href: "https://arxiv.org/abs/2603.01639" },
          { title: "HedgeSpec = Not-a-Bandit; Apache-2.0", site: "arXiv:2510.20064", href: "https://arxiv.org/abs/2510.20064" },
          { title: "EAGLE-3 — licenza NOASSERTION", site: "arXiv:2503.01840", href: "https://arxiv.org/abs/2503.01840" },
          { title: "DFlash — codice MIT", site: "arXiv:2602.06036", href: "https://arxiv.org/abs/2602.06036" },
          { title: "DSpark — repo ufficiale non trovato; in llama.cpp #25173", site: "arXiv:2607.05147", href: "https://arxiv.org/abs/2607.05147" },
        ]} />
      </Section>

      <Section heading="Non trovato / non verificato" id="nontrovato">
        <Properties items={[
          { label: "Curve pubbliche s(T) e ρ_mtp", value: "non trovate (Qwen-Next, MiMo, DeepSeek, EAGLE)" },
          { label: "bench/results 2026-09-23-*, 2026-09-27-spec", value: "citate nel codice, assenti nel repo @7dd5cf18" },
          { label: "Codice di AdaEDL e AdaEAGLE; paper PLD", value: "non trovati; il repo PLD non ha licenza" },
          { label: "draft-mtp su CPU con Qwen3.5", value: "codice, PR e tensori verificati; esecuzione non verificata" },
          { label: "mtp + eagle3 in llama.cpp", value: "dedotto dal codice, non eseguito" },
          { label: "Numeri vLLM #25136, sezioni DeepSeek-V3 e MiMo", value: "da rileggere alla fonte" },
          { label: "Script per il +13% di Colibri", value: "non trovato" },
        ]} />
        <Text>File: /workspace/strata-plus/scout.md (versione completa con tutti i permalink) e /workspace/scout/ricognizione-v1.md.</Text>
      </Section>
    </Page>
  );
}
