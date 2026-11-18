"""Persist finalized downloader paths without accessing the media files."""

import asyncio
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from ab_sdk import Plugin, hook, points, subscribe
from ab_sdk.events import TorrentOrganized
from ab_sdk.ingest import AddRequest


class OrganizedRecords(Plugin):
    @property
    def database_path(self) -> Path:
        return self.ctx.data_dir / "data.db"

    @contextmanager
    def database(self):
        db = sqlite3.connect(self.database_path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def initialize(self) -> None:
        self.ctx.data_dir.mkdir(parents=True, exist_ok=True)
        with self.database() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("BEGIN IMMEDIATE")
            db.execute("""
                CREATE TABLE IF NOT EXISTS organized_files (
                    path TEXT PRIMARY KEY NOT NULL,
                    bangumi_name TEXT,
                    bangumi_id INTEGER,
                    rss_id INTEGER,
                    status INTEGER NOT NULL DEFAULT 0 CHECK(status IN (0, 1)),
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    event_data TEXT NOT NULL
                )
            """)
            db.execute(
                "CREATE INDEX IF NOT EXISTS organized_files_bangumi ON organized_files(bangumi_id)"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS organized_files_status ON organized_files(status)"
            )

    async def setup(self) -> None:
        await asyncio.to_thread(self.initialize)

    @hook(points.TORRENT_ADDING)
    async def remember_bangumi(self, request: AddRequest):
        if request.bangumi.id is not None:
            rss_ids = {
                torrent.rss_id
                for torrent in request.torrents
                if torrent.rss_id is not None
            }
            metadata = {
                "bangumi_name": request.bangumi.official_title,
                "rss_id": next(iter(rss_ids)) if len(rss_ids) == 1 else None,
            }
            await self.ctx.kv.set(f"bangumi:{request.bangumi.id}", metadata)

    def save_event(self, event: TorrentOrganized, metadata: dict | None = None) -> int:
        paths = {file.path for file in event.files}
        if not paths:
            return 0

        metadata = metadata or {}
        bangumi_name = metadata.get("bangumi_name")
        if not bangumi_name or not bangumi_name.strip():
            bangumi_name = None
            self.ctx.log.error(
                "种子 %s（番剧 ID=%s）：未获取到缓存的官方名称，bangumi_name 留空",
                event.torrent_hash,
                event.bangumi_id,
            )
        payload = json.dumps(asdict(event), ensure_ascii=False, separators=(",", ":"))
        with self.database() as db:
            db.execute("BEGIN IMMEDIATE")
            result = db.executemany(
                """
                INSERT INTO organized_files (path, bangumi_name, bangumi_id, rss_id, event_data)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(path) DO NOTHING
            """,
                [
                    (
                        path,
                        bangumi_name,
                        event.bangumi_id,
                        metadata.get("rss_id"),
                        payload,
                    )
                    for path in sorted(paths)
                ],
            )
        return result.rowcount

    @subscribe(TorrentOrganized.kind, timeout=30)
    async def on_organized(self, event: TorrentOrganized) -> None:
        metadata = (
            await self.ctx.kv.get(f"bangumi:{event.bangumi_id}")
            if event.bangumi_id is not None
            else None
        )
        count = await asyncio.to_thread(self.save_event, event, metadata)
        if count:
            self.ctx.log.info("种子 %s：新增 %d 条文件记录", event.torrent_hash, count)
