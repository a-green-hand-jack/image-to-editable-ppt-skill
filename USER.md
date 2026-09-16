# 使用说明

> 文档责任：面向产品用户，说明安装、使用、输出观察和故障恢复。维护义务：说明运行前提，示例不依赖作者的设备或私有工具，明确完成条件与限制。不承载：架构、开发测试、评测日志和个人运维流程。

## 一键安装

```bash
curl -fsSL https://raw.githubusercontent.com/a-green-hand-jack/image-to-editable-ppt-skill/main/install.sh | bash
```

脚本安装 `editppt`，并注册 `image-to-editable-ppt` 到当前用户的 Codex skill 目录。安装后重启 Codex 或刷新 skill discovery。脚本优先使用 `uv tool`，其次使用 `pipx`。项目要求 Python 3.10 或更新版本；安装器会按 `pyproject.toml` 安装 Python 依赖，并提示是否缺少 LibreOffice 与 Poppler。若需要把缺少系统渲染器视为安装失败，可设置 `EDITPPT_REQUIRE_SYSTEM_DEPS=1`。

## 在 Codex 中使用

把 PNG 提供给 Codex，然后请求：

> 使用 image-to-editable-ppt，把这张图转换成对象级可编辑的 PPTX，保留文字、面板、箭头、图标和版式，并检查真实 PPTX 渲染。

模型会读取图片、生成对象清单、调用 `editppt`、验证结构并完成 PPTX。复杂插画可以保留为独立可选图片，但不能声称其内部笔画仍是矢量可编辑的。

最终 PPTX 默认先放原始光栅图，再放对应的可编辑结果，便于翻页比较。单张 PNG 输出两页；多页输入按“原图 1、结果 1、原图 2、结果 2……”排列。原图页仅供参考，编辑请使用其后一页；输入备注保留在对应的结果页。

## 图像后端配置

headless 或跨机器运行时，应显式选择图像后端，避免继承启动机器的隐式 OAuth：

```bash
export EDITPPT_IMAGE_BACKEND=api
export OPENAI_BASE_URL="https://your-openai-compatible-endpoint/v1"
export OPENAI_API_KEY="..."
export IMAGE_TO_EDITABLE_PPT_IMAGE_MODEL="your-image-model"
```

其中 API 地址、模型名和密钥由调用者自己的 provider 配置提供；不要把密钥写入 prompt、仓库或运行日志。只有在明确允许使用当前设备 Codex OAuth Images 时，才设置 `EDITPPT_IMAGE_BACKEND=codex-oauth`。`auto` 适合交互式开发，不是可移植 headless 运行的可靠默认值。

## Headless CLI

```bash
mkdir -p "$PWD/conversion/.agents/skills"
ln -s "${HOME}/.agents/skills/image-to-editable-ppt" \
  "$PWD/conversion/.agents/skills/image-to-editable-ppt"

codex exec -C "$PWD/conversion" --approve-for-me \
  --image "/path/to/input.png" \
  --json -o "$PWD/conversion/result.md" \
  'Use $image-to-editable-ppt to convert the attached PNG into an object-level editable PowerPoint. Put all run artifacts in ./run, inspect a real PPTX render, validate, record, and finalize. Return the final PPTX path and any remaining visual differences.' \
  > "$PWD/conversion/events.jsonl" 2> "$PWD/conversion/stderr.log"
```

`--approve-for-me` 仍遵守 Codex 运行时安全策略；不要把 API key 写进命令或仓库。

最终结果通常位于 `<workdir>/run/final/origin_edited.pptx`。只有同时具备最终 PPTX、结构验证和真实渲染记录，才算完成；存在一个 PPTX 文件或程序 preview 不能替代真实渲染证据。复杂图像后端失败时，运行可能只完成可安全近似的简单 pictogram，其余对象和差异必须在结果中明确记录。

## 导出论文用 PDF

完成 PPTX 后，可以用本地 LibreOffice 将它导出为 PDF：

```bash
editppt export-pdf run/final/origin_edited.pptx --out paper/figure.pdf --json
```

省略 `--out` 时，PDF 写在 PPTX 旁边并使用相同文件名。命令会在独立临时目录中转换，确认输出是有效 PDF 后再写入目标路径；`--renderer` 可用于指定 `soffice` 或 `libreoffice` 的可执行文件。

PDF 会保留 PPTX 中原生文本、线条、形状和表格的矢量表示，适合插入论文。被重建流程保留为独立位图的复杂插画、照片或图标仍然是位图；导出 PDF 不会把它们重新变成矢量路径。公式是否为矢量取决于 PPTX 中使用的公式素材格式。

最终组装的 deck 默认包含“原图对照页 + 可编辑结果页”的成对页面；如果论文只需要一张图，导出对应页面目录中的 `page.pptx`（单个可编辑页），或在最终 PDF 中选用对应的可编辑结果页。

## 本地 CLI

```bash
editppt doctor
editppt prepare input.png --job-dir ./run
editppt run status ./run
# 查看最近 10 条 agent/命令事件
editppt run status ./run --events 10
```

`editppt` 是确定性构建工具，不会自己理解图片；后续重建由 Codex skill 驱动。OCR 不可用时可以使用离线几何提示，但模型仍必须直接阅读原图。

`editppt run status` 会同时显示页面状态、运行状态年龄和最近事件摘要。若页面长期保持 `dispatched`，用 `--events 20` 检查最后一个命令；事件仍在更新表示 agent 仍在工作，事件和文件都长时间不更新才需要恢复或检查进程。

## 故障恢复

- 运行中断：保留 run 目录，使用 `codex exec resume` 继续同一会话。
- 缺少渲染器：保留 PPTX，并明确标记真实渲染未验证。
- LibreOffice 在沙箱中无法启动：让 headless 运行时审批单次渲染命令，不要关闭全部安全保护。
- skill 未出现：重启 Codex，确认 `~/.agents/skills/image-to-editable-ppt/SKILL.md` 存在。

输入图片和转换结果的版权归其各自权利人；本项目代码按 MIT 许可发布。
