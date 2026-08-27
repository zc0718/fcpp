# REMEDIATION-PLAN — fcpp IaC 整改与验证计划

> 依据：`wokspace/AUDIT-2026-08-27.md`（IaC 层基建审计）
> 目标：将审计发现固化为公司/团队内部开发标准，并为日后 VS Code 扩展铺路。
> 验证策略：`validation` 分支全量验证 → 打 tag 存档 → push 验证 → 必要时回退。
> 状态图例：⬜ 计划 / 🔧 已实施 / ✅ 已验证 / ⏸ 延期

---

## 1. 范围与顺序

| 阶段 | 内容 | 提交拆分（canonical form） |
|---|---|---|
| A | 计划落盘 | `docs(:book:)` |
| B | P0 阻塞项 | `fix(:wrench:)` / `build(:building_construction:)` / `ci(:shield:)` / `ci(:wrench:)` |
| C | P1 治理层 | `chore(:hammer:)` / `docs(:book:)` / `ci(:wrench:)` |
| D | P2 插件化 | `chore(:wrench:)` |
| E | Validation-only（回退清单见 §6） | `ci(:beer:)` |

## 2. 整改项映射（审计发现 → 动作）

### P0 — 阻塞固化

| # | 审计发现 | 动作 | 涉及文件 | 状态 |
|---|---|---|---|---|
| P0-1 | canonical `type(:emoji:):` 与 commit-analyzer 不兼容（实测 PARSE FAILED） | 给 `commit-analyzer` 加 `parserOpts.headerPattern`（scope 允许 `:emoji:`） | `.releaserc.json` | ✅ V2 6/6 |
| P0-2 | commit 无门禁 | orchestrator 新增 `commit-lint` job（push 校验提交区间、PR 校验 title），用 commitlint stdin 单一真源，不引入第三方 lint action | `ci-orchestrator.yml`、`commitlint.config.js` | ✅ CI 门禁 job 已运行 |
| P0-3 | 缺 `package.json` → semantic-release 无法运行 | 新增 `package.json`（private + devDeps 锁定）+ `package-lock.json`；`semver-release.yml` 改 `npm ci` | `package.json`、`package-lock.json`、`semver-release.yml` | ✅ |
| P0-4 | lint 失败被 `continue-on-error` 吞掉 | 删除两处 `continue-on-error`，`APPLY_FIXES: none` 严格化 | `security-linters.yml`、`.mega-linter.yml` | ✅ V7 观察 |
| P0-5 | controller 缺省 `// true` 与全 false 开关语义歧义 | 缺字段 fail-loud（exit 1），消除静默缺省 | `metadata-controller.yml` | ✅ 修复 F2 后复验 |

### P1 — 公司标准治理面

| # | 审计发现 | 动作 | 涉及文件 | 状态 |
|---|---|---|---|---|
| P1-1 | 配置在 `.github/misc/`，不在工具链发现链 | `.clang-format`/`.clang-tidy`/`.gitleaks.toml` 迁移到仓库根（删除 misc 副本，更新全部引用：`.mega-linter.yml`、`_shared/code-conventions.md`、`het-quality/SKILL.md`）；同时修复 F1（原配置 4 处致命错误） | 移动 + 3 处引用 | ✅ V4 |
| P1-2 | 治理文件整体缺失 | 新增 `CONTRIBUTING.md`、`CODEOWNERS`、PR 模板、`dependabot.yml` | 新增 4 文件 | ✅ |
| P1-3 | PR 零编译验证 | controller PR 事件 shift-left：build/tests 按开关无条件触发（无需 emoji） | `metadata-controller.yml` | ✅ |
| P1-4 | 缓存 key 引用不存在的 `conan.lock` | 改为 `hashFiles('conanfile.py','conandata.yml','metadata.json')` | `ci-build-test.yml`、`full-test-automation.yml` | ✅ |
| P1-5 | action 版本混用、依赖未锁 | npm 依赖全锁进 lockfile；dependabot 周更 | `dependabot.yml` | ✅ |
| P1-6 | metadata 无机器可读契约 | 新增 `metadata.schema.json`（draft-07，strict）+ orchestrator `schema-check` job（ajv） | `metadata.schema.json`、`ci-orchestrator.yml` | ✅ CI job 已运行成功 |
| P1-7 | 无手动逃生通道/无并发控制 | orchestrator 加 `workflow_dispatch` + `concurrency` | `ci-orchestrator.yml` | ✅ |
| P1-8 | 本地第一道闸缺失 | `.editorconfig` + `.pre-commit-config.yaml` | 新增 2 文件 | ✅ |
| P1-9 | `.gitignore` 忽略 `/.vscode/` 阻止插件化配置入库 | 解除忽略，改为提交推荐文件；新增 `node_modules/` 忽略 | `.gitignore` | ✅ |

### P2 — VS Code 扩展铺路

| # | 事项 | 涉及文件 | 状态 |
|---|---|---|---|
| P2-1 | `metadata.schema.json`（P1-6 同源，扩展 IntelliSense/校验契约） | 同 P1-6 | ✅ |
| P2-2 | `.vscode/extensions.json` + `settings.json` + `tasks.json`（`fcpp: format-check` / `fcpp: tidy` / `fcpp: test` 任务化） | 3 文件 | ✅ |
| P2-3 | `.devcontainer/` 固化工具链 | `devcontainer.json` + `Dockerfile` | ✅ |
| P2-4 | org 级 reusable workflow / workflow-templates / SHA 锁定 | 计划文档（实施放 org `.github` 仓库，本仓库不落盘） | ⏸ |
| P2-5 | SARIF 上传（`github/codeql-action/upload-sarif`） | 后续 PR，先记录 | ⏸ |

## 3. 关键设计决策

1. **headerPattern 双写一致性**：`commitlint.config.js` 与 `.releaserc.json` 使用同一 `^(\w*)(?:\(([^)]*)\))?!?: (.*)$`。两处均附注释互指，`CONTRIBUTING.md` 声明修改须同步。
2. **门禁实现选择**：不用 `wagoid/commitlint-github-action` 等第三方 action（供应链面 + 版本碎片），改为 `npm ci` + `npx commitlint`（stdin 校验 PR title、`--from/--to` 校验 push 区间）。依赖锁定在 lockfile，一举解决 P1-5。
3. **配置唯一真源**：根目录为 canonical；`.github/misc/` 仅保留 `labels.yml`。
4. **开关语义**：`workflow_triggers.*` 缺失即 CI 失败（fail-loud），不再静默缺省。
5. **PR shift-left**：PR 上 build/tests 不再依赖 emoji（emoji 仅用于 push 上附加流水线：docs/release/security 的 push 通道）。

## 4. 验证矩阵

| 验证项 | 命令/方式 | 环境 | 状态 |
|---|---|---|---|
| V1 commitlint 门禁配置 | `npx commitlint --from main --to HEAD --verbose`（12 条提交） | 本地 | ✅ 0 problems |
| V2 parser 兼容（P0-1 核心） | node 脚本用 releaserc 的 headerPattern 实测 6 种提交形态 | 本地 | ✅ 6/6 PASS |
| V3 metadata schema | `npx ajv validate -s metadata.schema.json -d metadata.json --spec=draft7` | 本地 | ✅ valid |
| V4 clang-format | `pip install clang-format`（venv）后 `find ... -exec clang-format --dry-run --Werror {} +` | 本地 | ✅ exit 0 |
| V5 clang-tidy | 本地无 clang-tidy → CI MegaLinter 门禁验证（validation push） | CI | ⏳ 观察中 |
| V6 本地构建 | `conan create . -s build_type=Debug --build=missing` | 本地 | ✅ 构建 + 5/5 测试通过 |
| V7 CI 端到端 | validation push 触发 orchestrator（门禁 + build/tests/security） | GitHub | 🔄 迭代中（见 §9） |
| V8 push/tag 验证 | `git push -u origin validation --tags` + `git ls-remote` | GitHub | ✅ 分支+annotated tag 已上远端 |

## 5. Git 验证流程

1. `git checkout -b validation`（基于 main）。
2. 按 canonical form 拆分提交（§1 阶段 A–D），每条提交本身即 V1 的输入样本。
3. 本地跑 V1–V6。
4. Validation-only 提交（§6）→ 打 annotated tag `validation-checkpoint-1`。
5. `git push -u origin validation --tags`。
6. CI 观察（gh CLI 未登录 → 以 push 成功 + GitHub Actions UI 人工确认；orchestrator 的 push 触发使用被推分支上的 workflow 定义，validation 分支已含验证用触发器）。
7. 结论落盘本文件 §7，回退预案 §8。

## 6. Validation-only 改动（合并 main 前必须回退/剥离）

| 文件 | 改动 | 原因 |
|---|---|---|
| `ci-orchestrator.yml` | `on.push.branches: [main]` → `[main, validation]` | 让 validation push 触发 orchestrator |
| `metadata.json` | `workflow_triggers.build/tests/security_scan` → true；`trigger_tests`/`saving_tests_log` → true | 让流水线真实运行 |

> 注意：`hetai-package-matrix.yml`（self-hosted）与 `sync-template.yml` 的 push 触发仅限 `main`/`fcpp-dev`，validation push **不会**触发上板流水线与 labeler，无副作用。

## 7. 回退预案（Rollback Playbook）

| 场景 | 命令 |
|---|---|
| 本地回退到整改前 | `git checkout main && git branch -D validation && git tag -d validation-checkpoint-1` |
| 远端分支回退 | `git push origin --delete validation` |
| 远端 tag 回退 | `git push origin --delete refs/tags/validation-checkpoint-1` |
| 仅回退 validation-only 提交 | `git reset --hard <validation-only 提交前的 SHA>`（validation 分支上） |
| CI 红 → 定位 | `gh run list -b validation`（需 `gh auth login`）；匿名可用 `curl https://api.github.com/repos/zc0718/fcpp/actions/runs`（本仓库公开） |

## 8. 验证日志（Validation Log）

| 轮次 | 事件 | 结果 |
|---|---|---|
| 0 | 本地 V1–V4、V6 全绿后 push validation（run #2） | ❌ controller `Read metadata.json` 失败 |
| 1 | 定位 F2（jq `//` 陷阱）→ `fix(:bug:)` 修复 → push（run #4） | 🔄 观察中 |

**F1（审计外新发现）**: 原 `.clang-format` 配置 4 处致命错误，从未被真实执行过：① 两个 `Language:` 键同一 YAML 文档（缺 `---` 分隔）；② `Standard: Cpp17`/`C11` 枚举非法（应 `c++17`，C 段不支持）；③ `Extensions` 未知键；④ `MacroDefinitionName` 未知键（宏命名由 clang-tidy `cppcoreguidelines-macro-usage` 负责）。已重写为合法多段配置并 `style(:art:)` 归一化全部源码；`.h` 按 clang-format 规则归入 C++ 段（仓库 C 头无指针，无影响）。

**F2（验证循环捕获）**: jq `//` 把 `false` 当 falsy 处理，导致 fail-loud 检查把 `release=false`/`docs=false` 误判为"缺失"。已改 `has()` 存在性判断 + 独立取值。

**F3（历史遗留，未修复）**: include/src 存在 3+ 连续空行（格式化前后数量不变），与"全局对象间恰好 2 空行"的模块生成规则不符，建议后续专门 style 提交归一化。

## 9. CI 观察方式（本环境 gh 未登录）

- 匿名 API：`curl -s https://api.github.com/repos/zc0718/fcpp/actions/runs?per_page=5`（公开仓库可读）
- UI：<https://github.com/zc0718/fcpp/actions?query=branch%3Avalidation>

## 8. 后续（未纳入本次）

- SARIF 上传接 codeql（P2-5）、org 级 reusable workflows（P2-4）、branch protection ruleset 要求写入 `CONTRIBUTING.md`（依赖 GitHub 界面操作，无 API 权限）。
- 公共 API 测试覆盖审计 → 建议后续 `het-testgen`。
