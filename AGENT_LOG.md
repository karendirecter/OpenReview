# AGENT_LOG.md

## 2026-05-29 Task 1 启动

- **时间戳与 task 编号**：2026-05-29 / Task 1
- **触发的 Superpowers 技能**：`using-superpowers`、`writing-plans`、`using-git-worktrees`
- **关键 prompt / context 配置**：正式进入 `PLAN.md` Task 1；遵循 `AI4SE_Final_Project0518.md` 第 4.6–4.8 节；每个模块一个 worktree、对应一个 PR；不确定处先询问用户。
- **工作区 / 分支**：`D:\course\2026_spring\AI4SE\project\.claude\worktrees\task1-bootstrap-settings` / `worktree-task1-bootstrap-settings`
- **当前状态**：已创建 Task 1 独立 worktree，准备按 TDD 执行 bootstrap project skeleton and settings。
- **人工干预**：用户明确要求按模块划分 worktree、严格走 Superpowers 流程、自动维护 `AGENT_LOG.md`。
- **学到的教训**：正式实现开始前，应先核对课程 4.6–4.8 约束并在日志中固化执行边界，避免后续 task 漂移。

## 2026-05-29 Task 1 TDD 进展（Step 1-4）

- **时间戳与 task 编号**：2026-05-29 / Task 1
- **触发的 Superpowers 技能**：`test-driven-development`
- **关键 prompt / context 配置**：严格按 `PLAN.md` Task 1 的红→绿流程，只为 `Settings` 与项目骨架补最小实现。
- **subagent 输出的关键片段或链接**：暂无 commit；已完成红灯验证命令 `uv run pytest tests/unit/test_config.py::test_settings_load_required_review_defaults -v`，先报 `ModuleNotFoundError: No module named 'app'`，随后在最小实现后转为通过。
- **人工干预**：无额外代码改写；仅按课程要求同步勾选 `PLAN.md` 中已完成的 Step 1-4。
- **学到的教训**：在空仓启动阶段，红灯可以是缺模块错误，只要失败原因确实对应“功能尚不存在”，即可作为有效 TDD 起点。

## 2026-05-29 Task 2 启动与 TDD 进展（Step 1-4）

- **时间戳与 task 编号**：2026-05-29 / Task 2
- **触发的 Superpowers 技能**：`using-git-worktrees`、`test-driven-development`
- **关键 prompt / context 配置**：新建 `task2-review-models` worktree；为保持任务独立又继承已完成基础，先 cherry-pick Task 1 提交 `bb23ebf` 再进入 Task 2 的 TDD。
- **工作区 / 分支**：`D:\course\2026_spring\AI4SE\project\.claude\worktrees\task2-review-models` / `worktree-task2-review-models`
- **subagent 输出的关键片段或链接**：Task 2 红灯验证命令 `uv run pytest tests/unit/test_models.py::test_review_task_binds_review_commit_sha -v` 报 `ModuleNotFoundError: No module named 'app.review'`；补齐 `app/review/__init__.py` 与 `app/review/models.py` 后，`tests/unit/test_config.py` 与 `tests/unit/test_models.py` 共 2 项通过。
- **人工干预**：无额外人工改写；同步勾选 `PLAN.md` 中 Task 2 Step 1-4。
- **学到的教训**：后续模块 worktree 若依赖已完成基础提交，应显式记录 cherry-pick 的来源提交，保证 AGENT_LOG 可追踪模块间承接关系。

## 2026-05-29 Task 3 基线修正

- **时间戳与 task 编号**：2026-05-29 / Task 3
- **触发的 Superpowers 技能**：`using-git-worktrees`
- **关键 prompt / context 配置**：Task 3 初次继承基线时缺少 Task 1 应用骨架，导致 `tests/unit/test_diff_parser.py` 红灯停在 `ModuleNotFoundError: No module named 'app'`；已回滚错误继承路径，并基于 `main-agent` 重新顺序 cherry-pick `bb23ebf`、`8e429ad`、`0351238` 重建 Task 3 基线。
- **工作区 / 分支**：`D:\course\2026_spring\AI4SE\project\.claude\worktrees\task3-diff-position-mapping` / `worktree-task3-diff-position-mapping`
- **人工干预**：用户要求继续推进 Task 3，因此先修正模块基线，再继续按 TDD 实施 diff parser。
- **学到的教训**：后续新模块 worktree 必须从 `main-agent` 干净基线开始，再按依赖顺序 cherry-pick已完成模块提交，不能只挑计划更新提交，否则会丢失运行所需骨架文件。

## 2026-05-29 Task 3 TDD 进展（Step 1-4）

- **时间戳与 task 编号**：2026-05-29 / Task 3
- **触发的 Superpowers 技能**：`test-driven-development`
- **关键 prompt / context 配置**：对照 `SPEC.md` 中“解析 diff，建立文件、hunk、绝对行号与可回贴位置之间的映射”要求，只实现 Task 3 单 hunk starter 版本，不提前扩展到多 hunk orchestration。
- **subagent 输出的关键片段或链接**：红灯验证命令 `uv run pytest tests/unit/test_diff_parser.py::test_build_position_mapping_returns_added_line_positions -v` 最终稳定报 `ModuleNotFoundError: No module named 'app.review.diff_parser'`；补齐 `app/review/diff_parser.py` 后，`tests/unit/test_config.py`、`tests/unit/test_models.py`、`tests/unit/test_diff_parser.py` 共 3 项通过。
- **人工干预**：无额外人工改写；同步勾选 `PLAN.md` 中 Task 3 Step 1-4。
- **学到的教训**：当红灯先暴露的是基线缺口而不是目标函数缺失时，应先修复可运行基线，再重新获得针对目标能力的有效红灯。

## 2026-05-29 Task 4 TDD 进展（Step 1-4）

- **时间戳与 task 编号**：2026-05-29 / Task 4
- **触发的 Superpowers 技能**：`test-driven-development`
- **关键 prompt / context 配置**：继续在 Task 3 的同模块 worktree 中完成上下文加载；对照 `SPEC.md` 中“必须包含当前 diff hunk，必要时允许读取完整文件”实现最小版 `select_review_context`。
- **subagent 输出的关键片段或链接**：红灯验证命令 `uv run pytest tests/unit/test_context_loader.py::test_select_review_context_falls_back_to_full_file_when_needed -v` 稳定报 `ModuleNotFoundError: No module named 'app.review.context_loader'`；补齐 `app/review/context_loader.py` 后，`tests/unit/test_config.py`、`tests/unit/test_models.py`、`tests/unit/test_diff_parser.py`、`tests/unit/test_context_loader.py` 共 4 项通过。
- **人工干预**：用户明确确认 Task 4 继续留在 Task 3 的同一 worktree 中完成；Task 5 再开新 worktree。
- **学到的教训**：同一模块内紧邻任务共享同一个 worktree 更符合“一个模块一个 worktree”的边界，也减少重复继承基线的成本。

## 2026-05-29 Task 5 启动与 TDD 进展（Step 1-4）

- **时间戳与 task 编号**：2026-05-29 / Task 5
- **触发的 Superpowers 技能**：`using-git-worktrees`、`test-driven-development`
- **关键 prompt / context 配置**：在用户完成 Task3-4 的 PR merge 后，以最新远程 `main-agent` 作为权威基线创建 `task5-schema-validation` worktree；对照 `SPEC.md` 中 JSON Schema、allowed file、正整数行号与恶意输入防御要求，实现最小版 LLM payload 校验。
- **工作区 / 分支**：`D:\course\2026_spring\AI4SE\project\.claude\worktrees\task5-schema-validation` / `worktree-task5-schema-validation`
- **subagent 输出的关键片段或链接**：红灯验证命令 `uv run pytest tests/unit/test_schema_validation.py::test_validate_llm_payload_rejects_unknown_file_path -v` 稳定报 `ModuleNotFoundError: No module named 'app.review.schema'`；补齐 `app/review/schema.py` 后，`tests/unit/test_config.py`、`tests/unit/test_models.py`、`tests/unit/test_diff_parser.py`、`tests/unit/test_context_loader.py`、`tests/unit/test_schema_validation.py` 共 5 项通过。
- **人工干预**：用户明确说明后续 `PLAN.md` 由其自行维护，因此从 Task 5 起只更新 `AGENT_LOG.md`，不再改写 `PLAN.md`。
- **学到的教训**：当用户收回 `PLAN.md` 维护权后，进度与偏差说明都必须集中沉淀到 `AGENT_LOG.md`，否则过程证据会断档。

## 2026-05-29 Task 6 TDD 进展（Step 1-4）

- **时间戳与 task 编号**：2026-05-29 / Task 6
- **触发的 Superpowers 技能**：`test-driven-development`
- **关键 prompt / context 配置**：继续在 `task5-schema-validation` worktree 中完善基础接口；对照 `SPEC.md` 中结果渲染层的 summary / inline / suggestion 语义，先实现最小版 `render_inline_comment`，确保 suggestion 代码块按 GitHub 语法包裹。
- **subagent 输出的关键片段或链接**：红灯验证命令 `uv run pytest tests/unit/test_rendering.py::test_render_inline_comment_wraps_suggestion_block -v` 稳定报 `ModuleNotFoundError: No module named 'app.review.rendering'`；补齐 `app/review/rendering.py` 后，`tests/unit/test_config.py`、`tests/unit/test_models.py`、`tests/unit/test_diff_parser.py`、`tests/unit/test_context_loader.py`、`tests/unit/test_schema_validation.py`、`tests/unit/test_rendering.py` 共 6 项通过。
- **人工干预**：无额外人工改写；延续用户关于“Task5-Task8 先共用同一 worktree”的边界设定继续推进。
- **学到的教训**：在基础接口阶段，先用单一明确断言把 suggestion 渲染 contract 钉住，比一开始就扩展 summary/render_mode 全量行为更稳妥。

## 2026-05-29 Task 7 TDD 进展（Step 1-4）

- **时间戳与 task 编号**：2026-05-29 / Task 7
- **触发的 Superpowers 技能**：`test-driven-development`
- **关键 prompt / context 配置**：继续在同一基础接口 worktree 中补齐规则层最小入口；先实现可插拔 analyzer protocol 与 registry，保证后续通用 diff 规则和 Python 规则都能通过同一 `run_analyzers` 收敛输出 `IssueHit`。
- **subagent 输出的关键片段或链接**：红灯验证命令 `uv run pytest tests/unit/test_rules_registry.py::test_run_analyzers_collects_hits_from_all_plugins -v` 稳定报 `ModuleNotFoundError: No module named 'app.rules'`；补齐 `app/rules/base.py` 与 `app/rules/registry.py` 后，`tests/unit/test_config.py`、`tests/unit/test_models.py`、`tests/unit/test_diff_parser.py`、`tests/unit/test_context_loader.py`、`tests/unit/test_schema_validation.py`、`tests/unit/test_rendering.py`、`tests/unit/test_rules_registry.py` 共 7 项通过。
- **人工干预**：无额外人工改写；继续遵循“Task5-Task8 共用 task5 worktree”的用户边界。
- **学到的教训**：先把规则层的聚合接口固定下来，再往里面塞具体 analyzer，会比先写具体规则再回头抽象 registry 更省返工。

## 2026-05-29 Task 8 TDD 进展（Step 1-4）

- **时间戳与 task 编号**：2026-05-29 / Task 8
- **触发的 Superpowers 技能**：`test-driven-development`
- **关键 prompt / context 配置**：继续在基础接口 worktree 中补齐通用 diff 规则；对照 `SPEC.md` 中“通用 Diff 审查”与 `IssueHit` 输出约定，先用 `except Exception: pass` 这一类高风险吞异常模式钉住最小启发式 analyzer。
- **subagent 输出的关键片段或链接**：红灯验证命令 `uv run pytest tests/unit/test_rules_registry.py::test_general_diff_analyzer_flags_broad_exception_pass -v` 稳定报 `ModuleNotFoundError: No module named 'app.rules.diff_general'`；补齐 `app/rules/diff_general.py` 后，`tests/unit/test_config.py`、`tests/unit/test_models.py`、`tests/unit/test_diff_parser.py`、`tests/unit/test_context_loader.py`、`tests/unit/test_schema_validation.py`、`tests/unit/test_rendering.py`、`tests/unit/test_rules_registry.py` 共 8 项通过。
- **人工干预**：无额外人工改写；继续沿用用户确认的 Task5-Task8 共享 worktree 边界。
- **学到的教训**：先用一个高置信、可解释的通用 diff 模式建立 analyzer 结构，比一开始追求覆盖很多弱规则更利于后续扩展和调试。

## 2026-05-29 Task 9 启动与 TDD 进展（Step 1-4）

- **时间戳与 task 编号**：2026-05-29 / Task 9
- **触发的 Superpowers 技能**：`using-git-worktrees`、`test-driven-development`
- **关键 prompt / context 配置**：在用户完成 Task5-8 的 PR merge 后，基于最新 `main-agent` 新建 `task9-python-ast-analyzer` worktree；对照 `SPEC.md` 中 Python 深度分析要求，先实现 `async def` 中 `time.sleep` 的阻塞 I/O 检测，作为 AST analyzer 的最小切入点。
- **工作区 / 分支**：`D:\course\2026_spring\AI4SE\project\.claude\worktrees\task9-python-ast-analyzer` / `worktree-task9-python-ast-analyzer`
- **subagent 输出的关键片段或链接**：红灯验证命令 `uv run pytest tests/unit/test_rules_python_ast.py::test_python_ast_analyzer_flags_blocking_sleep_in_async_function -v` 稳定报 `ModuleNotFoundError: No module named 'app.rules.python_ast'`；补齐 `app/rules/python_ast.py` 后，`tests/unit/test_config.py`、`tests/unit/test_models.py`、`tests/unit/test_diff_parser.py`、`tests/unit/test_context_loader.py`、`tests/unit/test_schema_validation.py`、`tests/unit/test_rendering.py`、`tests/unit/test_rules_registry.py`、`tests/unit/test_rules_python_ast.py` 共 9 项通过。
- **人工干预**：用户明确要求 Task9 进入新的独立 worktree；如与旧模块有冲突，以已 merge 的远程 `main-agent` 为准。
- **学到的教训**：在 Python AST 规则层，先用单一高置信的阻塞调用模式验证 AST 遍历框架，再逐步扩展 None access 与 await 相关规则，会更容易定位误报来源。

## 2026-05-29 Task 10 TDD 进展（Step 1-4）

- **时间戳与 task 编号**：2026-05-29 / Task 10
- **触发的 Superpowers 技能**：`test-driven-development`
- **关键 prompt / context 配置**：继续在 Task9 的同模块 worktree 中补齐 Python 规则的补充来源；对照 `SPEC.md` 中 AST + Semgrep 组合策略，实现最小版 Semgrep JSON 结果到 `IssueHit` 的适配层。
- **subagent 输出的关键片段或链接**：红灯验证命令 `uv run pytest tests/unit/test_rules_semgrep_runner.py::test_parse_semgrep_output_returns_issue_hits -v` 稳定报 `ModuleNotFoundError: No module named 'app.rules.semgrep_runner'`；补齐 `app/rules/semgrep_runner.py` 后，`tests/unit/test_config.py`、`tests/unit/test_models.py`、`tests/unit/test_diff_parser.py`、`tests/unit/test_context_loader.py`、`tests/unit/test_schema_validation.py`、`tests/unit/test_rendering.py`、`tests/unit/test_rules_registry.py`、`tests/unit/test_rules_python_ast.py`、`tests/unit/test_rules_semgrep_runner.py` 共 10 项通过。
- **人工干预**：用户明确要求 Task10 继续留在 Task9 的当前分支中完成。
- **学到的教训**：把 Semgrep 适配层先收敛成纯 payload → `IssueHit` 转换函数，可以在不引入真实子进程调用的前提下先把结构和数据契约稳定住。

## 2026-05-29 Task 11 启动与 TDD 进展（Step 1-4）

- **时间戳与 task 编号**：2026-05-29 / Task 11
- **触发的 Superpowers 技能**：`using-git-worktrees`、`test-driven-development`
- **关键 prompt / context 配置**：在用户完成 Task9-10 的 PR merge 且确认 `PLAN.md` 已更新到 `main-agent` 后，基于最新主线新建 `task11-llm-client` worktree；对照 `SPEC.md` 中 LLM client 抽象与 OpenAI-compatible DeepSeek 配置要求，实现最小版 `LLMClient` protocol 与请求构造函数。
- **工作区 / 分支**：`D:\course\2026_spring\AI4SE\project\.claude\worktrees\task11-llm-client` / `worktree-task11-llm-client`
- **subagent 输出的关键片段或链接**：红灯验证命令 `uv run pytest tests/unit/test_llm_client.py::test_build_review_request_targets_configured_model -v` 稳定报 `ModuleNotFoundError: No module named 'app.llm'`；补齐 `app/llm/base.py` 与 `app/llm/openai_compatible.py` 后，`tests/unit/test_config.py`、`tests/unit/test_models.py`、`tests/unit/test_diff_parser.py`、`tests/unit/test_context_loader.py`、`tests/unit/test_schema_validation.py`、`tests/unit/test_rendering.py`、`tests/unit/test_rules_registry.py`、`tests/unit/test_rules_python_ast.py`、`tests/unit/test_rules_semgrep_runner.py`、`tests/unit/test_llm_client.py` 共 11 项通过。
- **人工干预**：用户明确要求新开 Task11 分支，并强调要继承已更新到 `main-agent` 的 `PLAN.md`；同时继续保持 `PLAN.md` 由用户自行维护。
- **学到的教训**：当计划文档由用户手工维护时，新的 worktree 不应再从旧分支继承 PLAN 变更，而必须直接从最新主线读取，否则很容易在接口约束上读到过期内容。

## 2026-05-29 Task 12 TDD 进展（Step 1-4）

- **时间戳与 task 编号**：2026-05-29 / Task 12
- **触发的 Superpowers 技能**：`test-driven-development`
- **关键 prompt / context 配置**：继续在 Task11 的同模块 worktree 中补齐 Prompt 构造能力；对照 `SPEC.md` 中 commit SHA 注入、diff 上下文、候选问题摘要与严格 JSON 契约要求，实现最小版 `build_review_prompt`。
- **subagent 输出的关键片段或链接**：红灯验证命令 `uv run pytest tests/unit/test_llm_client.py::test_build_review_prompt_includes_commit_sha_and_json_contract -v` 稳定报 `ModuleNotFoundError: No module named 'app.prompts'`；初版 prompt 因未包含带引号的 `"findings"` 契约字符串导致测试失败，修正 `app/prompts/review_prompt.py` 后，`tests/unit/test_config.py`、`tests/unit/test_models.py`、`tests/unit/test_diff_parser.py`、`tests/unit/test_context_loader.py`、`tests/unit/test_schema_validation.py`、`tests/unit/test_rendering.py`、`tests/unit/test_rules_registry.py`、`tests/unit/test_rules_python_ast.py`、`tests/unit/test_rules_semgrep_runner.py`、`tests/unit/test_llm_client.py` 共 12 项通过。
- **人工干预**：无额外人工改写；继续遵循用户要求，仅更新 `AGENT_LOG.md`，不回写 `PLAN.md`。
- **学到的教训**：Prompt builder 的测试应该直接钉住关键契约字面量（如 `"findings"`），这样能更早发现“语义相近但不满足解析约束”的提示词缺陷。

## 2026-05-29 Task 13 TDD 进展（Step 1-4）

- **时间戳与 task 编号**：2026-05-29 / Task 13
- **触发的 Superpowers 技能**：`test-driven-development`
- **关键 prompt / context 配置**：继续在 Task11 的同模块 worktree 中实现编排层最小护栏；对照 `SPEC.md` 中“head_sha 漂移则任务过期”的约束，先实现 `ensure_not_stale` 作为 Stage 1/Stage 2 orchestrator 的第一条硬性守卫。
- **subagent 输出的关键片段或链接**：红灯验证命令 `uv run pytest tests/unit/test_orchestrator.py::test_ensure_not_stale_raises_when_head_sha_changes -v` 稳定报 `ModuleNotFoundError: No module named 'app.review.orchestrator'`；补齐 `app/review/orchestrator.py` 后，`tests/unit/test_config.py`、`tests/unit/test_models.py`、`tests/unit/test_diff_parser.py`、`tests/unit/test_context_loader.py`、`tests/unit/test_schema_validation.py`、`tests/unit/test_rendering.py`、`tests/unit/test_rules_registry.py`、`tests/unit/test_rules_python_ast.py`、`tests/unit/test_rules_semgrep_runner.py`、`tests/unit/test_llm_client.py`、`tests/unit/test_orchestrator.py` 共 13 项通过。
- **人工干预**：无额外人工改写；继续沿用用户要求，在同一 Task11 分支中串行推进相关内核模块。
- **学到的教训**：先把 stale commit guard 独立成一个可测试函数，比一开始就把完整 orchestrator 流程揉进一个大对象更容易锁定漂移控制语义。
## 2026-05-29 Task 14 TDD 进展（Step 1-4）

- **时间戳与 task 编号**：2026-05-29 / Task 14
- **触发的 Superpowers 技能**：`test-driven-development`
- **关键 prompt / context 配置**：继续在同一个 `task11-llm-client` worktree 内推进，按 `SPEC.md` 对 LLM 结构化输出的约束收紧 `validate_llm_payload`，确保 `line_number` 为正整数，且 `end_line_number` 不能早于 `line_number`。
- **subagent 输出的关键片段或链接**：新增 `tests/unit/test_robustness_llm_payloads.py`，覆盖负行号与反向区间两类恶意 payload；更新 `app/review/schema.py`，对非法 finding 直接丢弃。`uv run pytest tests/unit/test_robustness_llm_payloads.py -v` 通过，共 2 项测试。
- **人工干预**：无；遵循用户要求，仅同步 `AGENT_LOG.md`，不回写 `PLAN.md`。
- **学到的教训**：当鲁棒性任务已被前序守卫部分覆盖时，应继续补相邻不变量的回归测试，而不是为了“制造改动”做空转实现。

## 2026-05-29 Task 15 TDD 进展（Step 1-4）

- **时间戳与 task 编号**：2026-05-29 / Task 15
- **触发的 Superpowers 技能**：`test-driven-development`
- **关键 prompt / context 配置**：按 `SPEC.md` 实现最小 GitHub webhook 触发路径，只有 PR 上下文中的 `issue_comment` 且评论正文精确为 `/review` 时才进入评审流程。
- **subagent 输出的关键片段或链接**：新增 `app/github/models.py`、`app/github/webhook.py`，并在 `app/main.py` 中加入 `POST /webhooks/github`；新增 `tests/integration/test_github_webhook_route.py`，同时覆盖 ignored 与 accepted 两种分支。`uv run pytest tests/integration/test_github_webhook_route.py -v` 通过，共 2 项测试。
- **人工干预**：无。
- **学到的教训**：对 webhook 入口同时保留正向触发与反向拒绝测试，能最快防住“所有 PR 评论都误触发评审”的回归。

## 2026-05-29 Task 16 TDD 进展（Step 1-4）

- **时间戳与 task 编号**：2026-05-29 / Task 16
- **触发的 Superpowers 技能**：`test-driven-development`
- **关键 prompt / context 配置**：补充本地入口 helper，使评审内核可以脱离 GitHub 单独构造 `ReviewTask`，满足 `SPEC.md` 中“webhook / 本地脚本 / CLI 共享统一业务入口”的要求。
- **subagent 输出的关键片段或链接**：新增 `scripts/run_local_review.py` 中的 `build_local_task(...)`，并新增 `tests/integration/test_review_pipeline.py`。`uv run pytest tests/integration/test_review_pipeline.py -v` 通过。
- **人工干预**：无。
- **学到的教训**：先固定一个最小本地任务构造器，比在每个后续流程测试里重复伪造 webhook payload 更稳、更省返工。

## 2026-05-29 Task 17 容器化骨架

- **时间戳与 task 编号**：2026-05-29 / Task 17
- **触发的 Superpowers 技能**：无
- **关键 prompt / context 配置**：补齐课程要求的容器化交付骨架：`Dockerfile`、`docker-compose.yml` 与 `.env.example`，并明确运行时环境变量约束。
- **subagent 输出的关键片段或链接**：基于 `python:3.11-slim` 创建 Dockerfile，使用 `uv sync --frozen --no-dev` 安装运行时依赖，并通过 `uvicorn app.main:app` 启动 FastAPI；补充 `docker-compose.yml` 暴露 `8000` 端口。
- **验证结果**：`uv run pytest -q` 通过，结果为 `18 passed in 0.20s`。本地 `docker --version` 可用；`docker build -t github-pr-auto-review .` 已尝试执行，但在解析 `python:3.11-slim` 时被外部镜像仓库连通性阻塞，因此当前只能确认容器文件已就位，尚未在此环境完成镜像构建验收。
- **人工干预**：暂无；若后续环境可访问 Docker Hub，应在该 worktree 重新执行构建以完成 Task 17 验证闭环。
- **学到的教训**：容器化任务要明确区分“项目侧已准备好”与“环境侧网络/仓库受限”，避免把外部依赖阻塞误记成应用缺陷。


## 2026-05-29 GitHub App 与容器环境实连验证

- **时间戳**：2026-05-29
- **关键动作**：根据用户已填写的 `.env`，补充 `github_private_key` 的 `\\n -> \n` 归一化逻辑，保证 `.env` 中单行 PEM 私钥可被 PyGithub 正常解析。
- **代码修正**：更新 `app/config.py`，并在 `tests/unit/test_config.py` 增加私钥换行归一化测试；`uv run pytest tests/unit/test_config.py -q` 通过。
- **GitHub App 验证结果**：使用 `GITHUB_APP_ID`、`GITHUB_PRIVATE_KEY` 与 `GITHUB_INSTALLATION_ID` 成功访问 GitHub API，当前 app 可见 1 个 installation，目标 installation 为 `136482236`，账号 `karendirecter`，可访问仓库 `karendirecter/notion-lite`。
- **容器验证结果**：`docker build -t github-pr-auto-review .` 成功；容器 `github-pr-auto-review` 已成功启动并通过 `/health` 检查。
- **Webhook 验证结果**：本地 `POST /webhooks/github` 在携带 `X-GitHub-Event: issue_comment` 且评论正文为 `/review` 时返回 `{\"status\":\"accepted\"}`；未带该事件头时返回 `{\"status\":\"ignored\"}`，符合当前实现。
- **注意事项**：日志中发现曾有请求打到 `/webhook` 与 `/` 并返回 404，因此 GitHub App 的 webhook URL 必须明确配置为 `/webhooks/github`。

## 2026-05-29 评审业务流补全与真实回贴验证

- **时间戳**：2026-05-29
- **关键动作**：对照 `SPEC.md` 复查后，确认项目最大缺口不是“连通性”，而是 webhook 进入后没有真正拉取 PR、执行分析并回贴结果。为此新增 `app/github/service.py`，把 GitHub PR 拉取、`ReviewTask` 构造、Stage 1/Stage 2 编排调用与评论发布接通。
- **代码补全**：
  - `app/main.py`：新增 `X-Hub-Signature-256` 校验、JSON body 解码与后台任务调度。
  - `app/github/webhook.py`：新增 HMAC-SHA256 webhook 签名校验。
  - `app/github/models.py`：补齐 repository / issue / comment 等真实 webhook 字段。
  - `app/review/orchestrator.py`：从单一 `ensure_not_stale` 扩展为可运行的 `review_pull_request`、Stage 1 扫描、Stage 2 LLM 复核降级与 summary 汇总。
  - `app/review/rendering.py`：补齐 summary comment 与 inline comment 列表渲染。
  - `app/llm/openai_compatible.py`：补齐真实 OpenAI-compatible client，允许 Stage 2 调用结构化模型输出。
  - `app/rules/diff_general.py`：修正 broad exception 规则的行号定位，避免 inline comment 总落在错误位置。
- **测试补充**：
  - 新增 `tests/integration/test_github_review_service.py`
  - 更新 `tests/integration/test_github_webhook_route.py`
  - 全量 `uv run pytest -q` 通过，结果为 `21 passed in 0.62s`
- **容器验证**：重建 `github-pr-auto-review` 镜像并替换运行容器，新容器健康检查通过。
- **真实 GitHub 验证**：
  - 读取最新 GitHub App delivery，确认真实 `/review` payload 指向 `karendirecter/notion-lite` 的 PR `#1`
  - 用新实现对该 payload 手动补跑一次完整流程，脚本返回 `review-processed`
  - 回读 PR 评论后确认新增 1 条顶层评论，内容为“未发现高置信正确性缺陷，检查通过。”
  - 当前该 PR 的 review inline comment 数为 0，原因是 Stage 1 未命中候选问题，因此按规格降级为“通过总结”
