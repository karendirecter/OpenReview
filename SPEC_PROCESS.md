# SPEC_PROCESS.md

## 1. 文档目的

本文记录我与主开发智能体基于 Superpowers `brainstorming` 技能协作生成 `SPEC.md` 与后续 `PLAN.md` 的过程性证据，重点说明：

- 智能体提出了哪些关键问题，如何帮助我把模糊想法收束成可执行规约
- 在至少 3 轮关键迭代中，我如何采纳、修正或拒绝智能体建议
- 哪些设计决策来自 AI 提议，哪些来自我主动纠偏
- 我对本轮 Superpowers brainstorming 体验的反思

> 说明：截至当前阶段，项目尚未进入 4.5“陌生智能体冷启动试跑”。因此本文暂时只覆盖 4.1–4.4 阶段的规约生成过程；4.5 相关验证记录将在完成冷启动试跑后补充到本文后续章节。

---

## 2. 初始项目设想与第一次收束

### 2.1 初始设想

我最初提出的项目主题是：构建一个**集成 GitHub Pull Request 的代码自动评审系统**，供个人或团队开发者使用，解决人工审核耗时且准确率不稳定的问题，并作为第二审阅者提升个人开发水平。

这个表述说明了项目价值，但仍然过于宽泛：

- “自动评审”到底评什么？
- 以什么形态接入 GitHub？
- 是做研究型原型，还是做真实可跑通的产品闭环？
- 大模型在系统中扮演什么角色？

### 2.2 智能体的关键追问

智能体没有直接接受“做一个 PR 自动评审系统”这个表述，而是继续追问多个关键边界，其中最早且最重要的问题包括：

1. **MVP 首版优先评审什么内容？**
2. **系统如何接入 GitHub PR？**
3. **大模型是规则增强、LLM 主导，还是双阶段 pipeline？**
4. **MVP 首版支持哪些语言？**
5. **输出结果是 PR 总结、行级评论，还是还要支持 suggestion？**

这些问题迫使我把一个“看起来方向正确但尚不具备实现边界”的主题，逐步收束为可以写进正式规约的产品定义。

### 2.3 第一轮决策结果

在这一轮中，我做出的最重要选择包括：

- MVP **以代码正确性优先**，而不是先做风格检查或安全扫描全集
- 接入形态采用 **混合模式**：评审内核可本地脚本/CLI 调用，同时预留 GitHub App 接口
- 评审策略采用 **双阶段 pipeline**：先规则/静态分析初筛，再由 LLM 复核与生成评论
- 语言策略采用 **混合模式**：以通用 diff 审查为主，并对 Python 做深度分析
- 输出形态采用 **双层 + 修复建议**：PR 总结 + Inline Comment + GitHub suggestion

### 2.4 我的处理决策

我采纳了智能体关于“必须优先收窄 MVP”的做法，因为如果不先限定评审目标、输入输出与触发方式，后续写 `SPEC.md` 时就很容易沦为一个抽象愿景，而不是可验证的工程规约。

---

## 3. 关键迭代一：从“泛化自动评审”到“真实可用的窄 MVP”

### 3.1 对话节选

> 智能体：这个系统的“最小可用版本”里，你希望它自动评审什么内容？
>
> 我：代码正确性优先。
>
> 智能体：当系统发现问题时，你希望它输出什么粒度的结果作为 MVP？
>
> 我：双层 + 修复建议。PR 顶层总结、行级评论、并在行内评论中包含符合 GitHub `suggestion` 标准格式的代码块。
>
> 智能体：这次课程项目里，你希望系统是“真实可用优先”，还是“研究/展示方法论优先”？
>
> 我：两者兼顾，但偏真实可用。核心目标是 GitHub App 链路、双阶段 Pipeline 与行内 Suggestion 真实闭环，绝不靠 Mock 演示。

### 3.2 AI 的建议

智能体提出了 3 种推进方案，其中我最终采纳的是：

- **产品范围按 A 收窄**：GitHub App 接入 + PR 总结 + Inline Comment + Suggestion + Python 深度分析 + 通用 Diff 审查
- **系统分层按 B 设计**：GitHub App 只是接入壳，真正可复用、可脚本调用、便于测试的部分是评审业务内核

智能体的明确建议是：**产品范围按 A 收窄，系统分层按 B 设计。**

### 3.3 我的取舍理由

我采纳这个建议，是因为它同时满足了两类目标：

1. **课程目标**：MVP 范围被显式限定，更容易形成清晰的 `SPEC.md` 和可拆分的 `PLAN.md`
2. **产品目标**：即使首版功能较窄，也能真正跑通 GitHub App → 评审 pipeline → inline suggestion 回贴的闭环

如果没有这一轮收束，项目很容易难以在开发周期内做到真实可用。

### 3.4 这一轮体现的 AI 价值

这一轮中，AI 的最大价值是不断追问**产品边界**和**完成标准**，逼迫我在“想做很多事”的冲动与“开发时间/交付周期”的现实之间做平衡。

---

## 4. 关键迭代二：从“能评论”到“能稳定落到 GitHub Diff 上”

### 4.1 对话节选

> 智能体：我建议内部定义 `ReviewTask`、`ChangedFile`、`IssueHit`、`ReviewFinding`、`RenderedComment` 等核心领域对象，并要求 LLM 输出严格 JSON Schema。
>
> 我：潜在风险：Stage 1 静态分析工具拿到的通常是目标文件真实行号，但 GitHub Inline Comment 实际要求绑定 diff hunk 位置或严格的 `line/start_line + commit_id`。如果开发者中途又 push 了新代码，评论会漂移。
>
> 我：可以在标准化任务和 `IssueHit` 数据流中附带 `commit_sha`，业务内核和渲染层必须锁定在这个唯一 commit 上。
>
> 智能体：这个补充非常关键，我会把它上升为设计约束：内部结果不能只记录文件与绝对行号，还必须绑定对应 `commit_sha` 与可回贴的 diff 定位信息。

### 4.2 AI 的原始建议

智能体最初给出的方向已经比较正确：

- 建立稳定的内部领域模型，而不是直接围绕 GitHub API 拼装逻辑
- 强制 LLM 以 JSON Schema 返回结构化结果，避免把自由文本直接送去 GitHub
- 把 suggestion 包装放在渲染层，而不是让模型直接生成完整 GitHub 评论文本

### 4.3 我的修正与补强

我认为仅有 `file_path + line_number` 还不足以支撑真实的 GitHub Inline Comment 回贴，因此补充了两个关键工程约束：

1. **commit 绑定**：每个候选问题和最终评论都必须绑定 `review_commit_sha`
2. **漂移防御**：如果评审期间 PR 头部 commit 变化，则旧任务过期，不继续回贴

这一点本质上是在把“LLM 评审结果”从一个抽象文本对象，修正为一个**受版本约束的可执行回贴对象**。

### 4.4 我的取舍理由

我之所以强调这一点，是因为这个系统的真实价值不在于“模型说得是否像一个 reviewer”，而在于它能否把建议**稳定且正确地挂到开发者正在看的那一行代码上**。如果定位漂移，哪怕建议本身正确，产品体验也会严重受损。

### 4.5 这一轮体现的 AI 与人的分工

这一轮中，AI 更擅长给出一套标准化数据模型，而我补充的是一个只有在真实 GitHub PR 交互里才会暴露出来的产品级约束：**评论定位稳定性**。这说明 brainstorming 过程并不是“接受 AI 方案”，而是“在人类经验和 AI 结构化能力之间做来回校准”。

---

## 5. 关键迭代三：从“结构化输出”到“把 LLM 当作不可信输入处理”

### 5.1 对话节选

> 智能体：建议 LLM 输出中包含 `file_path`、`line_number`、`commit_sha`、`risk_level`、`issue_detail`、`suggested_code` 等字段，并做严格 Schema 校验。
>
> 我：建议增加 `end_line_number` 或 `original_code_snippet`，否则 suggestion 只靠一个 `line_number` 无法精确知道要替换哪几行。
>
> 我：另外，`commit_sha` 不应该交给模型去“猜”，系统应在 Prompt 中固定，并在解析时直接覆盖为当前 `review_commit_sha`。
>
> 智能体：我会把它们写成明确设计决策：用 `end_line_number` 或 `original_code_snippet` 锚定 suggestion 替换范围，并由系统注入并覆盖 `commit_sha`。
>
> 我：还应加入“大模型恶意输入测试”，例如负数行号、路径穿越、超长垃圾字符。预期系统要么丢弃、要么降级，但不能崩溃。
>
> 智能体：这条测试要求很好，而且应该进 spec：把 LLM 输出当作不可信外部输入处理。

### 5.2 AI 的建议

智能体在这一轮中提出了两个正确的大方向：

- LLM 输出必须结构化，并经过 JSON + Schema + 业务三层校验
- 渲染层负责把内部结果转换成 GitHub 顶层总结和 inline suggestion，而不是让模型直接输出平台相关格式

### 5.3 我的修正与补强

我进一步补充了三项重要约束：

1. **Suggestion 锚点增强**：加入 `end_line_number` 或 `original_code_snippet`，精确锚定替换范围
2. **commit_sha 由系统接管**：不相信模型能正确返回哈希，系统应强制覆盖
3. **恶意/异常 LLM 响应测试**：把模型输出视为不可信输入，显式设计鲁棒性测试

### 5.4 我的取舍理由

如果缺少这些约束，系统会出现三个问题：

- suggestion 可能覆盖错误代码范围
- 一次无意义的哈希幻觉就可能导致整条评论报废
- 面对异常 JSON 时系统可能崩溃，形成稳定性风险

因此，我没有把“结构化输出”理解成单纯的 Prompt 工程，而是把它视作**外部不可信输入的解析问题**。这一转变会直接影响测试策略和安全边界。

### 5.5 这一轮体现的 AI 价值与局限

AI 擅长把“需要结构化”这件事说清楚，但在边界条件、坏输入、防御性解析、GitHub 平台细节等问题上，仍然需要我主动补充真实世界的工程约束。

---

## 6. 关键迭代四：从“自动触发更智能”到“/review 默认触发更可控”

### 6.1 对话节选

> 智能体：MVP 首版你希望评审触发方式是什么？
>
> 我：两者都支持，但命令触发为默认。
>
> 我：系统通过监听 GitHub App 的 `issue_comment` 事件，当检测到开发者在 PR 下回复 `/review` 时才正式触发评审 Pipeline；同时在架构上预留直接接收 `pull_request` 事件的接口，但默认关闭或通过配置开启。
>
> 智能体：这个选择很合理，我会把它写成明确产品决策：MVP 默认 `/review` 命令触发，`pull_request` 自动触发仅做架构预留并由配置开关控制。

### 6.2 AI 的建议

AI 用多项选择的方式逼我明确：是自动触发、命令触发，还是两者兼顾。这种追问看似简单，但实际上把一个常见的“默认大家都想自动化”的隐性假设显式化了。

### 6.3 我的取舍理由

我最终选择“命令触发为默认”，核心原因不是功能能力，而是**工程成本与调试可控性**：

- 在课程开发阶段，自动触发会带来大量无意义的 Token 消耗
- PR 频繁 push 时，自动任务容易并发叠加，反而影响验证体验
- `/review` 触发更适合作为 MVP 的主路径，因为开发者可以显式决定何时需要 AI 第二审阅者

同时，我要求系统保留自动触发接口，是为了避免后续架构重做，使产品有演进空间。

### 6.4 这一轮体现的 AI 价值

AI 在这一轮的价值不在于给出技术细节，而在于通过提问让我提前面对“默认行为是什么”这个往往会拖到很后面才讨论的问题。这个问题一旦晚定，会同时影响 webhook 设计、配置结构、日志语义和用户体验。

---

## 7. 关键迭代五：技术栈、问题类型与部署边界的定稿

### 7.1 关键定稿内容

在后续多轮追问中，我又进一步与智能体共同敲定了以下边界：

- **技术栈**：Python + FastAPI + PyGithub（Webhook 异步驱动）+ pytest + uv
- **Python 深度分析首批问题类型**：
  1. 资源与连接未正确关闭
  2. None/空值相关运行时崩溃
  3. FastAPI/异步阻塞与缺失 `await`
- **评审结果无问题时的交互规则**：
  - `/review` 触发：即使未发现高置信问题，也要发一条正向总结
  - 自动触发：若未来开启且未发现问题，则保持静默
- **部署边界**：两者都要，但本地联调优先，Docker 作为课程必交封装
- **大模型接入策略**：通过统一抽象层接入，MVP 默认采用兼容 OpenAI 格式的火山引擎 DeepSeek

### 7.2 这些问题为什么重要

这些追问看起来像“实现细节”，但实际上它们决定了 `SPEC.md` 是否能达到“陌生智能体冷启动可读”的程度。比如：

- 不写清楚“无问题时是否回评论”，就会在实现时出现不同 agent 的不一致理解
- 不提前限定 Python 三类深度问题，后续规则层很容易无限扩张
- 不明确本地优先 + Docker 必做，就会把“能写代码”和“能交课程作业”割裂开

---

## 8. 哪些建议来自 AI，哪些是我修正或推翻的

### 8.1 我采纳的 AI 建议

以下建议主要由 AI 提出，我认为合理并采纳：

- 必须先收窄 MVP 边界，再写正式 spec
- 产品范围按“真实闭环优先”的窄范围定义
- 系统结构应采用“接入壳 + 高内聚评审内核”的分层方式
- 采用双阶段 pipeline，而不是一开始就完全依赖 LLM 自由审查
- 用结构化 JSON Schema 约束模型输出
- 将 suggestion 包装逻辑留在渲染层而不是 Prompt 中硬编码

### 8.2 我修正或补强的 AI 建议

以下点并非我推翻 AI，而是我认为原建议不够落地，因此进行了修正：

- **GitHub App 权限边界**：补充最小权限原则，只申请读取仓库内容/PR 变更和写入评论，不碰组织管理与私钥
- **规则层结构**：强调规则分析层必须可插拔，而不是只为 Python 写死逻辑
- **行级评论定位**：增加 `commit_sha` 绑定与漂移过期控制
- **Suggestion 范围锚点**：增加 `end_line_number` / `original_code_snippet`
- **commit_sha 防幻觉策略**：由系统覆盖注入，不相信模型返回值
- **鲁棒性测试**：把恶意/异常 LLM JSON 响应纳入单元测试与降级策略

### 8.3 我没有采纳的潜在方向

虽然 AI 没有强推，但在多项选择推进中，其实隐含着一些我有意识没有选择的方向：

- 没有选择“LLM 主导型评审”，因为这会削弱可解释性与可控性
- 没有选择“自动触发为默认”，因为课程阶段更需要可控调试成本
- 没有选择“多语言深度分析”，因为这会让 MVP 范围过大

---

## 9. 对 Superpowers brainstorming 技能的反思

### 9.1 做得好的地方

1. **强迫我做边界决策**
   - 它不会满足于“做一个 PR 自动评审系统”这样的模糊表述，而是不断追问优先级、输出粒度、触发方式、部署边界等关键问题。
   - 这些问题在普通自由对话里很容易被跳过，但恰恰是决定 spec 质量的核心。

2. **把抽象需求拉到可验证层面**
   - 例如从“自动评审”追问到“是否需要 suggestion”“无问题时是否评论”“如何控制自动触发噪音”，这些都直接影响后续测试与验收。

3. **适合课程过程证据的积累**
   - 通过一问一答式收束，我可以清楚看见哪些决策是如何被确认的，这对于撰写 `SPEC_PROCESS.md` 和之后的 `REFLECTION.md` 很有帮助。

### 9.2 让我不满或需要人工纠偏的地方

1. **对真实平台约束的敏感度仍然不足**
   - 像 GitHub inline comment 的定位、commit 漂移、防止评论挂错位置等问题，并不是它一开始主动给出的，而是我后续补上的。

2. **对坏输入/异常输入的防御性思维不够强**
   - 它会提出“做 Schema 校验”，但如果没有我继续要求，就未必会自然上升到“把 LLM 输出当作不可信外部输入处理”的程度。

3. **容易先给出结构正确的答案，再依赖人补充真实工程约束**
   - 这并不是完全的缺点，但说明它更像一个能快速搭出骨架的设计伙伴，而不是一个天然了解平台边缘条件的资深工程师。

### 9.3 我的总体评价

这次 brainstorming 的最大价值，不是替我“想出一个项目”，而是帮助我把一个过于宏大的方向，逐步压缩成一个既能满足课程要求、又有机会真实落地的 MVP 规约框架。它更像一种**高频设计审问器**：不断追问模糊点，逼迫人类把隐性假设显式化。

但与此同时，它并不能替代真实工程经验。凡是涉及平台细节、异常输入、防御性设计、权限边界、漂移控制等“会在真实系统里出事”的地方，仍然需要我主动提出并修正。也正因为如此，这种协作方式才符合课程想训练的能力：**AI 可以帮助你更快地形成结构，但“做什么”和“怎样才算做对”仍然必须由人负责。**

---

## 10. 4.5 冷启动验证记录

### 10.1 验证概述

**验证时间**：2026-05-28
**执行智能体**：Claude Code (glm-5)
**执行模式**：陌生智能体冷启动试跑
**执行任务范围**：PLAN.md Task 1-3
**执行结果**：任务成功完成，但发现多处文档缺陷

### 10.2 停下来发问的地方

在执行过程中，智能体在以下关键点停下来发问：

#### 问题 1：Git 设置步骤缺失
**发问时机**：任务开始前
**问题描述**：PLAN.md 没有包含关联远程仓库和创建分支的步骤，所有 Task 都假设在已有仓库的基础上进行。用户要求在”冷启动分支”上工作，但文档没有指定分支名称。
**智能体行为**：向用户询问冷启动分支的具体名称，并确认远程仓库状态。

#### 问题 2：目录结构创建顺序问题
**发问时机**：执行 Task 1 Step 1 时
**问题描述**：PLAN.md Task 1 直接创建 `tests/unit/test_config.py`，但没有先创建 `tests/`、`tests/unit/`、`tests/conftest.py` 等必要的目录结构。
**智能体行为**：向用户询问文档缺陷的处理方式（边执行边修复、先修复再执行、仅报告缺陷）。

#### 问题 3：环境依赖确认
**发问时机**：任务开始前
**问题描述**：PLAN.md Task 1 依赖 `uv` 工具，要求 Python >=3.11，包含 `semgrep` 依赖，但没有说明如何安装 uv，也没有检查当前环境。
**智能体行为**：向用户询问环境依赖情况（uv、Python 版本、Semgrep）。

### 10.3 SPEC.md 和 PLAN.md 缺陷汇总

#### 缺陷 1：缺少 Git 设置步骤（PLAN.md）

**影响范围**：所有 Task
**严重程度**：高
**缺陷描述**：
- PLAN.md 没有包含初始化 Git 仓库、关联远程仓库、创建分支的步骤
- 所有 Task 都假设在已有仓库的基础上进行
- 用户要求在特定分支上工作，但文档没有指定分支名称

**修改建议（diff 形式）**：

```diff
--- PLAN.md (original)
+++ PLAN.md (modified)
@@ -1,3 +1,33 @@
 # GitHub PR Auto Review System Implementation Plan

+## Prerequisites Setup
+
+**Before starting any tasks, ensure the following prerequisites are met:**
+
+- [ ] **Step 0.1: Initialize Git repository**
+
+Run: `git init`
+Expected: Git repository initialized in current directory
+
+- [ ] **Step 0.2: Add remote repository**
+
+Run: `git remote add origin https://github.com/karendirecter/OpenReview.git`
+Expected: Remote repository added successfully
+
+- [ ] **Step 0.3: Create and switch to cold-start branch**
+
+Run: `git checkout -b cold-start`
+Expected: New branch created and switched
+
+- [ ] **Step 0.4: Verify environment prerequisites**
+
+Check Python version: `python --version` (requires >=3.11)
+Check uv installation: `uv --version`
+Expected: Python 3.11+ installed, uv available
+
+- [ ] **Step 0.5: Create necessary directory structure**
+
+Run: `mkdir -p tests/unit tests/integration tests/integration/fixtures app app/review app/github app/rules app/llm app/prompts scripts`
+Expected: All necessary directories created
```

#### 缺陷 2：缺少测试目录结构创建说明（PLAN.md Task 1）

**影响范围**：Task 1, Task 2, Task 3
**严重程度**：中
**缺陷描述**：
- Task 1 直接创建 `tests/unit/test_config.py`，但没有先创建必要的目录
- 缺少 `tests/conftest.py`、`tests/unit/__init__.py`、`tests/integration/__init__.py` 的创建说明
- 缺少 `.gitignore` 文件的创建说明

**修改建议（diff 形式）**：

```diff
--- PLAN.md (original Task 1)
+++ PLAN.md (modified Task 1)
@@ -74,6 +74,10 @@
 ### Task 1: Bootstrap project skeleton and settings

 **Files:**
+- Create: `.gitignore` (新增)
+- Create: `tests/conftest.py` (新增)
+- Create: `tests/unit/__init__.py` (新增)
+- Create: `tests/integration/__init__.py` (新增)
 - Create: `pyproject.toml`
 - Create: `app/__init__.py`
 - Create: `app/main.py`
@@ -85,6 +89,21 @@
 - [ ] **Step 1: Write the failing settings test**

+注意：在编写测试之前，必须先创建必要的目录结构：
+
+Run: `mkdir -p tests/unit tests/integration`
+Expected: Test directories created
+
+Create `tests/conftest.py`:
+```python
+# tests/conftest.py
+# Shared fixtures for unit tests
+```
+
+Create `tests/unit/__init__.py` and `tests/integration/__init__.py`:
+```python
+# Test package marker
+```
+
 ```python
 from app.config import Settings
```

#### 缺陷 3：模型定义不完整（PLAN.md Task 2 vs SPEC.md 6.1-6.6）

**影响范围**：Task 2, Task 5
**严重程度**：高
**缺陷描述**：
- SPEC.md 定义了 6 个核心模型：ChangedFile、ReviewTask、IssueHit、ReviewFinding、ReviewResult、RenderedComment
- PLAN.md Task 2 只定义了部分模型（ChangedFile、ReviewTask、IssueHit）
- ReviewFinding 在 Task 5 才定义，破坏了模型定义的完整性
- ReviewResult 和 RenderedComment 在 PLAN.md 中完全没有定义

**修改建议（diff 形式）**：

```diff
--- PLAN.md (original Task 2)
+++ PLAN.md (modified Task 2)
@@ -203,7 +203,7 @@
 ### Task 2: Define core review domain models

 **Files:**
+- Modify: `app/review/models.py` (should include all models from SPEC.md 6.1-6.6)
 - Create: `app/review/models.py`
 - Create: `app/review/__init__.py` (新增)
 - Test: `tests/unit/test_models.py` (rename from test_orchestrator.py)
```

```diff
--- PLAN.md (original Task 2 Step 3)
+++ PLAN.md (modified Task 2 Step 3)
@@ -248,6 +248,112 @@
     evidence: str
     original_code_snippet: str | None = None
     diff_position_hint: int | None = None
+
+
+class ReviewFinding(BaseModel):
+    “””Represents a final issue after LLM verification (SPEC.md 6.4).”””
+    file_path: str
+    line_number: int
+    end_line_number: int
+    commit_sha: str
+    risk_level: str
+    confidence: float
+    issue_title: str
+    issue_detail: str
+    why_it_matters: str
+    fix_strategy: str
+    suggested_code: str
+    original_code_snippet: str
+
+
+class ReviewResult(BaseModel):
+    “””Represents aggregated review result (SPEC.md 6.5).”””
+    review_commit_sha: str
+    summary: str
+    overall_risk: str
+    findings: list[ReviewFinding]
+    stats: dict[str, int] = Field(default_factory=dict)
+    render_mode: str
+
+
+class RenderedComment(BaseModel):
+    “””Represents a final comment ready for GitHub (SPEC.md 6.6).”””
+    comment_type: str
+    body: str
+    file_path: str | None = None
+    line_number: int | None = None
+    end_line_number: int | None = None
+    side: str | None = None
+    commit_sha: str
```

#### 缺陷 4：测试文件命名不当（PLAN.md Task 2）

**影响范围**：Task 2
**严重程度**：低
**缺陷描述**：
- Task 2 的测试文件名为 `test_orchestrator.py`，但测试内容是模型的基本属性
- 应该命名为 `test_models.py`，因为测试的是 domain models 而非 orchestrator

**修改diff**：

```diff
--- PLAN.md (original Task 2)
+++ PLAN.md (modified Task 2)
@@ -206,7 +206,7 @@
 **Files:**
 - Create: `app/review/models.py`
 - Test: `tests/unit/test_orchestrator.py`
+- Test: `tests/unit/test_models.py` (rename to better reflect test content)
```

#### 缺陷 5：缺少测试 fixture 文件创建说明（PLAN.md Task 3）

**影响范围**：Task 3, Task 4
**严重程度**：中
**缺陷描述**：
- Task 3 需要 `tests/integration/fixtures/sample_pr_diff.patch` 文件
- Task 4 需要 `tests/integration/fixtures/sample_python_file.py` 文件
- PLAN.md 没有说明如何创建这些 fixture 文件，以及它们的内容应该是什么

**修改diff**：

```diff
--- PLAN.md (original Task 3)
+++ PLAN.md (modified Task 3)
@@ -303,6 +303,10 @@
 **Files:**
+- Create: `tests/integration/fixtures/sample_pr_diff.patch` (新增)
+- Create: `tests/integration/fixtures/sample_python_file.py` (新增 for Task 4)
 - Create: `app/review/diff_parser.py`
 - Test: `tests/unit/test_diff_parser.py`
 - Test: `tests/integration/fixtures/sample_pr_diff.patch`
```

#### 缺陷 6：缺少 pytest 配置说明（PLAN.md Task 1）

**影响范围**：Task 1
**严重程度**：中
**缺陷描述**：
- `pyproject.toml` 中配置了 `pythonpath = [“.”]`，但没有说明此配置的重要性
- 如果没有此配置，pytest 无法找到 `app` 模块
- PLAN.md 步骤中缺少对此配置的解释

**修改diff**：

```diff
--- PLAN.md (original Task 1 Step 3)
+++ PLAN.md (modified Task 1 Step 3)
@@ -115,6 +115,9 @@

 [tool.pytest.ini_options]
 testpaths = [“tests”]
+pythonpath = [“.”]
+# 注意：pythonpath 配置至关重要，否则 pytest 无法导入 app 模块
+# 所有测试文件需要能导入 app.* 模块，因此必须将项目根目录加入 Python path
```

#### 缺陷 7：环境变量说明不足（PLAN.md Task 1 vs SPEC.md）

**影响范围**：Task 1
**严重程度**：低
**缺陷描述**：
- `.env.example` 中定义了环境变量，但没有说明每个变量的用途和来源
- 特别是 `LLM_BASE_URL` 为什么是火山引擎的端点，应该有背景说明
- SPEC.md 8.4 提到使用火山引擎 DeepSeek，但 PLAN.md 缺少连接说明

**修改diff**：

```diff
--- PLAN.md (original Task 1 .env.example)
+++ PLAN.md (modified Task 1 .env.example)
@@ -178,3 +178,8 @@
 LLM_API_KEY=replace-me
 LLM_MODEL=deepseek-v4-flash-260425

+# 环境变量说明：
+# - LLM_BASE_URL: 火山引擎提供的 DeepSeek 接口端点（见 SPEC.md 8.4）
+# - LLM_MODEL: DeepSeek 模型名称，默认使用 flash 版本降低成本
+# - GITHUB_TRIGGER_MODE: 触发方式，comment 表示手动 /review 命令触发
+# - ENABLE_PULL_REQUEST_AUTO_REVIEW: 自动触发开关，MVP 默认关闭
```

#### 缺陷 8：Python 深度规则实现细节未决（SPEC.md 11.3 vs PLAN.md）

**影响范围**：Task 9, Task 10
**严重程度**：中
**缺陷描述**：
- SPEC.md 11.3 未决问题：”Python 深度规则首版具体采用 AST、自定义启发式规则还是 Semgrep 组合”
- PLAN.md Task 9 和 Task 10 已经决定使用 AST + Semgrep，但这个决策应该在 SPEC.md 中明确
- 缺少对 AST 分析器具体实现策略的说明

**修改diff**：

```diff
--- SPEC.md (original 11.3)
+++ SPEC.md (modified 11.3)
@@ -639,7 +639,8 @@
 ### 11.3 当前未决问题

-- Python 深度规则首版具体采用 AST、自定义启发式规则还是 Semgrep 组合，仍需在 `PLAN.md` 中进一步细化任务拆分
+已决：Python 深度规则首版采用 **AST 启发式分析 + Semgrep 补充分析** 的组合策略
+AST 分析器负责快速检测 None access、async blocking I/O 等常见模式
+Semgrep 用于更复杂的资源泄漏和安全相关规则
 - 本地隧道联调方案（如具体工具选择）尚未在本规约中锁定，可在实现计划中补充
 - 自动触发模式的去重/防抖策略属于未来扩展，不纳入 MVP 必做范围
```

#### 缺陷 9：diff_parser 实现过于简化（PLAN.md Task 3）

**影响范围**：Task 3
**严重程度**：中
**缺陷描述**：
- PLAN.md Step 3 的 `build_position_mapping` 实现过于简化
- 缺少对 `unidiff` 库的使用（尽管依赖中包含 `unidiff>=0.7.5`）
- 缺少对多 hunk diff 的处理逻辑
- 缺少对 diff_position 和绝对行号的精确映射说明

**修改diff**：

```diff
--- PLAN.md (original Task 3 Step 3)
+++ PLAN.md (modified Task 3 Step 3)
@@ -336,6 +336,12 @@
 ```python
 def build_position_mapping(patch: str, new_start: int) -> dict[int, int]:
+    “””
+    Build mapping from absolute line numbers to GitHub review positions.
+
+    注意：此实现为简化版本，实际应使用 unidiff 库解析完整的 diff 结构，
+    支持多 hunk 场景和更复杂的 diff 格式。
+    “””
     mapping: dict[int, int] = {}
     current_line = new_start
     position = 0
```

#### 缺陷 10：缺少 app 包子目录创建说明（PLAN.md Task 1-3）

**影响范围**：Task 1, Task 2, Task 3
**严重程度**：中
**缺陷描述**：
- Task 2 需要 `app/review/__init__.py`，但没有创建步骤说明
- Task 后续需要 `app/github/__init__.py`、`app/rules/__init__.py` 等子目录
- PLAN.md 缺少对 Python 包结构创建的统一说明

**修改diff**：

```diff
--- PLAN.md (original)
+++ PLAN.md (modified)
@@ -1,5 +1,7 @@
 # GitHub PR Auto Review System Implementation Plan

+**注意：每个 app 子目录创建时，都需要同时创建对应的 __init__.py 文件作为包标记。**
+
 > **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
```

### 10.4 与原意不一致的解读

智能体在执行过程中，以下解读与原计划意图存在偏差：

#### 解读偏差 1：测试文件命名

**原计划意图**：Task 2 测试文件名为 `test_orchestrator.py`
**智能体解读**：应该命名为 `test_models.py`，因为测试内容是模型属性
**偏差原因**：PLAN.md 测试文件命名不合理，导致智能体认为应该有更合适的命名
**处理方式**：智能体按照 PLAN.md 原计划创建 `test_orchestrator.py`，但在代码注释中标出了命名问题

#### 解读偏差 2：模型定义范围

**原计划意图**：Task 2 只定义部分模型，Task 5 才定义 ReviewFinding
**智能体解读**：应该在 Task 2 中统一定义所有核心模型，符合 SPEC.md 的模型定义
**偏差原因**：SPEC.md 定义了完整的模型列表，但 PLAN.md 的拆分不合理
**处理方式**：智能体按照 SPEC.md 的完整性在 Task 2 中定义了所有模型，但在注释中标出了 PLAN.md 的拆分问题

### 10.5 文档修订汇总

根据上述缺陷，建议对 PLAN.md 和 SPEC.md 进行以下修订：

#### PLAN.md 修订

1. **添加前置步骤章节**：增加 Prerequisites Setup 章节，包含 Git 设置、环境检查、目录结构创建
2. **调整模型定义时机**：在 Task 2 中定义所有核心模型，移除 Task 5 中重复的 ReviewFinding 定义
3. **补充目录创建说明**：在每个 Task 的 Files 列表中，补充必要的目录和 __init__.py 创建步骤
4. **改进测试 fixture 说明**：明确说明测试 fixture 文件的创建时机和内容
5. **增强配置说明**：对 pyproject.toml 和 .env.example 中的关键配置添加注释说明
6. **统一命名规范**：将 test_orchestrator.py 重命名为 test_models.py

#### SPEC.md 修订

1. **解决未决问题**：在 11.3 章节明确 Python 深度规则的实现策略（AST + Semgrep）
2. **补充实现细节**：对 8.4 章节的 DeepSeek 接入添加更详细的技术说明
3. **增强数据模型说明**：对 6.1-6.6 章节的模型定义补充字段用途说明

### 10.6 关键 Diff 补充

以下是智能体在执行 Task 1-3 过程中创建的所有文件的完整清单：

**Task 1 文件清单**：
- `.gitignore`（PLAN.md 缺少）
- `pyproject.toml`
- `app/__init__.py`
- `app/config.py`
- `app/main.py`
- `.env.example`
- `tests/conftest.py`（PLAN.md 缺少）
- `tests/unit/__init__.py`（PLAN.md 缺少）
- `tests/integration/__init__.py`（PLAN.md 缺少）
- `tests/unit/test_config.py`

**Task 2 文件清单**：
- `app/review/__init__.py`（PLAN.md 缺少说明）
- `app/review/models.py`（包含 SPEC.md 定义的所有 6 个模型，PLAN.md 只定义了 3 个）
- `tests/unit/test_orchestrator.py`（命名不当，应为 test_models.py）

**Task 3 文件清单**：
- `app/review/diff_parser.py`
- `tests/unit/test_diff_parser.py`
- `tests/integration/fixtures/sample_pr_diff.patch`（PLAN.md 缺少创建说明）
- `tests/integration/fixtures/sample_python_file.py`（Task 4 需要，提前创建）

---

**验证完成时间**：2026-05-28
**执行智能体**：Claude Code (glm-5)
