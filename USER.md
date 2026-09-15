# 使用说明

> 文档责任：面向产品用户，说明安装、使用、输出观察和故障恢复。维护义务：说明运行前提，示例不依赖作者的设备或私有工具，明确完成条件与限制。不承载：架构、开发测试、评测日志和个人运维流程。

## 一键安装

```bash
curl -fsSL https://raw.githubusercontent.com/a-green-hand-jack/image-to-editable-ppt-skill/main/install.sh | bash
```

脚本安装 `editppt`，并注册 `image-to-editable-ppt` 到当前用户的 Codex skill 目录。安装后重启 Codex 或刷新 skill discovery。脚本优先使用 `uv tool`，其次使用 `pipx`。

## 在 Codex 中使用

把 PNG 提供给 Codex，然后请求：

> 使用 image-to-editable-ppt，把这张图转换成对象级可编辑的 PPTX，保留文字、面板、箭头、图标和版式，并检查真实 PPTX 渲染。

模型会读取图片、生成对象清单、调用 `editppt`、验证结构并完成 PPTX。复杂插画可以保留为独立可选图片，但不能声称其内部笔画仍是矢量可编辑的。

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

最终结果通常位于 `<workdir>/run/final/origin_edited.pptx`。只有同时具备最终 PPTX、结构验证和真实渲染记录，才算完成。

## 本地 CLI

```bash
editppt doctor
editppt prepare input.png --job-dir ./run
editppt run status ./run
```

`editppt` 是确定性构建工具，不会自己理解图片；后续重建由 Codex skill 驱动。OCR 不可用时可以使用离线几何提示，但模型仍必须直接阅读原图。

## 故障恢复

- 运行中断：保留 run 目录，使用 `codex exec resume` 继续同一会话。
- 缺少渲染器：保留 PPTX，并明确标记真实渲染未验证。
- LibreOffice 在沙箱中无法启动：让 headless 运行时审批单次渲染命令，不要关闭全部安全保护。
- skill 未出现：重启 Codex，确认 `~/.agents/skills/image-to-editable-ppt/SKILL.md` 存在。

输入图片和转换结果的版权归其各自权利人；本项目代码按 MIT 许可发布。
