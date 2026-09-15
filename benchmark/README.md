# 固定图片案例

18 张 PNG 来自用户提供的 MacBook I2P 目录，复制日期为 2026-09-15。文件名、原始像素和文件字节保留，逐一核对过源端及目标端 SHA-256；清单见 `SHA256SUMS`。这些是输入素材，不是成功重建结果或已标注 ground truth。

```bash
# 在仓库根检查输入完整性
sha256sum -c benchmark/SHA256SUMS
```

| 文件组 | 数量 |
| --- | ---: |
| AutoSOTA_fig1–6 | 6 |
| EvoScientist_fig_1 | 1 |
| OmniScientist_fig_1–3 | 3 |
| PaperClaw_fig_1、2、5 | 3 |
| PaperOrchestra_fig_1 | 1 |
| auto_reseach_ai_fig_1 | 1 |
| the_ai_scientist_fig_1 | 1 |
| the_ai_scientist_v2_fig_1–2 | 2 |

文件名中的 `reseach` 按原名保留。不同图的比例不同，后续优化按一图一个 run：

```bash
editppt prepare benchmark/PaperOrchestra_fig_1.png --job-dir /absolute/output/PaperOrchestra_fig_1
editppt run next /absolute/output/PaperOrchestra_fig_1
```

随后由 agent 按产品 skill 完成重建。评测同时观察文字准确性及可编辑性、原生结构、对象/箭头覆盖、复杂素材保真和真实 PPTX 渲染；程序 preview 和结构验证不能代替视觉验收。保留失败产物、后端信息和代码版本，不覆盖输入，也不提前填写成功分数。

图片用于用户指定的本地开发评测；原图版权归各权利人，本项目 MIT 代码许可不授予这些图片额外转载或再分发权。
