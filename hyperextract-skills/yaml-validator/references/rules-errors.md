# Common Error Patterns

Common YAML configuration errors and fixes. See [SKILL.md](SKILL.md) for workflow.

---

## Missing Required Field

```
ERROR: Missing required field 'output'
Fix: Add output field definition
```

**Fix**:
```yaml
output:
  description: '...'
  fields:
    - name: field1
      type: str
```

---

## Invalid Type Value

```
ERROR: type value 'graphh' is not valid
Valid values: model, list, set, document, graph, hypergraph, temporal_graph, spatial_graph, spatio_temporal_graph
Fix: Correct to 'graph'
```

**Fix**:
```yaml
type: graph  # Correct
```

---

## Missing Identifiers

```
ERROR: graph type requires identifiers.relation_members
Fix: Add relation_members configuration
```

**Fix**:
```yaml
identifiers:
  entity_id: name
  relation_id: '{source}|{relation_type}|{target}'
  relation_members:
    source: source
    target: target
```

---

## Hypergraph Grouping Errors

### ❌ Field type should be list

```yaml
# Wrong
- name: attackers
  type: str

# Correct
- name: attackers
  type: list
```

### ❌ Format mismatch

```yaml
# Wrong: participants is str, but using list format
relation_members: [participants]

# Correct: simple hypergraph
relation_members: participants

# Correct: nested hypergraph
relation_members: [attackers, defenders]
```

---

## Missing Time/Location Field

```
ERROR: temporal_graph requires identifiers.time_field
Fix: Add time_field configuration
```

**Fix**:
```yaml
identifiers:
  time_field: event_date
```

---

## Naming Convention Errors

| Error | Fix |
|-------|-----|
| name: "earnings_call" | name: "EarningsCall" |
| tags: [Finance] | tags: [finance] |
| field_name: "companyName" | field_name: "company_name" |

---

## Quick Reference

| Error | Quick Fix |
|-------|-----------|
| Missing output | Add output section |
| Invalid type | Check valid types |
| Missing identifiers | Add identifiers section |
| Wrong relation_members type | String vs List |
| Missing time_field | Add to identifiers |
