from __future__ import annotations

import shutil
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_PROJECT_ROOT = _BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DEV_MODE: bool = False
    DEV_MODE_RAG: bool = False
    FIXTURE_DIR: str = "projects/M_plus_MemoryLLM_ppt169_20260409"
    UPLOAD_DIR: str = "backend/uploads"
    PPT_CACHE_DIR: str = "backend/uploads/ppt_cache"
    SKILL_DIR: str = ".claude/skills/paper-to-ppt"
    CLAUDE_CLI_PATH: str = ""
    GIT_BASH_PATH: str = ""
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"
    LLM_MODEL: str = "glm-4-flash"

    @property
    def project_root(self) -> Path:
        return _PROJECT_ROOT

    def _resolve_project_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return (self.project_root / path).resolve()

    @property
    def fixture_path(self) -> Path:
        return self._resolve_project_path(self.FIXTURE_DIR)

    @property
    def upload_path(self) -> Path:
        return self._resolve_project_path(self.UPLOAD_DIR)

    @property
    def ppt_cache_path(self) -> Path:
        return self._resolve_project_path(self.PPT_CACHE_DIR)

    @property
    def skill_path(self) -> Path:
        return self._resolve_project_path(self.SKILL_DIR)

    @property
    def claude_cli_path(self) -> Path | None:
        if self.CLAUDE_CLI_PATH:
            return self._resolve_project_path(self.CLAUDE_CLI_PATH)
        found = shutil.which("claude")
        return Path(found) if found else None

    @property
    def git_bash_path(self) -> Path | None:
        if self.GIT_BASH_PATH:
            return self._resolve_project_path(self.GIT_BASH_PATH)
        for candidate in (
            r"C:\Program Files\Git\bin\bash.exe",
            r"D:\software\GIT\Git\usr\bin\bash.exe",
        ):
            path = Path(candidate)
            if path.exists():
                return path
        found = shutil.which("bash")
        if found and "system32\\bash.exe" not in found.lower():
            return Path(found)
        return None


settings = Settings()