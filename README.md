# Poster Studio

学术海报模板和创作流程，整理自 BeatEdit 海报的制作过程。包含三种竖版版式，以及预览、二维码生成、PDF/PNG 导出和打包工具。

## 先看版式

打开 `index.html` 查看模板。初始尺寸为 A0 竖版，可按会议要求调整。

| 模板 | 适合什么内容 | 阅读路径 |
|---|---|---|
| `band-story` | 动机、分析和机制值得展开；BeatEdit 这次的叙事方向 | 问题 → 要求 → 核心表达 → 机制 → 结果 |
| `two-column` | 方法与实验证据分量相近，素材较多 | 左栏建立问题和方法，右栏验证与分析 |
| `figure-first` | 一幅图能解释主要贡献 | 问题 → 大主图 → 机制/分析 → 证据 |

复制模板后替换 TODO 和示例二维码，配色与字号在 CSS 顶部统一调整。

| 顺序叙事 | 双栏 | 主图优先 |
|---|---|---|
| ![Band story scaffold](previews/band-story.png) | ![Two column scaffold](previews/two-column.png) | ![Figure first scaffold](previews/figure-first.png) |

## 一次安装

在项目目录创建 Python 环境并安装依赖：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```

也可以复用已有的海报环境。

## 五个常用动作

以下命令在仓库目录运行：

```bash
# 1. 从模板创建项目
.venv/bin/python tools/poster.py init band-story ../MyPaper_Poster

# 2. 启动预览，修改 MyPaper_Poster/poster.html 后刷新页面
.venv/bin/python tools/poster.py preview --root ../MyPaper_Poster --port 8791
# 打开 http://127.0.0.1:8791/poster.html，修改后刷新。

# 3. 生成二维码
.venv/bin/python tools/poster.py qr 'https://example.com/my-paper' ../MyPaper_Poster/assets/paper.svg

# 4. 检查并导出
.venv/bin/python tools/poster.py check ../MyPaper_Poster/poster.html
.venv/bin/python tools/poster.py export ../MyPaper_Poster/poster.html --out ../MyPaper_Poster/final-01 --dpi 300

# 5. 确认交付内容后打包
.venv/bin/python tools/poster.py package ../MyPaper_Poster --final ../MyPaper_Poster/final-01 --out ../MyPaper_Poster-delivery.zip --privacy-reviewed
```

占位稿检查加 `--draft`；阶段审阅用 72/150 DPI，最终导出用 300 DPI。每次导出使用新目录，保留需要的阶段版本。

## 内容与流程

- [创作流程](docs/01-workflow.md)：从读论文到交付的六个阶段。
- [本次迭代复盘](docs/02-iteration-lessons.md)：哪些有效，哪些尝试被否决，怎样减少重复操作。
- [组件与排版](docs/03-components.md)：标题、徽章、图、结果卡、联系人与二维码。
- [验收与交付](docs/04-preflight.md)：印刷检查与打包清单。
- [可直接复制的任务指令](docs/05-prompts.md)：新建、局部修改、终检。

新项目的 `notes/` 包含需求、数据出处和设计决定记录。最终交付包包含成品、源码和引用的素材。

## 参考

创作经验来自 BeatEdit 海报的实际迭代，导出流程参考 [Posterly](https://github.com/Chenruishuo/posterly)。本仓库的模板与工具独立编写。

## 测试

```bash
.venv/bin/python -m unittest discover -s tests -v
# 可选：实际 Chromium → PDF → QR → PNG → zip 集成检查（需要依赖与 Chromium）
POSTERKIT_BROWSER_TESTS=1 .venv/bin/python -m unittest discover -s tests -v
```

模板缩略图见 `previews/`。
