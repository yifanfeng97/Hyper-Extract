# he template validate

在运行抽取之前，检查 Hyper-Extract YAML 模板的结构和语义问题。

`load_template()` 只验证文档是否符合 Pydantic `TemplateCfg` 形状。标识符引用了不存在的字段、display 占位符与 schema 不匹配、时序/空间类型缺少 time/location 字段时，错误会拖到抽取阶段才出现。本命令把这些检查提前到编写模板时。

`template` 是命令组，`validate` 是子命令。

---

## 用法

```bash
he template validate PATH [--json] [--all]
```

## 参数

| 参数 | 说明 |
|----------|-------------|
| `PATH` | 模板 YAML 文件；使用 `--all` 时可以是目录 |

## 选项

| 选项 | 别名 | 默认值 | 说明 |
|--------|-------|---------|-------------|
| `--json` | | 关闭 | 输出机器可读 JSON，而不是 Rich 文本 |
| `--all` | | 关闭 | 校验目录下每一个 `*.yaml` / `*.yml` 文件 |

---

## 说明

校验器是给模板作者用的旁路工具，**不会**改变运行时 `load_template()` 的行为。

检查项来自 `hyperextract-skills/yaml-validator/` 与 `templates/DESIGN_GUIDE.md`：

| 编码 | 检查 | 严重级别 |
|------|--------|----------|
| `HE-T001` | YAML 可解析 | error |
| `HE-T002` | 文档符合 `TemplateCfg` | error |
| `HE-T003` | 标识符字段（`entity_id`、`relation_id`、`relation_members`、`item_id`、`time_field`、`location_field`）在对应 output schema 中存在 | error |
| `HE-T004` | `relation_members` 类型与 AutoType 匹配（`graph` / 时序 / 空间 → dict；`hypergraph` → 字符串或列表）。dict 的**值**是边 schema 的字段名。超图成员字段必须为 `type: list`。 | error |
| `HE-T005` | display 中的 `{field}` 占位符在对应 schema 中存在 | error |
| `HE-T006` | 时序类型定义 `time_field`；空间类型定义 `location_field` | error |
| `HE-T007` | 已声明的语言在双语字典字段中齐全 | warning |
| `HE-T008` | 字段数超过 DESIGN_GUIDE 上限 5（图的实体/关系，或 `model`/`list`/`set` 的 `output.fields`） | warning |
| `HE-T009` | `domain/name` 与 Gallery 中已有 preset 冲突 | warning |

存在任何 **error** 时退出码为 **1**；全部通过或仅有 warning 时为 **0**。

---

## 示例

### 校验单个文件

```bash
he template validate ./my_template.yaml
```

### 机器可读诊断

```bash
he template validate ./my_template.yaml --json
```

```json
{
  "file": "./my_template.yaml",
  "diagnostics": [
    {
      "code": "HE-T003",
      "severity": "error",
      "path": "identifiers.entity_id",
      "message": "Field 'nickname' is not defined in output.entities"
    }
  ],
  "ok": false
}
```

### 校验全部内置 preset

```bash
he template validate hyperextract/templates/presets --all
```

目录模式配合 `--json` 时，每个文件包在 `results` 里：

```json
{
  "results": [
    {"file": "…/base_graph.yaml", "diagnostics": [], "ok": true}
  ],
  "ok": true
}
```

---

## Python API

CLI 是同一套检查的薄封装：

```python
from hyperextract.utils.template_engine import validate_template

result = validate_template("my_template.yaml")
print(result.ok, result.to_dict())
```

---

## 另请参见

- [`he list template`](list.md) — 浏览内置模板
- [`he parse`](parse.md) — 使用模板抽取
- [创建自定义模板](../../python/guides/custom-templates.md)
- [模板库](../../templates/index.md)
