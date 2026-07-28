# DEFET Data Plotter 2.0

用于读取、处理和绘制 DEFET switch `.dat` 数据的 Windows 桌面软件。

## 本版本功能

- 读取一个或多个 `.dat` 文件，预期列为 `V1 V2 V3 V4 R a t`。
- `R` 直接使用文件中的已计算电阻值；可过滤测量开始前的 `R <= 0` 数据。
- 自动生成：
  - `compression_mm`：位移基线校正后的压缩量；
  - `time_s = (t - t0) / 1000`。
- X 轴可选择任意数据列；Y 轴可同时选择任意一列或多列。
- 每条 Y 曲线均可单独设置颜色、实线/虚线类型及线宽。
- 内置五套各含五色的论文风格配色：
  - Nature-inspired muted
  - Science-inspired contrast
  - IEEE-inspired print-safe
  - ACS-inspired color-blind safe
  - Grayscale print
- 配色名称表示设计取向，并非期刊的官方强制模板；可对任意曲线自定义颜色。
- 多文件自动排列成子图网格；统一使用当前坐标、配色和曲线样式。
- 单个子图的导出宽度和高度可调，多图导出尺寸随网格自动增加。
- 图例、坐标轴和图内文字语言可独立选择 English/中文，不受界面语言影响；默认 English。
- 中文/English 界面可即时切换，并保留当前文件和绘图设置。
- 预览区中：
  - 鼠标左键拖动：平移当前子图；
  - 鼠标滚轮：以光标位置为中心缩放；
  - Matplotlib 工具栏仍可用于复位、保存等操作。
- 支持 PNG、PDF、SVG、TIFF 图像导出及处理后 CSV 导出。

## 运行

Windows 下双击：

`run_defet_plotter.bat`

若提示缺少 NumPy 或 Matplotlib，先双击：

`install_requirements.bat`

也可以在命令行运行：

```powershell
python defet_data_plotter.py
```

## 基本使用

1. 打开一个或多个 `.dat` 文件，并在文件列表中选择要展示的文件。
2. 设置位移基线、压缩方向和时间归零规则。
3. 在“坐标轴”中选择一个 X 列和一个或多个 Y 列。
4. 选择配色并点击“应用配色”；需要时再逐条修改颜色、线型和线宽。
5. 图内标注默认使用英语，可在“图形”区域单独切换。
6. 在预览区检查结果，然后导出图像或处理后的 CSV。

## 默认处理规则

1. 直接使用文件中的 `R` 列。
2. 删除 `R <= 0` 的行。
3. 以初始时间窗口内 `a` 的中位数作为 `a0`。
4. 默认 `compression_mm = a - a0`，负值截为 0。
5. `time_s = (t - first_valid_t) / 1000`。

如果机器坐标方向相反，可在 GUI 中改为 `a0 - a`。

## 自检

```powershell
python defet_data_plotter.py --self-test
```

自检会使用合成数据验证读取、处理、CSV 导出、多子图和绘图功能。
