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
Searchable, filterable list with real-time `/` search query input, pagination, and `ListSelectMsg` submission.

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

