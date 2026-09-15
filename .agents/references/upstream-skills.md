# 开源参考与采纳边界

调研日期：2026-09-15。以下是已读取的设计参考，不代表在本机实测过它们的输出质量。未引入额外生成库或复制第三方脚本。

| 参考 | 固定 revision / 许可 | 本项目采纳 |
| --- | --- | --- |
| [ningzimu/image-to-editable-ppt-skill](https://github.com/ningzimu/image-to-editable-ppt-skill/tree/6b6b2d488eaa50ec3a86388beb7c69eb7ddbd831/skills/image-to-editable-ppt) | `6b6b2d488eaa50ec3a86388beb7c69eb7ddbd831` / MIT | 当前项目已采用同类 manifest、逐页状态、来源记录、前景素材分离流程；本轮保留并理顺产品边界。 |
| [fengting124/paper-figure-pptx-skill](https://github.com/fengting124/paper-figure-pptx-skill/blob/2af11e75d3f15fa8190cff6518d1b14a956f377d/SKILL.md) | `2af11e75d3f15fa8190cff6518d1b14a956f377d` / MIT | 科研图按文本/结构/复杂视觉分类；真实 PPTX 渲染与程序 preview 分开，检查渲染中的字体、连线和边缘。落实到产品 render-validation 引用和逐页提示。 |

有意保留的差异：本项目使用现有 Python/OOXML builder，不为参考 PptxGenJS 而另建生成器；保留现有严格前景分离合同，不引入整组截图或语义替换默认模式；依据观察到的错误迭代，不机械要求固定两轮修复；通过 PATH 或用户指定位置发现渲染器，不硬编码 Windows 路径。

也查看了 `anthropics/skills/skills/pptx`。其目录中的 `LICENSE.txt` 明确为专有条款，因此不将其作为可复用的开源 skill，不复制其提示、脚本或素材。不要用仓库整体的可见性推断子目录许可。
