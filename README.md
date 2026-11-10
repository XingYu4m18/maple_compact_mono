# Maple Compact Mono

基于 [Maple Mono](https://github.com/subframe7536/maple-font) 的非官方字体实验仓库，尝试在保留中文原有字形大小的同时，缩窄英文并减少中文左右留白。

当前提供 **Maple Compact NF CN**：英文占宽 **500**、中文占宽 **1000**，保留中英文 **2∶1** 的宽度关系，以及原版的连字规则和 Nerd Fonts 图标。

本项目不是 Maple Mono 官方版本，也不代表上游作者认可或推荐。当前属于实验性派生字体，建议与原版并存试用。

## 为什么制作

Maple Mono NF CN 7.9 的英文占宽为 600，中文占宽为 1200。较宽的中文占位保证了中英文对齐，但也使中文左右留白比较明显。

本仓库中的变体采用以下方式处理：

| 项目 | 上游原版 | Compact 变体 |
| :--- | ---: | ---: |
| em 单位 | 1000 | 1000 |
| 英文占宽 | 600 | 500 |
| 中文占宽 | 1200 | 1000 |
| 英文字形 | 原宽度 | 横向缩至 5/6，高度保持不变 |
| 中文字形 | 原大小 | 保持大小，仅向左平移 100 单位以居中 |
| 中英文宽度关系 | 2∶1 | 2∶1 |

实现按上游字形的占宽分类：1200 单位的全宽字形保持轮廓大小；600 单位字形以及零占宽的组合字形进行横向缩放。NF 图标也会随之横向收窄；没有新增、删除或重新设计图标。

## 效果对比

下面依次为等距更纱、Maple Mono NF CN 原版和本项目的 Compact 变体，使用相同的名义字号：

![等距更纱、原版 Maple 与 Compact 对比](docs/assets/comparison.png)

斜体对比：上方为原版，下方为 Compact 变体。

![原版和 Compact 的斜体对比](docs/assets/comparison-italic.png)

图片用于观察排版差异；不同操作系统、应用和字号下的实际效果可能不同。对比图中的更纱字体本身不包含在本仓库中。

## 当前字体

字体家族名：**`Maple Compact NF CN`**。目前提供四个静态字重样式：

| 样式 | 文件 |
| :--- | :--- |
| 常规 | [MapleCompactNFCN-Regular.ttf](fonts/maple_compact_nf_cn/MapleCompactNFCN-Regular.ttf) |
| 粗体 | [MapleCompactNFCN-Bold.ttf](fonts/maple_compact_nf_cn/MapleCompactNFCN-Bold.ttf) |
| 斜体 | [MapleCompactNFCN-Italic.ttf](fonts/maple_compact_nf_cn/MapleCompactNFCN-Italic.ttf) |
| 粗斜体 | [MapleCompactNFCN-BoldItalic.ttf](fonts/maple_compact_nf_cn/MapleCompactNFCN-BoldItalic.ttf) |

在 GitHub 打开字体文件后，可以使用 **Download raw file** 下载；也可通过 **Code → Download ZIP** 下载整个仓库。尚未提供可变字体及其他字重。

## 安装

### Ubuntu / Linux

在仓库根目录执行，无需 `sudo`：

```bash
mkdir -p "$HOME/.local/share/fonts/maple_compact_mono"
cp fonts/maple_compact_nf_cn/*.ttf "$HOME/.local/share/fonts/maple_compact_mono/"
cp OFL.txt "$HOME/.local/share/fonts/maple_compact_mono/"
cp -R licenses "$HOME/.local/share/fonts/maple_compact_mono/"
fc-cache -f "$HOME/.local/share/fonts/maple_compact_mono"
fc-match 'Maple Compact NF CN'
```

查询结果应指向 `MapleCompactNFCN-Regular.ttf`。字体使用独立家族名称，不会覆盖 `Maple Mono NF CN` 或 `Sarasa Mono SC`。

### Windows

下载四个 `.ttf` 文件，选中后右键选择“安装”（Windows 11 可能需要先选择“显示更多选项”），然后完整退出并重新打开需要使用字体的应用。

### VS Code

在**当前使用的配置档**中，执行“首选项：打开用户设置(JSON)”，按需加入或修改：

```json
{
  "editor.fontFamily": "'Maple Compact NF CN', monospace",
  "editor.fontLigatures": true,
  "terminal.integrated.fontFamily": "'Maple Compact NF CN', monospace",
  "markdown.preview.fontFamily": "'Maple Compact NF CN', monospace"
}
```

首次安装后，如果应用继续显示旧字体，请保存文件后**完整退出所有 VS Code 窗口并重新启动**。只执行 Reload Window 不一定能刷新进程中的字体列表。

`markdown.preview.fontFamily` 针对 VS Code 内置预览；Markdown Preview Enhanced 使用自己的样式配置，需要单独设置。Emoji 的 PDF 显示效果也不由 NF 图标支持保证。

## 已知限制

- **中文斜体越界**：保持斜体中文字形原大小并移除横向留白后，一部分笔画会伸出 1000 单位的字符格。部分应用可能出现紧贴、重叠或裁切，不能保证所有终端、编辑器和 PDF 查看器都一致。
- **小字号显示变化**：字形横向几何改变后，原有 TrueType hinting 不再适用，因此本变体移除了相关指令和全局 hinting 表。小字号清晰度可能与原版不同。
- **英文外观改变**：英文、符号、连字组成部分和 NF 图标横向缩窄，不再具有原版的宽高比例。
- **检查不是跨平台兼容性认证**：验证覆盖字形轮廓、字符映射、宽度、纵向度量和 GSUB 规则，不代表每个罕见字符、混排组合和应用都经过人工检查。
- **仅四个样式**：不包含 Thin、Light、Medium、SemiBold 等字重，也没有可变字体。

普通常规与粗体在 U+4E00～U+9FFF 范围的检查中未发现轮廓超出字符占位；斜体结果详见 [验证报告](reports/validation.json)。字体不会改变源文件中的字符或编译结果。

## 重新构建

需要 Python 3.10 或更新版本。脚本依赖锁定在 [requirements.txt](requirements.txt)，上游输入锁定在 [upstream.lock.json](upstream.lock.json)。

在仓库根目录执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tools/build_compact.py
```

Windows 可将 `.venv/bin/python` 换为 `.venv\Scripts\python.exe`。

默认下载上游 **7.9** 的 `MapleMono-NF-CN.zip`，验证压缩包与四个源字体的 SHA-256，再生成 `fonts/maple_compact_nf_cn/` 中的字体和 `reports/validation.json`。缓存保存在 `.cache/`，不提交到 Git。下载压缩包约 152 MiB，需要额外磁盘空间用于解压和构建。

也可以指定已下载的原版字体目录，脚本仍会核对源字体哈希：

```bash
.venv/bin/python tools/build_compact.py --source-dir /path/to/original_ttf
```

只生成常规样式，且不覆盖仓库自带字体：

```bash
.venv/bin/python tools/build_compact.py \
  --styles Regular \
  --output-dir dist/test_fonts \
  --report dist/test_validation.json
```

这是对**上游已发布静态 TTF** 的几何变换，不是重新编译 Maple Mono 的原始字体工程。脚本固定了新构建文件的修改时间，但仓库中最初手工生成的历史二进制与重建结果不承诺逐字节相同；几何变换和保留规则由验证程序检查。

## 验证

校验仓库中四个字体文件的哈希：

```bash
sha256sum -c SHA256SUMS
```

对照锁定的上游字体，验证现有输出而不重建：

```bash
.venv/bin/python tools/build_compact.py --verify-only
```

验证项目包括：

- 字形数量、顺序及 Unicode 字符映射保持一致。
- GSUB 二进制保持一致，保留上游连字与替换规则。
- 每个字形的占宽和轮廓坐标符合指定变换。
- 中文全宽轮廓仅平移，不缩放；纵向度量保持一致。
- 统计常用汉字范围的越界数量、最大越界量及示例。

生成报告后可查看 [reports/validation.json](reports/validation.json)。如果重新构建并准备发布，需要同步更新 `SHA256SUMS`。

## 仓库结构

```text
maple_compact_mono/
├── README.md
├── OFL.txt
├── THIRD_PARTY_NOTICES.md
├── SHA256SUMS
├── upstream.lock.json
├── requirements.txt
├── .cz.toml
├── fonts/
│   └── maple_compact_nf_cn/
├── tools/
│   └── build_compact.py
├── reports/
│   └── validation.json
├── docs/assets/
└── licenses/
```

后续变体可放在 `fonts/` 下各自的目录中，使用独立字体家族名，并补充构建输入、验证结果、对比图和许可证。

## 提交规范

使用 Commitizen 的 `cz_conventional_commits` 规范，配置见 [.cz.toml](.cz.toml)。提交格式为：

```text
type(scope): description
```

例如：

```text
feat(fonts): add compact Maple Mono NF CN variant
fix(build): preserve full-width outline geometry
docs(readme): explain installation and italic limitations
```

安装 Commitizen 后可执行 `cz commit` 交互创建提交，或使用 `cz check --rev-range HEAD~1..HEAD` 检查后续提交。第一次提交没有父提交，检查时可用 `git log -1 --pretty=%B | cz check`。

## 许可证与来源

字体按 **SIL Open Font License 1.1** 分发，保留上游版权与许可证，完整文本见 [OFL.txt](OFL.txt)。允许按协议修改和再分发；不得将字体本身单独出售，不得暗示上游作者背书，也需遵守保留字体名称的限制。

嵌入图标及上游组件的版权、来源和附加许可证见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 与 [licenses/](licenses/)。本仓库未额外打包上游原版字体或更纱字体。

- [Maple Mono 7.9](https://github.com/subframe7536/maple-font/releases/tag/v7.9)
- [Maple Mono 官方中文说明](https://github.com/subframe7536/maple-font/blob/v7/README_CN.md)
- [Resource Han Rounded / 资源圆体](https://github.com/CyanoHao/Resource-Han-Rounded)
- [Nerd Fonts 3.4.0](https://github.com/ryanoasis/nerd-fonts/tree/v3.4.0)
- [Sarasa Gothic / 更纱黑体（仅对比图）](https://github.com/be5invis/Sarasa-Gothic)
