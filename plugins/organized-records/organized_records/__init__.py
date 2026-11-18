"""Record finalized downloader paths without touching the media files."""

import asyncio
import re
import sqlite3
from contextlib import closing
from dataclasses import replace
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Annotated

import httpx2
from ab_sdk import Plugin, secret_field, subscribe
from ab_sdk.events import OrganizedFile, TorrentOrganized
from pydantic import BaseModel, Field, StringConstraints


class Options(BaseModel):
    api_base_url: str = Field(
        "http://127.0.0.1:7892/api/v1", title="AutoBangumi API 地址"
    )
    api_token: Annotated[str, StringConstraints(strip_whitespace=True)] = secret_field(
        ...,
        min_length=1,
        title="AutoBangumi API 令牌",
        description="必填，使用 scope=api 的令牌。",
    )


def bangumi_name_from_path(path: str) -> str | None:
    path_type = (
        PureWindowsPath
        if re.match(r"^(?:[A-Za-z]:[\\/]|\\\\)", path)
        else PurePosixPath
    )
    for parent in path_type(path).parents:
        if re.fullmatch(r"Season [0-9]+", parent.name):
            return re.sub(r"\s*\([0-9]{4}\)$", "", parent.parent.name.strip()) or None
    return None


class OrganizedRecords(Plugin[Options]):
    config_model = Options
    client_factory = httpx2.AsyncClient

    @property
    def database_path(self) -> Path:
        return self.ctx.data_dir / "data.db"

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path, timeout=10)

    async def setup(self) -> None:
        await asyncio.to_thread(self.initialize)

    def initialize(self) -> None:
        self.ctx.data_dir.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.executescript("""
                PRAGMA journal_mode = WAL;
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS organized_files (
                    file_path TEXT PRIMARY KEY NOT NULL,
                    file_kind TEXT NOT NULL,
                    bangumi_id INTEGER NOT NULL,
                    bangumi_name TEXT,
                    rss_id INTEGER,
                    torrent_hash TEXT NOT NULL,
                    downloader_id TEXT NOT NULL,
                    status INTEGER NOT NULL DEFAULT 0 CHECK(status IN (0, 1)),
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS organized_files_bangumi ON organized_files(bangumi_id);
                CREATE INDEX IF NOT EXISTS organized_files_status ON organized_files(status);
                COMMIT;
            """)

    async def resolve_rss_id(self, bangumi_id: int) -> int | None:
        try:
            async with (
                asyncio.timeout(10),
                self.client_factory(
                    base_url=self.config.api_base_url,
                    headers={"Authorization": f"Bearer {self.config.api_token}"},
                    follow_redirects=False,
                    trust_env=False,
                ) as client,
            ):
                response = await client.get(f"bangumi/get/{bangumi_id}")
                rss_link = response.raise_for_status().json().get("rss_link")
                if not rss_link:
                    return None

                response = await client.get("rss")
                for feed in response.raise_for_status().json():
                    if isinstance(feed, dict) and feed.get("url") == rss_link:
                        rss_id = feed.get("id")
                        return rss_id if type(rss_id) is int else None
        except (
            httpx2.HTTPError,
            httpx2.InvalidURL,
            ValueError,
            TimeoutError,
            AttributeError,
            TypeError,
        ) as exc:
            reason = (
                f"HTTP {exc.response.status_code}"
                if isinstance(exc, httpx2.HTTPStatusError)
                else type(exc).__name__
            )
            self.ctx.log.warning(
                "番剧 ID=%s：RSS ID 查询失败（%s）", bangumi_id, reason
            )
        return None

    def new_files(self, files: tuple[OrganizedFile, ...]) -> tuple[OrganizedFile, ...]:
        seen = set()
        new = []
        with closing(self.connect()) as db:
            for file in files:
                if file.path in seen:
                    continue
                seen.add(file.path)
                row = db.execute(
                    "SELECT 1 FROM organized_files WHERE file_path = ?", (file.path,)
                ).fetchone()
                if row is None:
                    new.append(file)
        return tuple(new)

    def save_event(self, event: TorrentOrganized, rss_id: int | None = None) -> int:
        rows = [
            (
                file.path,
                file.kind,
                event.bangumi_id,
                bangumi_name_from_path(file.path),
                rss_id,
                event.torrent_hash,
                event.downloader_id,
            )
            for file in event.files
        ]
        with closing(self.connect()) as db, db:
            return db.executemany(
                """
                INSERT INTO organized_files (
                    file_path, file_kind, bangumi_id, bangumi_name, rss_id,
                    torrent_hash, downloader_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO NOTHING
                """,
                rows,
            ).rowcount

    @subscribe(TorrentOrganized.kind, timeout=30)
    async def on_organized(self, event: TorrentOrganized) -> None:
        if not event.files or event.bangumi_id is None:
            return
        files = await asyncio.to_thread(self.new_files, event.files)
        if not files:
            return
        rss_id = await self.resolve_rss_id(event.bangumi_id)
        count = await asyncio.to_thread(
            self.save_event, replace(event, files=files), rss_id
        )
        if count:
            self.ctx.log.info("种子 %s：新增 %d 条文件记录", event.torrent_hash, count)
