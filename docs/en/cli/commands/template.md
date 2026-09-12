# he template validate

Check a Hyper-Extract YAML template for structural and semantic problems before you run extraction.

`load_template()` only verifies that the document matches the Pydantic `TemplateCfg` shape. Identifier fields that do not exist, display placeholders that do not match the schema, and missing time/location fields on temporal or spatial types otherwise fail later, during extraction. This command runs those checks up front.

`template` is a command group; `validate` is the subcommand.

---

## Synopsis

```bash
he template validate PATH [--json] [--all]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `PATH` | Template YAML file, or a directory when `--all` is set |

## Options

| Option | Alias | Default | Description |
|--------|-------|---------|-------------|
| `--json` | | off | Print machine-readable JSON instead of Rich text |
| `--all` | | off | Validate every `*.yaml` / `*.yml` file under a directory |

---

## Description

The validator is a sidecar for template authors. It does **not** change runtime `load_template()` behavior.

Checks follow `hyperextract-skills/yaml-validator/` and `templates/DESIGN_GUIDE.md`:

| Code | Check | Severity |
|------|--------|----------|
| `HE-T001` | YAML is parseable | error |
| `HE-T002` | Document matches `TemplateCfg` | error |
| `HE-T003` | Identifier fields (`entity_id`, `relation_id`, `relation_members`, `item_id`, `time_field`, `location_field`) exist on the relevant output schema | error |
| `HE-T004` | `relation_members` type matches AutoType (`graph` / temporal / spatial → dict; `hypergraph` → string or list). Dict **values** are edge-schema field names. Hypergraph member fields must be `type: list`. | error |
| `HE-T005` | Display `{field}` placeholders exist on the corresponding schema | error |
| `HE-T006` | Temporal types define `time_field`; spatial types define `location_field` | error |
| `HE-T007` | Declared languages are present on bilingual dict fields | warning |
| `HE-T008` | Field count exceeds the DESIGN_GUIDE limit of 5 (graph entity/relation, or `model`/`list`/`set` `output.fields`) | warning |
| `HE-T009` | `domain/name` collides with a Gallery preset | warning |

Exit code **1** if any **error** is reported; **0** if the template is clean or has warnings only.

---

## Examples

### Validate one file

```bash
he template validate ./my_template.yaml
```

### Machine-readable diagnostics

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

### Validate every bundled preset

```bash
he template validate hyperextract/templates/presets --all
```

Directory mode with `--json` wraps each file:

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

The CLI is a thin wrapper around the same checks:

```python
from hyperextract.utils.template_engine import validate_template

result = validate_template("my_template.yaml")
print(result.ok, result.to_dict())
```

---

## See Also

- [`he list template`](list.md) — Browse bundled templates
- [`he parse`](parse.md) — Extract with a template
- [Creating Custom Templates](../../python/guides/custom-templates.md)
- [Template Library](../../templates/index.md)
