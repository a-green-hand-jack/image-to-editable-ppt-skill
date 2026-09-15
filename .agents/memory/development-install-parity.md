# 开发机源码与安装版本一致性

> 文档责任：面向维护者和 coding agent，记录本地开发安装与仓库源码的一致性要求。维护义务：避免把旧 wheel 或全局安装误认为当前源码。不承担：用户安装器的发布流程或个人凭据管理。

开发机上的 `editppt` 必须与当前 checkout 的 `src/editppt` 保持一致。修改产品源码后，重新运行 editable 安装（例如 `uv tool install --force --editable .`），再用 `editppt --help`、目标子命令和回归测试确认入口实际加载的是新代码。不要仅凭 `command -v editppt` 判断版本；需要识别 Python 包路径或使用 `PYTHONPATH=src` 做对照。

如果 headless 任务使用了旧安装，必须把它标记为版本漂移证据，不能把其失败或成功直接归因于当前源码。发布或正式评测前应先完成安装 parity 检查，并记录 checkout commit、安装入口和 CLI 能力版本。
