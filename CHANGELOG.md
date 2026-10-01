# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0](https://github.com/kimusan/espresso/compare/v0.2.0...v1.0.0) - 2026-10-01

### 🚀 Features

- **release**: Automate CHANGELOG.md generation with Conventional Commits parsing and Keep a Changelog standard ([a858c2c](https://github.com/kimusan/espresso/commit/a858c2c))
- **release**: Upgrade release helper to interactive Espresso TUI with pipeline progress, toasts, dialogs, and confetti ([cb6a8d7](https://github.com/kimusan/espresso/commit/cb6a8d7))
- **release**: Add automated release helper script with pre-flight checks and rollback instructions ([2dd3c9c](https://github.com/kimusan/espresso/commit/2dd3c9c))

### 🐛 Bug Fixes

- **release**: Dynamically report passed test count in release helper ([29ad09e](https://github.com/kimusan/espresso/commit/29ad09e))
- **workspace**: Fix exit ValueError and implement toggle explorer sidebar ([429e92d](https://github.com/kimusan/espresso/commit/429e92d))
- **workspace**: Fix gear icon border overflow and terminal line-wrap blanking ([92e140a](https://github.com/kimusan/espresso/commit/92e140a))

### 📖 Documentation

- **wiki**: Remove wiki_staging and add publish_wiki automation script and workflow ([eb281ca](https://github.com/kimusan/espresso/commit/eb281ca))
- Audit and update documentation for all 39 beans, Grid engine, gestures, line-diffing, and CLI ([5e8438c](https://github.com/kimusan/espresso/commit/5e8438c))

### 🛠️ Maintenance & Packaging

- Centralize version in src/espresso/__init__.py via dynamic flit packaging ([cfb04a8](https://github.com/kimusan/espresso/commit/cfb04a8))
- Add GitHub release workflow for PyPI and multi-platform packages ([f9e0cf6](https://github.com/kimusan/espresso/commit/f9e0cf6))

## [0.2.0](https://github.com/kimusan/espresso/releases/tag/v0.2.0) - 2026-10-01

### 🚀 Features

- **v0.2.0**: Add CommandPalette, GitTree, BarChart, Grid layout, CLI tool, and Demo 14 ([9f75bb4](https://github.com/kimusan/espresso/commit/9f75bb4))
- **beans**: Add Spring, Confetti, DiffViewer, and Form with demo 13 ([e9a1963](https://github.com/kimusan/espresso/commit/e9a1963))
- **beans**: Add Splitter, Slider, Sparkline, Marquee, and SortableList with interactive demo 12 ([17b0bb7](https://github.com/kimusan/espresso/commit/17b0bb7))
- **beans**: Add PipelineProgress, MarkdownViewer, CodeViewer, QuickFix, DetailSelector, and ImageViewer ([6d51064](https://github.com/kimusan/espresso/commit/6d51064))
- **beans**: Enhance List with bubblelister scrolling, numbering, and badges ([e5f133b](https://github.com/kimusan/espresso/commit/e5f133b))
- **beans**: Add DatePicker component inspired by bubble-datepicker ([bb9de59](https://github.com/kimusan/espresso/commit/bb9de59))
- **examples**: Add Tab 5 showcasing FlexBox, Metrics, NavStack, and StatusBar ([3eb1032](https://github.com/kimusan/espresso/commit/3eb1032))
- **beans**: Add StatusBar, Metric cards, and NavStack ([be4d40d](https://github.com/kimusan/espresso/commit/be4d40d))
- **crema**: Add Stickers-inspired responsive FlexBox proportional grid ([d84d28e](https://github.com/kimusan/espresso/commit/d84d28e))
- **core**: Add easy mouse toggle and mouse support to component gallery ([9d716d2](https://github.com/kimusan/espresso/commit/9d716d2))
- **examples**: Add 10_component_gallery showcase for new beans ([48cb381](https://github.com/kimusan/espresso/commit/48cb381))
- **beans**: Add paginator, list, filepicker, dialog, prompts, toast, tabs, and tree ([28e1444](https://github.com/kimusan/espresso/commit/28e1444))
- **crema**: Support solid and gradient background box fills with text on top ([f8ac483](https://github.com/kimusan/espresso/commit/f8ac483))
- **crema**: Add background gradients, multi-stop gradients, and card padding fills ([9c22425](https://github.com/kimusan/espresso/commit/9c22425))
- **examples**: Add fullscreen multi-panel RSS reader demo fetching schulz.dk ([914f43d](https://github.com/kimusan/espresso/commit/914f43d))
- **examples**: Add dynamic per-tab content views and direct number shortcuts in dashboard ([58c265d](https://github.com/kimusan/espresso/commit/58c265d))
- **crema**: Implement ANSI word-wrapping, TrueColor gradients, and border titles ([6fbe7f9](https://github.com/kimusan/espresso/commit/6fbe7f9))
- **beans**: Implement TextArea, Help, Timer, and Stopwatch components ([8df2cce](https://github.com/kimusan/espresso/commit/8df2cce))
- **examples**: Add practical conventional git commit helper CLI ([d67205a](https://github.com/kimusan/espresso/commit/d67205a))
- **examples**: Add interactive multi-step order wizard demo ([56ed69e](https://github.com/kimusan/espresso/commit/56ed69e))
- **beans**: Implement Table component with column formatting and row selection ([a65bf9a](https://github.com/kimusan/espresso/commit/a65bf9a))
- **beans**: Implement scrollable Viewport component ([1687db9](https://github.com/kimusan/espresso/commit/1687db9))
- **beans**: Implement Progress bar component with customizable fill styles ([33dffa6](https://github.com/kimusan/espresso/commit/33dffa6))
- **beans**: Implement TextInput component with cursor editing and password masking ([9b76333](https://github.com/kimusan/espresso/commit/9b76333))
- **beans**: Implement Spinner component with animation presets ([17513b8](https://github.com/kimusan/espresso/commit/17513b8))
- **examples**: Add fullscreen mouse and resize demo ([1aef275](https://github.com/kimusan/espresso/commit/1aef275))
- **core**: Implement flicker-free double-buffered line-diffing renderer ([49931e7](https://github.com/kimusan/espresso/commit/49931e7))
- **core**: Implement XTerm SGR 1006 mouse event decoding ([46bb22c](https://github.com/kimusan/espresso/commit/46bb22c))
- **examples**: Add dashboard layout demo using Crema styling ([9b6c071](https://github.com/kimusan/espresso/commit/9b6c071))
- **crema**: Implement 2D layout composition primitives (join, place) ([ab8a222](https://github.com/kimusan/espresso/commit/ab8a222))
- **crema**: Implement Style class with declarative box model rendering ([f5917e7](https://github.com/kimusan/espresso/commit/f5917e7))
- **crema**: Implement border definitions and box presets ([3bce2f0](https://github.com/kimusan/espresso/commit/3bce2f0))
- **crema**: Implement Unicode cell width calculator and ANSI truncation ([a5ef4c4](https://github.com/kimusan/espresso/commit/a5ef4c4))
- **crema**: Implement TrueColor, ANSI 256, and NO_COLOR support ([38605de](https://github.com/kimusan/espresso/commit/38605de))
- **examples**: Add interactive counter and shopping list demos ([9fd32f2](https://github.com/kimusan/espresso/commit/9fd32f2))
- **core**: Implement Program runtime event loop and screen renderer ([14a6250](https://github.com/kimusan/espresso/commit/14a6250))
- **core**: Implement terminal raw mode driver and ANSI escape controls ([af1ef1c](https://github.com/kimusan/espresso/commit/af1ef1c))
- **core**: Implement ANSI escape sequence parser and key message types ([eb6e7aa](https://github.com/kimusan/espresso/commit/eb6e7aa))
- **core**: Implement The Elm Architecture protocol, commands, and messages ([7b09e02](https://github.com/kimusan/espresso/commit/7b09e02))

### 🐛 Bug Fixes

- **confetti, form**: Fix particle glyph widths, cannon physics, click alignment, and retriggering ([3041756](https://github.com/kimusan/espresso/commit/3041756))
- **keys, sortable_list**: Support space key alias and direct shift+arrow reordering ([41706b1](https://github.com/kimusan/espresso/commit/41706b1))
- **beans**: Add screen offset translation, slider row isolation, marquee loop scrolling, and sortable list bounds handling ([7bde047](https://github.com/kimusan/espresso/commit/7bde047))
- **demo**: Enable alt_screen, mouse wheel support, and full window sizing for markdown viewer and editor ([53ee16d](https://github.com/kimusan/espresso/commit/53ee16d))
- **viewport**: Prevent layout jumping when scrolling empty lines ([2525547](https://github.com/kimusan/espresso/commit/2525547))
- **examples**: Correct mouse click row mapping for FilePicker, Tree, Prompts, and List ([644f71f](https://github.com/kimusan/espresso/commit/644f71f))
- **examples**: Make 10_component_gallery full window edge-to-edge ([9716653](https://github.com/kimusan/espresso/commit/9716653))
- **core**: Ensure instant quit on QuitMsg, unhandled ctrl-c, and support Q/ctrl-z ([5f9040e](https://github.com/kimusan/espresso/commit/5f9040e))
- **keys**: Map ASCII 8 to ctrl+h and configure editor demo 07 with alt_screen ([127e628](https://github.com/kimusan/espresso/commit/127e628))
- **crema**: Correct char_width for symbols and fix button hitboxes in demo 04 ([52c9bcb](https://github.com/kimusan/espresso/commit/52c9bcb))
- **core**: Ensure line clearing occurs before text rendering to prevent blank screen ([434ecf5](https://github.com/kimusan/espresso/commit/434ecf5))
- **core**: Prevent terminal staircase skew and resolve BlockingIOError on stdout ([b6bc9ab](https://github.com/kimusan/espresso/commit/b6bc9ab))

### 📖 Documentation

- **beans**: Document screen offset coordinates and marquee loop scrolling ([6066673](https://github.com/kimusan/espresso/commit/6066673))
- Update component catalog and guides with all 20 beans and FlexBox ([577145c](https://github.com/kimusan/espresso/commit/577145c))
- **project**: Add root README, architectural guides, and wiki staging docs ([e1720c8](https://github.com/kimusan/espresso/commit/e1720c8))

### 🧪 Tests

- **beans**: Add unit test suite for all standard UI components ([e01e75e](https://github.com/kimusan/espresso/commit/e01e75e))
- **core**: Add unit tests for mouse decoding and stream integration ([2f8d807](https://github.com/kimusan/espresso/commit/2f8d807))
- **crema**: Add test suite for styling, borders, colors, and layout ([72fa36f](https://github.com/kimusan/espresso/commit/72fa36f))
- **core**: Add comprehensive unit test suite for TEA, keys, and program loop ([4e7ece0](https://github.com/kimusan/espresso/commit/4e7ece0))

### 🛠️ Maintenance & Packaging

- **tests**: Add edge case tests, audit docstrings, and update documentation ([c1132c8](https://github.com/kimusan/espresso/commit/c1132c8))
- **project**: Initialize project structure and packaging configuration ([7367e6b](https://github.com/kimusan/espresso/commit/7367e6b))
