# Image to Editable PPT

把科研论文插图、流程图、幻灯片截图、扫描 PDF 和图片型 PPT/PPTX 重建为**对象级可编辑的 PowerPoint**，尽量保持原图的文字、布局、层级和视觉身份。输入有演讲备注时保留备注。

这是一套由视觉 coding agent 使用的 skill，以及配套的 `editppt` 确定性 CLI。Agent 负责理解图片和编写对象清单；CLI 负责输入规范化、素材处理、PPTX 构建、验证和断点恢复。单独运行 `editppt prepare` 不会自动完成图片理解或重建。

主要使用方式是 **headless Codex 加载 skill，输入 PNG，输出 PPTX**。图片理解、对象重建和视觉修正由该进程中的 foundation model 完成，调用者不需要手工编写 manifest。挂载和执行命令见 [USER.md](USER.md#headless-codexpng--pptx)。

## 完整目标形态

- 文字、标题、数字、标签成为可编辑文本框；面板、线条、箭头、曲线、表格成为原生 PowerPoint 对象。
- 复杂图标、照片、插画经过保真分离，作为独立可选择、移动和替换的图片对象。独立图片不等于其内部笔画可编辑；公式目前保留 LaTeX 源及渲染素材，不声称原生公式可编辑。
- 保持源图比例、位置、字体层级、色彩、连线方向、图标实例数及层叠顺序；不以整页图片加文字覆盖充当重建。
- `manifest.json` 是逐页及最终 PPTX 的唯一构建依据。素材、坐标、来源和校验信息随运行保留，失败可以定位和恢复。
- 同时验证对象结构与真实 PPTX 渲染。程序预览、结构校验和视觉通过是不同的证据，不能相互替代。

已有运行时支持输入准备、逐页任务、文字尺寸提示、图像素材分离处理、原生形状/渐变/路径/表格、公式素材、构建和结构检查。视觉质量仍需在真实案例上逐页验证；当前没有对下述 18 个案例的整体通过率声明。

当前真实试跑记录：`PaperClaw_fig_2` 已由 headless Codex 完成，结构校验和 LibreOffice 渲染均通过；`PaperClaw_fig_5` 已启动独立试跑，尚未计入完成案例。运行日志和中间产物位于 `benchmark/runs/`（该目录不进入 Git）。

## 入口

- [USER.md](USER.md)：安装、使用、观察、故障恢复。
- [DEV.md](DEV.md)：架构、开发目标、验证和发布。
- [AGENTS.md](AGENTS.md)：coding agent 的边界和约束。
- [产品 skill](src/editppt/skills/image-to-editable-ppt/SKILL.md)：重建工作流。
- [benchmark/](benchmark/)：18 张固定 PNG 测试输入；见 [案例说明](benchmark/README.md)。

```text
src/editppt/                    产品唯一来源：CLI、runtime、可分发 skill
README.md / DEV.md / USER.md     分别面向了解产品、开发、使用
AGENTS.md                       coding agent 开发约束
.agents/                        开发资料、工具、工作流与测试；不进入发布物
benchmark/                      用户提供的固定评测图片；不进入发布物
pyproject.toml / uv.lock         构建元数据、依赖与精确锁定
```

开源实现参考及取舍见 [.agents/references/upstream-skills.md](.agents/references/upstream-skills.md)。代码采用 MIT 许可；benchmark 图片的权利归各自权利人，不因放入本仓库而自动适用代码许可。
