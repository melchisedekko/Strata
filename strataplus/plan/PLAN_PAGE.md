# Strata+ — piano di ricerca speculative decoding (export della Page)

Export del sorgente della Page del piano di ricerca (Lead), 2026-10-26 19:14 CET. Il sorgente TSX è riportato integralmente qui sotto.

```tsx
import { Page, Section, Text, Callout, Table, Segmented, Steps, NumberedList, LinkCards, TableOfContents, Properties, useState } from "grok/canvas";

type Cat = "mtp" | "head" | "draft" | "ngram" | "policy";

const TECH: Record<Cat, string[][]> = {
  mtp: [
    ["MTP nativo (DeepSeek-V3)", "No", "2° token accettato 85–90%, ~1,8x TPS (paper)", "vLLM ROCm: sì (MTP nativo testato su MI300X/MI355X)", "Base di Strata", "Altrove", "https://arxiv.org/abs/2412.19437"],
    ["MTP Qwen3.8-Flash-Next (1 layer, multi-step)", "No", "Strata 2,4–3,2 tok/pass; vLLM MTP-3 AL 2,98 (A100)", "Strata HIP: sì (R9700, 7900 XTX, Strix Halo, 780M); vLLM: validato MI355X BF16", "È il drafter attuale", "In Strata", "https://github.com/Niko1221/Strata/blob/main/docs/HOW_IT_WORKS.md"],
    ["MiMo MTP", "No", "MTP usato per spec decoding (paper)", "n.v.", "Riferimento per MTP multi-layer", "Altrove", "https://arxiv.org/abs/2505.07608"],
    ["MTP ricorsivo oltre la profondità addestrata", "No", "vLLM riusa il layer MTP con passaggi extra; best N=4–7 su Qwen3.5/3.6", "vLLM ROCm: sì (blog AMD)", "Strata già concatena fino a 3 draft", "In Strata (fino a --spec 4)", "https://vllm.ai/blog/2026-08-23-speculative-decoding-amd-gpus"],
    ["FastMTP (fine-tune MTP ricorsivo + vocab ridotto)", "No (fine-tune del layer)", "2,03x vs 1,21x MTP vanilla (paper)", "Agnostico", "Alto: migliora il drafter esistente", "Altrove", "https://arxiv.org/abs/2509.18362"],
  ],
  head: [
    ["EAGLE-1", "Head leggero", "2,7–3,5x (paper, LLaMA2)", "SGLang/vLLM ROCm: sì via EAGLE-3", "Nessun checkpoint per Qwen3.8", "Altrove", "https://arxiv.org/abs/2401.15077"],
    ["EAGLE-2 (albero dinamico)", "Head leggero", "3,05–4,26x (paper)", "Albero su ROCm in SGLang (kernel Triton, PR #21369)", "Albero costoso con GDN ricorrente", "Altrove", "https://arxiv.org/abs/2406.16858"],
    ["EAGLE-3", "Head (feature multi-layer)", "fino a 6,5x (paper); misurato su MI300X/MI355X nel blog vLLM", "vLLM ROCm sì; SGLang ROCm sì (MI300 PR #36659)", "Nessun checkpoint Qwen3.8 trovato", "Altrove", "https://arxiv.org/abs/2503.01840"],
    ["HASS", "Head", "2,81–4,05x, +8–20% vs EAGLE-2 (paper)", "n.v.", "Ricetta di training per un head", "Altrove", "https://arxiv.org/abs/2408.15766"],
    ["GRIFFIN", "Head", "+8% acceptance length, +7% speedup vs base (paper)", "n.v.", "Ricetta di training", "Altrove", "https://arxiv.org/abs/2502.11018"],
    ["Medusa / typical acceptance", "Più head", "2,2–3,6x (paper)", "n.v.", "Basso (MTP già migliore)", "Altrove", "https://arxiv.org/abs/2401.10774"],
    ["Hydra", "Head sequenziali", "fino a 1,31x vs Medusa, 2,70x vs AR (paper)", "n.v.", "Basso", "Altrove", "https://arxiv.org/abs/2402.05109"],
    ["ReDrafter", "RNN drafter", "fino a 2,8x (H100), 2,3x (MLX) (paper)", "n.v.", "Basso", "Altrove", "https://arxiv.org/abs/2403.09919"],
    ["DFlash / DFlash2 (block diffusion)", "Sì (5 layer)", "Qwen3.8: AL 2,98→4,08, +25% tok/s vs MTP-3 su 2xA100 (PR fork vLLM)", "vLLM ROCm sì (blog AMD); Strata: CUDA e HIP", "Medio-alto se fine-tunato sul target", "In Strata (sperimentale, non default)", "https://github.com/Niko1221/Strata/pull/3322"],
    ["DSpark (DFlash + testa Markov + confidenza)", "Sì", "Su MI300X/MI355X nel blog vLLM (cifre per modello da rileggere)", "vLLM ROCm sì", "Proposta in Strata PR #3397", "Plausibile per Strata", "https://arxiv.org/abs/2607.05147"],
  ],
  draft: [
    ["Draft model separato (Leviathan / Chen)", "Sì", "1,3–3x su MI300X (blog ROCm)", "vLLM ROCm: sì", "Basso: VRAM tolta alla cache esperti", "Altrove", "https://rocm.blogs.amd.com/artificial-intelligence/spec_decode_mi300x/README.html"],
    ["DistillSpec", "Sì (distillato)", "+10–45% vs SD standard (paper)", "Agnostico", "Utile per fine-tune drafter", "Altrove", "https://arxiv.org/abs/2310.08461"],
    ["PARD (AMD)", "Sì (draft parallelo)", "fino a 2,47x MI250X / 3,13x MI300X in vLLM (AMD)", "Nativo AMD", "Basso-medio: nessun PARD per Qwen3.8", "Altrove", "https://www.amd.com/en/developer/resources/technical-articles/accelerating-generative-llms-interface-with-parallel-draft-model-pard.html"],
  ],
  ngram: [
    ["Prompt lookup decoding", "No", "Strata: edit di codice +6–11%; Colibri +6–7%", "Agnostico (CPU)", "Già presente", "In Strata", "https://github.com/apoorvumang/prompt-lookup-decoding"],
    ["Suffix drafter Strata (--suffix-draft, --lookup-chain)", "No", "--lookup-chain e default --suffix-draft discussi nelle issue #1301/#1303/#1305", "Agnostico", "Già presente", "In Strata", "https://github.com/Niko1221/Strata/issues/1301"],
    ["SuffixDecoding (albero dei suffissi globale)", "No", "Forte su agentic/RL (paper)", "vLLM metodo suffix (Arctic Inference)", "Alto per loop agentici", "Altrove", "https://arxiv.org/abs/2411.04975"],
    ["llama.cpp ngram-simple / map-k / map-k4v / mod", "No", "ngram-mod: pool hash condiviso fra slot", "Backend HIP di llama.cpp: plausibile, non verificato", "Alto: pool persistente", "Altrove", "https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md"],
    ["Colibri corpus-draft (REST-like)", "No", "+22% tok/s su replay GLM-5.2 (doc Colibri)", "CPU/Vulkan", "Medio-alto per agentic", "Altrove", "https://github.com/JustVugg/colibri/blob/main/docs/corpus-draft.md"],
    ["Colibri grammar-forced drafts", "No", "Guadagno proporzionale alla densità di span strutturali; guardia sotto il 50% di accettazione", "CPU/Vulkan", "Medio per JSON/tool call", "Altrove", "https://github.com/JustVugg/colibri/blob/main/docs/grammar-draft.md"],
    ["Lookahead decoding", "No", "fino a ~1,8x (paper)", "n.v.", "Basso-medio", "Altrove", "https://arxiv.org/abs/2402.02057"],
    ["REST", "No (datastore)", "1,62–2,36x (paper)", "n.v.", "Medio", "Altrove", "https://arxiv.org/abs/2311.08252"],
    ["Token Recycling", "No", "~2x, ~2,3x su codice (paper)", "n.v.", "Medio: riusa i candidati scartati", "Altrove", "https://arxiv.org/abs/2408.08696"],
    ["SGLang NGRAM", "No", "n.d.", "Docs: solo CUDA (da riconfermare)", "Riferimento", "Altrove", "https://docs.sglang.io/docs/advanced_features/speculative_decoding"],
  ],
  policy: [
    ["DraftPolicy di Strata (MTP vs lookup, tokens/ms)", "No", "Lookup sempre preso perdeva 2–8% su testo; la policy lo evita", "Agnostico", "È la base dell'ipotesi H1", "In Strata", "https://github.com/Niko1221/Strata/blob/main/include/strata/spec/draft_policy.hpp"],
    ["Gate Colibri (proposta che vale di più)", "No", "MTP+lookup al gate +13% su edit di codice (doc)", "CPU/Vulkan", "Confronto diretto", "Altrove", "https://github.com/JustVugg/colibri/blob/main/docs/speculative.md"],
    ["SpecDec++", "Classificatore", "2,04–2,26x, +7–11% vs SD (paper)", "Agnostico", "Stop drafting appreso", "Altrove", "https://arxiv.org/abs/2405.19715"],
    ["DISCO", "Classificatore", "+10% vs lookahead statico ottimo (paper)", "Agnostico", "Profondità dinamica", "Altrove", "https://arxiv.org/abs/2405.04304"],
    ["AdaEDL", "No (entropia)", "+10–57% vs SD statico (paper)", "Agnostico", "Facile da provare", "Altrove", "https://arxiv.org/abs/2410.18351"],
    ["SVIP", "No (entropia)", "fino a +20% SpecBench (paper)", "Agnostico", "Facile da provare", "Altrove", "https://arxiv.org/abs/2411.18462"],
    ["AdaEAGLE (LDLP, MLP a 3 layer)", "MLP minuscolo", "1,62x vs AR, +2% vs EAGLE fisso (paper)", "Agnostico", "Predittore di lunghezza su hidden MTP", "Altrove", "https://arxiv.org/abs/2412.18910"],
    ["BanditSpec", "No", "UCB/EXP3 su configurazioni (paper)", "Agnostico", "Selettore fra drafter", "Altrove", "https://arxiv.org/abs/2505.15141"],
    ["Not-a-Bandit / HedgeSpec (ICLR 2026)", "No", "fino a +83,7% tok/s vs EAGLE3, +49% MAT vs BanditSpec (paper)", "Agnostico", "Valutazione controfattuale gratuita di tutti i drafter", "Altrove", "https://arxiv.org/abs/2510.20064"],
    ["Learning to Draft (ICLR 2026)", "Policy RL", "2,24–4,32x, fino a +36,4% vs EAGLE3 (paper)", "Agnostico", "Ottimizza direttamente tokens/s del ciclo", "Altrove", "https://arxiv.org/abs/2603.01639"],
    ["Verifica ad albero (SpecInfer / Sequoia)", "No", "Alberi ottimizzati per hardware (paper)", "SGLang ROCm: kernel Triton", "Costoso con stato GDN ricorrente", "Plausibile per Strata", "https://arxiv.org/abs/2305.09781"],
  ],
};

const HYP: string[][] = [
  ["H1", "Arbitro MTP + prompt lookup v2: per ogni passo sceglie la fonte con feature contestuali e feedback controfattuale (Hedge)", "+3–10% su edit di codice e agentic, circa 0 su chat (stima)", "Bassa-media", "Base in Strata (DraftPolicy); estensione plausibile"],
  ["H2", "Pool n-gram persistente fra richieste (stile ngram-mod / SuffixDecoding / corpus Colibri)", "+5–20% su loop agentici ripetitivi (stima)", "Media", "Altrove"],
  ["H3", "Quantizzazione del layer MTP: esperti int8/Q8 invece di 2 bit, accettazione per profondità", "+2–8% di accettazione ai livelli 2–3 (stima)", "Bassa", "Plausibile (Colibri: head int4 crolla a 0–4%)"],
  ["H4", "Profondità dinamica appresa (LDLP / AdaEDL / SVIP) sopra la soglia --spec-min-p", "+2–5% (stima)", "Bassa-media", "Parziale in Strata (STRATA_SPEC_COST)"],
  ["H5", "Modello di costo consapevole degli esperti (unione degli esperti per finestra, hit rate)", "+2–6% su GPU con offload (stima)", "Media", "Plausibile (domanda aperta in Colibri)"],
  ["H6", "Valutare DFlash2 (già su CUDA e HIP) contro MTP e fine-tunarlo sulle feature del target; DSpark dopo", "+5–25% (fork vLLM +25% su A100; Strata Metal +7,5–8,5%)", "Alta", "In Strata (CUDA e HIP)"],
  ["H7", "Fine-tune FastMTP del layer MTP (self-distillation multi-step)", "+5–15% di tokens/pass (stima)", "Alta (serve il checkpoint BF16 da 335 GB)", "Altrove"],
  ["H8", "Draft grammaticali per JSON e tool call", "Proporzionale agli span strutturali (Colibri)", "Bassa-media", "Altrove"],
  ["H9", "Albero MTP top-2 al primo livello", "Incerto: righe extra = più esperti mancati", "Alta", "Plausibile"],
  ["H10", "Head EAGLE-3 addestrato sulle feature MTP/target", "Incerto: DFlash2 esiste già", "Alta", "Plausibile"],
];

const TEAM: string[][] = [
  ["Architetto speculative decoding (lead)", "Ordina le ipotesi, definisce le metriche, decide go/no-go", "Questa pagina, dati dei benchmark", "Roadmap, decisioni per fase"],
  ["Scout SOTA e fork", "Legge Colibri, llama.cpp, vLLM, SGLang, PR DFlash/DSpark ed estrae cosa riusare", "Repo, paper, issue", "Note di trasferimento con file, flag, numeri"],
  ["Ingegnere misure e benchmark", "Protocollo A/B a coppie interleaved su AMD (R9700, 7900 XTX, Strix Halo) e una NVIDIA di riferimento", "Build Strata, set HumanEval/MT-Bench/SpecBench + trace agentici", "Tabelle tok/s, tokens/pass, waste, intervalli"],
  ["Ricercatore policy decisionali", "Arbitro H1, profondità H4, costo H5: replay offline e poi online", "Trace con le proposte di tutte le fonti", "Policy C++ piccola e deterministica"],
  ["Implementatore engine C++/HIP", "Integra le policy, il pool n-gram, la quantizzazione MTP e l'integrazione di DFlash2 nella DraftPolicy", "Sorgente Strata, spec delle policy", "PR con flag opt-in e test di parità"],
  ["Ingegnere training drafter", "Fine-tune FastMTP o DFlash2 sulle feature di Qwen3.8 e quantizzazioni", "Checkpoint BF16, dati generati dal target", "Checkpoint, curve di accettazione per posizione"],
  ["Garante correttezza e riproducibilità", "Identità greedy, rejection sampling esatto, determinismo (#1928)", "PR, suite di parità", "Gate di rilascio, report di regressione"],
];

export default function App() {
  const [cat, setCat] = useState<Cat>("mtp");
  return (
    <Page
      title="Strata+ — piano di ricerca speculative decoding"
      summary="Cosa fa già Strata, cosa esiste altrove (Colibri, llama.cpp, vLLM, SGLang, AMD) e un piano ordinato di ipotesi, esperimenti e ruoli per migliorare il drafting MTP di Qwen3.8-Flash-Next."
      width="wide"
    >
      <TableOfContents
        items={[
          { label: "Sintesi" },
          { label: "Verifica dei fatti" },
          { label: "Già in Strata, altrove, plausibile" },
          { label: "Confronto delle tecniche" },
          { label: "Ipotesi ordinate" },
          { label: "Ipotesi H1 nel dettaglio" },
          { label: "Piano degli esperimenti" },
          { label: "Squadra proposta" },
          { label: "Cosa non è verificato" },
          { label: "Fonti principali" },
        ]}
      />

      <Section heading="Sintesi">
        <Callout lead="Il punto">
          Strata (github.com/Niko1221/Strata) esiste e usa davvero il layer MTP di Qwen3.8-Flash-Next (fino a 3 draft, 2,4–3,2 token per pass). Ha già un arbitro per round fra MTP e prompt lookup (DraftPolicy) e un DFlash2 su CUDA e HIP. Il margine più economico sta nel migliorare l'arbitro, nell'aggiungere memoria n-gram fra richieste e nel rivedere la quantizzazione del layer MTP. DFlash2 gira già anche su AMD/HIP: resta da valutarlo contro l'MTP e, se serve, fine-tunarlo sul target.
        </Callout>
        <Text>Colibrì è il motore Colibri (github.com/JustVugg/colibri): C puro, esperti MoE letti dal disco, con MTP + prompt lookup + gate per Qwen3.8-Flash-Next attivi di default.</Text>
      </Section>

      <Section heading="Verifica dei fatti">
        <Table
          columns={["Affermazione", "Esito", "Fonte"]}
          rows={[
            ["Strata è un progetto reale", { text: "Confermato", tone: "success" }, "https://github.com/Niko1221/Strata"],
            ["Qwen3.8-Flash-Next esiste (125B + 51B n-gram + 4B MTP, 6B attivi, MTP a 1 layer multi-step)", { text: "Confermato", tone: "success" }, "https://huggingface.co/Qwen/Qwen3.8-Flash-Next"],
            ["MTP fino a 3 token, 2,4–3,2 token per pass", { text: "Confermato (doc Strata)", tone: "success" }, "https://github.com/Niko1221/Strata/blob/main/docs/HOW_IT_WORKS.md"],
            ["Default: --spec 4 --spec-min-p 0.5 (draft solo se il MTP è almeno al 50%)", { text: "Confermato", tone: "success" }, "https://ai.thesatyajit.com/articles/strata-engine"],
            ["Prompt lookup fino a 5 token, edit di codice +6–11%", { text: "Confermato", tone: "success" }, "https://github.com/Niko1221/Strata/blob/main/docs/DETAILS.md"],
            ["Strata combina MTP e lookup", { text: "Confermato: arbitro per round + --lookup-chain", tone: "success" }, "https://github.com/Niko1221/Strata/blob/main/include/strata/spec/draft_policy.hpp"],
            ["Strata ha EAGLE", { text: "Non trovato", tone: "warning" }, "Ricerca issue/PR Niko1221/Strata"],
            ["Strata ha un draft model separato", { text: "Sì, DFlash2 su CUDA e HIP", tone: "success" }, "https://github.com/Niko1221/Strata/pull/1426"],
            ["Strata gira su AMD", { text: "Confermato: HIP (gfx1100, gfx12, gfx1151, 780M) con MTP", tone: "success" }, "https://github.com/Niko1221/Strata/blob/main/docs/AMD_HIP.md"],
            ["Colibri: MTP + prompt lookup per Qwen3.8", { text: "Confermato", tone: "success" }, "https://github.com/JustVugg/colibri/blob/main/docs/speculative.md"],
            ["llama.cpp: draft-mtp e draft-eagle3", { text: "Confermato (entrambi documentati)", tone: "success" }, "https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md"],
            ["llama.cpp: MTP + EAGLE-3 insieme sullo stesso checkpoint", { text: "Non documentato", tone: "warning" }, "Docs: --spec-type accetta una lista; con draft model + draftless vince il draftless"],
          ]}
        />
      </Section>

      <Section heading="Già in Strata, altrove, plausibile">
        <Table
          columns={["Meccanismo", "In Strata", "Altrove", "Note"]}
          rows={[
            ["MTP come drafter primario", { text: "Sì (default)", tone: "success" }, "vLLM, llama.cpp, Colibri", "Testa MTP presa dal checkpoint BF16; esperti a 2 bit; vocab ridotto a 106.299 id"],
            ["Prompt lookup / suffix drafter", { text: "Sì (default)", tone: "success" }, "Colibri, llama.cpp, vLLM", "Arbitrato per round: tokens attesi per ms"],
            ["MTP + lookup nella stessa finestra", { text: "Sì (--lookup-chain, opt-in)", tone: "success" }, "Colibri: sceglie una proposta per verify", "Guadagno da misurare (issue #1301, #1303)"],
            ["Profondità MTP in base al costo", { text: "Sì (STRATA_SPEC_COST, opt-in)", tone: "success" }, "Gate di Colibri", "Usa la prob. del draft e il costo misurato della finestra"],
            ["Draft accoppiati Gumbel / rejection sampling", { text: "Sì (opt-in)", tone: "success" }, "Standard", "Accettazione 52,8→59,9% su Strix Halo, +9% tok/s"],
            ["DFlash / DFlash2", { text: "Sì (CUDA e HIP)", tone: "warning" }, "vLLM (anche ROCm), llama.cpp", "CUDA 4070 Ti: più lento dell'MTP; Metal fine-tunato +7,5–8,5%"],
            ["DSpark", { text: "Solo proposta (PR #3397)", tone: "warning" }, "vLLM, llama.cpp", "Testa di confidenza = decisore integrato"],
            ["EAGLE-3", { text: "No", tone: "danger" }, "vLLM, SGLang, llama.cpp", "Nessun checkpoint pubblico per Qwen3.8 trovato"],
            ["Pool n-gram fra richieste", { text: "No", tone: "danger" }, "llama.cpp ngram-mod, vLLM suffix, corpus Colibri", "Richiesta nell'issue #1161 (chiusa)"],
            ["Draft grammaticali", { text: "No", tone: "danger" }, "Colibri", "Strata supporta già response_format JSON"],
          ]}
        />
      </Section>

      <Section heading="Confronto delle tecniche">
        <Segmented<Cat>
          options={[
            { value: "mtp", label: "MTP" },
            { value: "head", label: "Head e drafter" },
            { value: "draft", label: "Draft model" },
            { value: "ngram", label: "N-gram e retrieval" },
            { value: "policy", label: "Decisori" },
          ]}
          value={cat}
          onChange={(v: Cat) => setCat(v)}
        />
        <Table
          columns={["Tecnica", "Modello extra?", "Speedup / accettazione (fonte)", "AMD / ROCm", "Fit per Strata", "Evidenza", "Link"]}
          rows={TECH[cat]}
        />
        <Text>Gli speedup dei paper sono misurati su altri modelli e hardware: servono per ordinare le idee, non per prevedere Strata. n.v. significa che non ho verificato il supporto AMD.</Text>
      </Section>

      <Section heading="Ipotesi ordinate">
        <Table
          columns={["#", "Ipotesi", "Guadagno atteso", "Sforzo", "Evidenza"]}
          rows={HYP}
        />
        <Text>L'ordine pesa guadagno per sforzo sull'hardware consumer di Strata, dove ogni GiB di VRAM tolto alla cache degli esperti costa velocità. I guadagni marcati come stima sono mie ipotesi da misurare.</Text>
      </Section>

      <Section heading="Ipotesi H1 nel dettaglio">
        <Properties
          items={[
            { label: "Punto di partenza", value: "DraftPolicy::choose confronta i token attesi per ms dell'MTP (EMA) con quelli del lookup (q per lunghezza del match, 4 bucket) e sceglie una finestra" },
            { label: "Sfida chiave", value: "Scegliere la fonte a ogni passo e non sprecare righe di verifica quando le fonti divergono" },
            { label: "Idea 1: feedback controfattuale", value: "Dopo il verify si conoscono i token veri: si può calcolare quanti token avrebbe accettato anche la fonte scartata, senza chiamate extra al target (idea di HedgeSpec)" },
            { label: "Idea 2: accordo fra fonti", value: "Se lookup e MTP coincidono sui primi token, più fiducia e finestra più lunga; se divergono al token 1, scegliere con le feature e non pagare entrambe" },
            { label: "Idea 3: feature", value: "Lunghezza del match, p1 e entropia dell'MTP, profondità, codice o prosa, posizione nel contesto, hit rate degli esperti" },
            { label: "Idea 4: determinismo", value: "Una modalità che non dipende dal tempo misurato (issue #1928: le scelte guidate dal tempo cambiano l'arrotondamento CPU)" },
            { label: "Metrica principale", value: "tok/s in coppie interleaved; poi tokens/pass e righe sprecate per finestra" },
          ]}
        />
      </Section>

      <Section heading="Piano degli esperimenti">
        <Steps
          steps={[
            { title: "Fase 0 — Baseline e strumentazione (1 settimana)", detail: "Build Strata su R9700, 7900 XTX, Strix Halo e una RTX. Log per round: proposte MTP e lookup con prob., match, righe, accettati, ms, esperti mancati (STRATA_SPEC_DEPTH=1, /metrics)." },
            { title: "Fase 1 — Replay offline di H1 e H4", detail: "Dai trace calcolare l'oracolo (fonte e profondità migliori a posteriori) e il divario della DraftPolicy attuale. Se il divario è sotto il 3%, H1 scende in priorità." },
            { title: "Fase 2 — H1 online", detail: "Arbitro Hedge + feature, opt-in. A/B 6–12 coppie interleaved, greedy e temperatura 0,7, con identità greedy controllata." },
            { title: "Fase 3 — H3 e H2", detail: "Ablazione della quantizzazione MTP (Q2, Q4, Q8 per gli esperti MTP) con accettazione per posizione; pool n-gram persistente su trace agentici (sessioni di edit ripetute)." },
            { title: "Fase 4 — H5 e H8", detail: "Costo della finestra con l'unione degli esperti; draft grammaticali per output JSON e tool call." },
            { title: "Fase 5 — H6 e H7 (solo se le fasi 1–4 lasciano margine)", detail: "Valutazione di DFlash2 su HIP contro MTP, poi fine-tune sulle feature del target; FastMTP sul layer MTP. Protocollo v2 della squadra: /workspace/strata-plus/piano.md (solo CPU, metriche indipendenti dall'hardware, proxy Qwen3.5-2B/0.8B con MTP nativo). Ogni GiB di VRAM va pagato col calo di slot esperti." },
          ]}
        />
        <Table
          columns={["Benchmark", "Cosa misura", "Note"]}
          rows={[
            ["HumanEval / MBPP", "Codice da zero", "Il lookup aiuta poco qui"],
            ["Trace di edit di codice (rename, refactor)", "Ripetizione dal contesto", "Dove lookup e n-gram rendono"],
            ["MT-Bench", "Chat multi-turno", "Controllo che non si perda velocità"],
            ["SpecBench", "Mix standard di spec decoding", "Confronto con la letteratura"],
            ["Trace agentici con tool call", "JSON, ripetizioni fra richieste", "Per H2 e H8"],
            ["Prompt lunghi (32K–128K)", "Costo per riga che cresce col contesto", "La DraftPolicy ha bucket per contesto"],
          ]}
        />
        <Text>Metriche: tok/s di decode (mediana su coppie interleaved), tokens per pass di verifica, accettazione per posizione, righe sprecate per finestra, speedup contro --spec 1, VRAM del drafter e slot esperti persi, identità greedy.</Text>
      </Section>

      <Section heading="Squadra proposta">
        <Table columns={["Ruolo", "Mandato", "Input", "Output"]} rows={TEAM} />
      </Section>

      <Section heading="Cosa non è verificato">
        <NumberedList
          items={[
            "Il numero esatto di tokens/pass di Strata su AMD per prompt di codice e di chat: i dati pubblici sono soprattutto tok/s.",
            "La configurazione --spec 4 --spec-min-p 0.65 --mtp rt indicata dall'utente: non l'ho trovata nelle fonti pubbliche; il default documentato è --spec 4 --spec-min-p 0.5.",
            "Se llama.cpp esegue draft-mtp e draft-eagle3 insieme: la documentazione non lo dice.",
            "Che SGLang NGRAM sia solo CUDA: lo indica un riassunto della documentazione, da riconfermare.",
            "Speculative decoding di llama.cpp su HIP con MTP di Qwen3.8: plausibile, non testato.",
            "Lo stato finale dell'issue #1161 (pool n-gram): risulta chiusa, non ho letto come.",
            "Tutti i guadagni marcati come stima nelle ipotesi.",
          ]}
        />
      </Section>

      <Section heading="Fonti principali">
        <LinkCards
          links={[
            { title: "Strata — repository", site: "github.com", href: "https://github.com/Niko1221/Strata" },
            { title: "Strata — DraftPolicy (MTP vs lookup)", site: "github.com", href: "https://github.com/Niko1221/Strata/blob/main/include/strata/spec/draft_policy.hpp" },
            { title: "Strata in the source (analisi del codice)", site: "ai.thesatyajit.com", date: "2026-10-06", href: "https://ai.thesatyajit.com/articles/strata-engine" },
            { title: "Qwen3.8-Flash-Next — model card", site: "huggingface.co", href: "https://huggingface.co/Qwen/Qwen3.8-Flash-Next" },
            { title: "Colibri — MTP drafts and prompt lookup", site: "github.com", href: "https://github.com/JustVugg/colibri/blob/main/docs/speculative.md" },
            { title: "llama.cpp — speculative decoding docs", site: "github.com", href: "https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md" },
            { title: "Speculative decoding in vLLM on AMD GPUs", site: "vllm.ai", date: "2026-08-23", href: "https://vllm.ai/blog/2026-08-23-speculative-decoding-amd-gpus" },
            { title: "DFlash2 per Qwen3.8-Flash-Next (fork vLLM)", site: "github", date: "2026-10-19", href: "https://github.cnmirror.space/wtdcode/vllm-backport/pull/128" },
            { title: "Strata PR #3457 — DFlash2 su Metal", site: "github.com", href: "https://github.com/Niko1221/Strata/pull/3457" },
            { title: "Not-a-Bandit (HedgeSpec)", site: "arxiv.org", href: "https://arxiv.org/abs/2510.20064" },
            { title: "Learning to Draft", site: "arxiv.org", href: "https://arxiv.org/abs/2603.01639" },
            { title: "AMD PARD", site: "amd.com", href: "https://www.amd.com/en/developer/resources/technical-articles/accelerating-generative-llms-interface-with-parallel-draft-model-pard.html" },
          ]}
        />
      </Section>
    </Page>
  );
}


```
