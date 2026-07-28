"""Flexible bilingual GUI for DEFET .dat processing and paper-style plotting.

Expected whitespace-separated columns:
    V1  V2  V3  V4  R  a  t

Version 2 adds arbitrary X/Y column selection, per-series styles, five
publication-inspired palettes, automatic multi-file subplot layout, independent
figure-label language, and direct mouse pan/zoom in the preview.
"""

from __future__ import annotations

import csv
import math
import queue
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

import matplotlib

if "--self-test" in sys.argv:
    matplotlib.use("Agg")

from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.ticker import AutoMinorLocator, LogLocator, NullFormatter

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk


APP_NAME = "DEFET Data Plotter"
APP_VERSION = "2.0.0"

RAW_KEYS = ("V1", "V2", "V3", "V4", "R", "a_raw", "t_raw_ms")
COLUMN_KEYS = RAW_KEYS + ("compression_mm", "time_s")
LINE_STYLES = ("-", "--", "-.", ":")
BASELINE_METHODS = ("Median of first window", "First valid value", "Minimum of first window")
DISPLACEMENT_DIRECTIONS = ("a − a0", "a0 − a")
FONT_CHOICES = ("Microsoft YaHei", "Arial", "Times New Roman", "DejaVu Sans", "Calibri")

PALETTES = {
    "Nature-inspired muted": ["#3B4CC0", "#B40426", "#1B9E77", "#984EA3", "#FF7F00"],
    "Science-inspired contrast": ["#0C5DA5", "#FF2C00", "#00B945", "#845B97", "#FF9500"],
    "IEEE-inspired print-safe": ["#00629B", "#E37222", "#00843D", "#7A4183", "#A6192E"],
    "ACS-inspired color-blind safe": ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"],
    "Grayscale print": ["#000000", "#404040", "#737373", "#A6A6A6", "#D0D0D0"],
}

PALETTE_DISPLAY_ZH = {
    "Nature-inspired muted": "Nature 风格参考（柔和）",
    "Science-inspired contrast": "Science 风格参考（高对比）",
    "IEEE-inspired print-safe": "IEEE 风格参考（印刷安全）",
    "ACS-inspired color-blind safe": "ACS 风格参考（色盲友好）",
    "Grayscale print": "灰度印刷",
}

OPTION_ZH = {
    "Median of first window": "初始窗口中位数",
    "First valid value": "首个有效值",
    "Minimum of first window": "初始窗口最小值",
}

COLUMN_LABELS = {
    "en": {
        "V1": "V1 voltage (V)",
        "V2": "V2 voltage (V)",
        "V3": "V3 voltage (V)",
        "V4": "V4 voltage (V)",
        "R": "Resistance (Ω)",
        "a_raw": "Raw position a",
        "t_raw_ms": "Raw time t (ms)",
        "compression_mm": "Compression (mm)",
        "time_s": "Time (s)",
    },
    "zh": {
        "V1": "V1 电压（V）",
        "V2": "V2 电压（V）",
        "V3": "V3 电压（V）",
        "V4": "V4 电压（V）",
        "R": "电阻（Ω）",
        "a_raw": "原始位置 a",
        "t_raw_ms": "原始时间 t（ms）",
        "compression_mm": "压缩量（mm）",
        "time_s": "时间（s）",
    },
}

UI = {
    "en": {
        "app": "DEFET Data Plotter",
        "ready": "Ready. Open one or more .dat files.",
        "file": "File",
        "open_files_menu": "Open .dat files…",
        "open_folder_menu": "Open folder…",
        "export_plot_menu": "Export arranged figure…",
        "export_csv_menu": "Export processed CSV…",
        "exit": "Exit",
        "language": "Language",
        "help": "Help",
        "data_help": "Data format and controls",
        "about": "About",
        "files": "Files",
        "open_files": "Open files",
        "select_all": "Select all",
        "remove": "Remove",
        "processing": "Processing",
        "raw_positive": "Remove rows where file R ≤ 0",
        "baseline_method": "a0 method",
        "initial_window": "Initial window (s)",
        "direction": "Compression direction",
        "clamp": "Clamp negative compression to 0",
        "zero_time": "Set first valid time to 0 s",
        "max_points": "Max plot points / file",
        "axes": "Data columns",
        "x_column": "X axis",
        "y_columns": "Y axes (Ctrl/Shift multi-select)",
        "style": "Series style",
        "palette": "Recommended palette",
        "apply_palette": "Apply palette",
        "series": "Selected Y series",
        "color": "Color",
        "line_style": "Line style",
        "line_width": "Line width",
        "apply_style": "Apply series style",
        "figure": "Figure",
        "annotation_language": "Figure labels",
        "english": "English",
        "chinese": "中文",
        "font": "Font",
        "font_size": "Font size",
        "x_scale": "X scale",
        "y_scale": "Y scale",
        "grid": "Light major grid",
        "legend": "Legend",
        "figure_title": "Optional figure title",
        "panel_size": "Export panel W × H (in)",
        "dpi": "DPI",
        "update": "Update preview",
        "export": "Export figure",
        "plot_tab": "Figure preview",
        "summary_tab": "Data summary",
        "mouse_hint": "Mouse: left-drag pan · wheel zoom · toolbar Home resets",
        "summary_file": "File",
        "summary_rows": "Raw rows",
        "summary_valid": "Valid rows",
        "summary_duration": "Duration (s)",
        "summary_compression": "Compression range (mm)",
        "summary_r": "R range (Ω)",
        "summary_a0": "a0",
        "empty": "Open one or more .dat files",
        "open_title": "Open DEFET .dat files",
        "folder_title": "Open folder containing .dat files",
        "no_dat": "No .dat files were found in that folder.",
        "already_loaded": "All selected files are already loaded.",
        "load_busy": "A file load is already running.",
        "loading": "Loading {count} file(s)…",
        "loaded": "Loaded {count} file(s); {total} total.",
        "load_errors": "Some files could not be loaded:",
        "processing_errors": "Processing warnings:",
        "select_files": "Select at least one loaded file.",
        "select_y": "Select at least one Y column.",
        "settings_error": "Window must be ≥0 and max plot points must be ≥100.",
        "style_error": "Check line width, font size, panel size, and DPI.",
        "plotted": "Arranged {count} file(s) as {rows} × {cols} panels.",
        "export_title": "Export arranged figure",
        "export_failed": "Could not export figure:",
        "csv_folder": "Choose processed CSV output folder",
        "saved_plot": "Figure saved: {path}",
        "saved_csv": "Exported {count} processed CSV file(s): {path}",
        "palette_note": "Palettes are publication-style references, not mandatory journal specifications.",
        "help_text": (
            "Expected columns:\nV1  V2  V3  V4  R  a  t\n\n"
            "R is read directly from the file. By default, rows with R ≤ 0 are removed.\n"
            "Select one X column and one or more Y columns. Each Y series has a shared\n"
            "color, line style, and width across all file panels.\n\n"
            "Multiple files are arranged automatically. Left-drag pans the panel under\n"
            "the mouse; the wheel zooms around the pointer; toolbar Home resets limits.\n\n"
            "CSV column names remain fixed in English for downstream scripts."
        ),
        "about_text": "Flexible bilingual processing and publication-style plotting for DEFET measurements.",
    },
    "zh": {
        "app": "DEFET 数据绘图工具",
        "ready": "就绪。请打开一个或多个 .dat 文件。",
        "file": "文件",
        "open_files_menu": "打开 .dat 文件…",
        "open_folder_menu": "打开文件夹…",
        "export_plot_menu": "导出排版图…",
        "export_csv_menu": "导出处理后的 CSV…",
        "exit": "退出",
        "language": "语言",
        "help": "帮助",
        "data_help": "数据格式与操作",
        "about": "关于",
        "files": "文件",
        "open_files": "打开文件",
        "select_all": "全选",
        "remove": "移除",
        "processing": "数据处理",
        "raw_positive": "删除文件中 R ≤ 0 的数据行",
        "baseline_method": "a0 基准方法",
        "initial_window": "初始窗口（s）",
        "direction": "压缩位移方向",
        "clamp": "将负压缩位移截为 0",
        "zero_time": "将首个有效时间设为 0 s",
        "max_points": "每文件最大绘图点数",
        "axes": "数据列",
        "x_column": "X 轴",
        "y_columns": "Y 轴（Ctrl/Shift 多选）",
        "style": "曲线风格",
        "palette": "推荐配色",
        "apply_palette": "应用配色",
        "series": "当前 Y 曲线",
        "color": "颜色",
        "line_style": "线型",
        "line_width": "线宽",
        "apply_style": "应用曲线风格",
        "figure": "图表",
        "annotation_language": "图片标注语言",
        "english": "English",
        "chinese": "中文",
        "font": "字体",
        "font_size": "字号",
        "x_scale": "X 轴尺度",
        "y_scale": "Y 轴尺度",
        "grid": "浅色主网格",
        "legend": "图例",
        "figure_title": "可选总标题",
        "panel_size": "导出单图宽 × 高（英寸）",
        "dpi": "DPI",
        "update": "更新预览",
        "export": "导出图表",
        "plot_tab": "图表预览",
        "summary_tab": "数据摘要",
        "mouse_hint": "鼠标：左键拖动平移 · 滚轮缩放 · 工具栏 Home 恢复",
        "summary_file": "文件",
        "summary_rows": "原始行数",
        "summary_valid": "有效行数",
        "summary_duration": "时长（s）",
        "summary_compression": "压缩范围（mm）",
        "summary_r": "R 范围（Ω）",
        "summary_a0": "a0",
        "empty": "请打开一个或多个 .dat 文件",
        "open_title": "打开 DEFET .dat 文件",
        "folder_title": "打开包含 .dat 文件的文件夹",
        "no_dat": "该文件夹中没有找到 .dat 文件。",
        "already_loaded": "所选文件均已加载。",
        "load_busy": "已有文件加载任务正在运行。",
        "loading": "正在读取 {count} 个文件…",
        "loaded": "已加载 {count} 个文件；当前共 {total} 个。",
        "load_errors": "部分文件无法读取：",
        "processing_errors": "数据处理警告：",
        "select_files": "请至少选择一个已加载文件。",
        "select_y": "请至少选择一个 Y 数据列。",
        "settings_error": "初始窗口不得小于 0，最大绘图点数不得小于 100。",
        "style_error": "请检查线宽、字号、单图尺寸和 DPI。",
        "plotted": "已将 {count} 个文件自动排为 {rows} × {cols} 个子图。",
        "export_title": "导出排版图",
        "export_failed": "无法导出图表：",
        "csv_folder": "选择处理后 CSV 输出文件夹",
        "saved_plot": "图表已保存：{path}",
        "saved_csv": "已导出 {count} 个处理后 CSV：{path}",
        "palette_note": "配色为期刊风格参考，不代表期刊强制规范。",
        "help_text": (
            "输入列顺序：\nV1  V2  V3  V4  R  a  t\n\n"
            "R 直接读取文件中的已计算结果；默认删除 R ≤ 0 的数据行。\n"
            "X 轴单选，Y 轴可以多选。每条 Y 曲线的颜色、线型和线宽会统一\n"
            "应用到所有文件子图。\n\n"
            "多文件会自动排版。鼠标左键拖动当前子图，滚轮以指针为中心缩放，\n"
            "工具栏 Home 可恢复坐标范围。\n\n"
            "导出的 CSV 列名保持固定英文，便于后续脚本分析。"
        ),
        "about_text": "用于 DEFET 测量的灵活双语数据处理与论文风格绘图工具。",
    },
}


@dataclass
class RawData:
    path: Path
    columns: dict[str, np.ndarray]
    n_rows: int


@dataclass
class ProcessSettings:
    remove_nonpositive_r: bool = True
    baseline_method: str = BASELINE_METHODS[0]
    baseline_window_s: float = 1.0
    displacement_direction: str = DISPLACEMENT_DIRECTIONS[0]
    clamp_negative_displacement: bool = True
    zero_time: bool = True
    max_plot_points: int = 5000


@dataclass
class ProcessedData:
    path: Path
    columns: dict[str, np.ndarray]
    a0: float
    n_raw: int
    n_valid: int

    def downsample_indices(self, maximum: int) -> np.ndarray:
        if self.n_valid <= maximum:
            return np.arange(self.n_valid)
        return np.unique(np.linspace(0, self.n_valid - 1, maximum).astype(int))


@dataclass
class SeriesStyle:
    color: str
    linestyle: str = "-"
    linewidth: float = 1.25


def load_dat_file(path: str | Path) -> RawData:
    path = Path(path)
    try:
        values = np.loadtxt(path, usecols=range(7), ndmin=2)
    except ValueError:
        values = np.genfromtxt(path, usecols=range(7), comments="#", invalid_raise=False, ndmin=2)
        values = values[np.all(np.isfinite(values), axis=1)]
    if values.ndim != 2 or values.shape[1] != 7 or not len(values):
        raise ValueError("Expected seven numeric columns: V1 V2 V3 V4 R a t.")
    return RawData(path, {key: values[:, i] for i, key in enumerate(RAW_KEYS)}, len(values))


def process_raw_data(raw: RawData, settings: ProcessSettings) -> ProcessedData:
    valid = np.ones(raw.n_rows, dtype=bool)
    for array in raw.columns.values():
        valid &= np.isfinite(array)
    if settings.remove_nonpositive_r:
        valid &= raw.columns["R"] > 0
    if not np.any(valid):
        raise ValueError("No valid rows remain after filtering.")

    columns = {key: array[valid].copy() for key, array in raw.columns.items()}
    relative_s = (columns["t_raw_ms"] - columns["t_raw_ms"][0]) / 1000.0
    initial = relative_s <= max(settings.baseline_window_s, 0.0)
    if not np.any(initial):
        initial[0] = True

    if settings.baseline_method == BASELINE_METHODS[0]:
        a0 = float(np.median(columns["a_raw"][initial]))
    elif settings.baseline_method == BASELINE_METHODS[1]:
        a0 = float(columns["a_raw"][0])
    elif settings.baseline_method == BASELINE_METHODS[2]:
        a0 = float(np.min(columns["a_raw"][initial]))
    else:
        raise ValueError(f"Unsupported baseline method: {settings.baseline_method}")

    if settings.displacement_direction == DISPLACEMENT_DIRECTIONS[0]:
        compression = columns["a_raw"] - a0
    else:
        compression = a0 - columns["a_raw"]
    if settings.clamp_negative_displacement:
        compression = np.maximum(compression, 0.0)

    columns["compression_mm"] = compression
    columns["time_s"] = relative_s if settings.zero_time else columns["t_raw_ms"] / 1000.0
    return ProcessedData(raw.path, columns, a0, raw.n_rows, int(valid.sum()))


def write_processed_csv(data: ProcessedData, output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["file_name", *COLUMN_KEYS])
        arrays = [data.columns[key] for key in COLUMN_KEYS]
        for row in zip(*arrays):
            writer.writerow([data.path.name, *row])


def apply_paper_style(font_family: str, font_size: float) -> None:
    plt.rcParams.update(
        {
            "font.family": font_family,
            "font.size": font_size,
            "axes.labelsize": font_size,
            "axes.titlesize": font_size + 1,
            "xtick.labelsize": max(font_size - 1, 6),
            "ytick.labelsize": max(font_size - 1, 6),
            "legend.fontsize": max(font_size - 1, 6),
            "axes.linewidth": 0.8,
            "xtick.direction": "in",
            "ytick.direction": "in",
            "xtick.top": True,
            "ytick.right": True,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.05,
        }
    )


def subplot_grid(count: int) -> tuple[int, int]:
    if count <= 1:
        return 1, 1
    cols = math.ceil(math.sqrt(count))
    rows = math.ceil(count / cols)
    return rows, cols


class DEFETPlotterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.language = "zh"
        self.raw_data: dict[Path, RawData] = {}
        self.display_paths: list[Path] = []
        self.series_styles: dict[str, SeriesStyle] = {}
        self.load_queue: queue.Queue = queue.Queue()
        self.is_loading = False
        self.axes: list = []
        self._pan_axis = None

        self._build_variables()
        self.title(f"{self.tr('app')} {APP_VERSION}")
        self.geometry("1500x940")
        self.minsize(1120, 740)
        self._configure_ttk()
        self._build_menu()
        self._build_layout()
        self._bind_global_events()
        self.after(100, self._poll_load_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def tr(self, key: str, **kwargs) -> str:
        value = UI[self.language].get(key, UI["en"].get(key, key))
        return value.format(**kwargs) if kwargs else value

    def option_text(self, canonical: str, language: str | None = None) -> str:
        language = language or self.language
        if canonical in BASELINE_METHODS and language == "zh":
            return OPTION_ZH[canonical]
        if canonical in PALETTES and language == "zh":
            return PALETTE_DISPLAY_ZH[canonical]
        return canonical

    def canonical_option(self, display: str, choices: Iterable[str]) -> str:
        for canonical in choices:
            if display in (canonical, self.option_text(canonical, "en"), self.option_text(canonical, "zh")):
                return canonical
        return display

    def column_text(self, key: str, language: str | None = None) -> str:
        return COLUMN_LABELS[language or self.language][key]

    def column_key(self, display: str) -> str:
        for key in COLUMN_KEYS:
            if display in (key, COLUMN_LABELS["en"][key], COLUMN_LABELS["zh"][key]):
                return key
        return display

    def _build_variables(self) -> None:
        self.language_var = tk.StringVar(value=self.language)
        self.remove_r_var = tk.BooleanVar(value=True)
        self.baseline_var = tk.StringVar(value=self.option_text(BASELINE_METHODS[0]))
        self.window_var = tk.StringVar(value="1.0")
        self.direction_var = tk.StringVar(value=DISPLACEMENT_DIRECTIONS[0])
        self.clamp_var = tk.BooleanVar(value=True)
        self.zero_time_var = tk.BooleanVar(value=True)
        self.max_points_var = tk.StringVar(value="5000")

        self.x_var = tk.StringVar(value=self.column_text("time_s"))
        self.palette_var = tk.StringVar(value=self.option_text(next(iter(PALETTES))))
        self.series_var = tk.StringVar(value="")
        self.series_line_var = tk.StringVar(value="-")
        self.series_width_var = tk.StringVar(value="1.25")
        self.annotation_language_var = tk.StringVar(value="English")
        self.font_var = tk.StringVar(value="Arial")
        self.font_size_var = tk.StringVar(value="9")
        self.x_scale_var = tk.StringVar(value="linear")
        self.y_scale_var = tk.StringVar(value="linear")
        self.grid_var = tk.BooleanVar(value=True)
        self.legend_var = tk.BooleanVar(value=True)
        self.title_var = tk.StringVar(value="")
        self.panel_width_var = tk.StringVar(value="3.25")
        self.panel_height_var = tk.StringVar(value="2.65")
        self.dpi_var = tk.StringVar(value="300")
        self.status_var = tk.StringVar(value=self.tr("ready"))

    def _configure_ttk(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Status.TLabel", padding=(8, 4))

    def _build_menu(self) -> None:
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label=self.tr("open_files_menu"), command=self.open_files, accelerator="Ctrl+O")
        file_menu.add_command(label=self.tr("open_folder_menu"), command=self.open_folder)
        file_menu.add_separator()
        file_menu.add_command(label=self.tr("export_plot_menu"), command=self.export_figure, accelerator="Ctrl+S")
        file_menu.add_command(label=self.tr("export_csv_menu"), command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label=self.tr("exit"), command=self._on_close)
        menu.add_cascade(label=self.tr("file"), menu=file_menu)

        language_menu = tk.Menu(menu, tearoff=False)
        language_menu.add_radiobutton(label="中文", value="zh", variable=self.language_var, command=lambda: self.set_language("zh"))
        language_menu.add_radiobutton(label="English", value="en", variable=self.language_var, command=lambda: self.set_language("en"))
        menu.add_cascade(label=self.tr("language"), menu=language_menu)

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label=self.tr("data_help"), command=self.show_help)
        help_menu.add_command(label=self.tr("about"), command=self.show_about)
        menu.add_cascade(label=self.tr("help"), menu=help_menu)
        self.config(menu=menu)

    def _build_layout(self) -> None:
        apply_paper_style(self.font_var.get(), self._safe_float(self.font_size_var.get(), 9.0))
        pane = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True)
        controls = ttk.Frame(pane, padding=9, width=380)
        workspace = ttk.Frame(pane, padding=(4, 8, 8, 8))
        pane.add(controls, weight=0)
        pane.add(workspace, weight=1)

        controls_canvas = tk.Canvas(controls, highlightthickness=0, width=370)
        controls_scroll = ttk.Scrollbar(controls, orient=tk.VERTICAL, command=controls_canvas.yview)
        controls_inner = ttk.Frame(controls_canvas)
        controls_inner.bind("<Configure>", lambda _e: controls_canvas.configure(scrollregion=controls_canvas.bbox("all")))
        controls_canvas.create_window((0, 0), window=controls_inner, anchor="nw", width=350)
        controls_canvas.configure(yscrollcommand=controls_scroll.set)
        controls_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        controls_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._build_file_panel(controls_inner)
        self._build_processing_panel(controls_inner)
        self._build_axis_panel(controls_inner)
        self._build_series_panel(controls_inner)
        self._build_figure_panel(controls_inner)

        notebook = ttk.Notebook(workspace)
        notebook.pack(fill=tk.BOTH, expand=True)
        plot_tab = ttk.Frame(notebook)
        summary_tab = ttk.Frame(notebook)
        notebook.add(plot_tab, text=self.tr("plot_tab"))
        notebook.add(summary_tab, text=self.tr("summary_tab"))

        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_tab)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        toolbar_row = ttk.Frame(plot_tab)
        toolbar_row.pack(fill=tk.X)
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_row, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.pack(side=tk.LEFT)
        ttk.Label(toolbar_row, text=self.tr("mouse_hint")).pack(side=tk.RIGHT, padx=8)
        self._connect_canvas_events()
        self._draw_empty()

        columns = ("file", "rows", "valid", "duration", "compression", "r", "a0")
        self.summary_tree = ttk.Treeview(summary_tab, columns=columns, show="headings")
        headings = {
            "file": self.tr("summary_file"),
            "rows": self.tr("summary_rows"),
            "valid": self.tr("summary_valid"),
            "duration": self.tr("summary_duration"),
            "compression": self.tr("summary_compression"),
            "r": self.tr("summary_r"),
            "a0": self.tr("summary_a0"),
        }
        widths = {"file": 180, "rows": 85, "valid": 85, "duration": 100, "compression": 160, "r": 200, "a0": 100}
        for key in columns:
            self.summary_tree.heading(key, text=headings[key])
            self.summary_tree.column(key, width=widths[key], anchor=tk.W if key == "file" else tk.E)
        yscroll = ttk.Scrollbar(summary_tab, orient=tk.VERTICAL, command=self.summary_tree.yview)
        xscroll = ttk.Scrollbar(summary_tab, orient=tk.HORIZONTAL, command=self.summary_tree.xview)
        self.summary_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.summary_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        summary_tab.rowconfigure(0, weight=1)
        summary_tab.columnconfigure(0, weight=1)
        ttk.Label(self, textvariable=self.status_var, style="Status.TLabel", anchor=tk.W).pack(fill=tk.X)
        self._ensure_series_styles()
        self._refresh_series_selector()

    def _build_file_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text=self.tr("files"), padding=8)
        frame.pack(fill=tk.X, pady=(0, 7))
        list_row = ttk.Frame(frame)
        list_row.pack(fill=tk.X)
        self.file_list = tk.Listbox(list_row, selectmode=tk.EXTENDED, height=6, exportselection=False)
        scroll = ttk.Scrollbar(list_row, orient=tk.VERTICAL, command=self.file_list.yview)
        self.file_list.configure(yscrollcommand=scroll.set)
        self.file_list.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_list.bind("<<ListboxSelect>>", lambda _e: self.update_preview())
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(row, text=self.tr("open_files"), command=self.open_files).pack(side=tk.LEFT)
        ttk.Button(row, text=self.tr("select_all"), command=self.select_all_files).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text=self.tr("remove"), command=self.remove_selected_files).pack(side=tk.LEFT)

    def _build_processing_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text=self.tr("processing"), padding=8)
        frame.pack(fill=tk.X, pady=(0, 7))
        ttk.Checkbutton(frame, text=self.tr("raw_positive"), variable=self.remove_r_var).pack(anchor=tk.W)
        self._combo_row(frame, self.tr("baseline_method"), self.baseline_var, [self.option_text(v) for v in BASELINE_METHODS])
        self._entry_row(frame, self.tr("initial_window"), self.window_var)
        self._combo_row(frame, self.tr("direction"), self.direction_var, DISPLACEMENT_DIRECTIONS)
        ttk.Checkbutton(frame, text=self.tr("clamp"), variable=self.clamp_var).pack(anchor=tk.W)
        ttk.Checkbutton(frame, text=self.tr("zero_time"), variable=self.zero_time_var).pack(anchor=tk.W)
        self._entry_row(frame, self.tr("max_points"), self.max_points_var)

    def _build_axis_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text=self.tr("axes"), padding=8)
        frame.pack(fill=tk.X, pady=(0, 7))
        self._combo_row(frame, self.tr("x_column"), self.x_var, [self.column_text(k) for k in COLUMN_KEYS])
        ttk.Label(frame, text=self.tr("y_columns")).pack(anchor=tk.W, pady=(4, 1))
        self.y_list = tk.Listbox(frame, selectmode=tk.EXTENDED, height=7, exportselection=False)
        for key in COLUMN_KEYS:
            self.y_list.insert(tk.END, self.column_text(key))
        self.y_list.pack(fill=tk.X)
        self.y_list.selection_set(COLUMN_KEYS.index("V1"))
        self.y_list.selection_set(COLUMN_KEYS.index("V2"))
        self.y_list.bind("<<ListboxSelect>>", self._on_y_selection)

    def _build_series_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text=self.tr("style"), padding=8)
        frame.pack(fill=tk.X, pady=(0, 7))
        self._combo_row(frame, self.tr("palette"), self.palette_var, [self.option_text(k) for k in PALETTES])
        ttk.Button(frame, text=self.tr("apply_palette"), command=self.apply_palette).pack(fill=tk.X, pady=(2, 5))
        ttk.Label(frame, text=self.tr("palette_note"), wraplength=320).pack(anchor=tk.W, pady=(0, 5))
        self.series_combo = self._combo_row(frame, self.tr("series"), self.series_var, ())
        self.series_combo.bind("<<ComboboxSelected>>", lambda _event: self._sync_series_controls())
        style_row = ttk.Frame(frame)
        style_row.pack(fill=tk.X, pady=2)
        ttk.Button(style_row, text=self.tr("color"), command=self.choose_series_color).pack(side=tk.LEFT)
        self.color_swatch = tk.Label(style_row, width=4, background="#0072B2", relief=tk.SUNKEN)
        self.color_swatch.pack(side=tk.LEFT, padx=(4, 10))
        ttk.Label(style_row, text=self.tr("line_style")).pack(side=tk.LEFT)
        ttk.Combobox(style_row, textvariable=self.series_line_var, values=LINE_STYLES, state="readonly", width=5).pack(side=tk.LEFT, padx=4)
        ttk.Label(style_row, text=self.tr("line_width")).pack(side=tk.LEFT)
        ttk.Entry(style_row, textvariable=self.series_width_var, width=6).pack(side=tk.LEFT, padx=4)
        ttk.Button(frame, text=self.tr("apply_style"), command=self.apply_series_style).pack(fill=tk.X, pady=(3, 0))

    def _build_figure_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text=self.tr("figure"), padding=8)
        frame.pack(fill=tk.X, pady=(0, 7))
        self._combo_row(frame, self.tr("annotation_language"), self.annotation_language_var, ("English", "中文"))
        self._combo_row(frame, self.tr("font"), self.font_var, FONT_CHOICES, editable=True)
        self._entry_row(frame, self.tr("font_size"), self.font_size_var)
        scales = ("linear", "log")
        self._combo_row(frame, self.tr("x_scale"), self.x_scale_var, scales)
        self._combo_row(frame, self.tr("y_scale"), self.y_scale_var, scales)
        ttk.Checkbutton(frame, text=self.tr("grid"), variable=self.grid_var).pack(anchor=tk.W)
        ttk.Checkbutton(frame, text=self.tr("legend"), variable=self.legend_var).pack(anchor=tk.W)
        self._entry_row(frame, self.tr("figure_title"), self.title_var)
        size_row = ttk.Frame(frame)
        size_row.pack(fill=tk.X, pady=2)
        ttk.Label(size_row, text=self.tr("panel_size")).pack(side=tk.LEFT)
        ttk.Entry(size_row, textvariable=self.panel_width_var, width=5).pack(side=tk.LEFT, padx=(5, 2))
        ttk.Entry(size_row, textvariable=self.panel_height_var, width=5).pack(side=tk.LEFT)
        ttk.Label(size_row, text=self.tr("dpi")).pack(side=tk.LEFT, padx=(8, 2))
        ttk.Entry(size_row, textvariable=self.dpi_var, width=5).pack(side=tk.LEFT)
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(row, text=self.tr("update"), command=self.update_preview).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text=self.tr("export"), command=self.export_figure).pack(side=tk.LEFT, padx=(5, 0))

    @staticmethod
    def _entry_row(parent: ttk.Frame, label: str, variable: tk.Variable) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=variable, width=17).pack(side=tk.RIGHT)

    @staticmethod
    def _combo_row(
        parent: ttk.Frame,
        label: str,
        variable: tk.Variable,
        values: Iterable[str],
        editable: bool = False,
    ) -> ttk.Combobox:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label).pack(side=tk.LEFT)
        combo = ttk.Combobox(row, textvariable=variable, values=tuple(values), width=27, state="normal" if editable else "readonly")
        combo.pack(side=tk.RIGHT)
        return combo

    def _bind_global_events(self) -> None:
        self.bind_all("<Control-o>", lambda _e: self.open_files())
        self.bind_all("<Control-s>", lambda _e: self.export_figure())
        self.x_var.trace_add("write", lambda *_: self.update_preview())
        self.x_scale_var.trace_add("write", lambda *_: self.update_preview())
        self.y_scale_var.trace_add("write", lambda *_: self.update_preview())
        self.annotation_language_var.trace_add("write", lambda *_: self.update_preview())

    def _connect_canvas_events(self) -> None:
        self.canvas.mpl_connect("button_press_event", self._on_mouse_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_motion)
        self.canvas.mpl_connect("button_release_event", self._on_mouse_release)
        self.canvas.mpl_connect("scroll_event", self._on_mouse_scroll)

    def _on_mouse_press(self, event) -> None:
        if event.button != 1 or event.inaxes is None or self.toolbar.mode:
            return
        self._pan_axis = event.inaxes
        self._pan_axis.start_pan(event.x, event.y, 1)

    def _on_mouse_motion(self, event) -> None:
        if self._pan_axis is None or event.x is None or event.y is None:
            return
        self._pan_axis.drag_pan(1, event.key, event.x, event.y)
        self.canvas.draw_idle()

    def _on_mouse_release(self, event) -> None:
        if self._pan_axis is None:
            return
        self._pan_axis.end_pan()
        self._pan_axis = None
        self.canvas.draw_idle()

    def _on_mouse_scroll(self, event) -> None:
        ax = event.inaxes
        if ax is None or event.xdata is None or event.ydata is None:
            return
        factor = 1 / 1.2 if event.button == "up" else 1.2
        ax.set_xlim(self._zoom_limits(ax.get_xlim(), event.xdata, factor, ax.get_xscale()))
        ax.set_ylim(self._zoom_limits(ax.get_ylim(), event.ydata, factor, ax.get_yscale()))
        self.canvas.draw_idle()

    @staticmethod
    def _zoom_limits(limits, center: float, factor: float, scale: str):
        lo, hi = limits
        if scale == "log" and lo > 0 and hi > 0 and center > 0:
            lo_l, hi_l, c_l = np.log10([lo, hi, center])
            return 10 ** (c_l - (c_l - lo_l) * factor), 10 ** (c_l + (hi_l - c_l) * factor)
        return center - (center - lo) * factor, center + (hi - center) * factor

    def set_language(self, language: str) -> None:
        if language == self.language:
            return
        x_key = self.column_key(self.x_var.get())
        y_keys = self.selected_y_keys()
        baseline = self.canonical_option(self.baseline_var.get(), BASELINE_METHODS)
        palette = self.canonical_option(self.palette_var.get(), PALETTES)
        selected_files = set(self.selected_paths()) if hasattr(self, "file_list") else set()
        self.language = language
        self.language_var.set(language)
        self.x_var.set(self.column_text(x_key))
        self.baseline_var.set(self.option_text(baseline))
        self.palette_var.set(self.option_text(palette))
        plt.close(self.figure)
        for child in self.winfo_children():
            child.destroy()
        self.title(f"{self.tr('app')} {APP_VERSION}")
        self._build_menu()
        self._build_layout()
        for i, path in enumerate(self.display_paths):
            self.file_list.insert(tk.END, path.name)
            if path in selected_files:
                self.file_list.selection_set(i)
        self.y_list.selection_clear(0, tk.END)
        for key in y_keys:
            self.y_list.selection_set(COLUMN_KEYS.index(key))
        self._refresh_series_selector()
        self.status_var.set(self.tr("ready"))
        self.update_preview()

    def selected_paths(self) -> list[Path]:
        if not hasattr(self, "file_list"):
            return []
        return [self.display_paths[i] for i in self.file_list.curselection()]

    def selected_y_keys(self) -> list[str]:
        if not hasattr(self, "y_list"):
            return ["V1", "V2"]
        return [COLUMN_KEYS[i] for i in self.y_list.curselection()]

    def open_files(self) -> None:
        paths = filedialog.askopenfilenames(title=self.tr("open_title"), filetypes=[("DAT", "*.dat"), ("All files", "*.*")])
        if paths:
            self._start_loading([Path(p) for p in paths])

    def open_folder(self) -> None:
        folder = filedialog.askdirectory(title=self.tr("folder_title"))
        if not folder:
            return
        paths = sorted(Path(folder).glob("*.dat"))
        if not paths:
            messagebox.showinfo(self.tr("app"), self.tr("no_dat"))
            return
        self._start_loading(paths)

    def _start_loading(self, paths: list[Path]) -> None:
        paths = [p for p in paths if p not in self.raw_data]
        if not paths:
            self.status_var.set(self.tr("already_loaded"))
            return
        if self.is_loading:
            messagebox.showinfo(self.tr("app"), self.tr("load_busy"))
            return
        self.is_loading = True
        self.status_var.set(self.tr("loading", count=len(paths)))

        def worker() -> None:
            loaded, errors = [], []
            for path in paths:
                try:
                    loaded.append(load_dat_file(path))
                except Exception as exc:
                    errors.append(f"{path.name}: {exc}")
            self.load_queue.put((loaded, errors))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_load_queue(self) -> None:
        try:
            loaded, errors = self.load_queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_load_queue)
            return
        for raw in loaded:
            self.raw_data[raw.path] = raw
            self.display_paths.append(raw.path)
            self.file_list.insert(tk.END, raw.path.name)
        self.is_loading = False
        if loaded:
            self.select_all_files()
            self.status_var.set(self.tr("loaded", count=len(loaded), total=len(self.raw_data)))
        if errors:
            messagebox.showwarning(self.tr("app"), self.tr("load_errors") + "\n\n" + "\n".join(errors))
        self.after(100, self._poll_load_queue)

    def select_all_files(self) -> None:
        self.file_list.selection_set(0, tk.END)
        self.update_preview()

    def remove_selected_files(self) -> None:
        for index in reversed(self.file_list.curselection()):
            path = self.display_paths.pop(index)
            self.raw_data.pop(path, None)
            self.file_list.delete(index)
        if self.display_paths:
            self.file_list.selection_set(0, tk.END)
        self.update_preview()

    def get_settings(self) -> ProcessSettings:
        try:
            window = float(self.window_var.get())
            maximum = int(float(self.max_points_var.get()))
            if window < 0 or maximum < 100:
                raise ValueError
        except ValueError as exc:
            raise ValueError(self.tr("settings_error")) from exc
        return ProcessSettings(
            remove_nonpositive_r=self.remove_r_var.get(),
            baseline_method=self.canonical_option(self.baseline_var.get(), BASELINE_METHODS),
            baseline_window_s=window,
            displacement_direction=self.direction_var.get(),
            clamp_negative_displacement=self.clamp_var.get(),
            zero_time=self.zero_time_var.get(),
            max_plot_points=maximum,
        )

    def get_figure_values(self) -> tuple[float, float, float, int]:
        try:
            font_size = float(self.font_size_var.get())
            panel_w = float(self.panel_width_var.get())
            panel_h = float(self.panel_height_var.get())
            dpi = int(float(self.dpi_var.get()))
            if min(font_size, panel_w, panel_h, dpi) <= 0:
                raise ValueError
        except ValueError as exc:
            raise ValueError(self.tr("style_error")) from exc
        return font_size, panel_w, panel_h, dpi

    def process_selected(self) -> list[ProcessedData]:
        settings = self.get_settings()
        processed, errors = [], []
        for path in self.selected_paths():
            try:
                processed.append(process_raw_data(self.raw_data[path], settings))
            except Exception as exc:
                errors.append(f"{path.name}: {exc}")
        if errors:
            messagebox.showwarning(self.tr("app"), self.tr("processing_errors") + "\n\n" + "\n".join(errors))
        return processed

    def _on_y_selection(self, _event=None) -> None:
        self._ensure_series_styles()
        self._refresh_series_selector()
        self.update_preview()

    def _ensure_series_styles(self) -> None:
        palette = PALETTES[self.canonical_option(self.palette_var.get(), PALETTES)]
        for i, key in enumerate(self.selected_y_keys()):
            self.series_styles.setdefault(key, SeriesStyle(palette[i % len(palette)]))

    def _refresh_series_selector(self) -> None:
        keys = self.selected_y_keys()
        displays = [self.column_text(k) for k in keys]
        current_key = self._series_key()
        self.series_combo.configure(values=displays)
        if current_key in keys:
            self.series_var.set(self.column_text(current_key))
        else:
            self.series_var.set(displays[0] if displays else "")
        self._sync_series_controls()

    def _series_key(self) -> str | None:
        display = self.series_var.get()
        return self.column_key(display) if display else None

    def _sync_series_controls(self) -> None:
        key = self._series_key()
        if key is None:
            return
        self._ensure_series_styles()
        style = self.series_styles[key]
        self.series_line_var.set(style.linestyle)
        self.series_width_var.set(f"{style.linewidth:g}")
        if hasattr(self, "color_swatch"):
            self.color_swatch.configure(background=style.color)

    def apply_palette(self) -> None:
        canonical = self.canonical_option(self.palette_var.get(), PALETTES)
        colors = PALETTES[canonical]
        for i, key in enumerate(self.selected_y_keys()):
            current = self.series_styles.get(key, SeriesStyle(colors[i % 5]))
            self.series_styles[key] = SeriesStyle(colors[i % 5], current.linestyle, current.linewidth)
        self._sync_series_controls()
        self.update_preview()

    def choose_series_color(self) -> None:
        key = self._series_key()
        if key is None:
            return
        self._ensure_series_styles()
        _rgb, color = colorchooser.askcolor(color=self.series_styles[key].color, title=self.tr("color"))
        if color:
            self.series_styles[key].color = color
            self.color_swatch.configure(background=color)
            self.update_preview()

    def apply_series_style(self) -> None:
        key = self._series_key()
        if key is None:
            return
        try:
            width = float(self.series_width_var.get())
            if width <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(self.tr("app"), self.tr("style_error"))
            return
        self._ensure_series_styles()
        self.series_styles[key].linestyle = self.series_line_var.get()
        self.series_styles[key].linewidth = width
        self.update_preview()

    def _annotation_language(self) -> str:
        return "zh" if self.annotation_language_var.get() == "中文" else "en"

    def update_preview(self) -> None:
        if not hasattr(self, "figure"):
            return
        try:
            processed = self.process_selected()
            font_size, _panel_w, _panel_h, _dpi = self.get_figure_values()
        except ValueError as exc:
            self.status_var.set(str(exc))
            return
        y_keys = self.selected_y_keys()
        if not processed:
            self._draw_empty()
            self._update_summary([])
            return
        if not y_keys:
            self.status_var.set(self.tr("select_y"))
            self._draw_empty()
            return

        self._ensure_series_styles()
        apply_paper_style(self.font_var.get(), font_size)
        rows, cols = subplot_grid(len(processed))
        self.figure.clear()
        axes_array = self.figure.subplots(rows, cols, squeeze=False)
        all_axes = list(axes_array.ravel())
        self.axes = all_axes[: len(processed)]
        for ax in all_axes[len(processed) :]:
            ax.set_visible(False)

        settings = self.get_settings()
        x_key = self.column_key(self.x_var.get())
        label_lang = self._annotation_language()
        for ax, data in zip(self.axes, processed):
            idx = data.downsample_indices(settings.max_plot_points)
            x = data.columns[x_key][idx]
            for key in y_keys:
                style = self.series_styles[key]
                ax.plot(
                    x,
                    data.columns[key][idx],
                    color=style.color,
                    linestyle=style.linestyle,
                    linewidth=style.linewidth,
                    label=COLUMN_LABELS[label_lang][key],
                )
            ax.set_title(data.path.stem)
            ax.set_xlabel(COLUMN_LABELS[label_lang][x_key])
            if len(y_keys) == 1:
                ax.set_ylabel(COLUMN_LABELS[label_lang][y_keys[0]])
            else:
                ax.set_ylabel(" / ".join(COLUMN_LABELS[label_lang][k] for k in y_keys))
            try:
                ax.set_xscale(self.x_scale_var.get())
                ax.set_yscale(self.y_scale_var.get())
            except ValueError:
                ax.set_xscale("linear")
                ax.set_yscale("linear")
            self._style_axis(ax)
            if self.legend_var.get():
                ax.legend(frameon=False, loc="best")

        title = self.title_var.get().strip()
        if title:
            self.figure.suptitle(title, y=0.995)
        self.figure.tight_layout(pad=1.0, rect=(0, 0, 1, 0.98 if title else 1))
        self.canvas.draw_idle()
        self._update_summary(processed)
        self.status_var.set(self.tr("plotted", count=len(processed), rows=rows, cols=cols))

    def _style_axis(self, ax) -> None:
        ax.tick_params(which="both", direction="in", top=True, right=True)
        if ax.get_xscale() == "linear":
            ax.xaxis.set_minor_locator(AutoMinorLocator())
        else:
            ax.xaxis.set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10) * 0.1))
            ax.xaxis.set_minor_formatter(NullFormatter())
        if ax.get_yscale() == "linear":
            ax.yaxis.set_minor_locator(AutoMinorLocator())
        else:
            ax.yaxis.set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10) * 0.1))
            ax.yaxis.set_minor_formatter(NullFormatter())
        if self.grid_var.get():
            ax.grid(True, which="major", color="#B0B0B0", alpha=0.28, linewidth=0.55)

    def _draw_empty(self) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, self.tr("empty"), ha="center", va="center", color="#666666", transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        self.axes = [ax]
        self.canvas.draw_idle()

    def _update_summary(self, processed: list[ProcessedData]) -> None:
        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)
        for data in processed:
            c = data.columns
            duration = float(c["time_s"][-1] - c["time_s"][0])
            self.summary_tree.insert(
                "",
                tk.END,
                values=(
                    data.path.name,
                    f"{data.n_raw:,}",
                    f"{data.n_valid:,}",
                    f"{duration:.3f}",
                    f"{np.min(c['compression_mm']):.4g} to {np.max(c['compression_mm']):.4g}",
                    f"{np.min(c['R']):.4g} to {np.max(c['R']):.4g}",
                    f"{data.a0:.6g}",
                ),
            )

    def export_figure(self) -> None:
        if not self.selected_paths():
            messagebox.showinfo(self.tr("app"), self.tr("select_files"))
            return
        path = filedialog.asksaveasfilename(
            title=self.tr("export_title"),
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg"), ("TIFF", "*.tif")],
        )
        if not path:
            return
        try:
            _font_size, panel_w, panel_h, dpi = self.get_figure_values()
            rows, cols = subplot_grid(len(self.selected_paths()))
            old_size = self.figure.get_size_inches()
            self.figure.set_size_inches(panel_w * cols, panel_h * rows)
            self.figure.savefig(path, dpi=dpi)
            self.figure.set_size_inches(old_size)
            self.canvas.draw_idle()
            self.status_var.set(self.tr("saved_plot", path=path))
        except Exception as exc:
            messagebox.showerror(self.tr("app"), self.tr("export_failed") + f"\n{exc}")

    def export_csv(self) -> None:
        processed = self.process_selected()
        if not processed:
            messagebox.showinfo(self.tr("app"), self.tr("select_files"))
            return
        folder = filedialog.askdirectory(title=self.tr("csv_folder"))
        if not folder:
            return
        errors = []
        for data in processed:
            try:
                write_processed_csv(data, Path(folder) / f"{data.path.stem}_processed.csv")
            except Exception as exc:
                errors.append(f"{data.path.name}: {exc}")
        if errors:
            messagebox.showwarning(self.tr("app"), "\n".join(errors))
        else:
            self.status_var.set(self.tr("saved_csv", count=len(processed), path=folder))

    def show_help(self) -> None:
        messagebox.showinfo(self.tr("data_help"), self.tr("help_text"))

    def show_about(self) -> None:
        messagebox.showinfo(self.tr("app"), f"{self.tr('app')} {APP_VERSION}\n\n{self.tr('about_text')}")

    @staticmethod
    def _safe_float(value: str, fallback: float) -> float:
        try:
            return float(value)
        except ValueError:
            return fallback

    def _on_close(self) -> None:
        plt.close(self.figure)
        self.destroy()


def self_test() -> int:
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as tmp:
        root = Path(tmp)
        path = root / "synthetic.dat"
        n = 1001
        t = np.arange(n) * 4.0 + 3_000_000.0
        a = 50.0 + 5.0 * np.arange(n) / (n - 1)
        v1 = np.full(n, 5.0)
        v2 = 4.5 - 2.5 * np.arange(n) / (n - 1)
        v3 = np.sin(np.linspace(0, 4 * np.pi, n))
        v4 = np.cos(np.linspace(0, 4 * np.pi, n))
        r = np.geomspace(3e10, 2e7, n)
        r[:10] = -1
        np.savetxt(path, np.column_stack([v1, v2, v3, v4, r, a, t]), delimiter="\t")
        raw = load_dat_file(path)
        processed = process_raw_data(raw, ProcessSettings(max_plot_points=300))
        assert raw.n_rows == n
        assert processed.n_valid == n - 10
        assert np.isclose(processed.columns["time_s"][0], 0)
        assert set(processed.columns) == set(COLUMN_KEYS)
        assert subplot_grid(1) == (1, 1)
        assert subplot_grid(6) == (2, 3)
        assert len(PALETTES) == 5 and all(len(colors) == 5 for colors in PALETTES.values())
        csv_path = root / "processed.csv"
        write_processed_csv(processed, csv_path)
        assert csv_path.exists() and csv_path.stat().st_size > 1000
        apply_paper_style("DejaVu Sans", 9)
        fig, axs = plt.subplots(1, 2, figsize=(6, 3))
        idx = processed.downsample_indices(300)
        for ax in axs:
            ax.plot(processed.columns["compression_mm"][idx], processed.columns["V1"][idx])
            ax.plot(processed.columns["compression_mm"][idx], processed.columns["V2"][idx])
        fig.tight_layout()
        png = root / "test.png"
        fig.savefig(png, dpi=120)
        plt.close(fig)
        assert png.exists() and png.stat().st_size > 1000
    print("SELF-TEST PASSED")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    app = DEFETPlotterApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
