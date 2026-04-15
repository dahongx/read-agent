## 1. Backend: Config & Cache
- [x] 1.1 `config.py`: DEV_MODE 默认 False，新增 PPT_CACHE_DIR、SKILL_DIR
- [x] 1.2 `models.py`: 新增 PptConfig 模型，SessionState 新增 ppt_config 字段
- [x] 1.3 `upload.py`: 接收 ppt_config JSON 字段，存入 session，传给 run_tasks

## 2. Backend: Real PPT Generation
- [x] 2.1 新建 `services/ppt_generator.py`：compute_cache_key、run_skill_script
- [x] 2.2 `ppt_generator.py`：generate_design_spec — Strategist prompt → design_spec.md
- [x] 2.3 `ppt_generator.py`：generate_slides — 逐页 LLM 生成 SVG + 演讲稿
- [x] 2.4 `task_manager.py`：_ppt_task 替换 stub，完整流程 + 缓存命中
- [x] 2.5 `task_manager.py`：删除 DEV_MODE 分支

## 3. Backend: Slides & Notes Serving
- [x] 3.1 `sessions.py`：_get_slides_dir 只读 svg_final/，删除 DEV_MODE 分支
- [x] 3.2 `script.py`：删除 fixture notes 分支，读 ppt_path.parent/notes/

## 4. Frontend: Upload Page Config Form
- [x] 4.1 `UploadPage.tsx`：新增配置表单（模板/页数/语言/风格/受众）
- [x] 4.2 模板选择展示名称和简介（7个模板硬编码）
- [x] 4.3 上传时 ppt_config 随 FormData 提交
- [x] 4.4 `ProgressPage.tsx`：进度已动态显示后端广播的 step 字符串，无需改动

## 5. Frontend: Remove DEV_MODE Dependencies
- [x] 5.1 `PptViewerPage.tsx`：确认无 DEV_MODE 硬编码
- [x] 5.2 `startup.py`：删除 fixture 校验，只做目录初始化

## 6. Documentation
- [x] 6.1 `.env.example`：更新，新增 SKILL_DIR、PPT_CACHE_DIR
- [x] 6.2 `start_prod.bat`：更新注释说明完整流程
