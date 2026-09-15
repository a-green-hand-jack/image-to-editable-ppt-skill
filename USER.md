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

将 `src/editppt/skills/image-to-editable-ppt/` 注册为 agent 的 skill 目录。例如在个人 Codex 使用且目标不存在时：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s "$PWD/src/editppt/skills/image-to-editable-ppt" \
  "${CODEX_HOME:-$HOME/.codex}/skills/image-to-editable-ppt"
```

受统一 profile 管理的机器按其 skill 发布流程注册，不覆盖已有安装。wheel 安装的 skill 也包含完整资源；在同一 Python 环境执行下式可以找到它：

```bash
python -c 'from importlib.resources import files; print(files("editppt") / "skills" / "image-to-editable-ppt")'
```

重启或刷新 agent 的 skill 发现，再请求：

> 使用 image-to-editable-ppt，把这张图重建成可编辑 PPTX，保留所有标签、箭头、图标和版式，并检查真实 PPTX 渲染。

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

## 恢复

- 首先运行 `editppt run next <run>` 或 `run status` 读取当前状态，保留失败日志和现有素材。
- 校验失败由原页面 owner 修复对应 manifest/素材，重新构建、渲染、验证后再 record；不手改任务状态或 `passed`。
- worker 仍在运行时等待；只有确实丢失或终止后才按 CLI 帮助执行 `run reset --agent-id <id> --confirm-lost`。
- 安装路径错误：从仓库根重新安装，不再使用旧 `cli/` 子目录。
- 缺少真实渲染器时保留 PPTX 和程序预览，明确标记真实渲染未验证，不能声称视觉验收完成。

卸载 CLI 使用 `uv tool uninstall image-to-editable-ppt-cli`（或 pipx）。skill 注册按安装渠道撤销，不删除原始输入或运行记录。
