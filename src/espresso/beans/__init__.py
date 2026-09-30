"""Beans: Standard library of reusable TUI components for Espresso.

Inspired by Bubbles.
"""

from espresso.beans.codeviewer import (
    CodeViewer,
    SyntaxTheme,
    THEME_DRACULA,
    THEME_ESPRESSO,
    THEME_MONOKAI,
    highlight_code,
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
from espresso.beans.statusbar import StatusBar, StatusSection
from espresso.beans.table import Column, Table
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
]

