# 发布的 GitHub 资源与本地产物边界

> 文档责任：面向维护者和 coding agent，记录本项目的发布渠道及一次发布对应的 GitHub 资源数量约束。维护义务：避免把本地产物当作发布面，或创建重复 tag、重复 release。不承担：具体版本号或发布说明内容。

用户所说的“发布”固定表示一次发布操作只创建：

- 一个 GitHub tag；
- 一个对应的 GitHub Release。

发布前先检查目标 tag 和 release 是否已存在，选择唯一版本号；提交并推送源码后再创建 tag 和 release，并验证 tag、release 与远端提交一致。不要额外创建同一版本的备用 tag、测试 release 或重复发布条目。

正式发布直接通过 GitHub tag 和对应的 GitHub Release 完成。仓库本地不创建或保留 `dist/` 作为 release 发布面，也不把本地 wheel/sdist 视为正式发布；安装器直接使用 GitHub 上的目标 ref。
