# IP-SAKTI Sahayak — Master Frontend Build Execution Prompt
**SIH 2026 · SIH26045 · Ministry of Ayush · Software · Team Owner (Frontend/Integration): Faizan Khan**

---

## 0. How to use this document

This is the single file you paste into your coding agent (Claude Code, Antigravity, whatever you're running). It supersedes nothing in your 49-page Technical Execution Plan — it sits *on top of it* as the frontend/experience layer spec. Paste this whole document as context once, then feed the agent **one numbered prompt at a time** from Section 9. Never skip ahead — each prompt assumes the previous one's acceptance criteria are met.

Two source documents are the twin ground truth. Never let the agent violate either:

1. **Technical Execution Plan (49 pages)** — defines the backend contract: classification → law → RAG → citation → confidence/abstention. This is functional law. Not up for creative reinterpretation.
2. **This document** — defines how that pipeline is *experienced* by a user and a judge, through the Baba character and the 3D/voice layer.

**The one rule that overrides every other instruction in this file:** the visual layer illustrates real backend state. It never performs a stage that hasn't actually happened.

---

## 1. Ground truth & non-negotiables

- Backend flow is fixed: `classify → (clarify if ambiguous) → retrieve → rerank → validate evidence → generate → cite → confidence/abstain`. The frontend orchestrates none of this logic — it only calls `POST /api/answer` and renders what comes back.
- TKDL is never claimed as accessed. If the Baba is ever asked about it, he uses the exact safe statement from Section 3 of the Execution Plan, no paraphrase that could imply more.
- India and international jurisdictions are never blended in one answer, visually or verbally.
- Confidence is computed mechanically by the backend (Section 10 of the plan) — the frontend never invents or softens a confidence tier for dramatic effect.
- Voice is a delivery layer, not a decision layer. STT converts speech to text; TTS converts the backend's answer to speech. No business logic lives between those two conversions.
- Abstention is designed to look like *competence*, not failure. No sad states, no error-red panic screens — a calm, deliberate "here's what's missing" moment.

---

## 2. Reality-vs-Visualization contract

This table is the spec the agent must implement literally — every visual beat maps to one real backend/frontend event, and *only* that event triggers it.

| Backend/frontend event | Baba does | Environment does | UI shows |
|---|---|---|---|
| User says wake phrase / taps mic | Head lifts, eyes focus to camera | Ambient light warms slightly | Mic permission prompt if needed |
| `POST /api/answer` request sent | Attentive posture, listening animation | — | Waveform on input |
| STT transcript received | Slight nod | — | Transcript text appears, editable |
| `classification.started` | Thoughtful expression | Slight environment dim | "Understanding your formulation…" |
| `classification.requires_clarification` | Asks the question aloud | — | Clarification card + quick-reply chips |
| `classification.completed` | Confirms with a small gesture | — | Classification card (category, confidence, reasoning) |
| `retrieval.started` | Turns toward library, shrinks to PiP | Library panel expands | "Searching authoritative sources…" |
| `retrieval.documents_found` (N chunks) | Selects/opens a book per chunk (capped visual count, not 1:1 literal) | Book glow / shelf highlight | Evidence cards populate one by one |
| `evidence.validation_started` | Reads intently | — | "Validating evidence…" |
| `evidence.validation_completed` | Closes book, turns back | — | Evidence cards lock (checkmark) |
| `answer.generated` | Returns to full frame | Library recedes | Answer text streams in |
| Citation rendered | Gestures toward citation on speak | Citation pulses once | Inline numbered citation, clickable |
| `voice.speaking` (TTS start) | Lip-sync active, calm posture | — | Captions synced under Baba |
| `voice.finished` | Returns to idle/ready | — | Follow-up prompt shown |
| `answer.abstained` | Closes book gently, open palm gesture (not slumped/sad) | Library dims, doesn't disappear | Red-family badge (see §4) + "Here's what's missing" panel |
| Jurisdiction mismatch detected | Explains verbally, gestures to selector | Selector pulses | Explicit "outside current scope" message |
| Any downstream service timeout/503 | Calm "still working" loop, never frozen mid-gesture | — | "This is taking longer than usual" + retry, never a blank screen |

If an agent-generated feature isn't in this table, it doesn't ship without adding a row here first.

---

## 3. One authoritative state machine

Two overlapping state lists exist in the source material (frontend orchestration states and Baba animation states). Collapse them into **one** machine — scattered parallel state trackers are how demo-day desync bugs happen.

```
IDLE
 → WAKE            (wake phrase / mic tap)
 → LISTENING        (mic active, STT running)
 → TRANSCRIBING      (partial transcript streaming)
 → UNDERSTANDING       (POST /api/answer sent, awaiting classification)
 → CLARIFICATION         (classification.requires_clarification)
      ↺ back to UNDERSTANDING on user reply
 → CLASSIFYING              (classification.completed, brief confirm beat)
 → SEARCHING                   (retrieval.started)
 → EVIDENCE_FOUND                  (retrieval.documents_found)
 → VALIDATING                          (evidence.validation_started/completed)
 → GENERATING                              (answer streaming)
 → ANSWER_READY                                (full answer + citations rendered)
 → SPEAKING                                        (TTS active, lip-sync driven)
 → FOLLOW_UP                                            (ready for next turn → back to LISTENING)

Side branches from any state:
 → ABSTAINING   (evidence.validation fails / confidence = insufficient)
 → ERROR        (network/service failure, 503, timeout)
 → SLEEP        (no interaction for N seconds, from FOLLOW_UP or IDLE)
```

Each state owns exactly: Baba animation clip, camera position, UI panel visible, progress copy, audio cue. One state = one row in the Section 2 table = one Zustand/Redux slice value. No boolean flags scattered across components (`isLoading`, `isSearching`, `isSpeaking` living independently is exactly what to avoid).

---

## 4. Design system

Grounded choice, not a generated-page default. Deliberately avoiding: cream+terracotta, near-black+neon, uniform SaaS card kit, ALL-CAPS eyebrows, middle-dot meta strings, arrows appended to buttons.

**Color** — aged manuscript + turmeric, not a chatbot palette:
- `--ink-900: #1C1712` — background, deep warm charcoal-brown (not pure black)
- `--parchment-100: #EDE6D6` — evidence panels, cards, aged-paper tone
- `--turmeric-500: #C98A2B` — primary accent, active states, links
- `--sage-600: #5B7B4F` — high confidence / verified state
- `--clay-500: #B85C38` — low confidence
- `--ash-600: #7A4A42` — insufficient evidence / abstention (muted red-brown, not alarm red — abstention reads as composed, not broken)
- `--indigo-700: #3A4A63` — jurisdiction / structural UI chrome

**Type** — two families, clearly distinct roles:
- **Fraunces** (serif, optical sizing) for the Baba's spoken lines, screen headlines, classification result headline — carries the manuscript/heritage voice.
- **Source Sans 3** for body copy, evidence text, forms, buttons — legible, government-document-appropriate, no heritage cosplay where precision matters.
- Sentence case everywhere. No tracked-out caps labels. Line length under 80 characters in evidence panels.

**Layout** — asymmetric, not a centered hero:
```
Desktop:
┌─────────────────────────────┬───────────────┐
│                             │               │
│      BABA STAGE (left,      │  EVIDENCE /   │
│      ~60% width)            │  LIBRARY      │
│                             │  (right,      │
│  [transcript / captions]    │  collapsible) │
│                             │               │
└─────────────────────────────┴───────────────┘
```
Baba is the anchor, not a centered mascot in a hero banner. Evidence panel slides in from the right only when retrieval starts — it does not exist as dead space beforehand.

**Motion** — one orchestrated sequence per state transition, not scattered hover effects. The library-expand-on-retrieval is the single "wow" beat; everything else (button hover, card entry) is quiet and fast (150–200ms).

**Confidence badges** — shape + color + text, never color alone: a filled circle icon (●) whose fill level (full/half/quarter/empty) redundantly encodes tier alongside the color, so it isn't relying on color perception.

---

## 5. Technology stack — realistic for a 36-hour build

| Layer | Choice | Why |
|---|---|---|
| 3D scene | **Three.js via React Three Fiber + Drei** | You already know React; R3F keeps the scene declarative and integrates with your existing component tree instead of a separate imperative Three.js app |
| Baba character | **Pre-rigged GLB model** (Mixamo or ReadyPlayerMe base, re-skinned/re-textured, not modeled from scratch) | Modeling a character from zero in a hackathon is the #1 way to burn 20 hours on 3D polish nobody scores |
| Baba animation | **Morph targets for facial expression + a small animation clip library** (idle/listen/think/speak/abstain — 5-6 clips max) | A full animation state machine per micro-state is unnecessary; 5-6 clips blended covers the whole table in §2 |
| Lip sync | **Amplitude-based mouth-open animation driven by TTS audio**, not phoneme/viseme mapping | Viseme-accurate lip sync needs a phoneme pipeline you don't have time to build; amplitude-driven jaw movement reads as "speaking" convincingly enough for a judge at demo distance |
| Camera/transitions | **GSAP** for camera moves and PiP collapse/expand | More reliable timeline control than CSS transitions for the library-expand sequence |
| 2D UI (cards, panels, badges) | **Standard React + Tailwind**, NOT 3D | Evidence cards, citations, confidence badges are text-heavy and need to be selectable/scannable — keep them flat DOM, overlaid on the 3D canvas |
| STT | **Web Speech API** (browser-native) with a push-to-talk fallback button | Wake-word detection ("Hey Ayurvedic AI") is not reliably available cross-browser — build push-to-talk as the real MVP path, wake-word as a stretch enhancement layered on top, never the only path |
| TTS | **Web Speech API SpeechSynthesis**, or a hosted TTS API if voice quality budget allows | Native browser TTS has zero setup cost and works offline-ish; only reach for a paid API if judges' first impression of voice quality becomes a real concern in testing |
| State management | **Zustand** | Lighter than Redux for a single state machine (§3), less boilerplate under time pressure |

What stays 2D/CSS regardless of how tempting 3D is: evidence panel, citation list, classification card, confidence badge, clarification chips, source viewer modal, settings. **Only the Baba and his immediate library environment are 3D.** Everything the judge needs to read stays flat and fast.

---

## 6. Frontend folder structure

Extends the base structure already frozen in Execution Plan §13.4 — does not replace it.

```
frontend/src/
├── components/          # ChatWindow, EvidencePanel, ClassificationCard,
│                         JurisdictionSelector, ConfidenceBadge,
│                         AbstentionCard, SourceViewerModal, HistorySidebar
├── baba/
│   ├── BabaScene.tsx     # R3F canvas root
│   ├── BabaModel.tsx     # GLB loader + morph target rig
│   ├── BabaAnimations.ts # clip library + blend logic
│   └── LipSync.ts        # amplitude-driven jaw driver
├── scenes/
│   ├── LibraryScene.tsx  # bookshelf/library environment, PiP transitions
│   └── LightingRig.tsx
├── voice/
│   ├── useSTT.ts         # Web Speech API wrapper, push-to-talk fallback
│   ├── useTTS.ts         # SpeechSynthesis wrapper, captions sync
│   └── VoiceControls.tsx # mic button, mute, replay, interrupt
├── state/
│   └── conversationMachine.ts  # the ONE state machine from §3 (Zustand)
├── animations/
│   └── transitions.ts    # GSAP camera/PiP sequences
├── overlays/
│   └── CaptionOverlay.tsx
├── hooks/
├── services/             # apiClient.ts, answerService.ts, historyService.ts
├── store/
└── types/                # shared with backend per Execution Plan §22
```

---

## 7. Screen inventory (condensed)

| # | Screen | Key components | Backend dependency |
|---|---|---|---|
| 1 | Landing / awakening | BabaScene (idle), voice hint, text-input fallback | none |
| 2 | Listening / transcript | VoiceControls, CaptionOverlay | STT only |
| 3 | Clarification | ClarificationCard, quick-reply chips | `/api/classify` (via `/api/answer`) |
| 4 | Classification result | ClassificationCard | `/api/answer` |
| 5 | Processing / library | LibraryScene, progress copy | `retrieval.*` events |
| 6 | Evidence + citations | EvidencePanel, inline citations | `/api/answer` response |
| 7 | Answer + confidence | Answer text, ConfidenceBadge | `/api/answer` response |
| 8 | Abstention | AbstentionCard (calm, not error-styled) | `abstained: true` |
| 9 | Jurisdiction switch | JurisdictionSelector | `/api/answer` jurisdiction field |
| 10 | Source viewer | SourceViewerModal | `/api/sources` |
| 11 | History | HistorySidebar | `/api/conversations/:id` |
| 12 | Settings (voice/language) | Settings panel | none |
| 13 | Judge dashboard (optional) | corpus stats, eval pass-rate | `/evaluate`, manifest.json |
| 14 | Mobile: full-screen Baba + bottom-sheet evidence | responsive variants of above | same APIs |

---

## 8. Non-negotiable fallback & accessibility rules

- Voice must never be the only way to use the product — a text input and click-driven UI always work.
- No 3D/WebGL → static Baba illustration + full 2D flow. Detect and degrade automatically, don't ask the user to "enable WebGL."
- TTS fails → captions still render from the same text; conversation continues silently.
- Mic permission denied → push-to-talk button becomes a text box, one click away, not a dead end.
- RAG/classification service down (503) → explicit "service degraded" message, never a frozen spinner or silent crash. This is a hard gate already defined in Execution Plan §13.2 — the frontend must render it, not swallow it.
- Reduced-motion preference respected: library-expand and camera moves collapse to instant cuts.
- Keyboard-only path exists for every interactive element; captions/transcript satisfy screen-reader needs for the voice layer.

---

## 9. Implementation order — 16 sequential agent prompts

Feed these to your coding agent **one at a time, in order**. Each is self-contained; don't let the agent jump ahead or "helpfully" pre-build later steps.

### Prompt 1 — Base product shell
**Objective:** Scaffold the React + TypeScript + Tailwind app with routing, base layout (§4 asymmetric grid), and the design tokens from §4 as CSS variables/Tailwind theme.
**Files:** `frontend/` root, `tailwind.config.ts`, `src/App.tsx`, `src/index.css`
**Acceptance:** App boots, empty Baba-stage/evidence-panel layout visible, correct colors/fonts loaded, responsive breakpoints from §7 in place.
**Do not:** Add any 3D, voice, or API calls yet.

### Prompt 2 — Conversation state machine
**Objective:** Implement the single state machine from §3 in Zustand. No UI wiring yet — just the machine, transitions, and a debug panel that prints current state.
**Files:** `src/state/conversationMachine.ts`
**Acceptance:** Every state and transition in §3 exists; invalid transitions are rejected with a console warning, not silently allowed.
**Do not:** Create parallel boolean flags (`isLoading`, etc.) anywhere in the app going forward.

### Prompt 3 — Static Baba (no animation, no voice)
**Objective:** Load the GLB model in `BabaScene.tsx` via R3F, render idle pose, correct lighting per §5.
**Files:** `src/baba/BabaScene.tsx`, `src/baba/BabaModel.tsx`
**Acceptance:** Baba renders correctly on desktop and mobile viewport sizes; WebGL-unavailable fallback (static image) verified by disabling WebGL in devtools.
**Do not:** Wire any state machine events yet — Baba is decorative at this step.

### Prompt 4 — Mock conversation (fake data)
**Objective:** Build ChatWindow + hardcoded mock `/api/answer` responses (use the mock JSON from Execution Plan §25/34.3) driving the state machine end-to-end with fake delays.
**Files:** `src/components/ChatWindow.tsx`, `src/services/mockApi.ts`
**Acceptance:** Full state machine cycle (idle → listening → … → answer_ready → follow_up) runs on a button click with fake data, no real backend needed yet.
**Do not:** Call real endpoints. This step proves the UI flow in isolation.

### Prompt 5 — STT integration
**Objective:** Implement `useSTT.ts` (Web Speech API + push-to-talk fallback), wire into LISTENING/TRANSCRIBING states.
**Files:** `src/voice/useSTT.ts`, `src/voice/VoiceControls.tsx`
**Acceptance:** Real transcript appears from real microphone input; push-to-talk fallback works identically when wake-word/continuous listening is unavailable.
**Do not:** Touch TTS or backend integration yet.

### Prompt 6 — TTS + Baba speaking
**Objective:** Implement `useTTS.ts`, wire SPEAKING state to amplitude-driven lip sync (§5) and caption overlay.
**Files:** `src/voice/useTTS.ts`, `src/baba/LipSync.ts`, `src/overlays/CaptionOverlay.tsx`
**Acceptance:** Given mock answer text, Baba's mouth animates while captions render in sync; TTS failure falls back to captions-only per §8.
**Do not:** Connect to real backend answers yet — keep using mock text from Prompt 4.

### Prompt 7 — Real API event bridge
**Objective:** Replace `mockApi.ts` with real `POST /api/answer` calls per Execution Plan §22, mapping response fields and streaming/event points to state machine transitions.
**Files:** `src/services/answerService.ts`, `src/services/apiClient.ts`
**Acceptance:** Real backend `/api/answer` call drives the full state machine; 503/timeout triggers the ERROR state fallback from §8, not a crash.
**Do not:** Change any backend contract shapes — if a field is missing, flag it as a bug for Faizan/Person 2, don't invent one.

### Prompt 8 — Classification visuals
**Objective:** Build `ClassificationCard.tsx` and clarification chip UI per §7 screen 3-4, wired to `classification.requires_clarification` / `classification.completed`.
**Files:** `src/components/ClassificationCard.tsx`
**Acceptance:** Matches Execution Plan §7's worked example output exactly (category, confidence, reasoning, clarification questions rendered as tappable chips).
**Do not:** Let the frontend make its own classification decisions — it only renders what `/api/answer` returned.

### Prompt 9 — Library / processing scene
**Objective:** Build `LibraryScene.tsx` — PiP collapse of Baba, library expand, book-selection animation — triggered strictly by `retrieval.started`/`retrieval.documents_found` events per §2's table.
**Files:** `src/scenes/LibraryScene.tsx`, `src/animations/transitions.ts`
**Acceptance:** Animation timing is driven by real event arrival, not a fixed fake duration — if retrieval takes 200ms or 4s, the visual matches, it doesn't fake a fixed "3 second search" every time.
**Do not:** Show library results before `retrieval.documents_found` actually fires.

### Prompt 10 — Evidence panel + citations
**Objective:** Build `EvidencePanel.tsx` and inline citation markers per Execution Plan §9's citation object fields.
**Files:** `src/components/EvidencePanel.tsx`
**Acceptance:** Every rendered citation has document title, authority, section, source URL, version, snippet — all pulled from the real citation object, none invented client-side.
**Do not:** Render a citation the backend didn't return, even for visual polish.

### Prompt 11 — Confidence + abstention
**Objective:** Build `ConfidenceBadge.tsx` (4-tier, shape+color per §4) and `AbstentionCard.tsx` (calm, composed tone per Execution Plan §10).
**Files:** `src/components/ConfidenceBadge.tsx`, `src/components/AbstentionCard.tsx`
**Acceptance:** Tier and abstention state come directly from `confidence_level`/`abstained` fields; abstention copy explains what's missing, never reads as an error state.
**Do not:** Let the LLM's own text override the mechanically-computed confidence tier.

### Prompt 12 — Jurisdiction switch
**Objective:** Build `JurisdictionSelector.tsx` per Execution Plan §11/§28, including the explicit out-of-scope message for cross-jurisdiction questions.
**Files:** `src/components/JurisdictionSelector.tsx`
**Acceptance:** Switching jurisdiction never blends prior India-context answer with new selection; out-of-scope questions show the explicit limitation message, not an improvised answer.
**Do not:** Imply broader country coverage than the "International (PCT overview + CBD-related principles only)" label allows.

### Prompt 13 — Responsive pass
**Objective:** Implement the desktop/laptop/tablet/mobile breakpoints from §5 and §7 screen 14.
**Files:** all above components, Tailwind responsive classes
**Acceptance:** Full flow (voice → classification → evidence → answer) works and is legible at 375px mobile width; Baba goes full-screen with bottom-sheet evidence on mobile.
**Do not:** Cut voice controls on mobile — mobile is voice-first, not voice-optional.

### Prompt 14 — History + source viewer
**Objective:** Build `HistorySidebar.tsx` and `SourceViewerModal.tsx` per Execution Plan §13.1/§22.
**Files:** `src/components/HistorySidebar.tsx`, `src/components/SourceViewerModal.tsx`
**Acceptance:** Conversation history persists per session via `/api/conversations/:id`; source viewer shows cached snapshot fallback if live URL fetch fails (per Execution Plan §32 risk register).
**Do not:** Build user authentication beyond the existing session-token stub — out of MVP scope per Execution Plan §26.

### Prompt 15 — Fallback/demo mode
**Objective:** Wire the full mock-mode path (Prompt 4's fixtures) as a one-flag runtime fallback (`--demo-mode`) for use if live services fail during judging.
**Files:** `src/services/mockApi.ts` (revived), a demo-mode toggle
**Acceptance:** Flipping the flag reproduces a full, convincing demo run with zero live network dependency, matching Execution Plan §29's local-fallback requirement.
**Do not:** Let demo mode be discoverable/toggleable by a judge accidentally — gate it behind a dev-only key combo or env flag.

### Prompt 16 — Performance & accessibility pass
**Objective:** GLB compression/LOD, lazy-load the 3D bundle behind a loading placeholder, reduced-motion handling, keyboard nav audit, screen-reader labels on all interactive elements per §8.
**Files:** all above
**Acceptance:** Time-to-first-interaction under a few seconds on a mid-range laptop; reduced-motion setting collapses all camera/library animations to instant cuts; full flow completable via keyboard alone.
**Do not:** Sacrifice the mobile voice-first flow for desktop performance gains.

---

## 10. Judge-facing non-negotiables (recap for the Baba's dialogue and all UI copy)

- Never say "I checked TKDL" — use the exact safe statement from Execution Plan §3.
- Never state a patent will definitely be granted or rejected.
- Never blend India and international answers in one response.
- Never present a low/insufficient confidence answer with high-confidence styling.
- Abstention is a demo strength, not something to hide — Section 31 of the Execution Plan explicitly recommends showing it live to judges. Make sure the abstention state actually looks *good* on stage.

This document plus the Technical Execution Plan is everything your agent needs to start on Prompt 1. Good luck.
