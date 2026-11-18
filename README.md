# AutoBangumi Plugins

用于存放、开发和维护 AutoBangumi 插件的独立仓库。每个插件在 `plugins/<plugin-id>/` 中独立管理源码、依赖、测试和使用说明。

## 目录结构

```text
plugins/
  <plugin-id>/
    plugin.toml          # AutoBangumi 4.0 插件清单
    pyproject.toml       # 插件自己的开发依赖和测试配置
    README.md
    <python_package>/
    tests/
    web-src/             # 可选：前端源码
    web/                 # 可选：构建后的前端资源
skills/
  autobangumi-plugin/    # 插件开发指南和 SDK 参考
```

## 新建插件

准备 Python 3.14+ 和 uv。先从 AutoBangumi 上游 Release 下载 `autobangumi_sdk-<版本>-py3-none-any.whl`，再在仓库根目录安装开发工具：

```bash
uv venv --python 3.14
source .venv/bin/activate
# 将路径替换成下载的 wheel 文件路径
uv pip install /absolute/path/to/autobangumi_sdk-0.5.0-py3-none-any.whl pytest

ab-plugin new my-plugin --kind rename --dir plugins
```

`--kind` 支持 `rename`、`notifier`、`search`。其它扩展点参见 [SDK 开发指南](skills/autobangumi-plugin/SKILL.md)。

在同一个已激活的环境中校验、测试和打包，使用插件目录中的测试配置：

```bash
cd plugins/my-plugin
ab-plugin validate .
python -m pytest
ab-plugin pack .
```

产物位于插件自己的 `dist/` 目录。每个插件可独立维护开发环境；使用 `uv sync` 前，需要在该插件的 `pyproject.toml` 中通过 `uv add` 将 SDK 依赖绑定到已下载的 wheel 或确定版本的 Release wheel URL，不要依赖 PyPI 中的同名包。

## 代码格式化

安装 uv 后，在仓库根目录运行：

```bash
make format        # 自动格式化所有插件的 Python 代码
make format-check  # 仅检查；CI 使用同一命令
```

规则位于 `ruff.toml`，使用固定版本的 Ruff，无需安装 AutoBangumi 或 SDK。详细约定见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 本地联调

在插件目录执行以下命令，将插件链接到另一份 AutoBangumi 实例的配置目录：

```bash
ab-plugin dev . --config-dir /absolute/path/to/autobangumi/config
```

该配置目录必须已有 `config.json` 或 `config_dev.json`。命令会开启开发模式、允许未签名插件并启用当前插件；首次链接后重启 AutoBangumi。

开发约定见 [CONTRIBUTING.md](CONTRIBUTING.md)。保留原项目的 MIT [许可证](LICENSE)。
