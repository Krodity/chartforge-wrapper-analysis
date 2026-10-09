# ChartForge 1.6.0: Desktop Wrapper Analysis and AI-Authorship Assessment

| | |
|---|---|
| **Subject** | `chartforgev1.6.0.AppImage` (ChartForge 1.6.0, Linux x86-64) |
| **SHA-256** | `1c257f653ac694334d9b2413cc2a7a6ddaa9c039a5b34986cde74aabdf493a34` |
| **Size** | 109,110,068 bytes |
| **Build time** | 2026-09-28 21:50 (squashfs creation time) |
| **Analysis date** | 2026-10-09 |
| **Method** | Static analysis only. The binary was never executed. |
| **Scope** | The desktop wrapper (4 files, §1.1) |

---

> **Note on scope.** This is an independent technical analysis of a freely distributed but proprietary application (`"license": "UNLICENSED"`). It includes no ChartForge source code beyond short excerpts quoted for commentary. The AI-authorship section is an evidence-based opinion; no method can prove whether code was written by AI.

## 1. Summary

ChartForge is a chart editor for rhythm games (Clone Hero / Rock Band style: 5-fret, 6-fret, drums, pro drums, vocals). It is a browser JavaScript application that uses three.js for 3D rendering, packaged inside an Electron 31 desktop wrapper.

### 1.1 Scope

The editor core is obfuscated, so this analysis focuses on the **desktop wrapper**: `main.js`, `preload.js`, `app/js/desktop-native.js` and `app/js/desktop-popout.js`, 1,936 lines in total.

### 1.2 Verdict

Likelihood that the desktop wrapper is substantially AI-written: **high, about 85–90%**.

The wrapper was very likely written mostly by an AI coding agent, directed by a human who knows the rhythm-game ecosystem well.

No method can prove AI authorship. These figures are an engineering judgement based on the evidence in section 5.

---

## 2. Unpacking procedure

The steps below can all be repeated, and none of them runs the target.

### 2.1 AppImage → squashfs

An AppImage is an ELF runtime with a squashfs image appended to it. I avoided `--appimage-extract` because it executes the binary. Instead I searched the file for the squashfs magic `hsqs`. It first appears at offset 32609, but that is a false positive inside the runtime. A valid superblock starts at **offset 188392**.

```sh
unsquashfs -s -o 188392 chartforgev1.6.0.AppImage   # superblock check
unsquashfs -q -o 188392 -d squashfs-root chartforgev1.6.0.AppImage
```

### 2.2 Electron payload

The extracted root is a standard `electron-builder` Linux layout: the `chartforge` Electron binary, Chromium `.pak` files, SwiftShader/Vulkan libraries, and `resources/app.asar` (8.9 MB). Strings in the binary identify the runtime as **Electron 31.7.7 / Chromium 126.0.6478.234**.

```sh
npx @electron/asar extract squashfs-root/resources/app.asar app
```

`resources/app-update.yml` points the updater at a generic HTTPS feed:

```yaml
provider: generic
url: https://chart-forge.app/
updaterCacheDirName: chartforge-updater
```

### 2.3 The wrapper files

The analysed wrapper is four files in the extracted `app/` directory: `main.js` and `preload.js` (main process and bridge), and `app/js/desktop-native.js` and `app/js/desktop-popout.js` (renderer side).

### 2.4 What this repository contains

This repository contains **only the analysis**: these reports, the line-count data, and the counting script. It contains no ChartForge code or binaries. Everything in the report can be reproduced from your own copy of the AppImage using Appendix A.

---

## 3. Architecture of the wrapper

### 3.1 Process model

```
┌──────────────────────────── main process (main.js, 645 lines) ───────────────────────────┐
│ startup log → <userData>/startup.log    electron-updater (opt-in, 6 h recheck)           │
│ native file IPC (cf-*)                  window-open policy / navigation lock             │
│ multi-window tab drag/hand-off broker   unsaved-changes dialog                           │
└───────────────▲──────────────────────────────────────────────────────────────────────────┘
                │ ipcRenderer.invoke / on   (contextBridge → window.cfNative)
┌───────────────┴──── renderer (sandbox:true, contextIsolation:true, nodeIntegration:false) ┐
│ app/index.html → 20 classic <script> tags sharing one global scope                        │
│ editor scripts + desktop-popout.js + desktop-native.js                                    │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

The renderer runs with `sandbox: true`, `contextIsolation: true` and `nodeIntegration: false`. The preload script exposes a short list of promise-returning functions as `window.cfNative`. Pop-out windows get the same settings.

The two renderer-side wrapper files are loaded last, after the editor's own scripts. Both describe themselves as *"Purely additive — no app code is modified"*. They hook into the editor's existing functions and DOM instead of changing them, which suggests the core was first built as a web app and the desktop layer was added afterwards.

### 3.2 IPC surface (`preload.js` → `main.js`)

| Channel | Direction | Purpose |
|---|---|---|
| `cf-open-chart-dialog` | invoke | Native open dialog. Opening a single chart also loads its folder companions |
| `cf-read-chart-bundle` | invoke | Chart path → chart + `song.ini` + audio stems + `album.*`. Video files are referenced by path and streamed, not read into memory |
| `cf-save-chart-dialog` | invoke | Save dialog, MIDI only |
| `cf-save-json-folder` | invoke | Pick a directory and write the exported `.json` folder. File names are sanitised |
| `cf-write-file` | invoke | Write a saved chart's bytes to disk |
| `cf-open-editor-window` | invoke | Open a second editor window for a torn-off tab |
| `cf-tab-drop-target` / `cf-tab-drag-end` / `cf-tab-hand-off` / `cf-tab-adopted` | invoke | Moving tabs between windows (4-step handshake) |
| `cf-tab-drag-over` / `cf-tab-incoming` / `cf-tab-adopt-confirmed` | main → renderer | Notifications for the steps above |

Tab hand-off uses a two-phase commit. The source window keeps its copy of the chart until the target window confirms with `cf-tab-adopted`, so the chart cannot be lost between windows. The main process tracks which window the pointer is over, because a renderer with pointer capture cannot see outside its own frame.

### 3.3 Pop-out windows (`desktop-popout.js`)

This is the most technically interesting part of the wrapper. Floating panels are made into real OS windows by:
- opening a same-origin child window with `window.open(…, 'popout-*')`, which `main.js` turns into a frameless, transparent `BrowserWindow`;
- **physically moving the panel's DOM nodes** into the child document, so all state, closures and listeners keep working;
- patching `document.getElementById` / `querySelector(All)` on the main document so they also search popped-out documents;
- mirroring the app's globals onto each child window, because inline `on*` attributes compile against the element's owner window;
- **re-assigning inline `on*` attributes after every move**, because a handler compiled once stays bound to the window it was compiled in, even after that window is gone;
- dragging the titlebar by hand (pointer capture + `window.moveTo`) instead of using `-webkit-app-region`, so the drag can be hit-tested against the main window's dock zones and the panel can re-dock.

### 3.4 File handling (from the wrapper's dialogs and loaders)

- **Open dialog accepts:** `.mid`, `.midi`, `.chart`, `.sng`, `.ini`, audio (`.ogg`, `.mp3`, `.wav`, `.opus`, `.flac`) and video (`.mp4`, `.webm`, `.m4v`).
- **Folder companions:** opening a single chart also loads `song.ini`, audio stems and `album.png/jpg/webp/gif/bmp` from the same folder. It skips `preview.*` files, which are listening clips rather than stems.
- **Save:** writes MIDI only. When the opened file was `.chart` or `.sng`, the original is never overwritten.
- **Export:** a `.json` chart folder, written into a directory the user picks.

### 3.5 Third-party code

| Package | Version | Notes |
|---|---|---|
| electron | 31.7.7 | Released mid-2024 and out of support at analysis time |
| electron-updater | 6.8.9 | Generic provider, `autoDownload = false`, asks before downloading |
| three | 0.128.0 | Ships as `vendor/three.min.js` |

---

## 4. Network behaviour (wrapper and `index.html`)

The wrapper and page shell make three kinds of network connection:
- **Auto-updates.** `electron-updater` checks `https://chart-forge.app/` at launch and every 6 hours. Nothing downloads until the user agrees, and declined versions are not offered again in the same session.
- **The feedback link.** `https://chart-forge.app/tracker/` opens in the system browser.
- **A three.js fallback.** If the bundled `vendor/three.min.js` fails to define `THREE`, `index.html` uses `document.write` to load three.js r128 from cdnjs.

The wrapper contains no telemetry or analytics.

---

## 5. AI-authorship assessment (desktop wrapper)

### 5.1 Approach

There is no reliable automated detector for AI-written code, so this is a judgement of style. I weighted each piece of evidence by how specific it is to AI coding agents compared with skilled human developers. Every observation below comes from the four readable wrapper files.

### 5.2 Evidence

**(a) Comment density and register.** Across the four files, comment lines equal **34.8% of the number of code lines**: about one comment line for every three lines of code. That is 2.2–4.6× the density of the human-written libraries bundled in the same package (§5.3). Most of these comments are full prose paragraphs explaining *why*, often naming the failure they prevent:

> ```js
> // The bar starts as an INDETERMINATE animation. Real progress events
> // switch it to a determinate fill; if the updater never emits progress
> // (differential downloads or a feed server without Content-Length do
> // this), the animation honestly shows "working" instead of a frozen 0%.
> ```

Thorough human developers do write comments like this. Writing them consistently, on every block, in this explanatory voice, is typical of LLM output.

**(b) Recognisable LLM phrasing.** Human engineers rarely put these phrases in code comments, but they are common in current LLM output:

| Phrase | Location |
|---|---|
| "the animation **honestly** shows 'working'" | `main.js:82` |
| "'old version until the next restart', **literally**." | `main.js:46` |
| "which is **exactly what we want** — no extra handling needed." | `main.js:480` |
| "logging **must never** break the app" / "the editor **must still** launch" | `main.js:16`, `:32` |
| "Zero dependencies." (a short sentence fragment used for emphasis) | `main.js:7` |
| "Offline or feed unreachable is routine — log, never bother the user." | `main.js:189` |

The four files contain **27 em-dashes (—)**. Developers rarely type that character into source code, but LLMs produce it constantly.

**(c) Comments that describe the change, not the code.** Both readable renderer files open with:

> `Purely additive — no app code is modified.`

This sentence is addressed to whoever reviews the patch. It reports the scope of an edit, which is how a coding agent summarises its own work. It tells a future reader of the file nothing useful. This is one of the most telling signs in the sample.

**(d) Leftover duplicate comment.** `main.js:499–504` has two comments in a row, each describing the same variables in different words:

```js
// Which editor window the cursor is over, for a tab dragged out of one window
// and dropped onto another. The dragging renderer has pointer capture and sees
// nothing outside its own frame, so only the main process can answer this.
// The window a dragged tab is currently hovering over, so it can show a drop
// indicator of its own. Only the source window sees the pointer, so it is the
// main process that has to tell the other side anything is happening.
let _tabDragHoverWinId = null;
```

This is a common artefact of iterative agent editing: a new block is inserted and the comment it replaced is left behind. A human editing by hand would almost always replace the old comment.

**(e) Capitals for emphasis.** "physically **MOVING** their DOM", "the renderer receives **ZERO** events", "**BY THEIR TITLEBAR**", "**INDETERMINATE**", "**NATIVE** open dialog", "element **REMOVAL**". Capitalised words like these are a familiar trait of Claude/GPT-style technical writing.

**(f) Structured documentation headers.** Each file starts with a long block comment containing a numbered "What it does" or "Other glue this module provides: 1) … 4) …" list. These cross-reference other files and functions by name (`_redockPanel`, `_getDockTarget`, `handleFiles()`). That is the summary an agent writes after reading the whole codebase.

**(g) Defensive coding with a commented reason on every catch.** Nearly every `try/catch` gets a short comment naming the case it covers: `/* already gone */`, `/* window went away */`, `/* unreadable folder: chart alone */`, `/* skip unreadable companion */`.

**(h) Packaging leftovers.** `package.json` lists `"author": {"name": "ChartForge", "email": "you@example.com"}`. This is a placeholder from a template or a generated scaffold that nobody filled in.

**(i) Expert platform knowledge, delivered evenly.** The wrapper handles several genuinely obscure Chromium/Electron behaviours correctly:
- inline handlers that stay bound to their compile-time window;
- `-webkit-app-region` dragging, which hides pointer events from the renderer;
- OS shadows that are drawn around a transparent window's rectangular bounds;
- `will-prevent-unload` firing silently.

A senior Electron developer could know all of this. What stands out is that every finding is written up as a polished explanatory paragraph, and none of the code is terse or abbreviated. That evenness fits an agent that discovers each problem while testing and records it as it goes.

### 5.3 Comment density by file

Also available as a standalone file, with representative excerpts: [COMMENT-DENSITY.md](COMMENT-DENSITY.md).

**Method.** I counted lines with a small JavaScript-aware scanner (`tools/jsloc.py`). It tracks `//` and `/* */` comments, string and template literals, and regex literals, so a `//` inside a string or regex is not counted as a comment. Each physical line falls into exactly one category:

- **code**: contains at least one code token, including lines that also end in a comment;
- **comment-only**: a comment and nothing else;
- **blank**: empty or whitespace only.

**Trailing** counts the code lines that also end in a comment (`foo(); // why`). Those lines are already included in *code*.

The main ratio is **comment ÷ code** = (comment-only + trailing) ÷ code lines, meaning comment lines per line of code. The second ratio, **comment-only share**, is comment-only lines as a percentage of all non-blank lines. As a cross-check, the comment-only counts match `grep -cE '^\s*(//|/\*|\*)'` exactly for all four files, and code + comment-only + blank equals the total line count of each file. Raw output is in `comment-density.tsv`.

#### 5.3.1 Desktop wrapper (as shipped)

| File | Total lines | Code | Comment-only | Trailing | Blank | **Comment ÷ code** | Comment-only share |
|---|---:|---:|---:|---:|---:|---:|---:|
| `main.js` | 645 | 494 | 107 | 21 | 44 | **25.9%** | 17.8% |
| `preload.js` | 63 | 19 | 30 | 0 | 14 | **157.9%** | 61.2% |
| `app/js/desktop-native.js` | 288 | 226 | 42 | 9 | 20 | **22.6%** | 15.7% |
| `app/js/desktop-popout.js` | 940 | 624 | 236 | 29 | 80 | **42.5%** | 27.4% |
| **Total** | **1,936** | **1,363** | **415** | **59** | **158** | **34.8%** | **23.3%** |

Notes:
- **`preload.js` has more comment lines than code lines (30 vs 19).** Every one-line bridge function has a two-to-four-line comment above it describing its arguments and the shape of what it resolves to. That is generated API documentation written into an internal file that only one other file consumes.
- **`desktop-popout.js` is the densest real module**, with one comment line for every 2.4 lines of code. Its 49-line header block alone accounts for 18% of its comment lines (49 of 265).
- 59 code lines carry trailing comments, and almost all of them give a *reason* (`// closing it doesn't cancel the download`, `// typing must not trigger editor keybinds`). None of them is a TODO, FIXME, initials, or a commented-out line of code. I found **zero commented-out code** in all 1,936 lines. Human codebases almost always contain some, and edits made by an AI agent almost never leave any.

#### 5.3.2 Comparison with human-written code in the same package

The same scanner, run on hand-written libraries that ship in ChartForge's `node_modules`:

| Library | Files | Code lines | Comment lines (only + trailing) | **Comment ÷ code** |
|---|---:|---:|---:|---:|
| three.js `src/` (r128) | 373 | 31,470 | 3,013 | **9.6%** |
| electron-updater `out/` (compiled from TS) | 32 | 3,783 | 447 | **11.8%** |
| js-yaml `lib/` | 24 | 2,867 | 447 | **15.6%** |
| sax `lib/` | 1 | 1,616 | 123 | **7.6%** |
| graceful-fs | 4 | 742 | 80 | **10.8%** |
| **ChartForge wrapper** | 4 | 1,363 | 474 | **34.8%** |

These are mature, well-maintained libraries, many of which document their public APIs with JSDoc. They fall between 7.6% and 15.6%. ChartForge's wrapper is **2.2–4.6× denser**, and its comments explain internal reasoning, not public APIs. High comment density alone does not prove AI authorship, since some engineers write very literate code. But density on this scale, in this explanatory style, with no commented-out code and no TODOs, is the pattern I would expect from an LLM agent writing to explain itself to the next agent or reviewer.

### 5.4 Evidence against, and what would change my mind

- **The work shows real domain judgement.** Examples from the wrapper: skipping `preview.*` because it is a listening clip, not a stem; never overwriting a `.chart` with MIDI on save; streaming large videos instead of reading them into memory. Someone clearly knows the Clone Hero / Rock Band ecosystem. That someone could be the human directing the agent, so this points to AI *assistance*, not to the absence of AI.
- **What would lower the estimate:** an earlier release, a public repository, or the web version at `chart-forge.app` showing terse, abbreviated, idiosyncratic comments or a commit history of gradual human iteration.
- **What would raise it:** the same sources showing `CLAUDE.md`/`AGENTS.md` files, commits that touch the whole codebase at once, or the same LLM phrasing elsewhere.

### 5.5 Verdict

ChartForge 1.6.0's desktop wrapper is **very likely the product of AI-agent-driven development under human direction (about 85–90%).** It carries several independent and fairly specific signs of LLM authorship:
- comments that report the scope of the patch;
- a leftover duplicate comment;
- characteristic word choice and em-dash use;
- dense explanatory prose with capitals for emphasis;
- a placeholder author field.

The domain decisions show an engaged human who understands rhythm-game charting, most likely acting as the product owner and tester rather than writing the code line by line.

---

## Appendix A: Repeating the analysis

```sh
mkdir chartforge-extracted && cd chartforge-extracted
unsquashfs -q -o 188392 -d squashfs-root ../chartforgev1.6.0.AppImage
npx @electron/asar extract squashfs-root/resources/app.asar app
```

## Appendix B: Commands behind the key observations

```sh
python3 -I <this-repo>/tools/jsloc.py app/main.js app/preload.js app/app/js/desktop-*.js   # comment density per file
grep -o '—' app/main.js app/preload.js app/app/js/desktop-*.js | wc -l  # em-dash count (27)
sed -n 495,505p app/main.js                                            # duplicate comment
grep -n 'Purely additive' app/app/js/desktop-*.js                      # patch-scope comments
```
