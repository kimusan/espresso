"""Beans: Standard library of reusable TUI components for Espresso.

Inspired by Bubbles.
"""

from espresso.beans.bar_chart import (
    BarChart,
    BarChartSelectMsg,
    BarItem,
    BarOrientation,
)
from espresso.beans.codeviewer import (
    CodeViewer,
    SyntaxTheme,
    THEME_DRACULA,
    THEME_ESPRESSO,
    THEME_MONOKAI,
    highlight_code,
)
from espresso.beans.command_palette import (
    CommandPalette,
    CommandPaletteCloseMsg,
    CommandPaletteSelectMsg,
    PaletteItem,
)
from espresso.beans.git_tree import (
    GitFileNode,
    GitFileStatus,
    GitTree,
    GitTreeSelectMsg,
    GitTreeToggleMsg,
)
from espresso.beans.datepicker import (
    DateChangeMsg,
    DatePicker,
    DatePickerFocus,
    DateSelectMsg,
)
from espresso.beans.detail_selector import DetailItem, DetailSelectMsg, DetailSelector
from espresso.beans.dialog import Dialog, DialogResultMsg
from espresso.beans.filepicker import FileEntry, FilePicker, FileSelectMsg, format_file_size
from espresso.beans.help import Help, KeyBinding, KeyMap
from espresso.beans.image import ImageViewer, RenderMode, parse_bmp, parse_ppm
from espresso.beans.list import List, ListItem, ListSelectMsg, PaginationMode
from espresso.beans.markdown import MarkdownViewer, render_markdown
from espresso.beans.metric import (
    LayoutDirection,
    Metric,
    MetricGroup,
    MetricLayout,
    MetricTrend,
)
from espresso.beans.navstack import NavEntry, NavPopMsg, NavPushMsg, NavStack
from espresso.beans.paginator import Paginator, PaginatorType
from espresso.beans.pipeline_progress import (
    PipelineCompleteMsg,
    PipelineProgress,
    PipelineStage,
    StageCompleteMsg,
    StageFailedMsg,
    StageStartMsg,
    StageStatus,
)
from espresso.beans.progress import Progress
from espresso.beans.prompt import (
    ConfirmPrompt,
    ConfirmSubmitMsg,
    MultiSelectPrompt,
    MultiSelectSubmitMsg,
    SelectPrompt,
    SelectSubmitMsg,
)
from espresso.beans.quickfix import QuickFix, QuickFixItem, QuickFixSelectMsg
from espresso.beans.spinner import (
    COFFEE,
    DOTS,
    GLOBE,
    LINE,
    MOON,
    POINTS,
    PULSE,
    Spinner,
    SpinnerTickMsg,
)
from espresso.beans.confetti import (
    Confetti,
    ConfettiMode,
    ConfettiTickMsg,
    Particle,
)
from espresso.beans.diff_viewer import (
    DiffHunk,
    DiffLine,
    DiffMode,
    DiffViewer,
)
from espresso.beans.form import Form, FormField, FormSubmitMsg
from espresso.beans.marquee import Marquee, MarqueeMode, MarqueeTickMsg
from espresso.beans.slider import (
    RangeSlider,
    RangeSliderChangeMsg,
    Slider,
    SliderChangeMsg,
)
from espresso.beans.sortable_list import ItemReorderedMsg, SortableItem, SortableList
from espresso.beans.sparkline import Sparkline, SparklineMode, SparklineTickMsg
from espresso.beans.spring import Spring, SpringTickMsg, SpringValue
from espresso.beans.splitter import (
    Splitter,
    SplitterOrientation,
    SplitterResizeMsg,
)
from espresso.beans.statusbar import StatusBar, StatusSection
from espresso.beans.table import Column, Table
from espresso.beans.switch import Switch, SwitchToggledMsg
from espresso.beans.select import Select, SelectChangeMsg
from espresso.beans.choice import Checkbox, CheckboxToggledMsg, RadioChangeMsg, RadioSet
from espresso.beans.modal_stack import ModalCloseMsg, ModalResultMsg, ModalStack
from espresso.beans.virtual_list import (
    VirtualList,
    VirtualListChangeMsg,
    VirtualListSelectMsg,
)
from espresso.beans.tabs import TabChangeMsg, TabStyle, Tabs
from espresso.beans.textarea import TextArea
from espresso.beans.textinput import EchoMode, TextInput
from espresso.beans.timer import (
    Stopwatch,
    StopwatchTickMsg,
    Timer,
    TimerTickMsg,
    TimerTimeoutMsg,
)
from espresso.beans.toast import ToastDismissMsg, ToastItem, ToastLevel, ToastManager
from espresso.beans.tree import Tree, TreeNode, TreeNodeSelectMsg
from espresso.beans.viewport import Viewport
from espresso.beans.scroll_view import ScrollChangeMsg, ScrollView
from espresso.beans.accordion import (
    Accordion,
    AccordionItem,
    AccordionSelectMsg,
    AccordionToggleMsg,
)
from espresso.beans.art_player import (
    AnimationDoneMsg,
    AnimationLoopMsg,
    ArtAnimation,
    ArtFrame,
    ArtPlayer,
    ArtPlayerTickMsg,
    parse_3a,
    parse_ans,
)

__all__ = [
    # Spinner
    "Spinner",
    "SpinnerTickMsg",
    "DOTS",
    "LINE",
    "PULSE",
    "POINTS",
    "MOON",
    "GLOBE",
    "COFFEE",
    # TextInput
    "TextInput",
    "EchoMode",
    # TextArea
    "TextArea",
    # Help & Keys
    "Help",
    "KeyBinding",
    "KeyMap",
    # Timer & Stopwatch
    "Timer",
    "TimerTickMsg",
    "TimerTimeoutMsg",
    "Stopwatch",
    "StopwatchTickMsg",
    # Progress
    "Progress",
    # Viewport
    "Viewport",
    # Table
    "Table",
    "Column",
    # Paginator
    "Paginator",
    "PaginatorType",
    # Dialog
    "Dialog",
    "DialogResultMsg",
    # List
    "List",
    "ListItem",
    "ListSelectMsg",
    "PaginationMode",
    # FilePicker
    "FilePicker",
    "FileEntry",
    "FileSelectMsg",
    "format_file_size",
    # Prompts
    "SelectPrompt",
    "SelectSubmitMsg",
    "MultiSelectPrompt",
    "MultiSelectSubmitMsg",
    "ConfirmPrompt",
    "ConfirmSubmitMsg",
    # Toast
    "ToastManager",
    "ToastItem",
    "ToastLevel",
    "ToastDismissMsg",
    # Tabs
    "Tabs",
    "TabStyle",
    "TabChangeMsg",
    # Tree
    "Tree",
    "TreeNode",
    "TreeNodeSelectMsg",
    # StatusBar
    "StatusBar",
    "StatusSection",
    # Metric
    "Metric",
    "MetricGroup",
    "MetricLayout",
    "MetricTrend",
    "LayoutDirection",
    # NavStack
    "NavStack",
    "NavEntry",
    "NavPushMsg",
    "NavPopMsg",
    # DatePicker
    "DatePicker",
    "DatePickerFocus",
    "DateSelectMsg",
    "DateChangeMsg",
    # CodeViewer
    "CodeViewer",
    "SyntaxTheme",
    "THEME_ESPRESSO",
    "THEME_DRACULA",
    "THEME_MONOKAI",
    "highlight_code",
    # MarkdownViewer
    "MarkdownViewer",
    "render_markdown",
    # PipelineProgress
    "PipelineProgress",
    "PipelineStage",
    "StageStatus",
    "StageStartMsg",
    "StageCompleteMsg",
    "StageFailedMsg",
    "PipelineCompleteMsg",
    # QuickFix
    "QuickFix",
    "QuickFixItem",
    "QuickFixSelectMsg",
    # DetailSelector
    "DetailSelector",
    "DetailItem",
    "DetailSelectMsg",
    # ImageViewer
    "ImageViewer",
    "RenderMode",
    "parse_ppm",
    "parse_bmp",
    # Splitter
    "Splitter",
    "SplitterOrientation",
    "SplitterResizeMsg",
    # Slider
    "Slider",
    "RangeSlider",
    "SliderChangeMsg",
    "RangeSliderChangeMsg",
    # Sparkline
    "Sparkline",
    "SparklineMode",
    "SparklineTickMsg",
    # Marquee
    "Marquee",
    "MarqueeMode",
    "MarqueeTickMsg",
    # SortableList
    "SortableList",
    "SortableItem",
    "ItemReorderedMsg",
    # Spring
    "Spring",
    "SpringValue",
    "SpringTickMsg",
    # Confetti
    "Confetti",
    "ConfettiMode",
    "ConfettiTickMsg",
    "Particle",
    # DiffViewer
    "DiffViewer",
    "DiffMode",
    "DiffHunk",
    "DiffLine",
    # Form
    "Form",
    "FormField",
    "FormSubmitMsg",
    # BarChart
    "BarChart",
    "BarItem",
    "BarOrientation",
    "BarChartSelectMsg",
    # CommandPalette
    "CommandPalette",
    "PaletteItem",
    "CommandPaletteSelectMsg",
    "CommandPaletteCloseMsg",
    # GitTree
    "GitTree",
    "GitFileNode",
    "GitFileStatus",
    "GitTreeSelectMsg",
    "GitTreeToggleMsg",
    # Switch
    "Switch",
    "SwitchToggledMsg",
    # Select
    "Select",
    "SelectChangeMsg",
    # Choice (RadioSet & Checkbox)
    "RadioSet",
    "RadioChangeMsg",
    "Checkbox",
    "CheckboxToggledMsg",
    # ModalStack
    "ModalStack",
    "ModalCloseMsg",
    "ModalResultMsg",
    # VirtualList
    "VirtualList",
    "VirtualListSelectMsg",
    "VirtualListChangeMsg",
    # ScrollView
    "ScrollView",
    "ScrollChangeMsg",
    # Accordion
    "Accordion",
    "AccordionItem",
    "AccordionToggleMsg",
    "AccordionSelectMsg",
    # ArtPlayer
    "ArtPlayer",
    "ArtAnimation",
    "ArtFrame",
    "ArtPlayerTickMsg",
    "AnimationDoneMsg",
    "AnimationLoopMsg",
    "parse_3a",
    "parse_ans",
]

