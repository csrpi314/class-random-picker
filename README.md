# class-random-picker
# 班级随机抽取系统

🎲 班级随机抽取系统 | PySide6 + 安全随机 | 支持加权抽取、CSV 导入、日志记录

一个基于 **PySide6** 开发的安全、可加权的班级随机抽取软件，支持按性别过滤抽取，适用于课堂点名、互动提问等场景。导入 CSV 班级名册后，可自定义每位学生的权重，抽取过程采用系统安全随机数，公平且可追溯。所有操作均记录日志，并可打包为独立 exe 分发。

![主界面截图](https://image.zsh26.cc.cd/file/AgACAgUAAyEGAAMBA3LocAADEmpxOqQm199UpRNVbi308zCn11qVAAKdEGsbdkaQVwy_bGLDLl4IAQADAgADeQADPQQ.png)
\* 截图所示数据仅供测试，由 Python 生成

## ✨ 功能特性

- **📋 CSV 名册导入（必含学号、性别列）**  
  支持 `学号,姓名,性别,权重` 四列的 CSV 文件（权重可选，默认为 1）。自动检测 UTF-8/GBK 编码。

- **🎲 安全加权随机**  
  使用 `secrets.SystemRandom()` 实现密码学安全随机，支持放回抽取。权重步长 0.50，0 表示不参与抽取。可随时在应用内调整。

- **👫 按性别过滤抽取**  
  主界面提供“全部抽取”、“只抽男生”、“只抽女生”三个单选按钮，切换后左侧列表实时显示对应性别的学生，抽取范围即时生效。

- **⚖️ 一键等权重置**  
  随时将所有学生权重恢复为 1，方便公平随机抽取。

- **📝 完整操作日志**  
  每次运行生成独立日志文件（`yyyyMMdd.log`，同一天内自动递增序号），时间戳精确到毫秒，记录权重修改、导入、抽取结果等。日志无数量上限。

- **💾 数据持久化**  
  学生名单与权重保存为 JSON，日志存放在自定义或默认目录（`%APPDATA%\ClassRandomSampling\`），安全可靠。支持程序内切换数据目录。

- **🖥️ 独立可执行文件**  
  可使用 Nuitka 打包为单文件 `.exe`，无需安装 Python 环境，分发即用。

## 🖼️ 界面预览

| 主界面 | 权重修改 | 抽取结果 |
|--------|----------|----------|
| ![主界面](https://image.zsh26.cc.cd/file/AgACAgUAAyEGAAMBA3LocAADEmpxOqQm199UpRNVbi308zCn11qVAAKdEGsbdkaQVwy_bGLDLl4IAQADAgADeQADPQQ.png) | ![权重](https://image.zsh26.cc.cd/file/AgACAgUAAyEGAAMBA3LocAADEWpxOqPBz2GWuOw-lzVmETBDTNxzAAKcEGsbdkaQV7y69GANxmX0AQADAgADeAADPQQ.png) | ![结果](https://image.zsh26.cc.cd/file/AgACAgUAAyEGAAMBA3LocAADE2pxOqRP-EcZwGfdKrcXuvqUaiL_AAKeEGsbdkaQV59ERTHEeBnyAQADAgADeQADPQQ.png) |

## 🚀 快速开始

### 运行环境
- Python 3.13.7（开发用，打包后无需依赖）
- PySide6 6.11.1

### 从源码运行
1. 克隆仓库：
```bash
git clone https://github.com/csrpi314/class-random-picker.git
cd class-random-picker
```
2. 安装依赖：

```bash
pip install pyside6==6.11.1
```
3. 运行软件：

```bash
python picker.py
```
## 📖 使用说明

1. 首次使用  
点击`菜单 文件 → 导入 CSV 名册`，选择符合格式的 CSV 文件（示例见下），确认后名单自动保存。

2. 调整权重  
通过 `操作 → 修改权重` 打开对话框，为不同学生设置不同权重（如课代表可设为 2，增加被抽中概率）。
也可 `操作 → 重置权重` 恢复等权。

3. 抽取学生  
点击右侧 `🎲 随机抽取` 按钮，结果将显示在界面中央，颜色变蓝并记录日志。

4. 查看记录  
右侧日志区显示本次运行的所有操作，历史日志默认保存在 %APPDATA%\ClassRandomSampling\ 下的 .log 文件中（可更改）。

## CSV 名册格式示例

```csv
姓名,性别,权重
张三,男,1
李四,女,2
王五,f,1.5
赵六,m
```
- 第一行为表头，必须包含“学号”、“姓名”、“性别” 列（支持中文或英文 id/name/sex）。

- “权重”列可选，缺失时自动设为 1。

- 性别支持：男/女、m/f（不区分大小写）。

- 编码推荐 UTF-8，也兼容 GBK。

## 🔧 技术栈

- UI：PySide6 (Qt for Python)

- 随机数：secrets.SystemRandom()

- 数据：JSON + 自定义日志文件

- 打包：Nuitka 4.1.3（运行需要 Windows 10 1809 或更高版本）

## 🐛 问题反馈

若有 bug 或建议，请在 [Issues](https://github.com/csrpi314/class-random-picker/issues) 中提出。