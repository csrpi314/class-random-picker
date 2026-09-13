# class-random-picker · 班级随机抽取系统

🎲 班级随机抽取系统 | PySide6 + 安全随机 | 支持加权抽取、CSV 导入、日志记录

一个基于 **PySide6** 开发的安全、可加权的班级随机抽取软件，支持按性别过滤抽取，适用于课堂点名、互动提问等场景。导入 CSV 班级名册后，可自定义每位学生的权重，抽取过程采用系统安全随机数，公平且可追溯。所有操作均记录日志，并可打包为独立 exe 分发。

![主界面截图](https://image.zsh26.cc.cd/file/AgACAgUAAyEGAAMBA3LocAADFmqBaZpMyUjA0LVOOj8ILfCVYOnAAAIvFWsbqAEIVFbTvIwVfBdfAQADAgADeQADPQQ.png)
\* 截图所示数据仅供测试，由 Python 生成

## ✨ 功能特性

- **📋 CSV 名册导入（必含学号、姓名、性别列）**
  支持 `学号,姓名,性别,权重` 四列的 CSV 文件（权重可选，默认为 1）。自动检测 UTF-8/GBK 编码，逐行严格校验；学号/姓名/性别等致命错误整体取消导入，不会产生半份数据；权重值非法（非 0/1）不取消导入，报错并自动恢复为 1。

- **🎲 安全随机抽取**
  使用 `secrets.SystemRandom()` 实现密码学安全随机，支持放回抽取。权重仅允许 0（不参与抽取）或 1（参与抽取）两个值，任何非法输入都会报错并自动恢复为默认值 1。可随时在应用内调整。

- **👫 按性别过滤抽取**
  主界面提供“全部抽取”、“只抽男生”、“只抽女生”三个单选按钮，切换后左侧列表实时显示对应性别的学生，抽取范围即时生效。

- **⚖️ 一键等权重置**
  随时将所有学生权重恢复为 1，方便公平随机抽取。

- **📝 完整操作日志**
  每次运行生成独立日志文件（`yyyyMMdd.log`，同一天内自动递增序号），时间戳精确到毫秒，记录权重修改、导入、抽取结果等。当日超过 500 条时弹窗提醒导出。

- **💾 数据持久化与备份**
  学生名单与权重保存为 JSON（原子写入，防崩溃损坏），保存前自动轮换备份（保留最近 10 份），损坏时自动从备份恢复；支持导出名册为 CSV。数据默认存放在 `%APPDATA%\ClassRandomSampling\`（Windows）或 `~/ClassRandomSampling/`（Linux / macOS），支持 `--data-dir` 参数和程序内切换。

- **🔒 单实例锁**
  同一数据目录同时只能运行一个实例（QLockFile），防止数据竞争。

- **🖥️ 独立可执行文件**
  可使用 Nuitka 打包为单文件 `.exe`，无需安装 Python 环境，分发即用。

## 🖼️ 界面预览

| 主界面 | 权重修改 | 抽取结果 |
|--------|----------|----------|
| ![主界面](https://image.zsh26.cc.cd/file/AgACAgUAAyEGAAMBA3LocAADFmqBaZpMyUjA0LVOOj8ILfCVYOnAAAIvFWsbqAEIVFbTvIwVfBdfAQADAgADeQADPQQ.png) | ![权重](https://image.zsh26.cc.cd/file/AgACAgUAAyEGAAMBA3LocAADFWqBaZrU_gAB7h0mIGiHP80KvJQI_AACLhVrG6gBCFQVdFqe8BQJKAEAAwIAA3gAAz0E.png) | ![结果](https://image.zsh26.cc.cd/file/AgACAgUAAyEGAAMBA3LocAADF2qBaZrLZ3EXiCV6c4rHZunMao5bAAIwFWsbqAEIVJvRCQNw5BOKAQADAgADeQADPQQ.png) |

## 📦 安装

### 运行环境

- Windows 10 1809 及以上 / Linux / macOS（源码运行）
- Python 3.13+（开发用，打包后无需依赖）
- PySide6 6.11.1

### 从源码安装运行

1. 克隆仓库：

```bash
git clone https://github.com/csrpi314/class-random-picker.git
cd class-random-picker
```

2. （推荐）创建并激活虚拟环境：

```bash
# Windows (CMD)
python -m venv .venv
.venv\Scripts\activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

3. 安装依赖：

```bash
pip install pyside6==6.11.1
```

4. 运行程序：

```bash
python main.py
```

### 打包为独立 exe（可选）

安装 Nuitka 后执行打包，生成免安装的单文件可执行程序：

```bash
pip install nuitka==4.1.3
python -m nuitka --onefile --windows-console-mode=disable --enable-plugin=pyside6 main.py
```

> 打包产物 `main.exe` 可直接分发，目标机器无需安装 Python（需 Windows 10 1809+）。

## 🚀 快速开始

1. **导入名册**
   点击 `菜单 文件 → 导入 CSV 名册`，选择符合格式的 CSV 文件（格式见下，仓库根目录的 `normal_student_200.csv` 是一份 200 人的测试名册，可直接导入体验），确认后名单自动保存。

2. **调整权重**
   通过 `操作 → 修改权重` 打开对话框，设置每位学生是否参与抽取（权重 1 = 参与，权重 0 = 不参与，仅允许这两个值）。
   也可 `操作 → 重置权重` 恢复全部为 1。

3. **抽取学生**
   在左侧选择抽取范围（全部 / 只抽男生 / 只抽女生），点击右侧 `🎲 随机抽取` 按钮，结果将显示在界面中央，颜色变蓝并记录日志。

4. **查看记录**
   右侧日志区显示本次运行的所有操作，历史日志默认保存在数据目录下的 `.log` 文件中（`%APPDATA%\ClassRandomSampling\`（Windows）或 `~/ClassRandomSampling/`（Linux / macOS），可更改）。

## 📖 使用示例

### 命令行参数

```bash
# Windows：默认数据目录 %APPDATA%\ClassRandomSampling
python main.py
# Linux / macOS：默认数据目录 ~/ClassRandomSampling
python3 main.py

# 使用自定义数据目录（名册、日志、备份均存于此）
python main.py --data-dir D:\我的班级      # Windows
python3 main.py --data-dir ~/classes/一年二班   # Linux / macOS
```

> 同一数据目录受单实例锁保护，重复启动会提示并退出；如需多班级并行，为每个班级指定不同的 `--data-dir` 即可。

### CSV 名册格式示例

```csv
学号,姓名,性别,权重
1,张三,男,1
2,李四,女,0
3,王五,f,1
4,赵六,m
```

- 第一行为表头，必须包含 **学号、姓名、性别** 列（支持中文或英文 `id` / `name` / `sex`，学号亦可用 `no`、`num` 等）。
- **权重**列可选，仅允许 0 或 1：缺失时自动设为 1；0 表示该学生不参与抽取；其他数值（如 0.5、2）导入时会报错并自动恢复为 1。
- 学号范围 1~999，不可重复。
- 性别支持：男/女、m/f，以及 male/female 等常见写法（不区分大小写）。
- 编码推荐 UTF-8（带或不带 BOM 均可），也兼容 GBK。

### 生成测试名册

`generator.py` 可生成 200 人的随机测试名册：

```bash
python generator.py
```

### 数据目录结构

```
# Windows：%APPDATA%\ClassRandomSampling\    Linux / macOS：~/ClassRandomSampling/
├── roster.json        # 当前名册（原子写入）
├── app.lock           # 单实例锁
├── logs\
│   └── yyyyMMdd.log   # 操作日志
└── backups\
    ├── roster_*.json  # 名册自动轮换备份（保留 10 份）
    └── 名册备份_*.csv # 手动导出的 CSV 备份
```

## 🗂️ 项目结构

```
class-random-picker/
├── main.py            # 应用入口：参数解析、单实例锁、日志初始化、窗口启动
├── config.py          # 全局常量（权重规则、CSV 表头别名、日志/备份策略等）
├── models.py          # Student 数据模型与 CSV 导入（编码探测 + 严格校验）
├── storage.py         # 数据持久化（JSON 原子写入、轮换备份、单实例锁）
├── logger.py          # 操作日志（毫秒时间戳、按天分文件、递增序号）
├── generator.py       # 测试名册生成脚本
├── ui/
│   ├── main_window.py # 主窗口（名单列表、性别过滤、抽取、日志区）
│   └── weight_dialog.py # 权重修改对话框
└── normal_student_200.csv  # 200 人测试名册
```

## 🔧 技术栈

- UI：PySide6 (Qt for Python)，跨平台（Windows / Linux / macOS）
- 随机数：`secrets.SystemRandom()`
- 数据：JSON + 自定义日志文件
- 打包：Nuitka 4.1.3（仅 Windows 生成 `.exe`，运行需要 Windows 10 1809 或更高版本；Linux / macOS 直接源码运行）

## 🤝 贡献指南

欢迎通过 Issue 和 Pull Request 参与贡献！

### 报告问题

1. 先在 [Issues](https://github.com/csrpi314/class-random-picker/issues) 中搜索是否已有同类问题；
2. 若无，请新建 Issue，并附上：**系统版本、Python / PySide6 版本、复现步骤、预期与实际结果**（如有报错请附完整截图或日志片段）。

### 提交代码

1. Fork 本仓库并克隆到本地；
2. 从 `main` 分支创建特性分支：

```bash
git checkout -b feat/your-feature
```

3. 完成修改后确保代码可正常运行：`python main.py` 能启动、导入名册/抽取/改权重等核心功能不受影响；
4. 提交 Pull Request，说明改动内容与动机，并关联相关 Issue（如 `Closes #12`）。

### 代码约定

- 模块顶部保留 UTF-8 编码声明与中文 docstring，说明模块职责；
- 可调参数统一收入 `config.py`，不要在业务代码中散落魔法数字；
- 涉及数据写入时保持“原子写入 + 自动备份”的既有策略；
- 界面文案与注释使用简体中文，保持与现有风格一致。

## 🐛 问题反馈

若有 bug 或建议，请在 [Issues](https://github.com/csrpi314/class-random-picker/issues) 中提出。
