# SPEC.md

## 1. 问题陈述

### 1.1 要解决的问题

现代软件团队高度依赖 Pull Request（PR）流程保障代码质量，但人工代码评审存在两个长期痛点：

1. **时效性不足**：评审者有限，PR 经常积压，开发流程被阻塞。
2. **正确性检查不稳定**：人工评审容易受上下文切换、疲劳和经验差异影响，导致一些可被提前发现的缺陷被遗漏。

本项目拟构建一个**集成 GitHub Pull Request 的自动代码评审系统**，为个人开发者和团队开发者提供一个以“代码正确性”为优先目标的 AI 第二审阅者。系统以 GitHub App 的方式接入 PR 工作流，在开发者显式触发 `/review` 命令后，对 PR 变更执行双阶段自动评审，并返回：

- PR 顶层总结（风险等级、变更摘要、总体结论）
- 精准挂载到 diff 行的 Inline Comment
- 符合 GitHub ```suggestion 语法的一键修复建议

### 1.2 目标用户

- **个人开发者**：希望在正式邀请他人 review 之前先获得一轮自动检查，提高自检质量。
- **小型团队开发者**：希望缩短 PR 等待时间，把自动评审作为人工 review 前置过滤层。
- **注重工程质量的团队**：希望用统一规则与结构化评论提高评审一致性。

### 1.3 为什么值得做

该系统的价值不在于替代人工 reviewer，而在于：

- 以更低延迟提供第一轮正确性检查
- 在人工 review 之前发现高风险、低层次的运行时问题
- 为个人开发者提供“第二审阅者”式反馈
- 在团队场景中减少人工 reviewer 把时间浪费在明显问题上的概率

### 1.4 项目定位与非目标

本项目是一个**窄范围、真实可用优先的 MVP**，重点验证以下闭环是否能真实跑通：

`GitHub App 接入 → PR 触发 → 规则初筛 → LLM 复核 → 结构化结果 → GitHub 顶层总结/Inline Comment/Suggestion 回贴`

本项目**不**尝试实现以下非目标：

- 不做完整代码托管平台或 CI 平台
- 不做多语言深度静态分析平台
- 不做自动修复并直接提交代码到仓库
- 不覆盖所有代码质量维度（如复杂风格规范、完整安全审计、依赖治理）
- 不实现云端多租户 SaaS 账户体系

---

## 2. 用户故事

以下用户故事遵循 INVEST 思路，聚焦 MVP 可交付范围。

1. **作为个人开发者**，我希望在 PR 下输入 `/review` 后得到一轮自动代码正确性检查，这样我可以在请求人工评审前先修掉明显问题。
2. **作为团队开发者**，我希望系统把高风险问题直接挂到具体 diff 行上，这样我可以快速理解问题发生的位置与原因。
3. **作为开发者**，我希望系统在可能的情况下附带 GitHub suggestion 代码块，这样我可以直接在网页端一键采纳修复建议。
4. **作为仓库维护者**，我希望 GitHub App 只申请最小必要权限，这样它不会触碰与代码评审无关的敏感仓库或组织能力。
5. **作为项目维护者**，我希望评审逻辑内核可在本地脚本或 CLI 中直接调用，这样我能在不依赖 GitHub 页面点击的情况下调试 Diff 解析、Prompt 和结果渲染。
6. **作为系统实现者**，我希望规则分析层是可插拔的，这样未来可以在不重写评审编排层的前提下扩展其他语言或规则来源。
7. **作为开发者**，我希望当 `/review` 触发后即使未发现高置信问题，系统也能返回一条明确的“检查通过”总结，这样我知道命令已经被处理，而不是静默失败。
8. **作为系统维护者**，我希望当 PR 在评审过程中出现新提交时，旧任务能自动过期，这样系统不会把评论挂到错误的代码版本上。

---

## 3. 功能规约

### 3.1 总体功能边界

系统由 5 个高内聚模块组成：

1. **GitHub 接入层**：接收 GitHub App webhook 事件、校验请求、拉取 PR 元数据、获取 diff 与源码上下文、提交评论。
2. **评审编排层**：将 webhook 输入标准化为内部 `ReviewTask`，组织双阶段评审流程，并处理任务状态、去重、过期控制与失败降级。
3. **评审业务内核**：执行 diff 解析、上下文提取、Prompt 组装、LLM 调用、结构化结果解析与业务校验。
4. **规则分析层**：执行通用 diff 审查与 Python 深度规则分析，输出候选问题 `IssueHit`。
5. **结果渲染层**：将统一的内部评审结果转换为 PR 顶层总结、Inline Comment 与 GitHub suggestion。

### 3.2 GitHub 接入层

#### 输入

- GitHub App webhook 事件
- 重点支持：
  - `issue_comment`（MVP 默认触发入口）
  - `pull_request`（仅做架构预留，默认关闭或由配置项控制）

#### 行为

- 验证 webhook 签名
- 判断评论是否位于 PR 上下文中
- 识别 `/review` 命令
- 获取 PR 基本信息：仓库、PR 编号、base SHA、head SHA、评论触发上下文
- 拉取变更文件、diff hunk、必要源码上下文
- 将 GitHub 平台原始数据转换为内部 `ReviewTask`
- 在评审完成后向 GitHub 提交：
  - 顶层总结评论
  - Inline Comment
  - 带 ```suggestion 的评论内容

#### 输出

- 标准化的 `ReviewTask`
- GitHub 回贴结果

#### 边界条件

- 评论不是 `/review` 时不触发评审
- 非 PR 上下文评论不触发评审
- `pull_request` 自动触发逻辑在 MVP 中默认关闭，但接口需保留

#### 错误处理

- webhook 验证失败：拒绝请求并记录日志
- GitHub API 获取 PR 数据失败：终止本次任务并记录可诊断错误
- 评论提交失败：记录失败信息，不得导致整个服务进程崩溃

#### 权限要求

GitHub App 必须遵循 **Principle of Least Privilege**：

- 仅申请读取仓库内容、PR 变更所需的只读权限
- 仅申请 PR 讨论区与行内评论写权限
- 不申请组织管理权限
- 不读取或写入与评审工作流无关的私人密钥和敏感管理能力

### 3.3 评审编排层

#### 输入

- `ReviewTask`

#### 行为

- 为每次评审绑定唯一 `review_commit_sha`
- 调用规则分析层执行 Stage 1 初筛
- 将候选问题与上下文交给业务内核执行 Stage 2 LLM 复核
- 执行去重、过滤、风险汇总与结果分组
- 监测 PR 是否发生新提交；若 `head_sha` 漂移，则当前任务过期
- 按触发来源控制输出行为：
  - `/review` 触发：即使无问题，也要回一条正向总结
  - 自动触发：若无问题则静默

#### 输出

- 统一 `ReviewResult`

#### 边界条件

- Stage 1 无候选问题时，`/review` 触发仍需输出通过总结
- Stage 2 结果不合法时允许降级输出普通总结或部分 inline comment

#### 错误处理

- 新提交导致 `review_commit_sha` 失效：丢弃旧任务，避免漂移回贴
- LLM 调用失败：生成可诊断的失败结果，避免系统无响应

### 3.4 评审业务内核

#### 输入

- 标准化 `ReviewTask`
- 规则层候选问题 `IssueHit` 列表
- Diff 与必要整文件上下文

#### 行为

- 解析 diff，建立文件、hunk、绝对行号与可回贴位置之间的映射
- 根据候选问题抽取必要上下文
- 默认策略为 **Diff + 必要整文件上下文**：
  - 必须包含当前 diff hunk
  - 必要时读取同文件周边片段
  - 当局部上下文不足以支持判断时，允许读取该变更文件的完整内容
- 构造结构化 Prompt，要求模型输出固定 JSON Schema
- 通过统一 LLM 客户端抽象层调用模型
- 解析 JSON 输出并执行：
  - JSON 解析
  - Schema 校验
  - 业务校验
- 将合法结果转换为内部 `ReviewFinding`

#### 输出

- `ReviewFinding` 列表

#### 边界条件

- 只允许引用当前 PR 中实际存在的文件路径
- 只允许定位到当前 `review_commit_sha` 对应的变更位置
- 不允许将未通过校验的自由文本直接送去 GitHub

#### 错误处理

- JSON 不合法：进入降级或丢弃流程
- 字段缺失但可推断：系统补全
- 字段错误且不可修复：丢弃该 finding，不影响其他结果

### 3.5 规则分析层

#### 输入

- `ChangedFile`
- `Diff`

#### 行为

规则分析层必须采用 **Pluggable（可插拔/策略模式）** 设计，核心接口定义为：

```python
def analyze(file_path: str, diff: Diff) -> list[IssueHit]:
    ...
```

MVP 中包含两类规则来源：

1. **通用 Diff 审查**：围绕变更范围、危险修改模式、可疑删除/绕过逻辑等提供语言无关候选点
2. **Python 深度分析**：重点覆盖以下三类代码正确性问题：
   - 资源与连接未正确关闭（如文件、数据库、网络连接缺失 `with` 或 `close()`）
   - None/空值相关运行时崩溃（对可能为 `None` 的对象直接访问属性或方法）
   - FastAPI/异步阻塞与缺失 `await`（在 `async def` 中使用阻塞 I/O，或异步调用遗漏 `await`）

#### 输出

- `IssueHit` 列表

#### 边界条件

- 仅对当前 PR 变更文件进行分析
- Python 深度规则仅在 Python 文件上启用

#### 错误处理

- 单个规则执行失败不应中断整个 Stage 1
- 规则工具不可用时应记录日志并允许其他规则继续执行

### 3.6 结果渲染层

#### 输入

- `ReviewFinding` 列表
- 触发来源（命令触发或自动触发）

#### 行为

- 聚合结果并生成 PR 顶层总结，至少包含：
  - 本次变更摘要
  - 风险等级
  - 问题数量与高风险问题提示
- 将可定位问题渲染为 Inline Comment
- 当存在可靠替换范围和建议代码时，生成 GitHub ```suggestion 代码块
- 对无问题结果执行触发模式差异化行为：
  - `/review` 触发：发“未发现高置信正确性缺陷，检查通过”类总结
  - 自动触发：静默

#### 输出

- GitHub 可提交评论对象集合

#### 边界条件

- 只有在 `line_number/end_line_number` 或 `original_code_snippet` 足以可靠锚定范围时才渲染 suggestion
- 若 suggestion 范围不可靠，可降级为普通 inline comment

#### 错误处理

- 渲染失败应丢弃单条评论，不影响其他评论输出

---

## 4. 非功能性需求

### 4.1 性能

- 对单个中小型 PR（例如 1–10 个变更文件）应能在可接受时间内返回结果，目标是在课堂演示与开发体验中保持可用。
- 系统应优先减少无意义的大模型调用：
  - `/review` 作为默认触发方式
  - 自动触发默认关闭
  - Stage 1 先筛出候选问题，减少 Stage 2 负载

### 4.2 安全

- GitHub App 仅持有最小必要权限
- webhook 请求必须做签名校验
- 所有 LLM 输出都必须视为**不可信外部输入**，进行严格解析与业务校验
- 禁止接受路径穿越、非法文件路径、负数行号、超长垃圾字段等异常输出直接进入回贴流程

### 4.3 可用性

- `/review` 命令触发必须有始有终：无论是否发现问题，都应对用户给出清晰反馈
- Inline Comment 必须尽可能挂载到具体代码位置，避免仅给出抽象结论
- suggestion 的生成必须以“可安全采纳”为前提，不可靠时宁可降级

### 4.4 可观测性

- 系统应记录至少以下关键信息：
  - 触发来源
  - 仓库与 PR 编号
  - `review_commit_sha`
  - Stage 1 候选问题数量
  - Stage 2 保留/驳回数量
  - 回贴成功/失败情况
- 日志应支持后续在 `AGENT_LOG.md` 与调试过程中追踪关键链路

### 4.5 可扩展性

- 规则层必须可插拔，便于未来扩展其他语言或规则工具
- LLM 客户端必须通过抽象层实现，便于切换 DeepSeek、OpenAI、Claude 等模型提供方
- 自动触发 PR 评审逻辑必须以配置开关控制，便于未来从命令触发平滑切换

---

## 5. 系统架构

### 5.1 架构概览

系统采用“**GitHub 接入壳 + 评审编排层 + 高内聚评审内核 + 可插拔规则层 + 结果渲染层**”的分层架构。

- GitHub 接入层负责平台集成与 webhook 生命周期
- 评审编排层负责组织双阶段评审流程
- 评审业务内核负责 diff、上下文、Prompt、LLM 与结构化解析
- 规则分析层负责生成候选问题
- 结果渲染层负责把统一内部结果转换成 GitHub 评论语义

这种架构的核心目标是：**让真正复杂且需要高频调试的评审逻辑脱离 GitHub 页面交互，变成可在本地脚本、CLI 与测试中直接调用的业务内核。**

### 5.2 数据流

1. GitHub App 接收到 `issue_comment` webhook
2. 接入层识别 `/review` 并拉取 PR 数据
3. 接入层构造 `ReviewTask`，绑定 `review_commit_sha`
4. 编排层调用规则分析层执行 Stage 1 初筛
5. 规则层输出 `IssueHit` 候选问题列表
6. 业务内核读取 diff 与必要整文件上下文，构造结构化 Prompt
7. LLM 输出 JSON，业务内核完成解析与校验
8. 编排层聚合为 `ReviewFinding` 与 `ReviewResult`
9. 结果渲染层输出顶层总结、Inline Comment 与 Suggestion
10. 接入层将结果回贴到 GitHub PR

### 5.3 漂移控制

- 每次评审绑定唯一 `review_commit_sha`
- `IssueHit`、`ReviewFinding` 与最终渲染结果都必须绑定该 commit
- 若 PR 在评审过程中出现新提交导致 `head_sha` 变化，则本轮任务过期
- 旧任务不得继续回贴，避免评论定位漂移

---

## 6. 数据模型

### 6.1 ReviewTask

表示一次完整评审任务，包含：

- `repo_owner`
- `repo_name`
- `pr_number`
- `base_sha`
- `head_sha`
- `review_commit_sha`
- `trigger_type`（`command` 或 `auto`）
- `trigger_comment_id`（若来自 `/review`）
- `changed_files`

### 6.2 ChangedFile

表示一个变更文件，包含：

- `file_path`
- `language`
- `status`（新增、修改、删除等）
- `diff_hunks`
- `surrounding_context`
- `full_file_content`（按需加载）
- `position_mapping`

### 6.3 IssueHit

表示规则层命中的候选问题，包含：

- `file_path`
- `line_number`
- `end_line_number`（可选，默认等于 `line_number`）
- `commit_sha`
- `rule_id`
- `severity`
- `message`
- `evidence`
- `original_code_snippet`（可选）
- `diff_position_hint`（可选）

### 6.4 ReviewFinding

表示经过 LLM 复核后的最终问题，包含：

- `file_path`
- `line_number`
- `end_line_number`
- `commit_sha`
- `risk_level`
- `confidence`
- `issue_title`
- `issue_detail`
- `why_it_matters`
- `fix_strategy`
- `suggested_code`
- `original_code_snippet`

### 6.5 ReviewResult

表示一次评审完成后的聚合结果，包含：

- `review_commit_sha`
- `summary`
- `overall_risk`
- `findings`
- `stats`
- `render_mode`

### 6.6 RenderedComment

表示准备提交到 GitHub 的最终评论对象，包含：

- `comment_type`（summary 或 inline）
- `body`
- `file_path`（inline 时必需）
- `line_number`
- `end_line_number`
- `side`
- `commit_sha`

---

## 7. API / 事件接口设计

### 7.1 Webhook 接口

#### `POST /webhooks/github`

用于接收 GitHub App webhook 事件。

**输入**
- HTTP headers（包含签名、事件类型等）
- GitHub webhook body

**行为**
- 校验签名
- 分发事件类型
- 对 `issue_comment` 事件识别 `/review`
- 对 `pull_request` 事件根据配置开关决定是否触发评审

**输出**
- 统一 HTTP 响应，表示已接受、忽略或拒绝

### 7.2 内部评审接口

该接口为评审业务内核提供统一入口，供 webhook 路由、本地脚本或 CLI 调用。

示意：

```python
def review_pull_request(task: ReviewTask) -> ReviewResult:
    ...
```

### 7.3 LLM 客户端抽象接口

系统通过统一抽象层调用大模型，避免业务内核直接绑定单一提供商。

示意：

```python
class LLMClient(Protocol):
    def review_findings(self, payload: PromptPayload) -> dict:
        ...
```

MVP 默认配置：

- **Provider 模式**：OpenAI 兼容接口
- **Base URL**：`https://ark.cn-beijing.volces.com/api/v3/`
- **Model Name**：`deepseek-v4-flash-260425`

未来应允许切换为原生 OpenAI 或 Claude 提供方。

---

## 8. 技术选型与理由

### 8.1 语言与服务框架

- **Python**：生态成熟，便于实现 webhook 服务、规则分析与测试。
- **FastAPI**：适合实现清晰的 webhook API，开发速度快，便于本地联调。

### 8.2 GitHub 集成

- **GitHub App**：最符合真实产品工作流，可监听 PR 与评论事件并回贴评审结果。
- **PyGithub**：用于与 GitHub API 交互，降低底层 REST 调用复杂度。

### 8.3 测试与运行方式

- **pytest**：便于覆盖单元测试、集成测试与异常输入测试。
- **uv**：用于依赖管理与本地运行，简化开发环境搭建。

### 8.4 LLM 选择

- **统一客户端抽象层**：避免业务逻辑与单一提供商深耦合。
- **MVP 默认接入火山引擎 DeepSeek（OpenAI 兼容）**：便于快速接入、控制调用方式，并保留未来切换空间。
- **默认连接方式**：通过 OpenAI SDK 的兼容模式配置自定义 `base_url` 指向火山引擎接口，默认模型为 `deepseek-v4-flash-260425`，优先兼顾接入成本、响应速度与课程项目的联调便利性。
- **配置来源约束**：`LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL` 必须全部通过环境变量注入，避免把提供商信息硬编码在评审内核中。

### 8.5 容器化

- **Dockerfile + docker-compose.yml**：满足课程要求，并把本地跑通的 FastAPI 接入壳与评审内核封装成可复现交付物。

---

## 9. 结构化 Prompt 与 LLM 输出 Schema

### 9.1 Prompt 设计目标

Prompt 设计必须服务于“稳定解析”，而不是追求语言表达丰富。模型的任务是：

- 基于候选问题和上下文判断是否确认该问题
- 生成适合开发者理解的简短说明
- 在可以安全替换时提供建议代码片段
- 严格输出符合 JSON Schema 的结构化结果

### 9.2 Prompt 输入要素

每次 Stage 2 调用至少包含：

- 当前 `review_commit_sha`（由系统注入，不依赖模型生成）
- PR 与文件上下文
- 当前 diff hunk
- 必要整文件上下文
- Stage 1 候选问题列表
- 输出 JSON Schema 约束
- 明确的禁止事项（不得输出额外文本，不得臆造文件路径，不得超出给定上下文）

### 9.3 JSON Schema（逻辑结构）

```json
{
  "summary": "string",
  "findings": [
    {
      "file_path": "string",
      "line_number": 1,
      "end_line_number": 1,
      "risk_level": "low|medium|high",
      "verdict": "confirm|reject|modify",
      "issue_title": "string",
      "issue_detail": "string",
      "why_it_matters": "string",
      "suggestion_rationale": "string",
      "suggested_code": "string",
      "original_code_snippet": "string",
      "confidence": 0.0
    }
  ]
}
```

### 9.4 字段约束与系统接管规则

- `commit_sha` **不要求模型返回**；系统在内部结果对象中直接填充/覆盖为当前 `review_commit_sha`
- `file_path` 必须属于当前 PR 变更文件集合
- `line_number` 必须为正整数且可映射到当前 diff/上下文
- `end_line_number` 缺失时默认等于 `line_number`
- `original_code_snippet` 用于辅助 suggestion 锚定
- `suggested_code` 为空时不得渲染 suggestion
- 模型不得输出额外解释性文本包裹 JSON

### 9.5 Suggestion 渲染规则

- 模型只输出建议替换代码内容，不直接输出 GitHub 评论完整格式
- 渲染层负责将 `suggested_code` 包装为 ```suggestion
- 只有当替换范围可可靠定位时才生成 suggestion
- 若范围不可靠，则降级为普通 inline comment

---

## 10. 验收标准

### 10.1 功能完成标准

以下条件同时满足时，MVP 功能视为完成：

1. GitHub App 能接收 PR 评论中的 `/review` 命令并触发评审流程
2. 系统能拉取 PR diff，并在必要时读取整文件上下文
3. Stage 1 能对 Python 文件检测至少以下三类问题：
   - 资源未关闭
   - None 相关崩溃风险
   - FastAPI/异步阻塞或缺失 `await`
4. Stage 2 能基于结构化 Prompt 返回可解析 JSON
5. 系统能生成并回贴：
   - 一条 PR 顶层总结
   - 至少一条正确定位的 Inline Comment
   - 在满足条件时生成 GitHub Suggestion
6. `/review` 触发但未发现问题时，系统仍能发出“检查通过”总结
7. 若 PR 在评审期间产生新提交，旧任务不会继续向旧 commit 回贴评论

### 10.2 工程完成标准

1. 评审业务内核可脱离 GitHub 页面，在本地脚本/CLI 中直接调用
2. 存在可一键运行的测试命令
3. 关键模块有单元测试覆盖
4. 具备 Dockerfile 与 docker-compose.yml，可完成本地容器化运行

### 10.3 质量完成标准

1. 非法 LLM JSON 不会导致服务崩溃
2. 包含路径穿越、负数行号、超长垃圾字段等恶意输入时，系统能够丢弃或降级处理
3. GitHub App 权限范围符合最小权限原则
4. 输出结果在评论定位与 suggestion 范围上可解释、可验证

---

## 11. 风险与未决问题

### 11.1 已识别风险

1. **评论定位漂移风险**
   - PR 在评审期间发生新提交，旧结果可能定位失效。
2. **LLM 结构化输出不稳定**
   - 模型可能返回非法 JSON、错误文件路径或无效行号。
3. **Suggestion 范围错误风险**
   - 如果替换范围锚定不准，可能生成误导性建议。
4. **GitHub API 交互复杂度**
   - Inline Comment 与 Suggestion 依赖精确的平台字段语义。
5. **规则层误报/漏报**
   - Python 规则覆盖有限，首版可能只能命中一部分典型缺陷。
6. **Token 与并发成本控制**
   - 若过早开启自动触发，可能带来不必要消耗与噪音。

### 11.2 缓解思路

- 使用 `review_commit_sha` 与任务过期机制控制漂移
- 用 JSON + Schema + 业务三层校验防御模型异常输出
- 用 `end_line_number` / `original_code_snippet` 增强 suggestion 锚点
- 采用 `/review` 作为默认触发方式控制成本
- 通过可插拔规则层为后续扩展留出演进空间

### 11.3 当前未决问题

- 已决：Python 深度规则首版采用 **AST 启发式分析 + Semgrep 补充分析** 的组合策略
- AST 分析器负责快速检测 None access、async blocking I/O 等常见模式
- Semgrep 用于补充资源泄漏及更复杂的模式匹配规则
- 本地隧道联调方案（如具体工具选择）尚未在本规约中锁定，可在实现计划中补充
- 自动触发模式的去重/防抖策略属于未来扩展，不纳入 MVP 必做范围

---

## 12. 4.5 冷启动验证前的文档约束

为满足课程 4.5 要求，`PLAN.md` 生成前必须保证本文已经对以下内容写明：

- 系统边界与非目标
- 双阶段 pipeline 的输入、输出与职责分工
- 结构化 LLM 输出 Schema
- GitHub 评论定位与 `review_commit_sha` 约束
- `/review` 与自动触发的行为差异
- Python 深度分析的 3 类问题边界
- 验收标准与风险说明

这样，后续“陌生智能体”在只读取 `SPEC.md` + `PLAN.md` 时，才能在没有口头补充的情况下理解系统要做什么、做到什么程度、哪些地方必须保守处理。
