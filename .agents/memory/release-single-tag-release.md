# 发布的 GitHub 资源边界

> 文档责任：面向维护者和 coding agent，记录本项目一次发布对应的 GitHub 资源数量约束。维护义务：避免重复 tag、重复 release 或把发布动作拆成多个公开版本。不承担：具体版本号或发布说明内容。

用户所说的“发布”固定表示一次发布操作只创建：

- 一个 GitHub tag；
- 一个对应的 GitHub Release。

发布前先检查目标 tag 和 release 是否已存在，选择唯一版本号；提交并推送源码后再创建 tag 和 release，并验证 tag、release 与远端提交一致。不要额外创建同一版本的备用 tag、测试 release 或重复发布条目。
