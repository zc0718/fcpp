# Contributing to fcpp（贡献指南）

## 提交规范（Commit Conventions — canonical form）

提交信息是**双通道**：conventional 前缀驱动版本号（semantic-release），emoji 驱动附加 CI 流水线（见 `.github/skills/_shared/gitmoji.md`）。

**Canonical form**: `<type>(<emoji|scope>)?!?: <description>`

| type | 用途 | 示例 |
|---|---|---|
| `feat` / `fix` / `perf` | 版本号变更（minor/patch） | `feat(:fire:): cross-compile support` |
| `docs` / `test` / `build` / `ci` / `refactor` / `style` / `chore` | 不触发版本变更 | `chore(release): 1.0.0 [skip ci]` |

- 破坏性变更：`feat!:` 或正文含 `BREAKING CHANGE:` → major。
- **CI 门禁强制**：`ci-orchestrator.yml` 的 `commit-lint` job 在 push/PR 上校验；本地自查 `npx commitlint --from HEAD~1 --to HEAD`。
- ⚠️ `commitlint.config.js` 与 `.releaserc.json` 的 `headerPattern` 必须同步修改，否则会出现"门禁通过但版本不自增"。

## PR 流程

1. 从 `main` 拉分支，按 canonical form 拆分提交。
2. 保证 `commit-lint`、`schema-check`、`build`、`tests`（PR 上 shift-left 强制）全绿。
3. 填写 PR 模板自检清单；`CODEOWNERS` 评审人为必审。
4. 合并到 `main` 后，release 由 `(:package:):` + Release 配置 + 开关触发（semantic-release）。

## 本地开发（Local Setup）

```bash
# 构建环境
source ~/venv/build/bin/activate
# node 工具（commitlint/ajv/semantic-release）
npm ci --no-audit --no-fund
# 第一道闸（一次性）
pip install pre-commit && pre-commit install

# 质量自查
npx ajv validate -s metadata.schema.json -d metadata.json --spec=draft7
find include src -type f \( -name '*.c' -o -name '*.h' -o -name '*.cpp' -o -name '*.hpp' \) -exec clang-format --dry-run --Werror {} +
clang-tidy src/*.cpp -- -std=c++17

# 构建 + 测试
conan create . -s build_type=Debug --build=missing
```

## 工程契约（Contracts）

- `metadata.json`：单一真源，schema 见 `metadata.schema.json`；字段语义见 `.github/skills/_shared/metadata-contract.md`。
- 代码规范：`.clang-format` / `.clang-tidy`（根目录，WarningsAsErrors）与 `.github/skills/_shared/code-conventions.md`。
- 测试体系：`test_package/test/{unit,stress}/`，GTest 只进 test_package（见 `test-conventions.md`）。

## 回退（Rollback）

CI/发布异常回退命令见 `wokspace/REMEDIATION-PLAN.md` §7。
