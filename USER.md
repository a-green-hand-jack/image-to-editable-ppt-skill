# 安装与使用

## 安装

需要 Python 3.10+ 和 uv（或 pipx）。从本项目 checkout 的根目录安装：

```bash
uv tool install --force .
# 或：pipx install --force .
editppt --help
editppt doctor
```

开发时可用 `uv tool install --force --editable .`。也可直接安装发行的 wheel。`doctor` 检查依赖和配置是否存在，不会证明远端 API 可用或重建质量达标。

将 `src/editppt/skills/image-to-editable-ppt/` 注册为 agent 的 skill 目录。推荐在任务目录挂载，只创建指向产品源码的链接，不复制第二份实现：

```bash
repo_dir="$PWD"
task_dir="$PWD/outputs/example"
mkdir -p "$task_dir/.agents/skills"
# 仅在目标不存在时执行；不覆盖已有 skill。
ln -s "$repo_dir/src/editppt/skills/image-to-editable-ppt" \
  "$task_dir/.agents/skills/image-to-editable-ppt"
```

受统一 profile 管理的机器按其 skill 发布流程注册，不覆盖已有安装。wheel 安装的 skill 也包含完整资源；在同一 Python 环境执行下式可以找到它：

```bash
python -c 'from importlib.resources import files; print(files("editppt") / "skills" / "image-to-editable-ppt")'
```

重启或刷新 agent 的 skill 发现，再请求：

> 使用 image-to-editable-ppt，把这张图重建成可编辑 PPTX，保留所有标签、箭头、图标和版式，并检查真实 PPTX 渲染。

## Headless Codex：PNG → PPTX

目标入口是加载此 skill 的 `codex exec`：模型自己看图、编写 manifest、调用 CLI、检查真实渲染并修正，调用者不需要手工标注对象或执行逐步转换。上面的任务目录挂载完成后，从同一 shell 执行：

```bash
codex exec -C "$task_dir" --approve-for-me \
  --image "$repo_dir/benchmark/PaperClaw_fig_2.png" \
  --json -o "$task_dir/result.md" \
  "Use \$image-to-editable-ppt to reconstruct the attached PNG as editable PowerPoint. Input: $repo_dir/benchmark/PaperClaw_fig_2.png. Put the run in ./conversion. Complete reconstruction, real PPTX render inspection, validation, record and finalize. Report the final PPTX path and remaining differences. Do not modify product source or global configuration." \
  > "$task_dir/events.jsonl" 2> "$task_dir/stderr.log"
```

使用受管 provider 的机器将 `codex exec` 换为现有的 `ai codex exec`，沿用已选账户；不要复制凭据或新增模型调度器。运行前安装 `editppt`，确保视觉模型可用；真实渲染还需要 LibreOffice (`soffice`) 和 Poppler (`pdftoppm`)，或可用的 PowerPoint 渲染通道。纯文字/流程图不需要图像生成后端，复杂插画分离仍需配置相应工具。

示例使用 Codex CLI 0.154 的 `--approve-for-me`：工作区内写入仍受沙箱限制，必要的外部命令交给运行时自动审批。它不是无条件放行。若渲染器已能在沙箱内工作，也可使用 `--sandbox workspace-write`；但无审批的非交互运行可能无法完成 Linux LibreOffice 渲染。不要用关闭全部保护来掩盖失败，受管环境的权限策略始终优先。

默认最终文件为 `<task_dir>/conversion/final/origin_edited.pptx`。进程退出码、`result.md` 和最终验证文件一起判断是否完成；退出成功或存在 PPTX 不代表视觉验收通过。中间稿及失败记录保留在任务目录。非交互进程遇到权限或工具缺失会报告阻塞，不能自动绕过。

Codex 的 `.agents/skills` 发现与符号链接支持见 [官方 skill 文档](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)，非交互入口见 [官方 codex exec 文档](https://developers.openai.com/codex/noninteractive/)。

## 运行和观察

单页由当前 agent 按提示重建；多页使用运行环境支持且允许的逐页 worker。`editppt` 提供确定性工具，不会自行启动视觉 agent。

```bash
editppt prepare input.png --job-dir /absolute/path/to/run
editppt run next /absolute/path/to/run
editppt run status /absolute/path/to/run
```

实际重建还包含生成逐页提示、dispatch、编写 manifest、构建和检查，遵循 [产品 skill](src/editppt/skills/image-to-editable-ppt/SKILL.md)。`next` 返回下一步，不能把准备成功视为转换完成。

文字提示默认遵循已有配置：有 PaddleOCR token 时可使用 OCR，否则使用离线几何测量。离线模式也能执行，agent 必须看原图读文字并测量字号；无需为了开始重建先开通 OCR。`--no-text-hints` 可跳过 prepare 的提示生成。

复杂前景分离需要可调用的图像编辑工具或用户配置的后端。模型和凭据属于本机配置，不写入产品源码、benchmark、提示或结果。局部纯原生页面不必调用图像生成。保密或只允许本地处理的输入应在请求中明确说明，agent 必须遵守；所需后端不可用时报告具体对象的阻塞。

## 检查与交付

运行目录保留 `page_jobs.json`、`deck_manifest.json` 及 `pages/page_NNN/`。每页包含原图、对象 manifest、素材来源、PPTX、程序预览和结构检查结果。真实渲染按 [render-validation.md](src/editppt/skills/image-to-editable-ppt/references/render-validation.md) 使用 LibreOffice 或 PowerPoint 检查。

结构验证通过后由 agent 执行 `run record`，所有页记录完成后执行 `run finalize`。交付需说明最终 PPTX 路径、真实渲染检查结果、哪些内容可编辑、哪些仍是独立图片/公式素材，以及未解决的差异。

### 已验证案例

`PaperClaw_fig_2` 已完成一次真实 headless Codex 转换：10 个可编辑文本框、25 个原生形状、无整页位图；LibreOffice 24.2.7.2 生成 PDF/PNG 并完成源图对照。字体替换、抗锯齿和虚线节奏差异已记录。结果曾通过 `.agents/scripts/ppt-to-mac --open` 传到 MacBook 的 `converted-pptx/`。这不代表 18 张 benchmark 全部通过。

## 恢复

- 首先运行 `editppt run next <run>` 或 `run status` 读取当前状态，保留失败日志和现有素材。
- 校验失败由原页面 owner 修复对应 manifest/素材，重新构建、渲染、验证后再 record；不手改任务状态或 `passed`。
- worker 仍在运行时等待；只有确实丢失或终止后才按 CLI 帮助执行 `run reset --agent-id <id> --confirm-lost`。
- 安装路径错误：从仓库根重新安装，不再使用旧 `cli/` 子目录。
- 缺少真实渲染器时保留 PPTX 和程序预览，明确标记真实渲染未验证，不能声称视觉验收完成。
- Linux 上 LibreOffice 可能因沙箱配置目录只读而退出 1；先使用任务目录内的新 profile，并通过 `codex exec --approve-for-me` 让运行时审批该单次渲染命令。若仍失败，保留 `attempt.txt` 并标记渲染未验证，不要反复改写全局 `HOME` 或关闭所有保护。

卸载 CLI 使用 `uv tool uninstall image-to-editable-ppt-cli`（或 pipx）。skill 注册按安装渠道撤销，不删除原始输入或运行记录。
