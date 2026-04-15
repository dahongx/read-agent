from __future__ import annotations

from enum import Enum
from typing import ClassVar, Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator

TemplateValue = Literal[
    "academic_defense",
    "anthropic",
    "google_style",
    "mckinsey",
    "exhibit",
    "重庆大学",
    "no_template",
]
PageCountValue = Literal[8, 10, 12, 15, 20]
LanguageValue = Literal["中文", "英文", "中英双语"]
StyleValue = Literal["学术汇报", "商务简报", "技术分享"]
AudienceValue = Literal["高校师生", "企业团队", "通用"]


class SessionStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    error = "error"


class PptConfig(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    TEMPLATE_PROMPT_VALUES: ClassVar[dict[str, str]] = {
        "academic_defense": "academic_defense",
        "anthropic": "anthropic",
        "google_style": "google_style",
        "mckinsey": "mckinsey",
        "exhibit": "exhibit",
        "重庆大学": "重庆大学",
        "no_template": "自由设计",
    }
    COLOR_SCHEMES_BY_TEMPLATE: ClassVar[dict[str, str]] = {
        "academic_defense": "蓝白为主，橙色强调",
        "anthropic": "深色科技感，品牌橙色强调",
        "google_style": "简洁白底，蓝红黄绿少量强调",
        "mckinsey": "蓝灰商务风，数据导向",
        "exhibit": "黑白灰为主，单一强调色突出结论",
        "重庆大学": "校色体系，学术答辩风格",
    }
    COLOR_SCHEMES_BY_STYLE: ClassVar[dict[str, str]] = {
        "学术汇报": "蓝白为主，橙色强调",
        "商务简报": "蓝灰商务风",
        "技术分享": "高对比科技风",
    }

    template: TemplateValue = "academic_defense"
    page_count: PageCountValue = 12
    language: LanguageValue = "中文"
    style: StyleValue = "学术汇报"
    audience: AudienceValue = "高校师生"

    @field_validator("page_count", mode="before")
    @classmethod
    def normalize_page_count(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.isdigit():
                return int(stripped)
        return value

    @property
    def template_prompt_value(self) -> str:
        return self.TEMPLATE_PROMPT_VALUES[self.template]

    @property
    def color_scheme_prompt_value(self) -> str:
        if self.template != "no_template":
            return self.COLOR_SCHEMES_BY_TEMPLATE.get(
                self.template,
                self.COLOR_SCHEMES_BY_STYLE[self.style],
            )
        return self.COLOR_SCHEMES_BY_STYLE[self.style]


class ProgressState(BaseModel):
    ppt_step: str = ""
    ppt_pct: int = 0
    rag_step: str = ""
    rag_pct: int = 0


class SessionState(BaseModel):
    session_id: str
    status: SessionStatus = SessionStatus.pending
    progress: ProgressState = ProgressState()
    error: Optional[str] = None
    pdf_path: Optional[str] = None
    ppt_path: Optional[str] = None
    rag_index_path: Optional[str] = None
    script: Optional[list[str]] = None
    ppt_config: Optional[PptConfig] = None


class UploadResponse(BaseModel):
    session_id: str
    status: SessionStatus
