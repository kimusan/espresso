# Welcome to the Espresso Wiki

**Espresso** is a lightweight, declarative terminal UI framework for Python inspired by Charm's **Bubble Tea**, **Lip Gloss**, and **Bubbles**.

## Table of Contents

1. [Getting Started](Getting-Started)
2. [The Elm Architecture (TEA)](The-Elm-Architecture)
3. [Crema: Styling & Layout Guide](Crema-Styling-Guide)
4. [Beans: Component Catalog](Beans-Component-Catalog)
5. [Examples & Recipes](https://github.com/kimschulz/espresso/tree/main/examples)

## Architecture at a Glance

* **`espresso`**: The core runtime engine coordinating terminal raw mode, event loop, SGR mouse tracking, and TEA dispatch.
* **`espresso.crema`**: The styling and layout engine with TrueColor, ANSI 256, box model, border titles, word wrapping, gradients, 2D joins, modal overlays, and responsive proportional FlexBox.
* **`espresso.beans`**: The standard component library (21 components: TextArea, Help, Timer, Stopwatch, Spinners, TextInputs, Tables, Viewports, Progress, Paginator, Dialogs, Lists, FilePicker, Prompts, Toasts, Tabs, Tree, StatusBar, KPI Metrics, NavStack, and DatePicker).
