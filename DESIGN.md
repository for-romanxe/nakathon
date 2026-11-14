---
name: Crew Health
description: A health manager that greets the crew each morning, sets today's routine, and keeps the numbers as evidence.
colors:
  bg: "#070A0F"
  surface: "#0C1117"
  surface-raised: "#101720"
  hairline: "#161E29"
  hairline-strong: "#1F2A37"
  ink: "#E6EAF0"
  ink-soft: "#A8B2BF"
  ink-muted: "#7D8896"
  normal: "#22D3A6"
  caution: "#F5C542"
  warning: "#FF5C73"
  body-lime: "#C6E84A"
  body-light: "#D6DBC9"
  cite-bg: "#142A4A"
  cite-ink: "#8AB8FF"
typography:
  display:
    fontFamily: "Inter, Noto Sans KR, system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  metric:
    fontFamily: "JetBrains Mono, ui-monospace, Menlo, monospace"
    fontSize: "34px"
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: "-0.03em"
  body:
    fontFamily: "Inter, Noto Sans KR, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "0em"
  label:
    fontFamily: "Inter, Noto Sans KR, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0em"
  mono-small:
    fontFamily: "JetBrains Mono, ui-monospace, Menlo, monospace"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "0em"
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
components:
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
    padding: "0"
  tile:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "14px 16px"
  banner-caution:
    backgroundColor: "#1E1A0C"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "16px 20px"
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "#0B0F14"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "9px 14px"
  button-secondary:
    backgroundColor: "#1A2432"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "9px 14px"
  badge-caution:
    backgroundColor: "#3A2F0C"
    textColor: "{colors.caution}"
    typography: "{typography.mono-small}"
    rounded: "{rounded.sm}"
    padding: "1px 7px"
  badge-warning:
    backgroundColor: "#3E1420"
    textColor: "{colors.warning}"
    typography: "{typography.mono-small}"
    rounded: "{rounded.sm}"
    padding: "1px 7px"
  badge-normal:
    backgroundColor: "#0D2A24"
    textColor: "{colors.normal}"
    typography: "{typography.mono-small}"
    rounded: "{rounded.sm}"
    padding: "1px 7px"
  cite:
    backgroundColor: "{colors.cite-bg}"
    textColor: "{colors.cite-ink}"
    typography: "{typography.mono-small}"
    rounded: "{rounded.sm}"
    padding: "0 4px"
---

# Design System: Crew Health

## Overview

A manager that talks to you every morning (아침마다 말 거는 관리자). The home screen opens with your name and the day, says in one coloured sentence how you are, and then gives today's guide: the routine you already follow, adjusted when your body asks for it, each change with its reason and source. The numbers and the pixel body sit below as evidence, not as the headline. Warmth lives in the words (greeting, plain sentences, "지켜볼게요"), never in decoration: the surface stays near-black navy, flat, with hairline borders and tabular mono numbers. The lime pixel body is still the one expressive element. Extracted from the multi-page mockup `mockup/app/` (primary); `mockup/dashboard.html` and `mockup/app.html` are earlier instrument-panel explorations, and the launch-film concept page `mockup/index.html` uses a separate warmer black (#0B0807) and is not part of this system.

## Colors

### Primary
- `ink` #E6EAF0 on `bg` #070A0F is the default text. `ink-soft` for secondary copy, `ink-muted` #7D8896 for labels (5.3:1 on `surface`; the earlier #6B7684 failed at 4.1:1).

### Status
- `normal` #22D3A6 (teal-green) may now say "you are fine": the one status sentence on the home screen is green on a normal day, and verification chips and the sync dot stay teal. Metric values themselves stay `ink` when normal.
- `caution` #F5C542 and `warning` #FF5C73 colour the status sentence, the arrow, the sigma figure, the tile border tint, the rail badge, and the "조정" label in the guide. Never red next to green for the same meaning; Caution vs Warning differ in lightness as well as hue.
- Advisory (참고, one metric off for one day) gets no colour at all: neutral arrow and sigma, a muted one-line note inside the guide, no badge.

### Body
- `body-lime` #C6E84A with ~8% `body-light` cells. Regions at Caution / Warning switch to `caution` / `warning` and a share of cells drift outward. Advisory regions stay lime.

### Named Rules
- **Colour is the day's verdict.** Green, yellow and red belong to the rule verdict (normal, caution, warning). A single metric off for a single day is not a verdict and stays uncoloured. Any coloured number must also carry a non-colour cue (▲▼ arrow, sigma, label).
- **Citations are blue.** `cite-bg` / `cite-ink` are reserved for source ids and never reused for status.

## Typography

- Inter for UI copy (Korean falls back to Noto Sans KR), JetBrains Mono for every number, id, timestamp and sigma. Pairing is on a contrast axis: humanist sans for words, mono for data.

### Hierarchy
- Greeting 24px/700 (-0.02em) → status sentence 17px/600 → guide item name 14.5px/600 → guide lines 13.5px → tile metric 30px mono/600 (22px on the compact home tiles) → panel heading 13px/600 → labels 12px/500 → mono-small 11px (guide labels 목표 · 조정 · 왜 at 10.5px mono).
- Sleep is formatted as `5h 10m`, sigma as `+2.7σ`, always with a sign.

### Named Rules
- No uppercase tracked eyebrows except the level line on the full-screen warning (`WARNING · 경보 · 즉시 조치`) and the mono level badges, which use the NASA level names.
- Copy speaks to the crew member in plain polite Korean (해요체) on the home screen; documents and procedures keep their formal register.

## Layout

- Home order, top to bottom: greeting with Sol and time → one status sentence with actions on the right → **오늘의 가이드** (the largest area) → evidence (six compact tiles beside a small body) → today's events → check-in streak. Content max width 1280px, gaps 16px.
- Other screens keep the section layout: panels in two or three columns, 16px gaps.
- Panels have no inner card nesting; inside a panel, rows are separated by hairlines, not boxes.

## Elevation & Depth

- Flat. Depth comes from surface steps (`bg` → `surface` → `surface-raised`) and hairlines, not shadows. The only shadow is on the body popover (`0 20px 60px rgba(0,0,0,.6)`) because it floats over the canvas.

## Shapes

- Radius 12px for panels and tiles, 8px for buttons, inputs and scale buttons, 4px for badges and citations. Pixel body cells are square with 1.5px gaps.

## Components

### Greeting and status line
- Name and time of day ("좋은 아침입니다, 승무원 A님." / "오늘 하루 수고했어요" in the evening), mono Sol · time · sync line, then a dot plus one sentence in the status colour, with at most three actions to the right. A mono metadata row underneath says who judged (rule, baseline, thresholds), whether a model explanation exists and passed verification, and "가상 데이터 · 의료 조언 아님".

### Guide row
- Three columns: item name with a small cadence line; a stack of labelled lines (`목표`, `조정`, `왜`, or `기록` for check-in results); a right column for progress, a button, or a done time. Rows without an adjustment show the goal only. Event-derived temporary items group under the event title with inline buttons. The advisory note is one muted row labelled `참고`.

### Check-in sheet
- A centred sheet over the home screen on first entry. The system pre-fills every answer; the crew member only taps to correct. 1–5 scales are five equal mono buttons with end labels; symptoms default to "없음". One primary button finalises the guide.

### Risk guidance (three lines)
- 위험 범주 (HRP category, by rule) · 가능한 상태 (a name from the fixed on-device list, always followed by "가능성", with evidence and citations) · 오늘 할 일 (rule actions with citations). Hairline-separated rows; when verification fails the middle line says it was withheld.

### Metric tile
- Label + context, metric with unit and arrow, baseline line with signed sigma, 7-day sparkline with dashed baseline. Border tints to the status colour at Caution/Warning only. The compact variant on the home screen drops the threshold suffix.

### Buttons
- Primary is `ink` on near-black (inverted), secondary is raised surface with hairline, caution variant for "share with medical officer". 9px vertical padding, 12px/600 label.

### Badges / Chips
- Mono 10–11px, 1px vertical padding, status background tints. Verification chips are `badge-normal`. The advisory badge is neutral.

### Pixel body
- Canvas, cells 5–8px, silhouette rasterised from paths. Hover brightens a region; click opens a popover anchored to the region with metric rows, sigma, note and citation. On the home screen it is small and sits beside the tiles as evidence.

## Do's and Don'ts

- Do greet by name and lead with what to do today; numbers come after, as evidence.
- Do keep the rule verdict and numbers visible next to any model sentence, and never let a sentence sound stronger than the verdict.
- Do show "판단 보류" with raw numbers when verification fails; never hide the failure.
- Do say "가능성" for any condition name, and only use names from the on-device list.
- Don't colour or badge a single metric that is off for a single day; write one quiet 참고 line instead.
- Don't add points, levels, badges or leaderboards. The morning check-in streak is the only game element.
- Don't add gradients, glass blur, glow or illustrations to make it feel warm; warmth is in the copy. The body is the only expressive element.
- Don't use colour for branding.
- Don't introduce a readiness score ring unless the team decides to; the current decision is a status sentence only.
- Don't nest cards inside panels; use hairline rows.
