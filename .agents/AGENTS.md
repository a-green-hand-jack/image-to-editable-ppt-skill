# 开发平面 Agent 指南

> 文档责任：面向在本仓库中工作的 coding agent，详细说明产品平面、开发平面、证据边界和渐进式披露规则。维护义务：让 agent 能在不猜测目录职责的情况下选择正确的源码、工具和验证入口。不负责：终端用户教程、个人设备配置和临时运行结果。

## 读取顺序与渐进式披露

从仓库根目录开始：

1. 先读根目录 `AGENTS.md`，获得不可违背的入口约束。
2. 再读本文件，理解目录所有权、平面边界和修改规则。
3. 任务涉及产品目标时读 `README.md`；涉及开发、验证或发布时读 `DEV.md`；涉及用户操作时读 `USER.md`。
4. 修改文档时读 `memory/document-responsibilities.md`；只有任务需要时才读取 `references/`、`knowledge/`、`workflows/`、`skills/` 或具体测试。
5. 处理某个产品 skill 时，只读该 skill 的 `SKILL.md` 及其明确链接且与当前任务相关的参考资料，不预加载整个 `.agents/`。

渐进式披露的原则是“先边界，后领域，最后细节”：不要因为一个任务涉及 PPT 就加载所有开发资料；先确认要修改的是产品源码、开发工具、文档还是评测证据，再读取对应子目录。

## 两个平面

### 产品平面：发布物的唯一来源

产品平面是 `src/editppt/`，只包含用户安装后运行所需的代码、资源和可分发 skill：

```text
src/editppt/
├── cli.py                         # editppt 公共命令入口
├── runtime/                       # 确定性准备、构建、验证、状态和组装
└── skills/image-to-editable-ppt/  # 随产品分发的 Codex skill 及其资源
```

产品平面必须能够脱离仓库根目录和 `.agents/` 运行。产品代码不得通过相对路径读取开发资料、个人配置、benchmark 或运行日志。`manifest.json` 是页面构建源；不能以整页截图加隐藏文本伪造可编辑性。

### 开发平面：不进入发布物

`.agents/` 是开发平面，不是第二份产品实现，也不属于 wheel/sdist 或运行依赖：

```text
.agents/
├── AGENTS.md          # 本文件：开发平面边界和渐进式读取
├── memory/            # 项目决策、教训和长期约束
├── knowledge/         # 领域知识；只放支持开发判断的资料
├── references/        # 外部开源参考、revision、license 和采纳边界
├── tools/             # 一次性或开发辅助工具，不是产品 API
├── skills/            # 仅服务开发过程的 agent skill
├── workflows/         # 可复用开发流程和检查顺序
├── scripts/           # 安装、发布、评测等开发辅助脚本
└── tests/             # 产品运行时和打包边界的回归测试
```

开发平面的脚本可以调用产品公共 CLI，但不能复制 `src/editppt/` 的实现，也不能要求产品运行时依赖 `.agents/`。如果某个工具需要进入用户安装流程，应先把它设计成产品平面的正式入口，再从开发平面调用；不能仅通过文档或软链接把开发脚本冒充产品能力。

## 评测输入与运行证据

`benchmark/` 是固定输入平面，不属于产品发布物。PNG 原始字节、文件名和哈希必须保持不变；运行结果放在明确的 `benchmark/runs/<run>/` 下，不覆盖输入。

一次评测证据至少区分：

- prepare：输入规范化和任务生成；
- reconstruction：模型生成 manifest 和页面 PPTX；
- structural validation：OOXML、对象、文字和来源合同；
- real render：LibreOffice/PowerPoint 等真实渲染器输出；
- record/finalize：通过 CLI 状态机记录并组装最终 deck。

程序 preview、存在一个 `.pptx` 文件或单次命令退出成功，都不能替代真实渲染证据。headless Codex 评测必须由独立进程加载产品 skill，只接收原始输入和任务要求；父会话手工提供对象答案只能算调试，不算端到端验收。

## 修改与验证边界

- 使用公开 `editppt` CLI 完成 prepare、build、validate、record、finalize；不要另建调度、监控或状态系统。
- 修改产品源码后，至少运行相关回归测试、CLI 帮助/入口检查和打包边界检查。
- 修改 skill 后运行 skill quick validation，并检查资源链接、frontmatter 和发布路径。
- 修改文档后检查责任头是否仍准确，正文是否混入个人设备、私有路径、凭据或临时运行结论。
- 引入外部参考时在 `.agents/references/` 记录固定 revision、license、实际采纳内容和未采纳边界。
- 只在用户明确要求时 commit、push 或发布；提交前保留并检查无关用户改动。

## 信息归属判断

写入前先问“这是谁的长期责任”：

| 信息 | 归属 |
| --- | --- |
| 产品能力、安装入口、用户可观察行为 | 产品文档或 `src/` |
| 源码结构、测试、构建和发布规则 | `DEV.md` 或本文件 |
| Agent 硬约束和读取顺序 | 根 `AGENTS.md` 或本文件 |
| 个人设备、SSH、私有默认目录、一次性传输 | 私有 skill / 私有 memory；不进入产品正文 |
| 某次运行的日志、PPTX、失败或视觉差异 | 对应 run 目录；不写成普遍能力 |

当边界不清时，优先保守地把信息留在开发运行记录，而不是扩大产品契约。
