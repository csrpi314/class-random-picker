# class-random-picker
# 班级随机抽取系统

🎲 班级随机抽取系统 | PySide6 + 安全随机 | 支持加权抽取、CSV 导入、日志记录


一个基于 **PySide6** 开发的安全、可加权的班级随机抽取软件，适用于课堂点名、互动提问等场景。支持导入 CSV 班级名册、自定义权重、一键重置权重，所有操作自动记录日志。

![主界面截图](https://image.zsh26.cc.cd/file/AgACAgUAAyEGAAMBA3LocAADD2psto1_wjHCuZ9SEPwCWcRnW8NRAALlE2sbf_1oV1qqkfstHNC0AQADAgADeQADPQQ.png)

## ✨ 功能特性

- **📋 CSV 名册导入**  
  支持带“姓名”和“权重”列的 CSV 文件，权重可省略（默认为 1）。

- **🎲 安全加权随机**  
  使用 `secrets.SystemRandom()` 实现密码学安全随机，支持放回抽取。  
  权重可在应用内随时调整，抽取概率与权重成正比。

- **⚖️ 一键等权重置**  
  随时将所有学生权重恢复为 1，方便公平随机抽取。

- **📝 完整操作日志**  
  每次运行生成独立日志文件（`yyyyMMdd.log`，同一天内自动递增序号），时间戳精确到毫秒，记录权重修改、导入、抽取结果等。

- **💾 数据持久化**  
  学生名单与权重保存为 JSON，日志存放在 `%APPDATA%\ClassRandomSampling\`，安全可靠。

## 🖼️ 界面预览

| 主界面 | 权重修改 | 抽取结果 |
|--------|----------|----------|
| ![主界面](https://image.zsh26.cc.cd/file/AgACAgUAAyEGAAMBA3LocAADD2psto1_wjHCuZ9SEPwCWcRnW8NRAALlE2sbf_1oV1qqkfstHNC0AQADAgADeQADPQQ.png) | ![权重](https://image.zsh26.cc.cd/file/AgACAgUAAyEGAAMBA3LocAADDmpstozzSQufm_wfx5EWYqna4lDRAALkE2sbf_1oV2F1gWgvOnTSAQADAgADeAADPQQ.png) | ![结果](https://image.zsh26.cc.cd/file/AgACAgUAAyEGAAMBA3LocAADEGpsto376Scy1D4Z8xWohk8Jaw-MAALmE2sbf_1oV0zopL8a1q4EAQADAgADeQADPQQ.png) |

## 🚀 快速开始

### 运行环境
- Python 3.13.7（开发用，打包后无需依赖）
- PySide6 6.11.1

### 从源码运行
1. 克隆仓库：
```bash
git clone https://github.com/your-name/ClassRandomSampling.git
cd ClassRandomSampling
```
2. 安装依赖：

```bash
pip install pyside6==6.11.1
```
3. 运行软件：

```bash
python random_picker.py
```
📖 使用说明
首次使用
点击菜单 文件 → 导入 CSV 名册，选择符合格式的 CSV 文件（示例见下），确认后名单自动保存。

调整权重
通过 操作 → 修改权重 打开对话框，为不同学生设置不同权重（如课代表可设为 2，增加被抽中概率）。
也可 操作 → 一键重置所有权重为 1 恢复等权。

抽取学生
点击右侧 🎲 随机抽取 按钮，结果将显示在界面中央，颜色变红并记录日志。

查看记录
右侧日志区显示本次运行的所有操作，历史日志保存在 %APPDATA%\ClassRandomSampling\ 下的 .log 文件中。

CSV 名册格式示例
```csv
姓名,权重
张三,1
李四,2
王五,1.5
赵六
```
第一行为表头，必须包含“姓名”列（或英文 name）。

“权重”列可选，缺失时自动设为 1。

编码为 UTF-8 或 UTF-8 with BOM。

🔧 技术栈
界面：PySide6 (Qt for Python)

随机数：secrets.SystemRandom()

数据：JSON + 自定义日志文件

打包：Nuitka 4.1.3

🐛 问题反馈
若有 bug 或建议，请在 [Issues](https://github.com/csrpi314/class-random-picker/issues) 中提出。