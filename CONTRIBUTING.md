# 插件开发约定

## 组织方式

- 每个插件放在 `plugins/<plugin-id>/`，id 使用小写字母、数字和连字符。
- 每个插件自行维护 `plugin.toml`、开发用 `pyproject.toml`、README 和测试。
- README 应说明插件用途、配置、兼容版本及安装方式。
- 新插件使用 AutoBangumi 4.0 的 `ab_sdk`，不导入宿主的 `module.*`，不复制宿主或 SDK 实现。

## 开发与验证

所有插件共用根目录的 `ruff.toml`，延续每行 88 字符、Python 3.14 的格式化规则。先安装 uv，再从仓库根目录运行：

```bash
make format        # 修改 Python 文件，统一格式
make format-check  # 只检查格式，不修改文件
```

命令固定 Ruff 版本，并显式加载根目录配置，插件自己的 `pyproject.toml` 不会覆盖这些格式化规则。第三方 `vendor/`、虚拟环境和构建产物不参与格式化。GitHub Actions 会在 push 和 pull request 时执行相同的格式检查；当前没有 Python 文件时也可运行。

`.git-blame-ignore-revs` 保留历史批量格式化提交。需要让本地 `git blame` 使用它时，可运行一次：

```bash
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

按根目录 README 安装上游 Release 的 SDK wheel。在插件目录运行：

```bash
ab-plugin validate .
python -m pytest
ab-plugin pack .
```

测试优先使用 `ab_sdk.testing` 的契约套件或 `create_plugin`。网络请求使用模拟响应，避免测试依赖真实账号、令牌和外部服务。

插件的 Python 依赖、前端依赖和锁文件分别保存在插件自己的目录。SDK 来源应固定到明确的 wheel 版本。不要提交虚拟环境、私钥、令牌、本地配置或 `dist/` 产物；前端运行资源 `web/` 按插件打包需求维护。

SDK 清单、扩展点、测试和 UI 参考见 [插件开发指南](skills/autobangumi-plugin/SKILL.md)。官方市场的收录和签名由上游维护，本仓库不自动发布。
