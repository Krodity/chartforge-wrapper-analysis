# ChartForge 1.6.0: Comment Density by File

Companion to [REPORT.md](REPORT.md) (§5.3). It measures how many comment lines each source file contains relative to its lines of code, and compares the result with human-written libraries bundled in the same package.

- **Subject:** `chartforgev1.6.0.AppImage` (SHA-256 `1c257f653ac694334d9b2413cc2a7a6ddaa9c039a5b34986cde74aabdf493a34`)
- **Raw data:** [comment-density.tsv](comment-density.tsv)
- **Counter:** [tools/jsloc.py](tools/jsloc.py)
- **Excerpts:** a representative sample is in [Representative excerpts](#representative-excerpts). The full comment text is not reproduced here, to respect the author's copyright; `tools/jsloc.py --dump` regenerates it from your own copy.

**Summary:** the four desktop-wrapper files have **34.8% comment lines per line of code** (474 comment lines, 1,363 code lines). Mature human-written libraries in the same `node_modules` range from **7.6% to 15.6%**.

## Method

I counted lines with a small JavaScript-aware scanner (`tools/jsloc.py`). It tracks `//` and `/* */` comments, string and template literals, and regex literals, so a `//` inside a string or regex is not counted as a comment. Each physical line falls into exactly one category:

- **code**: contains at least one code token, including lines that also end in a comment;
- **comment-only**: a comment and nothing else;
- **blank**: empty or whitespace only.

**Trailing** counts the code lines that also end in a comment (`foo(); // why`). Those lines are already included in *code*.

The main ratio is **comment ÷ code** = (comment-only + trailing) ÷ code lines, meaning comment lines per line of code. The second ratio, **comment-only share**, is comment-only lines as a percentage of all non-blank lines. As a cross-check, the comment-only counts match `grep -cE '^\s*(//|/\*|\*)'` exactly for all four files, and code + comment-only + blank equals the total line count of each file. Raw output is in `comment-density.tsv`.

## 1. Readable desktop wrapper (as shipped)

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

## 2. Comparison with human-written code in the same package

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

## Representative excerpts

A small sample of the 474 comment lines, chosen to show the style discussed in REPORT.md §5.2. Each excerpt is quoted for commentary, with its source line numbers.

**`main.js`**

~~~~text
   5 │ /* Startup logging: launches from a file manager have no visible stdout, so
   6 │  * key milestones and crashes also go to <userData>/startup.log. If the app
   7 │  * ever "opens nothing", that file says how far it got. Zero dependencies. */
  45 │   // If a downloaded update's restart is declined, it still installs on the
  46 │   // next normal quit — "old version until the next restart", literally.
  78 ◂ // closing it doesn't cancel the download
  79 │     // The bar starts as an INDETERMINATE animation. Real progress events
  80 │     // switch it to a determinate fill; if the updater never emits progress
  81 │     // (differential downloads or a feed server without Content-Length do
  82 │     // this), the animation honestly shows "working" instead of a frozen 0%.
 479 │   // Exports use blob downloads; Electron shows a native Save dialog by default,
 480 │   // which is exactly what we want — no extra handling needed.
~~~~

**`preload.js`**

~~~~text
  12 │   // Native open dialog. Resolves to { files: [{ name, data }] } (data is a
  13 │   // Uint8Array) or null if the user canceled. Picking a single .mid/.chart
  14 │   // also returns its folder companions (song.ini + audio).
~~~~

**`app/js/desktop-native.js`**

~~~~text
   4 │  * desktop app real filesystem loading. Purely additive, like
   5 │  * desktop-popout.js — no app code is modified.
~~~~

**`app/js/desktop-popout.js`**

~~~~text
   3 │  * Detaches the app's floating panels into real OS windows by physically
   4 │  * MOVING their DOM into same-origin child windows (same renderer process,
   5 │  * same JS context: all app state, closures, and listeners keep working).
   6 │  * Purely additive — no app code is modified.
  19 │  * DOCKABLE pop-outs (section floats and Tap Tempo) can be dragged BY THEIR
  20 │  * TITLEBAR straight back over the main window's side panels to re-dock —
  21 │  * no close required. This is why their titlebars use a hand-rolled window
  22 │  * drag (pointer capture + window.moveTo) instead of -webkit-app-region:
  23 │  * during an app-region drag the OS owns the move and the renderer receives
  24 │  * ZERO events, so there would be nothing to hit-test against the panels.
 205 ◂ // typing must not trigger editor keybinds
~~~~

`│` = comment-only line; `◂` = trailing comment (comment part only). Run `tools/jsloc.py --dump` on your own copy for the complete list.

## Reproducing

```sh
cd chartforge-decompiled
python3 -I <this-repo>/tools/jsloc.py app/main.js app/preload.js app/app/js/desktop-native.js app/app/js/desktop-popout.js
python3 -I <this-repo>/tools/jsloc.py --dump app/main.js app/preload.js app/app/js/desktop-*.js   # every comment line, with line numbers
find app/node_modules/three/src -name '*.js' -print0 | xargs -0 python3 -I <this-repo>/tools/jsloc.py   # baseline
```
