# Welcome to the Espresso Wiki

**Espresso** is a lightweight, declarative terminal UI framework for Python inspired by Charm's **Bubble Tea**, **Lip Gloss**, and **Bubbles**.

## Table of Contents

1. [Getting Started](Getting-Started)
2. [The Elm Architecture (TEA)](The-Elm-Architecture)
3. [Crema: Styling & Layout Guide](Crema-Styling-Guide)
4. [Beans: Component Catalog](Beans-Component-Catalog)
5. [Examples & Recipes](https://github.com/kimusan/espresso/tree/main/examples)

## Architecture at a Glance

* **`espresso`**: The core runtime engine coordinating terminal raw mode, event loop, flicker-free line-diffing alt-screen renderer, SGR mouse tracking, and desktop gesture synthesis (`MouseGestureTracker`).
* **`espresso.crema`**: The styling and layout engine with TrueColor, ANSI 256, box model, border titles, word wrapping, gradients, 2D joins, modal overlays, responsive proportional `FlexBox`, and multi-column `Grid`.
* **`espresso.beans`**: The standard component library (39 components: TextArea, Help, Timer, Stopwatch, Spinners, TextInputs, Tables, Viewports, Progress, Paginator, Dialogs, Lists, FilePicker, Prompts, Toasts, Tabs, Tree, StatusBar, Metric/MetricGroup, NavStack, DatePicker, PipelineProgress, MarkdownViewer, CodeViewer, QuickFix, DetailSelector, ImageViewer, Splitter, Sliders, Sparkline, Marquee, SortableList, Spring, Confetti, DiffViewer, Form/FormBuilder, CommandPalette, GitTree, and BarChart).
* **`espresso` CLI**: Standalone developer toolkit for listing (`espresso list`), running (`espresso run`), previewing (`espresso gallery`), and scaffolding (`espresso new`) applications.
