# ChartForge 1.6.0: Static Analysis

An independent technical analysis of the desktop wrapper of **ChartForge 1.6.0** (`chartforgev1.6.0.AppImage`), a free chart editor for Clone Hero / Rock Band style rhythm games. It covers how the app is packaged and built, and assesses how likely it is that the code was written with AI coding tools.

> This repository contains **no ChartForge code or binaries**. ChartForge is free to download but proprietary (`"license": "UNLICENSED"`). Only short excerpts are quoted, for commentary. Everything here can be reproduced from your own copy of the AppImage.

## Findings at a glance

- **Stack:** a browser JavaScript app using three.js r128, wrapped in Electron 31.7.7 / Chromium 126.
- **Scope:** the editor core is obfuscated, so the analysis focuses on the **desktop wrapper**: 4 files, 1,936 lines.
- **Network (wrapper):** an opt-in auto-updater (`chart-forge.app`), a feedback link opened in the system browser, and a cdnjs fallback for three.js. No telemetry in the wrapper.
- **Comment density:** the readable files have **34.8% comment lines per line of code**. Human-written libraries bundled in the same app range from 7.6% to 15.6%.
- **AI-authorship assessment (opinion):** desktop wrapper about **85–90%** likely to be substantially AI-written, most likely by an AI coding agent directed by a human with real rhythm-game domain knowledge.

## Contents

| File | What it is |
|---|---|
| [REPORT.md](REPORT.md) | Full report: scope, unpacking, wrapper architecture, IPC surface, file handling, network behaviour, AI-authorship assessment |
| [COMMENT-DENSITY.md](COMMENT-DENSITY.md) | Per-file comment and code line counts, baseline comparison, representative excerpts |
| [comment-density.tsv](comment-density.tsv) | Raw line counts for the four readable files |
| [tools/jsloc.py](tools/jsloc.py) | JavaScript-aware line counter (Python 3, standard library only); `--dump` lists every comment line |

## Reproducing

You need `unsquashfs`, Node.js (for `npx`) and Python 3. The steps are in [REPORT.md, Appendix A](REPORT.md#appendix-a-repeating-the-analysis). In short:

```sh
mkdir chartforge-decompiled && cd chartforge-decompiled
unsquashfs -q -o 188392 -d squashfs-root /path/to/chartforgev1.6.0.AppImage
npx @electron/asar extract squashfs-root/resources/app.asar app
python3 -I /path/to/this-repo/tools/jsloc.py app/main.js app/preload.js app/app/js/desktop-*.js
```

The analysis is static only; the application was never run.

## Caveats

- **The AI-authorship figures are an evidence-based opinion, not a measurement.** No tool can prove whether code was written by AI, and a careful human can produce every pattern described. The reasoning, and what would change the estimate, are in REPORT.md §5.
- **Version:** this analysis covers version 1.6.0 only, SHA-256 `1c257f653ac694334d9b2413cc2a7a6ddaa9c039a5b34986cde74aabdf493a34`.
