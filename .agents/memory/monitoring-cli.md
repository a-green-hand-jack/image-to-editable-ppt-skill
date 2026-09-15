# 运行监控入口约束

> 文档责任：面向后续 coding agent，记录本项目运行观测的唯一入口和禁止事项。维护义务：保持监控方式与公开 CLI 一致。不承担：具体某次运行的状态或日志。

监控、判断进程是否推进和定位阶段时，必须优先使用产品公开 CLI：

```bash
editppt run status <run> --events 10
editppt run status <run> --json --events 20
```

不得为同一能力自行编写轮询脚本、PID 追踪器、事件解析器或其他 glue code。需要更细的阶段信息时，应在现有 `editppt run status` 上增量扩展，并保持只读、机器可读和人类可读输出一致。进程表、文件时间和原始 `events.jsonl` 只能作为 CLI 诊断的辅助证据，不能替代公开入口。
