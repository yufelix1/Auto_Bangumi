# 整理文件记录（organized-records）

AutoBangumi 4.0 插件。收到 `torrent.organized` 事件后，把正片和字幕的整理结果写入 SQLite，供外部程序查询和标记处理状态。

## 安装和配置

1. 将安装包解压到 AutoBangumi 配置目录下的 `plugins/local/organized-records/`，确保 `plugin.toml` 直接位于该目录。
2. 在「设置 → 插件」开启「允许未签名插件」。
3. 在「设置 → 用户与访问控制 → API 令牌」创建一个 `scope=api` 的令牌。在插件设置中填写以下配置，然后启用插件。

| 设置 | 填写内容 |
| --- | --- |
| AutoBangumi API 地址（`api_base_url`） | 默认 `http://127.0.0.1:7892/api/v1`。自定义时填写插件能访问的完整 API 基础地址。 |
| AutoBangumi API 令牌（`api_token`） | 必填，填令牌本身，不加 `Bearer` 前缀。 |

## 数据库

插件启用后在 AutoBangumi 配置目录下创建 `plugin-data/organized-records/data.db`，表名为 `organized_files`。

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `file_path` | TEXT | 下载器侧的原始路径，主键 |
| `file_kind` | TEXT | `media`（正片）或 `subtitle`（字幕） |
| `bangumi_id` | INTEGER | 事件中的番剧 ID |
| `bangumi_name` | TEXT | 从路径提取的番剧名，无法提取时为 `NULL` |
| `rss_id` | INTEGER | 匹配到的 RSS 订阅 ID，未取得时为 `NULL` |
| `torrent_hash` | TEXT | 种子哈希 |
| `downloader_id` | TEXT | 下载器实例 ID |
| `status` | INTEGER | `0` 待处理（默认），`1` 已完成 |
| `created_at` | DATETIME | 首次入库时间 |
| `updated_at` | DATETIME | 初始等于入库时间，由外部程序更新 |

时间字段默认使用 SQLite 的 `CURRENT_TIMESTAMP`（UTC，`YYYY-MM-DD HH:MM:SS`）。

查询待处理记录：

```sql
SELECT file_path, file_kind, bangumi_id, bangumi_name, rss_id,
       torrent_hash, downloader_id, created_at, updated_at
FROM organized_files
WHERE status = 0
ORDER BY created_at, file_path;
```

```sql
UPDATE organized_files
SET status = 1, updated_at = CURRENT_TIMESTAMP
WHERE file_path = ?;
```

数据库使用 WAL 模式。外部程序连接时应设置合理的锁等待时间；在线备份请使用 SQLite backup API。

## 测试和打包

从 AutoBangumi 上游 Release 获取 `autobangumi_sdk-0.6.0-py3-none-any.whl`，放到本仓库的 `plugins/` 目录。SDK 不从 PyPI 安装。使用 Python 3.14 或更新版本，在仓库根目录执行：

```sh
cd plugins/organized-records
uv run pytest
uv run ab-plugin validate .
uv run ab-plugin pack .
```

安装包输出到 `dist/organized-records-<版本号>.zip`。
