# P0：统一架构方案

> **目标**：单篇和多篇走统一接口、统一会话模型、统一路径体系；真进度、实时日志、快速失败

**完成时间估算**：4-5 天**解决的核心问题**：

- ❌ 路径混乱（Claude 生成到 `projects/` 或 `output_dir`，代码要搜两个地方）
- ❌ 假进度（`pct = min(pct + 3, 85)` 每 30 秒硬涨，用户蒙在鼓里）
- ❌ 日志看不见（前端只看进度数字，失败时无法定位问题）
- ❌ 细粒度不足（没有 svg_output、svg_final、pptx 等关键阶段，是最后一次性生成保存吗）
- ❌ 错误信息片段（`stderr[-1000:]` 丢失完整链）
- ❌ 单多篇割裂（同一套逻辑却走不同路径）

---

## 一、问题诊断

| 问题                   | 当前状态                                                            | 后果                                          |
| ---------------------- | ------------------------------------------------------------------- | --------------------------------------------- |
| **路径混乱**     | Claude CLI 生成到 `projects/` 或 `output_dir`，代码要搜两个地方 | 维护复杂，容易找不到产物                      |
| **假进度**       | `pct = min(pct + 3, 85)` 每 30 秒硬涨                             | 用户蒙在鼓里，不知道真正进度                  |
| **日志看不见**   | 日志全在后端 `logger.info()`，前端只看进度数字                    | 失败时无法定位问题，浪费额度                  |
| **细粒度不足**   | 只有 "检查缓存" → "Claude 分析" → "完成"，没有中间状态            | 看不到 svg_output、svg_final、pptx 等关键阶段 |
| **错误信息片段** | `stderr[-1000:]` 只取最后 1000 字                                 | 完整的错误链丢失                              |
| **单多篇没区分** | 单篇和多篇用同一套逻辑，路径没有分类                                | 后续多篇改造会很混乱                          |

---

## 二、统一架构方案

### 2.1 统一的路径体系（干净、可理解、易扩展）

```
uploads/
├─ sessions/                              # ← 新增：所有 session 的元数据和产物
│  ├─ {session_id}/
│  │  ├─ metadata.json                   # session 类型、文件列表、配置、时间戳
│  │  ├─ input/                          # 输入文件
│  │  │  ├─ paper_1.pdf
│  │  │  └─ paper_2.pdf
│  │  ├─ output/                         # 最终产物（符号链接指向缓存）
│  │  │  ├─ slides.pptx
│  │  │  ├─ slides.svg/                  # SVG 集合
│  │  │  ├─ script.md
│  │  │  └─ rag_index/
│  │  └─ logs/                           # ← 新增：完整的生成日志
│  │     ├─ ppt_generation.log
│  │     └─ rag_building.log
│  └─ ...
│
├─ cache/                                 # ← 改名：替代原来的 ppt_cache + rag_cache
│  ├─ ppt/
│  │  ├─ {cache_key_v2}/                 # 多篇通用缓存键
│  │  │  ├─ metadata.json                # 包含哪些文件、什么配置
│  │  │  ├─ svg_output/                  # Claude 中间产物
│  │  │  ├─ svg_final/                   # 最终 SVG（产物）
│  │  │  ├─ notes/                       # Markdown 讲稿
│  │  │  └─ slides.pptx                  # 最终 PPTX（产物）
│  │  └─ ...
│  └─ rag/
│     ├─ {hash_v3}/                      # 单个 PDF
│     │  ├─ docstore.json
│     │  ├─ index_store.json
│     │  └─ vector_store.json
│     └─ ...
│
└─ papers/                                 # ← 新增：去重的 PDF 库（按 hash 存储）
   ├─ {pdf_hash}/
   │  └─ original.pdf
   └─ ...
```

**关键特点**：

- 现有产物全集中在 `sessions/{session_id}` 结构下（统一模型，单多篇一样）
- 缓存和输出明确分离：缓存在 `cache/`，输出是 symlink 指向它（避免重复存储）
- 日志独立保存在 `sessions/{session_id}/logs/`，便于回溯和诊断
- PPT 和 RAG 缓存互相独立，互不污染
- PDF 库 `papers/` 按 hash 去重，多篇上传时可复用

---

### 2.2 真实进度模型（基于产物，不靠定时器）

**当前假进度**：每 30 秒涨 3%，到 85%

**改成：基于产物的真实阶段**

```python
from enum import Enum

class GenerationStage(Enum):
    """定义真实的生成阶段"""
    CACHE_CHECK = ("01_cache_check", 5, "检查缓存...")
    MARKDOWN_EXTRACT = ("02_markdown", 15, "抽取 Markdown...")
    NOTES_GENERATION = ("03_notes", 25, "生成讲稿...")
    SVG_OUTPUT = ("04_svg_output", 50, "SVG 排版中...")
    SVG_FINAL = ("05_svg_final", 75, "SVG 最终化...")
    PPTX_EXPORT = ("06_pptx", 95, "导出 PPTX...")
    COMPLETE = ("07_complete", 100, "完成")
  
    def __init__(self, stage_id: str, progress_pct: int, description: str):
        self.stage_id = stage_id
        self.progress_pct = progress_pct
        self.description = description
```

**进度推进方式**（两种方案）：

**方案 A：基于文件系统监控（推荐）**

```python
# 监听 cache/{cache_key}/ 下产物的出现时机
# - canvas.md 创建 → 广播 stage=02_markdown, pct=15
# - notes/ 创建并有内容 → 广播 stage=03_notes, pct=25  
# - svg_output/ 创建 → 广播 stage=04_svg_output, pct=50
# - svg_final/ 创建且有 SVG → 广播 stage=05_svg_final, pct=75
# - *.pptx 创建 → 广播 stage=06_pptx, pct=95
# - 任务完成 → 广播 stage=07_complete, pct=100
```

**方案 B：Claude skill 输出结构化日志（备选）**

```python
# Claude skill 在关键阶段写入 marker 文件
# 后端监听这些 marker → 推进阶段
#
# marker 文件例：
# cache/{cache_key}/markers/
#   ├─ 02_markdown.done    # ← canvas.md 已生成
#   ├─ 03_notes.done      # ← notes/ 已完成
#   ├─ 04_svg_output.done # ← svg_output/ 已完成
#   └─ 05_svg_final.done  # ← svg_final/ 已完成
```

---

### 2.3 实时日志流（前端可见）

**改进日志推送**：不再靠后端 `logger.info()`，改成结构化事件推送

```python
from typing import Optional, Dict, Literal
from datetime import datetime

class LogEvent(BaseModel):
    """日志事件模型"""
    level: Literal["INFO", "WARNING", "ERROR"]
    timestamp: datetime
    stage: str  # "MARKDOWN_EXTRACT", "PPTX_EXPORT" 等
    message: str
    details: Optional[Dict] = None  # 包含 stdout/stderr 片段
    duration_ms: Optional[int] = None  # 该阶段耗时
```

**WebSocket 消息流**：

```json
{
  "event": "log",
  "level": "INFO",
  "stage": "MARKDOWN_EXTRACT",
  "message": "Successfully extracted 5 sections from page 1-10",
  "timestamp": "2026-04-23T10:30:45Z",
  "duration_ms": 1234
}

{
  "event": "log",
  "level": "INFO",
  "stage": "SVG_OUTPUT",
  "message": "SVG layout generation started",
  "details": {
    "total_slides": 12,
    "canvas_format": "16:9"
  }
}

{
  "event": "log",
  "level": "ERROR",
  "stage": "PPTX_EXPORT",
  "message": "Template file not found",
  "details": {
    "expected_path": "/path/to/template",
    "stderr": "FileNotFoundError: [Errno 2] No such file or directory..."
  }
}
```

**前端显示**：滚动日志面板，用户能看到 Claude 的实时动作

```
[INFO] 10:30:44  检查缓存... ✓
[INFO] 10:30:45  抽取 Markdown... 提取 5 个章节
[INFO] 10:31:00  生成讲稿... 完成
[INFO] 10:31:15  SVG 排版中... 12 页
[INFO] 10:32:00  SVG 最终化... ✓
[INFO] 10:32:30  导出 PPTX... ✓
[INFO] 10:33:00  完成 (耗时 3 分 16 秒)
```

---

### 2.4 失败快速、明确、可见

**当前**：错误信息只有最后 1000 字，用户看不到全貌

**改成**：完整的错误上下文和日志链

```python
class ExecutionError(Exception):
    """增强的执行错误类"""
    def __init__(
        self,
        stage: str,
        message: str,
        logs: str = "",
        stdout: str = "",
        stderr: str = "",
        duration_sec: int = 0
    ):
        self.stage = stage
        self.message = message
        self.logs = logs[-50000:]  # 取更多内容（50KB vs 原来的 1KB）
        self.stdout = stdout[-10000:]
        self.stderr = stderr[-10000:]
        self.duration_sec = duration_sec
  
    def to_dict(self):
        return {
            "error": self.message,
            "stage": self.stage,
            "duration_seconds": self.duration_sec,
            "logs": self.logs,
            "stdout_tail": self.stdout,
            "stderr_tail": self.stderr,
        }
```

**WebSocket 推送错误事件**：

```json
{
  "event": "error",
  "stage": "PPTX_EXPORT",
  "message": "Failed to export PPTX: Missing required template file",
  "duration_seconds": 432,
  "logs": "...(完整的 Claude CLI 输出最后 50KB)...",
  "stdout_tail": "...",
  "stderr_tail": "FileNotFoundError: [Errno 2]..."
}
```

**前端显示**：

```
❌ 失败于：PPTX 导出
原因：缺少模板文件
耗时：7 分 12 秒

[查看完整日志...] → 展开日志面板显示所有历史日志
完整错误信息：
  FileNotFoundError: [Errno 2] No such file or directory: '/path/to/template'
  
[重试]  [返回上传]
```

---

### 2.5 统一的会话模型（单篇多篇一套）

**当前**：SessionState 是单篇的，`pdf_path` 只能一个

**改成**：统一模型，支持单个或多个文件

```python
from datetime import datetime
from typing import List, Optional, Dict, Literal

class PaperFile(BaseModel):
    """文件引用"""
    file_id: str  # hash，用于去重和缓存
    filename: str
    size: int
    upload_time: datetime
    pdf_hash: str  # 用于 RAG 缓存键

class ProgressState(BaseModel):
    """进度状态"""
    stage: str  # 当前阶段 ID，e.g. "05_svg_final"
    stage_description: str
    progress_pct: int  # 0-100
    substeps: List[str] = []  # 子步骤列表，用于显示细节

class SessionState(BaseModel):
    """统一会话模型"""
    session_id: str
    session_type: Literal["single", "survey", "comparison"]
    paper_files: List[PaperFile]  # 可以是单个或多个
  
    status: SessionStatus  # pending, processing, ready, error
    progress: ProgressState  # 统一进度模型
    generation_logs: List[LogEvent] = []  # ← 新增：完整的生成日志序列
  
    ppt_config: PptConfig
  
    outputs: Dict[str, str] = {
        # 最终产物（相对 sessions/{session_id}/output/ 的路径）
        "slides_pptx": "slides.pptx",
        "slides_svg_dir": "slides.svg",
        "script_md": "script.md",
        "rag_index_dir": "rag_index",
    }
  
    cache_info: Dict[str, Any] = {
        "ppt_cache_key": Optional[str],  # 如果命中缓存，记录 cache_key
        "rag_cache_key": Optional[str],
        "cache_hit": bool,  # 是否命中缓存
    }
  
    timestamps: Dict[str, datetime] = {
        "created_at": datetime,
        "processing_started_at": Optional[datetime],
        "completed_at": Optional[datetime],
    }
  
    error: Optional[Dict] = None  # ExecutionError.to_dict()

class SessionStatus(str, Enum):
    pending = "pending"        # 已创建，等待处理
    processing = "processing"  # 处理中
    ready = "ready"            # 完成，产物就绪
    error = "error"            # 出错
```

---

## 三、三层改造清单

### 第一层：基础设施（1-2 天）

**目标**：建立新的目录结构和数据模型

#### 1.1 创建新文件

**a) `backend/app/utils/path_utils.py`**

```python
"""统一的路径管理工具"""
from pathlib import Path
from app.core.config import settings

def get_session_dir(session_id: str) -> Path:
    """获取 session 的根目录"""
    return settings.upload_path / "sessions" / session_id

def get_session_input_dir(session_id: str) -> Path:
    """获取 session 的输入文件目录"""
    d = get_session_dir(session_id) / "input"
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_session_output_dir(session_id: str) -> Path:
    """获取 session 的输出文件目录"""
    d = get_session_dir(session_id) / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_session_logs_dir(session_id: str) -> Path:
    """获取 session 的日志目录"""
    d = get_session_dir(session_id) / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_ppt_cache_dir(cache_key: str) -> Path:
    """获取 PPT 缓存目录"""
    d = settings.upload_path / "cache" / "ppt" / cache_key
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_rag_cache_dir(pdf_hash: str, version: str = "v3") -> Path:
    """获取 RAG 缓存目录"""
    d = settings.upload_path / "cache" / "rag" / f"{pdf_hash}-{version}"
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_papers_dir() -> Path:
    """获取 PDF 库目录"""
    d = settings.upload_path / "papers"
    d.mkdir(parents=True, exist_ok=True)
    return d

# 更多工具函数...
```

**b) `backend/app/utils/log_manager.py`**

```python
"""日志管理：写入文件 + WebSocket 推送"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from app.models import LogEvent
from app.services.connection_manager import manager as ws_manager

class LogManager:
    def __init__(self, session_id: str, log_dir: Path):
        self.session_id = session_id
        self.log_dir = log_dir
        self.log_file = log_dir / "generation.jsonl"  # JSONLines 格式
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
  
    def log(
        self,
        level: str,  # INFO, WARNING, ERROR
        stage: str,
        message: str,
        details: Optional[Dict] = None,
        duration_ms: Optional[int] = None,
    ):
        """记录日志事件并推送到前端"""
        event = LogEvent(
            level=level,
            timestamp=datetime.utcnow(),
            stage=stage,
            message=message,
            details=details,
            duration_ms=duration_ms,
        )
      
        # 写入文件
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")
      
        # WebSocket 推送
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(ws_manager.broadcast(
                self.session_id,
                {"event": "log", **event.model_dump()}
            ))
        except RuntimeError:
            # 可能不在 async 上下文中，忽略
            pass
  
    def log_info(self, stage: str, message: str, **kwargs):
        self.log("INFO", stage, message, **kwargs)
  
    def log_warning(self, stage: str, message: str, **kwargs):
        self.log("WARNING", stage, message, **kwargs)
  
    def log_error(self, stage: str, message: str, **kwargs):
        self.log("ERROR", stage, message, **kwargs)

# 导出单例
log_manager = None

def get_log_manager(session_id: str, log_dir: Path) -> LogManager:
    global log_manager
    if log_manager is None:
        log_manager = LogManager(session_id, log_dir)
    return log_manager
```

#### 1.2 改造现有文件

**c) `backend/app/models.py`** - 扩展数据模型

```python
# 新增导入
from datetime import datetime
from typing import Optional, Literal, Dict, Any, List

# 新增 GenerationStage
class GenerationStage(str, Enum):
    CACHE_CHECK = "01_cache_check"
    MARKDOWN_EXTRACT = "02_markdown"
    NOTES_GENERATION = "03_notes"
    SVG_OUTPUT = "04_svg_output"
    SVG_FINAL = "05_svg_final"
    PPTX_EXPORT = "06_pptx"
    COMPLETE = "07_complete"
  
    STAGE_DESC = {
        "01_cache_check": "检查缓存...",
        "02_markdown": "抽取 Markdown...",
        "03_notes": "生成讲稿...",
        "04_svg_output": "SVG 排版中...",
        "05_svg_final": "SVG 最终化...",
        "06_pptx": "导出 PPTX...",
        "07_complete": "完成",
    }
  
    STAGE_PCT = {
        "01_cache_check": 5,
        "02_markdown": 15,
        "03_notes": 25,
        "04_svg_output": 50,
        "05_svg_final": 75,
        "06_pptx": 95,
        "07_complete": 100,
    }

# 新增 LogEvent
class LogEvent(BaseModel):
    level: Literal["INFO", "WARNING", "ERROR"]
    timestamp: datetime
    stage: str
    message: str
    details: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = None

# 新增 PaperFile
class PaperFile(BaseModel):
    file_id: str  # hash
    filename: str
    size: int
    upload_time: datetime
    pdf_hash: str

# 改造 ProgressState
class ProgressState(BaseModel):
    stage: str = "01_cache_check"
    stage_description: str = "等待中..."
    progress_pct: int = 0
    substeps: List[str] = []

# 改造 SessionState
class SessionState(BaseModel):
    session_id: str
    session_type: Literal["single", "survey", "comparison"] = "single"
    paper_files: List[PaperFile] = []
  
    status: SessionStatus = SessionStatus.pending
    progress: ProgressState = ProgressState()
    generation_logs: List[LogEvent] = []
  
    ppt_config: Optional[PptConfig] = None
  
    outputs: Dict[str, str] = {
        "slides_pptx": "slides.pptx",
        "slides_svg_dir": "slides.svg",
        "script_md": "script.md",
        "rag_index_dir": "rag_index",
    }
  
    cache_info: Dict[str, Any] = {
        "ppt_cache_key": None,
        "rag_cache_key": None,
        "cache_hit": False,
    }
  
    timestamps: Dict[str, Optional[datetime]] = {
        "created_at": datetime.utcnow(),
        "processing_started_at": None,
        "completed_at": None,
    }
  
    error: Optional[Dict[str, Any]] = None
```

**d) `backend/app/core/config.py`** - 改造配置

```python
# 改造现有配置
class Settings(BaseSettings):
    # 原有配置...
  
    # 改造后的路径配置
    @property
    def sessions_path(self) -> Path:
        """session 根目录"""
        p = self.upload_path / "sessions"
        p.mkdir(parents=True, exist_ok=True)
        return p
  
    @property
    def cache_path(self) -> Path:
        """统一的缓存根目录"""
        p = self.upload_path / "cache"
        p.mkdir(parents=True, exist_ok=True)
        return p
  
    @property
    def papers_path(self) -> Path:
        """PDF 库目录"""
        p = self.upload_path / "papers"
        p.mkdir(parents=True, exist_ok=True)
        return p
  
    # 兼容旧配置（后续逐步迁移）
    @property
    def ppt_cache_path(self) -> Path:
        """PPT 缓存目录（兼容旧代码）"""
        return self.cache_path / "ppt"
  
    @property
    def rag_cache_path(self) -> Path:
        """RAG 缓存目录（兼容旧代码）"""
        return self.cache_path / "rag"
```

#### 1.3 初始化脚本

**e) `backend/app/core/startup.py`** - 初始化新目录结构

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化目录结构"""
    # 初始化新目录
    settings.sessions_path
    settings.cache_path
    settings.papers_path
    settings.ppt_cache_path
    settings.rag_cache_path
  
    logger.info(
        "Directory structure initialized:\n"
        "  Sessions: %s\n"
        "  Cache: %s\n"
        "  Papers: %s",
        settings.sessions_path,
        settings.cache_path,
        settings.papers_path,
    )
  
    yield
```

---

### 第二层：进度和日志系统（2-3 天）

**目标**：替换假进度为真进度，实现实时日志推送

#### 2.1 新建进度监控服务

**a) `backend/app/services/progress_tracker.py`**

```python
"""基于产物的真实进度监控"""
import asyncio
from pathlib import Path
from datetime import datetime
from app.models import GenerationStage, LogEvent
from app.services.connection_manager import manager as ws_manager

class ProgressTracker:
    """监听文件系统，推进真实进度"""
  
    def __init__(self, session_id: str, cache_dir: Path, log_manager):
        self.session_id = session_id
        self.cache_dir = cache_dir
        self.log_manager = log_manager
        self.current_stage = GenerationStage.CACHE_CHECK
        self.start_time = datetime.now()
  
    async def wait_for_stage(self, target_stage: GenerationStage, timeout_sec: int = 3600):
        """等待指定阶段完成，通过监听文件出现"""
        deadline = time.time() + timeout_sec
      
        while time.time() < deadline:
            if self._check_stage_complete(target_stage):
                duration = (datetime.now() - self.start_time).total_seconds()
                await self._broadcast_stage(target_stage, int(duration * 1000))
                return True
            await asyncio.sleep(2)  # 每 2 秒检查一次
      
        raise TimeoutError(f"Stage {target_stage.value} not completed within {timeout_sec}s")
  
    def _check_stage_complete(self, stage: GenerationStage) -> bool:
        """检查指定阶段的产物是否已生成"""
        if stage == GenerationStage.MARKDOWN_EXTRACT:
            return (self.cache_dir / "canvas.md").exists()
        elif stage == GenerationStage.NOTES_GENERATION:
            notes_dir = self.cache_dir / "notes"
            return notes_dir.exists() and len(list(notes_dir.glob("*.md"))) > 0
        elif stage == GenerationStage.SVG_OUTPUT:
            svg_output = self.cache_dir / "svg_output"
            return svg_output.exists() and len(list(svg_output.glob("*.svg"))) > 0
        elif stage == GenerationStage.SVG_FINAL:
            svg_final = self.cache_dir / "svg_final"
            return svg_final.exists() and len(list(svg_final.glob("*.svg"))) > 0
        elif stage == GenerationStage.PPTX_EXPORT:
            pptx_files = list(self.cache_dir.glob("*.pptx"))
            return len([p for p in pptx_files if not p.name.endswith("_svg.pptx")]) > 0
        return False
  
    async def _broadcast_stage(self, stage: GenerationStage, duration_ms: int):
        """广播阶段完成事件"""
        self.current_stage = stage
        self.log_manager.log_info(
            stage=stage.value,
            message=f"{stage.STAGE_DESC.get(stage.value, 'Progress')} ✓",
            duration_ms=duration_ms,
        )
      
        await ws_manager.broadcast(self.session_id, {
            "event": "progress",
            "stage": stage.value,
            "stage_description": stage.STAGE_DESC.get(stage.value),
            "progress_pct": stage.STAGE_PCT.get(stage.value, 0),
            "duration_ms": duration_ms,
        })
```

#### 2.2 改造 PPT 任务

**b) `backend/app/services/task_manager.py`** - 替换假进度

```python
# 替换现有的 _ppt_task

async def _ppt_task(session_id: str, pdf_path: str, config: PptConfig) -> str:
    from app.services.ppt_generator import compute_cache_key, run_paper_to_ppt
    from app.utils.path_utils import get_ppt_cache_dir, get_session_logs_dir
    from app.utils.log_manager import LogManager
    from app.services.progress_tracker import ProgressTracker

    # 初始化日志管理器
    log_dir = get_session_logs_dir(session_id)
    log_manager = LogManager(session_id, log_dir)
  
    # 初始化进度追踪器
    cache_key = compute_cache_key(pdf_path, config)
    cache_dir = get_ppt_cache_dir(cache_key)
    progress_tracker = ProgressTracker(session_id, cache_dir, log_manager)
  
    log_manager.log_info("01_cache_check", "检查缓存...")
  
    # 缓存检查
    existing = _find_project_dir(cache_dir)
    if existing:
        pptx_files = [p for p in existing.glob("*.pptx") if not p.name.endswith("_svg.pptx")]
        if pptx_files:
            log_manager.log_info(
                "01_cache_check",
                f"缓存命中 → {pptx_files[0].name}",
                details={"cache_key": cache_key},
            )
            session_store._sessions[session_id].cache_info["cache_hit"] = True
            session_store._sessions[session_id].cache_info["ppt_cache_key"] = cache_key
            return str(pptx_files[0])
  
    log_manager.log_info(
        "01_cache_check",
        f"缓存未中，调用 Claude CLI",
        details={"cache_key": cache_key},
    )
  
    # 运行 Claude CLI（改造后的版本支持真进度）
    try:
        project_dir = await run_paper_to_ppt(
            session_id, pdf_path, config, cache_dir, 
            log_manager=log_manager,
            progress_tracker=progress_tracker,
        )
    except Exception as e:
        log_manager.log_error(
            "06_pptx",
            f"PPT 生成失败: {str(e)}",
            details={"error": str(e)},
        )
        raise
  
    # 查找 PPTX 文件
    pptx_files = [p for p in project_dir.glob("*.pptx") if not p.name.endswith("_svg.pptx")]
    if not pptx_files:
        pptx_files = list(project_dir.glob("*.pptx"))
  
    if not pptx_files:
        raise RuntimeError("No PPTX file found after generation")
  
    log_manager.log_info(
        "07_complete",
        f"PPT 生成完成",
        details={"pptx_file": pptx_files[0].name},
        duration_ms=int((datetime.now() - progress_tracker.start_time).total_seconds() * 1000),
    )
  
    return str(pptx_files[0])
```

#### 2.3 改造 RAG 任务

**c) 类似改造 `_rag_task`**（实现日志和进度追踪）

---

### 第三层：缓存重写和统一接口（3-4 天）

**目标**：支持多文件缓存，实现统一的上传接口

#### 3.1 新建缓存管理服务

**a) `backend/app/services/cache_manager.py`**

```python
"""缓存键计算和管理"""
import hashlib
from typing import List
from app.models import PptConfig

def compute_cache_key_v2(
    paper_paths: List[str],
    session_type: str,  # "single" | "survey" | "comparison"
    config: PptConfig,
) -> str:
    """
    支持多文件的缓存键计算
  
    单篇：single_{pdf_hash}_{config_hash}
    多篇：survey_{pdf_hash1+pdf_hash2...}_{config_hash}
    """
    # 计算每个 PDF 的 hash
    paper_hashes = []
    for path in sorted(paper_paths):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        paper_hashes.append(h.hexdigest()[:16])
  
    # 合并 PDF hash（已排序，确保顺序一致）
    combined_pdf_hash = "".join(paper_hashes)
  
    # 计算配置 hash
    config_hash = hashlib.sha256(config.model_dump_json().encode()).hexdigest()[:8]
  
    # 生成最终缓存键
    cache_key = f"{session_type}_{combined_pdf_hash}_{config_hash}"
    return cache_key
```

#### 3.2 改造上传接口

**b) `backend/app/api/upload.py`** - 支持多文件上传

```python
# 改造现有的 upload_pdf 为支持多文件

@router.post("/api/upload", response_model=UploadResponse)
async def upload_pdf(
    files: List[UploadFile],  # ← 改成列表
    ppt_config: str = Form(default="{}"),
):
    """
    支持单个或多个 PDF 文件上传
  
    单篇：1 个文件 → session_type = "single"
    多篇：2+ 个文件 → session_type = "multi"（前端后续选择 survey/comparison）
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")
  
    # 验证所有文件都是 PDF
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"Only PDF files accepted: {file.filename}")
  
    # 解析配置
    config_payload = (ppt_config or "").strip()
    if not config_payload or config_payload == "{}":
        config = PptConfig()
    else:
        try:
            raw_config = json.loads(config_payload)
            config = PptConfig(**raw_config)
        except (json.JSONDecodeError, ValidationError) as e:
            raise HTTPException(status_code=400, detail=str(e))
  
    # 创建 session
    session = session_store.create_session(pdf_path="")  # 暂时留空，下面填充
  
    # 确定 session 类型
    session_type = "single" if len(files) == 1 else "multi"
    session.session_type = session_type
  
    # 保存所有文件
    from app.utils.path_utils import get_session_input_dir
    input_dir = get_session_input_dir(session.session_id)
  
    pdf_paths = []
    paper_files = []
  
    for file in files:
        dest = input_dir / file.filename
        async with aiofiles.open(dest, "wb") as f:
            while chunk := await file.read(1024 * 64):
                await f.write(chunk)
      
        pdf_paths.append(str(dest))
      
        # 创建 PaperFile 记录
        file_id = hashlib.sha256(dest.read_bytes()).hexdigest()[:16]
        paper_file = PaperFile(
            file_id=file_id,
            filename=file.filename,
            size=dest.stat().st_size,
            upload_time=datetime.utcnow(),
            pdf_hash=hashlib.sha256(dest.read_bytes()).hexdigest()[:16],
        )
        paper_files.append(paper_file)
  
    session.paper_files = paper_files
    session.ppt_config = config
  
    logger.info(
        "[UPLOAD] session=%s  type=%s  files=%d  config=%s",
        session.session_id, session_type, len(files), config.model_dump(),
    )
  
    # 启动后台任务
    asyncio.create_task(task_manager.run_tasks(session.session_id, pdf_paths, config))
  
    return UploadResponse(session_id=session.session_id, status=SessionStatus.pending)
```

#### 3.3 改造 session 查询接口

**c) `backend/app/api/sessions.py`** - 新增会话查询接口

```python
from fastapi import APIRouter, HTTPException
from app.services import session_store

router = APIRouter()

@router.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """获取 session 的完整状态"""
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
  
    return session.model_dump(mode='json')

@router.get("/api/sessions/{session_id}/logs")
async def get_session_logs(session_id: str):
    """获取 session 的完整日志"""
    from app.utils.path_utils import get_session_logs_dir
  
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
  
    logs_dir = get_session_logs_dir(session_id)
    log_file = logs_dir / "generation.jsonl"
  
    if not log_file.exists():
        return {"logs": []}
  
    logs = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                logs.append(json.loads(line))
  
    return {"logs": logs}
```

---

## 四、实现优先级和时间表

| 阶段                            | 工作                                          | 复杂度 | 依赖   | 预期收益                                 |
| ------------------------------- | --------------------------------------------- | ------ | ------ | ---------------------------------------- |
| **Day 1（第一层基础）**   | models.py + path_utils.py + log_manager.py    | ⭐⭐   | 无     | 后续所有工作的基础，目录结构设定         |
| **Day 2（第二层真进度）** | progress_tracker.py + task_manager 改造       | ⭐⭐⭐ | 第一层 | 用户看到真实进度和日志，可以快速定位问题 |
| **Day 3（第二层错误）**   | 改进错误处理和推送                            | ⭐     | 第一层 | 失败信息完整可见                         |
| **Day 4（第三层缓存）**   | cache_manager.py + upload 改造 + sessions API | ⭐⭐   | 前三天 | 多文件支持 + 统一接口                    |

---

## 五、实施建议

### 5.1 立即开始（第一层）

```bash
# 1. 创建新文件
touch backend/app/utils/__init__.py
touch backend/app/utils/path_utils.py
touch backend/app/utils/log_manager.py

# 2. 改造现有文件
# - backend/app/models.py    （扩展 SessionState, 新增 LogEvent 等）
# - backend/app/core/config.py  （改造路径配置）
# - backend/app/core/startup.py （初始化新目录）

# 3. 测试
pytest backend/tests/test_models.py
pytest backend/tests/test_path_utils.py
```

### 5.2 逐步推进

- **第一层完成后**，`uploads/` 目录结构立刻变成新的，所有 session 的产物集中管理
- **第二层完成后**，前端能看到真实进度（不再是假的 85%）和实时日志
- **第三层完成后**，多篇上传和统一接口就能接上

### 5.3 兼容性处理

- 改造不会立刻删除旧的 `ppt_cache/`、`rag_cache/` 等目录
- 新代码自动使用新路径，旧缓存保留以防需要回滚
- 逐步更新调用方，确保没有代码还在用 `settings.ppt_cache_path`

### 5.4 测试覆盖

```python
# 关键测试用例
def test_path_utils():
    """确保路径工具正确生成目录"""
  
def test_log_manager():
    """确保日志正确写入文件 + 推送 WebSocket"""
  
def test_progress_tracker():
    """确保能正确监听产物并推进阶段"""
  
def test_cache_key_v2():
    """确保多文件缓存键計算正確、可复现"""
  
def test_upload_multi_files():
    """确保支持多文件上传"""
```

---

## 六、成功指标

完成后的效果应该是：

- ✅ **路径干净统一**：所有 session 的产物都在 `uploads/sessions/{session_id}/` 下，清晰可见
- ✅ **真实进度**：前端显示 5% → 15% → 25% → ... → 100%，而不是假的 85%
- ✅ **用户看得见日志**：前端有日志面板，能看到 Claude CLI 的每一步动作
- ✅ **失败快速明确**：出错时，前端显示完整的错误堆栈和日志上下文，不再需要猜测
- ✅ **缓存可复用**：同配置二次运行命中同一个 PPT cache，节省时间和额度
- ✅ **单多篇统一**：单篇和多篇走同一套接口和数据模型，后续扩展不会再割裂
