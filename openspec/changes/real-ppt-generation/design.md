## Architecture

### 现有 skill 流程（已验证）

```
PDF
 └─ pdf_to_md.py              → sources/*.md
 └─ project_manager.py init   → projects/{name}/
 └─ Strategist (LLM)          → design_spec.md  ← 需要用户配置输入
 └─ Executor (LLM, 逐页)      → svg_output/*.svg + notes/total.md
 └─ finalize_svg.py           → svg_final/*.svg
 └─ total_md_split.py         → notes/{01..N}.md
 └─ svg_to_pptx.py            → *.pptx
```

### Web Agent 集成方案

**两个 BLOCKING 点前移到前端**：
- 模板选择 → 上传页面下拉选择
- 八项确认 → 上传页面表单（带推荐默认值）

用户点击"上传并生成"后，后端拿到 PDF + 配置，全自动跑完整流程。

### 缓存策略

```
cache_key = sha256(pdf_content)[:16] + "-" + sha256(config_json)[:8]
cache_dir = uploads/ppt_cache/{cache_key}/
```

命中条件：`cache_dir/svg_final/` 存在且非空。

命中时：直接返回已有项目路径，跳过所有 LLM 调用。

### 配置项（前端表单）

| 字段 | 类型 | 选项 | 默认值 |
|------|------|------|--------|
| template | select | academic_defense / anthropic / google_style / mckinsey / exhibit / 无模板 | academic_defense |
| page_count | select | 10页 / 12页 / 15页 / 20页 | 12页 |
| language | select | 中文 / 英文 | 中文 |
| style | select | 学术汇报 / 商务简报 / 技术分享 | 学术汇报 |
| audience | select | 高校师生 / 企业团队 / 通用 | 高校师生 |

八项确认中其余三项（色彩/图标/排版）由 Strategist 根据模板自动决定，不暴露给用户。

### 后端任务流程

```python
async def _ppt_task(session_id, pdf_path, config):
    # 1. 计算缓存 key
    cache_key = compute_cache_key(pdf_path, config)
    cache_dir = upload_path / "ppt_cache" / cache_key
    
    # 2. 命中缓存 → 直接返回
    if (cache_dir / "svg_final").exists():
        return str(cache_dir)
    
    # 3. PDF → Markdown
    run_script("pdf_to_md.py", pdf_path, output=cache_dir/"sources")
    
    # 4. 初始化项目
    run_script("project_manager.py", "init", cache_dir, format="ppt169")
    
    # 5. LLM Strategist → design_spec.md（传入配置参数）
    await generate_design_spec(cache_dir, config)
    
    # 6. LLM Executor → svg_output/ + notes/total.md（逐页，进度广播）
    await generate_slides(session_id, cache_dir, config)
    
    # 7. 后处理
    run_script("finalize_svg.py", cache_dir)
    run_script("total_md_split.py", cache_dir)
    run_script("svg_to_pptx.py", cache_dir, "-s", "final")
    
    return str(cache_dir)
```

### 前端页面变更

**UploadPage**：
- 新增配置表单区域（模板选择 + 4个下拉）
- 上传按钮文案改为"上传并生成 PPT"
- 配置项有推荐默认值，用户可直接点击上传

**ProgressPage**：
- PPT 生成进度细化：解析PDF / 生成大纲 / 生成第N页(共M页) / 后处理
- 命中缓存时显示"使用已有 PPT（配置未变更）"

**PptViewerPage**：
- 去掉 DEV_MODE 相关逻辑
- slides 来源统一为 `/api/sessions/{id}/slides`（已有接口）

### 去掉 DEV_MODE

- `config.py`：`DEV_MODE` 默认改为 `False`
- `task_manager.py`：删除 DEV_MODE 分支，只保留真实流程
- `sessions.py`：`_get_slides_dir` 只读 `ppt_path.parent/svg_final/`
- `script.py`：删除 fixture notes 分支，只用 `notes/` 目录

## Decisions

**Decision 1: 用 subprocess 调用 skill scripts，不重写逻辑**
skill scripts（pdf_to_md.py、finalize_svg.py 等）已经过充分测试，直接调用比重写更可靠。

**Decision 2: Strategist/Executor 用 LLM API 直接调用，不走 Claude Code CLI**
web agent 后端用 GLM-4-Flash，Strategist 生成 design_spec.md 和 Executor 生成 SVG 都通过 API 调用，不依赖 Claude Code 交互式环境。

**Decision 3: 缓存粒度为 PDF内容哈希 + 配置哈希**
同一 PDF 不同配置生成不同 PPT，同一 PDF 相同配置复用缓存。

**Decision 4: 进度广播细化到页级别**
Executor 逐页生成 SVG，每生成一页广播一次进度，前端显示"生成第3页/共12页"。
