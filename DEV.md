# 开发指南

> 文档责任：面向维护者和贡献者，说明结构、架构、开发目标、验证和发布方式。维护义务：保持源码、验证与发布边界一致，开发方法不依赖个人设备配置。不承载：用户教程、个人运维流程和临时运行结果。

## 两个平面

`src/editppt/` 是产品运行时完整且唯一的源码，Python 包名为 `editppt`，发行名为 `image-to-editable-ppt-cli`。其中 `skills/image-to-editable-ppt/` 包含 `SKILL.md`、提示模板、引用文档、提示生成脚本及 UI 元数据，随 wheel 分发。产品不得读取仓库根目录或 `.agents/` 才能工作。

`.agents/` 仅用于开发：`memory/` 放项目决策，`knowledge/` 放领域知识，`references/` 放开源参考，`tools/` 放开发工具，`skills/` 放开发专用技能，`workflows/` 放开发流程，`scripts/` 放安装和发布辅助脚本，`tests/` 放回归测试。没有内容的目录只保留占位，不属于产品发现路径。

`benchmark/` 是用户指定的开发输入集，PNG 保持原名、原始字节和 SHA-256。运行结果放到明确指定的独立目录，不覆盖输入，也不打包进 wheel/sdist。无容器部署需求，因此不添加 Dockerfile；`.dockerignore` 保留构建上下文边界。

## 架构

核心能力来自 foundation model 对图片、语义、布局和视觉差异的理解。优先改进模型输入、任务说明与视觉反馈；自己的编排只承担必要的文件处理、确定性构建和状态记录，不作为主要优化目标，不增加第二套 agent 调度系统。

1. `cli.py` 启动 `runtime/main.py` 的公开 `editppt` 命令。
2. `prepare` 规范化图片/PDF/PPT(X)，写入页图、画布、任务和备注。文字提示可选，离线提示仅测量几何。
3. 视觉 agent 根据产品 skill 识别对象，使用逐页提示进行重建；CLI 不内置第二套模型调度器。
4. `build_pptx_from_manifest.py` 把 manifest 转为 DrawingML/OOXML；`preview.png` 是 Pillow 程序预览。
5. 外部 LibreOffice/PowerPoint 渲染真实 PPTX，agent 比对源图。`validate_pptx.py` 检查结构及声明的对象覆盖，不自动判断视觉相似度。
6. `run record` 验证并记录文件哈希，`run finalize` 从 manifest 重建最终 deck 并检查结构和来源。

多页 deck 共用一套画布，按各页 `content_box` 等比放入。benchmark 图片比例各异，正式对比应一图一个 run，避免合并画布影响结果。

## 开发与验证

先检查已有兼容 Python 环境；没有时使用 `uv sync --locked` 建立项目 `.venv`。常规开发命令：

```bash
uv sync --locked
uv run editppt --help
uv run python -m unittest discover -s .agents/tests -v
uv build
```

已有兼容环境也可直接验证源码：

```bash
PYTHONPATH=src /path/to/python -m editppt.cli --help
PYTHONPATH=src /path/to/python -m unittest discover -s .agents/tests -v
```

改动打包时检查 wheel/sdist：仅含产品代码、skill 与必要构建/许可元数据，不能夹带 `.agents/`、`benchmark/`、运行输出或凭据。从解包的 wheel 验证 CLI 及提示模板，不能只验证 editable 安装。

## 开发目标与案例优化

当前重点是科学图的保真重建：文字字号和折行、重复图标一一对应、曲线/箭头与分支完整、原生表格、透明边缘以及真实 PPTX 中的字体和对象布局。沿用现有素材来源合同，不把开源参考中的整组截图或近似图标替换引入默认流程。

每次案例优化保留输入哈希、代码版本、使用的模型/后端、manifest、PPTX、程序预览、真实渲染及失败原因。对比结构可编辑性、文本准确性、对象覆盖和渲染保真度；像素相似度不能单独代表成功。只修复实际观察到的失败，不能把单个成功案例推广为全案例通过。

端到端案例必须由独立的 headless Codex 进程加载产品 skill，仅接收原始 PNG 和输出要求完成。父会话手写 manifest 或提供对象答案只能算调试，不能替代端到端证据。任务目录的 `.agents/skills/` 可通过符号链接挂载 `src/` 下的产品 skill；它不是第二份产品源码，也不进入发布物。保留 `codex exec --json` 日志和最终回复，若中途人工修复或续跑，明确记录边界。

## 安装与发布

最终用户使用根目录的 `install.sh`：它从 GitHub 下载指定 ref，安装 CLI，并注册 Codex skill。开发者在本地 checkout 中可使用 `uv tool install --force --editable .`；`.agents/scripts/install.sh` 只服务于已有 checkout，不是公开的一键安装入口。修改源码后重新安装或使用 editable 安装。

发行前运行上述检查，执行 `uv build` 产生 wheel/sdist。wheel 内 `editppt/skills/image-to-editable-ppt/` 是 skill 发布来源，仓库根的文档及 `.agents/` 不作为产品运行依赖。发布目标和渠道由具体发布请求决定；提交、推送和上传不会由构建或安装脚本自动执行。
