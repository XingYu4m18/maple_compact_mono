# 给后续 AI 的项目交接说明

交接日期：2026-11-10。本文记录项目目标、已完成的工作和维护方法。未来接手时，先核对当前文件、Git 状态及 GitHub 发布情况；日期、路径、工具版本和本机配置均可能变化。

## 项目目的与用户决定

本项目名为 **Maple Compact Mono**，仓库为：

- 本项目：<https://github.com/XingYu4m18/maple_compact_mono>
- 上游 Maple Mono：<https://github.com/subframe7536/maple-font>
- 原开发目录：`/home/xingyu/Projects/maple_compact_mono`

用户喜欢 Maple Mono 的字形、圆角和连字，但认为 CN 版本的中文两侧留白太多。用户最终确认的效果是：**英文变窄，中文保持原大小，中英文仍然按 2∶1 对齐**。不要把中文也横向缩小，不要靠字号或编辑器字符间距模拟这个效果。

这个仓库可能长期不再维护。优先保证现有成品能下载、脚本能独立运行、文档能支持后来者构建新版。没有更新请求时，不需要定期升级依赖、追赶上游、自动发布或重构。长期不活跃也不表示用户要求将仓库归档。

用户已经决定：

- 覆盖上游所有发布包及其中全部字重、斜体；可变字体继续保持可变。
- 包名、文件名、字体内部家族名等沿用上游命名，只在 `Maple` 后增加 `Compact`。
- README 面向下载和使用字体的人：突出开发动机、效果截图、下载安装、利用脚本处理未来新版。
- README 不放 VS Code 设置或 Commitizen 使用说明，不加入“非官方、不代表作者认可”等防御性措辞。保留必要的来源、版权、许可证和具体排版限制。
- 提交使用 Commitizen 对应的 Conventional Commits 格式，例如 `feat(build): ...`、`fix(fonts): ...`、`docs: ...`；不要求通过某个交互工具提交。

## 已发布的基线

2026-11-10 已完成并公开发布 [v7.9](https://github.com/XingYu4m18/maple_compact_mono/releases/tag/v7.9)，基于上游 v7.9：

- 44 个 ZIP，44 个独立 SHA-256 校验文件，共 88 个 Release 附件。
- 40 个静态包，每包 8 个字重及对应斜体，共 16 个字体；4 个可变包，每包正体、斜体各一个。合计 648 个字体文件，包含不同格式和预设的重复造型。
- 每个字体均经过构建内置验证，所有 GitHub Actions 任务成功。发布后抽查了静态与可变 ZIP 的完整性、校验值、字体名称和报告，以及 README 的 latest 下载路径。
- 基线代码提交：`2908308143f186fef3155c71a3bd769a58d340d2`。后续文档提交不需要移动既有发布标签。
- 推荐中文编程包：`MapleCompactMono-NF-CN-unhinted.zip`。

这些数量是 **v7.9 的事实**。未来上游数量变化时，应按当次清单核对，不能硬编码为必须 44 包或 648 个字体。

## 重要文件

| 文件 | 用途 |
| --- | --- |
| `README.md` | 给使用者看的说明、下载表、截图、安装和构建命令 |
| `tools/build_compact.py` | 解析上游 Release、下载校验、逐包构建、打包和生成发布说明 |
| `tools/compact_font.py` | 字形变换、重命名、hinting 处理、逐字体验证 |
| `upstream.release.json` | 固定的上游 v7.9 资源清单，含压缩包 URL 和 SHA-256 |
| `requirements.txt` | 固定的 Python 依赖 |
| `.github/workflows/release.yml` | 准备草稿、并行构建上传、验证齐全后公开发布 |
| `docs/assets/comparison.png` | 更纱、原版 Maple、Compact 的同字号对比 |
| `docs/assets/comparison-italic.png` | 原版与 Compact 的斜体对比 |
| `OFL.txt`、`THIRD_PARTY_NOTICES.md`、`licenses/` | 字体及组件的许可证、来源和版权 |
| `.cz.toml` | 历史提交规范配置，其中 `0.1.0` 不是字体 Release 版本号 |

`upstream.release.json` 保存的是源压缩包校验值；构建产物中每个字体的校验值位于 `compact-build.json`。不要混淆二者。

## 字体处理规则

实现以 `tools/compact_font.py` 为准。修改之前理解这些约束：

1. em 保持 1000；原字符占宽只接受 0、600、1200。
2. 原占宽 600 的英文、符号、NF 图标等，横向坐标乘 `5/6`，占宽改为 500；零占宽字形也做横向缩放，占宽仍为 0。
3. 原占宽 1200 的全宽字形，所有 x 坐标减 100，占宽改为 1000；轮廓本身不缩放。此规则按占宽判断，不仅按 Unicode 汉字区判断。
4. y 坐标、em 和原有纵向度量不变。
5. `Maple Mono NF CN` → `Maple Compact Mono NF CN`；`MapleMonoNormalNL-Bold.ttf` → `MapleCompactMonoNormalNL-Bold.ttf`。同时处理内部名称和 CFF 名称，保留版权与许可证名称记录。
6. 保留字符映射、上游 glyph 顺序及 GSUB 连字/字符变体规则。
7. 静态 TrueType 展平复合字形后处理；静态 CFF 重建轮廓；WOFF2 保持该格式。
8. 可变 TrueType 保留字形拓扑，处理基准坐标、复合字形偏移、gvar 和 HVAR；保留 `wght` 轴与实例。不可通过导出静态字体来冒充可变包。
9. 原 hinting 不适用于新字宽，须移除。hinted/AutoHint 静态 TrueType 包使用 `ttfautohint` 重新生成指令；unhinted 包不带旧指令。

`preflight()` 会拒绝未适配的字体结构，例如当前未支持的定位、颜色、变体表以及新字宽。遇到这类错误，应检查上游变化并实现适配，不能删掉检查让构建假装成功。当前可变字体适配仅限无 CJK 的单 `wght` 轴 TrueType；CFF 仅适配上游目前提供的静态非 CID 结构。

已知取舍：英文及图标横向比例改变；中文保持原大小并缩小占位后，部分斜体笔画会伸出字符格，某些应用可能紧贴或裁切。不要悄悄缩小中文来掩盖它；如果用户要改变这项取舍，需要明确讨论。

## 本地构建

需要 Python 3.10+；原发布工作流使用 Python 3.12、Ubuntu 24.04。依赖在 `requirements.txt` 中，目前为 `fonttools[woff]==4.65.0`、`ttfautohint-py==0.6.1`。优先在隔离环境运行，不向系统 Python 强行安装依赖。

以下命令从仓库根目录执行。安装了 uv 时：

```bash
# 仅列出固定基线的包，不下载字体
uv run --with-requirements requirements.txt python tools/build_compact.py --upstream-version 7.9 --list

# 仅生成清单、矩阵、发布说明，不构建字体
uv run --with-requirements requirements.txt python tools/build_compact.py --upstream-version 7.9 --catalog-only

# 构建一个完整包
uv run --with-requirements requirements.txt python tools/build_compact.py --upstream-version 7.9 --asset MapleMono-NF-CN-unhinted.zip

# 查询并构建未来最新稳定版的全部包
uv run --with-requirements requirements.txt python tools/build_compact.py --upstream-version latest --all
```

没有 uv 时可使用虚拟环境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tools/build_compact.py --upstream-version 7.9 --list
```

重要行为：

- 不传版本时默认 **7.9**，不会自动追踪最新版；要处理新版必须显式传版本或 `latest`。
- 不传 `--all` 或 `--asset` 时，只构建 `MapleMono-NF-CN-unhinted.zip`。
- `--asset` 接受上游名或 Compact 包名；传入 Compact 名称也会转换为上游下载名。
- 默认输出 `dist/v版本号/`，缓存 `.cache/release/`；支持 `--output-dir` 和 `--cache-dir`。
- `--styles Regular Italic` 等过滤器仅供静态字体冒烟检查，会生成不完整的同名包。请放入独立测试目录，**不能将这种产物当作完整 Release 附件上传**。可变包不要传该过滤器。
- 指定 v7.9 使用固定清单；指定其他稳定版或 `latest` 会调用上游 GitHub API。可用 `GH_TOKEN` 提升 API 访问额度，不能把令牌写入文件或日志。
- 下载必须匹配清单 SHA-256，并要求来源是官方对应 Release URL。未知 ZIP 命名、缺失摘要或格式变化会明确失败。
- 本地 `--all` 按包顺序构建，GitHub Actions 按包并行。完整中文字体处理较耗时，不能仅因几分钟无新输出就认定挂起。

每个 ZIP 包含字体、`README.txt`、许可证和 `compact-build.json`；同目录生成 `.sha256` 和 `reports/`。ZIP 内时间戳固定，不是实际构建日期。构建脚本不自动安装字体、不修改编辑器或系统字体设置。

## 验证和发布

调整字体处理逻辑后，至少覆盖本次受影响的格式/分支，再做正式完整构建。验证不能只确认文件能打开或截图看起来正常。

内置验证包括：cmap、GSUB、原 glyph 顺序、名称、版权与许可证、em、纵向度量、hinting 状态，以及逐字形轮廓和占宽。可变字体会检查 100、250、400、650、800 五个字重位置，允许实现中明确列出的舍入误差。hinted 包会检查重新生成的指令，但这不替代真实应用的小字号显示检查。

v7.9 上游有四个预设：`MapleMono`、`MapleMonoNL`、`MapleMonoNormal`、`MapleMonoNormalNL`；各 11 类包：Variable、TTF、TTF-AutoHint、OTF、Woff2、NF/CN/NF-CN 各自 hinted 与 unhinted。不要只构建旧对话最初提过的四个样式或四种组合。

现有发布流程：

1. 先提交代码并推送到目标仓库。
2. 在 GitHub Actions 的 **Build and publish fonts → Run workflow** 中指定上游版本或 `latest`；也可推送对应 `v版本号` 标签触发。
3. `prepare` 解析清单并创建或更新草稿 Release；`build` 最多并行 16 个包，每个包构建全部字体、验证并上传 ZIP/校验文件。
4. 全部构建成功后，`publish` 比较预期与实际附件名集合并检查大小，再公开 Release、设为 latest。
5. 发布后实际检查 Release 是否公开、附件是否完整，抽查下载与 SHA-256、ZIP 中字体数量/名称/许可证，检查 README 下载链接。

当前工作流使用仓库 `GITHUB_TOKEN`，需要 Actions 可用及 `contents: write`。原机器只有 SSH 推送认证，没有配置本地 GitHub API 写入授权；当时通过工作流完成发布。未来先检查当前授权，不要假设本地一定装了 gh 或已有令牌。

工作流允许继续补齐已有草稿，拒绝覆盖已经公开的 Release。不要因重试失败就删除公开版本或强制移动已发布标签。同一上游版本若要修复并再发布，应先设计版本策略；现有解析器只接受对应上游稳定版本格式，不能随意加 `-compact.1` 后缀而不调整逻辑。

未来更新上游时，还应检查许可证和组件来源是否变化，按需要更新固定清单、README 中基线版本/下载表、第三方说明和截图。现有 `THIRD_PARTY_NOTICES.md` 与 `licenses/` 是 v7.9 基线，不能默认永远适用于新版。脚本适配新版本不代表第三方许可已经自动更新。

## 缓存、产物和清理

- `.cache/` 包含下载的原始字体压缩包和早期测试解压文件，可整个删除；下次构建按需重新下载。它不是脚本依赖，也不是唯一源文件。
- `dist/` 是本地生成的字体包、验证报告和测试产物，可在确认没有待保留的未发布成果后清理。GitHub Release 和已安装字体不依赖它。
- `.venv/`、`.cache/`、`dist/`、`__pycache__/` 被 Git 忽略，不要提交数 GB 缓存或字体二进制。
- 正式成品放 Release，源码仓库保留工具、清单、文档、截图和许可证。
- 不能因为名字相似，就删除 `tools/`、`licenses/`、`docs/assets/`、`upstream.release.json` 或 `.git/`。

## 原开发机器的安装状态（仅供诊断）

2026-11-10 用户确认使用正常后，已将 Ubuntu 和 VS Code 字体统一为 **Maple Compact Mono NF CN**，安装的是 v7.9 NF-CN unhinted 全部 16 个字体：

- 字体目录：`~/.local/share/fonts/MapleCompactMonoNFCN/`。
- VS Code 默认设置：`~/.config/Code/User/settings.json`。
- 当时实际使用的 Ubuntu 配置档：`~/.config/Code/User/profiles/-10da70d4/settings.json`。修改默认设置并不保证当前配置档跟着改变；未来先查当前配置档及工作区覆盖。
- 上述两个配置中的 11 个字体设置均为 `'Maple Compact Mono NF CN', monospace`；保留连字及原有其他设置。
- GNOME 的 `font-name`、`document-font-name` 为 `Maple Compact Mono NF CN 11`；`monospace-font-name` 为 `Maple Compact Mono NF CN 13`；标题为 `Maple Compact Mono NF CN Bold 11`。
- 设置切换前的备份：`~/.local/state/font_switch/20261110_161536/`，只备份配置，没有保留旧字体。
- 已按用户要求删除安装目录 `SarasaMonoSC`、`SarasaUiSC`、`MapleMonoNFCN`、旧名称的 `MapleCompactNFCN`，共 34 个旧字体文件。新版完整家族名含 **Mono**，不要重新使用旧家族名 `Maple Compact NF CN`。

以上不是跨机器安装要求，也不是要求后续 AI 自动更改本机配置。维护仓库与安装字体是两件独立的事；只有用户提出安装/切换需求时才处理系统设置。遇到未刷新显示，先完整重开相关应用，必要时注销登录，不要为刷新字体随意结束进程或重置应用数据。需要 sudo 时先征得用户同意。

## 接手时的最短路径

先运行 `git status --short`，阅读本文与 README，再按需求查看两个工具脚本和发布工作流。若只是重建未来版本，先 `--list`/`--catalog-only` 检查上游，再构建一个完整目标包；修改适配时保持上述字形规则和验证强度，最后才做全量构建和发布。文档变更不用重新构建全部字体，也不用重新发布 v7.9。
