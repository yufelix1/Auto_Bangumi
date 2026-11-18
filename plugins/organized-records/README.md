# 整理文件记录

添加种子时通过 SDK 的 `torrent.adding` 钩子缓存番剧名和 RSS ID；整理完成（`torrent.organized`）后，将正片与字幕的路径、番剧信息、原始事件和处理状态保存到插件自己的 SQLite 数据库，供外部程序查询和处理。

- 将事件中文件的完整路径原样保存到 `path`，不截断、不按前缀过滤
- 每个文件一条记录，以 `path` 为主键；重复路径直接跳过，已有内容、状态和时间均不改变
- 新记录的 `status` 为 `0`（待处理），由外部程序处理后改为 `1`（已完成）

## 保存的记录

插件 ID 为 `organized-records`。数据库位于 `ctx.data_dir/data.db`，对应 AB 配置目录下的 `plugin-data/organized-records/data.db`。插件启动时自动创建数据库、`organized_files` 表和状态索引。

| 字段 | 类型 | 内容 |
| --- | --- | --- |
| `path` | TEXT PRIMARY KEY | 事件中文件的原始完整路径 |
| `bangumi_name` | TEXT | 添加种子时缓存的番剧官方名称；取不到时留空并记录 ERROR 日志，不从路径推断 |
| `bangumi_id` | INTEGER | 整理完成事件的番剧 ID |
| `rss_id` | INTEGER | 添加种子时的 RSS ID；未捕获或有多个不同 RSS ID 时为空 |
| `status` | INTEGER | `0` 待处理、`1` 已完成，默认 `0` |
| `created_at` | DATETIME | 首次入库时间，默认 `CURRENT_TIMESTAMP` |
| `updated_at` | DATETIME | 初始默认 `CURRENT_TIMESTAMP`，后续由外部程序更新 |
| `event_data` | TEXT | 完整整理完成事件的 JSON，包含 `torrent_hash`、`bangumi_id`、`downloader_id`、`files` |

时间使用 UTC，格式为 `YYYY-MM-DD HH:MM:SS`。默认时间只在插入时填写，修改状态时需主动更新 `updated_at`。

## 外部程序处理

查询待处理文件：

```sql
SELECT path, event_data, created_at, updated_at
FROM organized_files
WHERE status = 0
ORDER BY created_at, path;
```

处理完成后，使用参数绑定传入路径：

```sql
UPDATE organized_files
SET status = 1, updated_at = CURRENT_TIMESTAMP
WHERE path = ?;
```

数据库启用 WAL。外部程序应使用 SQLite 连接读写并设置合理的锁等待时间，备份使用 SQLite backup API。
插件只保存实际收到的事件，不回填历史记录；启动时仅创建当前表结构，不修改已有表结构。

## 安装

```bash
cp -r organized-records config/plugins/local/
```

在「设置 → 插件」中开启「允许未签名插件」，启用插件即可。

## 测试

```bash
cd organized-records
uv add ../autobangumi_sdk-0.6.0-py3-none-any.whl   # SDK 不在 PyPI：换成下载的轮子的实际路径
uv run pytest
```

## 打包

从本仓库根目录执行：

```bash
.venv/bin/python scripts/pack_plugin.py
```

每次打包自动递增补丁版本（例如 `0.1.1` → `0.1.2`），同步更新 `plugin.toml` 和 `pyproject.toml`，
校验通过后输出到 `dist/`。已有安装包保留；校验或打包失败时不会更新源文件中的版本号。
后续发布统一使用此命令；SDK 原生的 `ab-plugin pack` 不负责自动递增版本。
