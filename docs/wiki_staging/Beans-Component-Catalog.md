# Beans Component Catalog

`espresso.beans` provides the following components ready for use:

## `Spinner`
Animated spinners with presets: `DOTS`, `LINE`, `PULSE`, `POINTS`, `COFFEE`, `GLOBE`, `MOON`.

## `TextInput`
Interactive single-line text input with cursor blinking, navigation, and `EchoMode.PASSWORD`.

## `Progress`
Progress bars with customizable fill and empty styling.

## `Viewport`
Scrollable pane for viewing long content, supporting mouse wheel and keyboard navigation.

## `Table`
Column-formatted tables with interactive row selection and navigation.

## `TextArea`
Interactive multi-line text editor with line numbers, viewport scrolling, tab indentation, and cursor navigation.

## `Help`
Adaptive keybinding helper rendering compact single-line or multi-column full hotkey documentation.

## `Timer`
High-precision countdown timer driven by tea tick commands with formatted duration and percentage completion.

## `Stopwatch`
High-precision elapsed time tracker with split-second hundredths display and toggle/reset controls.

## `Paginator`
Pagination manager supporting bullet dots (`DOTS`), numeric counters (`NUMERIC`), and descriptive ranges (`COMPACT`) with zero-jitter bounds slicing.

## `Dialog`
Modal confirmation and decision box with custom buttons, keyboard/mouse selection, and `place_overlay` backdrop dimming.

## `List`
Searchable, filterable list with real-time `/` search query input, discrete pagination or continuous scrolling (`PaginationMode`), right-aligned badges, absolute and Vim relative numbering, tree continuation guides, and `ListSelectMsg` submission.

## `FilePicker`
Interactive terminal filesystem browser with human-readable file sizes, extension filtering, parent directory traversal, and hidden file toggling.

## `Prompt`
Interactive CLI prompt components:
- `SelectPrompt`: Single-choice menu with pointer indicator.
- `MultiSelectPrompt`: Checkbox selection with toggle and select-all (`a`).
- `ConfirmPrompt`: Boolean `[y/N]` confirmation with immediate hotkeys.

## `ToastManager`
Notification manager handling transient toast cards with severity levels (`INFO`, `SUCCESS`, `WARNING`, `ERROR`) and auto-dismiss async timers.

## `Tabs`
Top tab bar navigation with customizable styles (`PILL`, `LINE`, `BRACKET`), number hotkeys 1-9, and `TabChangeMsg`.

## `Tree`
Hierarchical tree view with Unicode branch connectors (`├──`, `└──`), collapsible branches, and node selection.

## `StatusBar`
Responsive multi-section status bar with Left, Center, and Right clusters, priority-based auto-truncation, and custom styles.

## `Metric` & `MetricGroup`
Dashboard KPI stat cards, tags, and summary lists with delta trend indicators (`UP`, `DOWN`, `NEUTRAL`), unit formatting, and inverted trend coloring.

## `NavStack`
Hierarchical view router managing sub-model transitions, automatic message forwarding, breadcrumb trails, and auto-pop on `Esc`.

## `DatePicker`
Interactive monthly calendar widget with day/week navigation, month/year focus modes, mouse date selection, and min/max date clamping.

## `PipelineProgress`
Multi-stage asynchronous task execution pipeline with live progress bar, per-stage status badges (`PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `SKIPPED`), elapsed execution times, and failure diagnostics.

## `MarkdownViewer`
Pure Python terminal Markdown document viewer parsing headings, bold, italic, code blocks, blockquotes, lists, and tables with smooth viewport scrolling.

## `CodeViewer`
Syntax-highlighted source code viewer with line numbers, active cursor line highlight (`▶`), themes (`THEME_ESPRESSO`, `THEME_DRACULA`, `THEME_MONOKAI`), and multi-language support (Python stdlib `tokenize` + regex tokenizers).

## `QuickFix`
Neovim-style diagnostic bottom drawer for viewing compiler/linter issues with severity badges (`ERR`, `WARN`, `INFO`, `HINT`), keyboard navigation, and seamless background view compositing via `wrap_view`.

## `DetailSelector`
Interactive selection menu paired with a live synchronized preview card below, collapsing to a concise summary on selection.

## `ImageViewer`
Terminal graphics viewer rendering 24-bit ANSI truecolor half-blocks (`▀`) and 10-step ASCII grayscale with native support for Netpbm PPM, 24-bit BMP, and raw RGB matrices.

## `Splitter`
Interactive dual-pane container (`Left | Right` or `Top / Bottom`) with a draggable and keyboard-resizable divider bar, min/max pane constraints, and automatic child sizing.

## `Slider` & `RangeSlider`
Tactile direct-manipulation numeric slider and dual-thumb range selector supporting click-to-seek, smooth mouse drag tracking, keyboard steps, and custom value badges.

## `Sparkline`
Real-time streaming charts with high-resolution 2D Unicode Braille curves (4× vertical resolution) and 1D block bars (`  ▂▃▄▅▆▇█`), auto-scaling, trend indicators (`↗`, `↘`, `→`), and vertical gradients.

## `Marquee`
Fixed-width smoothly scrolling animated text ticker with loop and bounce modes, configurable speed, and pause frames.

## `SortableList`
Reorderable item list supporting mouse drag-and-drop reordering with visual drop indicators (`▼ `, `[HOLDING]`) and keyboard `Space`+`Arrows` reordering.

## `Spring`
Physical damped harmonic oscillator simulation solving $m x'' + c x' + k (x - \text{target}) = 0$ with closed-form mathematical stability, overshoot rendering, and adjustable damping/stiffness presets.

## `Confetti`
2D celebratory particle physics emitter featuring radial bursts, corner cannons, and falling rain, complete with air drag, gravity, and non-destructive Crema overlaying (`place_overlay`).

## `DiffViewer`
High-fidelity Git diff visualizer with single-column Unified and dual-column Split views, line-number gutters, hunk headers, and intra-line word-level difference highlighting.

## `Form`
Composite multi-field data entry container with built-in field validation, inline error badges, Tab / Shift+Tab keyboard focus cycling, Up/Down arrow navigation, and `FormSubmitMsg` event dispatch.



