# Incremento 0 Linear Difficulty And Priority Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved Fibonacci difficulty estimates and Linear priorities to all 35 Incremento 0 issues.

**Architecture:** Treat Linear as the system of record and update only `priority` and `estimate`. Take a preflight snapshot, validate estimate `8` with one canary issue, update disjoint batches, and compare the final snapshot with the approved specification.

**Tech Stack:** Linear MCP issue APIs and the local Markdown specification.

## Global Constraints

- Source of truth: `docs/superpowers/specs/2026-08-09-incremento-0-difficulty-priority-design.md`.
- Workspace: `tejulo`.
- Team: `dev`.
- Project: `koty-app`.
- Scope: exactly `DEV-5` through `DEV-39`.
- Preserve every title, description, assignee, status, project, label, relation, and attachment.
- Mutations pass only `id`, `priority`, and `estimate` to `linear_save_issue`.
- Linear priority values are `1` Urgent, `2` High, `3` Medium, and `4` Low.
- Difficulty uses Fibonacci values `2`, `3`, `5`, and `8`.
- Stop immediately if the team rejects estimate `8`; do not substitute another scale.
- Do not perform Git commit, push, merge, or pull request operations.

---

### Task 1: Capture And Validate The Preflight Snapshot

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-difficulty-priority-design.md`
- Modify: none

**Interfaces:**
- Consumes: Linear project `koty-app` and team `dev`.
- Produces: a verified set of 35 issue identifiers safe to mutate.

- [ ] **Step 1: List the complete issue set**

Call `linear_list_issues` with:

```json
{
  "project": "koty-app",
  "team": "dev",
  "limit": 250,
  "includeArchived": true,
  "orderBy": "createdAt",
  "fields": [
    "id",
    "title",
    "priority",
    "estimate",
    "status",
    "assignee",
    "assigneeId",
    "labels",
    "project",
    "team"
  ]
}
```

Expected: `hasNextPage` is `false` and the result contains exactly the 35 identifiers `DEV-5` through `DEV-39`.

- [ ] **Step 2: Validate the mutation boundary**

Confirm every issue is in team `dev`, project `koty-app`, and status `Backlog`. Record each assignee, and stop without mutations if an identifier is absent, duplicated, archived unexpectedly, or assigned outside the approved project.

Expected: 18 issues remain assigned to Juan, 17 remain assigned to Avi, and no issue is unassigned.

### Task 2: Validate Fibonacci Estimates With A Canary

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-difficulty-priority-design.md`
- Modify: none

**Interfaces:**
- Consumes: the validated issue `DEV-19` from Task 1.
- Produces: proof that Linear accepts Fibonacci estimate `8` before bulk mutation.

- [ ] **Step 1: Update the canary issue**

Call `linear_save_issue` with:

```json
{
  "id": "DEV-19",
  "priority": 2,
  "estimate": 8
}
```

Expected: `DEV-19` keeps its title, assignee, status, project, team, labels, and relations; its priority becomes High and its estimate becomes `8`.

- [ ] **Step 2: Stop safely if the scale is unavailable**

If Linear rejects estimate `8`, do not mutate another issue. Report that estimates must be enabled for team `dev` with the Fibonacci scale before rerunning this plan.

### Task 3: Apply Urgent Priorities

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-difficulty-priority-design.md`
- Modify: none

**Interfaces:**
- Consumes: successful canary result from Task 2.
- Produces: nine issues with Urgent priority and approved estimates.

- [ ] **Step 1: Update the nine independent issues**

Call `linear_save_issue` once per row. Calls may run in parallel because they mutate distinct issues.

| Issue | `priority` | `estimate` |
| --- | ---: | ---: |
| `DEV-5` | 1 | 5 |
| `DEV-6` | 1 | 3 |
| `DEV-7` | 1 | 3 |
| `DEV-9` | 1 | 2 |
| `DEV-13` | 1 | 5 |
| `DEV-26` | 1 | 5 |
| `DEV-31` | 1 | 5 |
| `DEV-32` | 1 | 5 |
| `DEV-36` | 1 | 5 |

For each row, pass the issue identifier plus the numeric `priority` and
`estimate` values exactly as shown. Use JSON numbers, not strings.

Expected: all nine responses report Urgent and the estimate from the table.

### Task 4: Apply Remaining High Priorities

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-difficulty-priority-design.md`
- Modify: none

**Interfaces:**
- Consumes: successful canary result from Task 2.
- Produces: the remaining 14 High-priority issues; `DEV-19` was already updated by the canary.

- [ ] **Step 1: Update the 14 independent issues**

Call `linear_save_issue` once per row with `priority: 2` and the listed numeric estimate. Calls may run in parallel.

| Issue | `estimate` |
| --- | ---: |
| `DEV-8` | 5 |
| `DEV-10` | 5 |
| `DEV-14` | 5 |
| `DEV-17` | 3 |
| `DEV-18` | 5 |
| `DEV-20` | 8 |
| `DEV-21` | 5 |
| `DEV-22` | 5 |
| `DEV-27` | 8 |
| `DEV-29` | 3 |
| `DEV-30` | 8 |
| `DEV-33` | 8 |
| `DEV-37` | 8 |
| `DEV-38` | 8 |

Expected: these 14 responses report High; together with `DEV-19`, there are 15 High-priority issues.

### Task 5: Apply Medium And Low Priorities

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-difficulty-priority-design.md`
- Modify: none

**Interfaces:**
- Consumes: successful canary result from Task 2.
- Produces: eight Medium-priority and three Low-priority issues.

- [ ] **Step 1: Update the eight Medium issues**

Call `linear_save_issue` once per row with `priority: 3` and the listed numeric estimate. Calls may run in parallel.

| Issue | `estimate` |
| --- | ---: |
| `DEV-11` | 5 |
| `DEV-12` | 3 |
| `DEV-16` | 5 |
| `DEV-23` | 5 |
| `DEV-24` | 5 |
| `DEV-25` | 5 |
| `DEV-34` | 5 |
| `DEV-35` | 5 |

Expected: all eight responses report Medium and the listed estimate.

- [ ] **Step 2: Update the three Low issues**

Call `linear_save_issue` once per row with `priority: 4` and the listed numeric estimate. Calls may run in parallel.

| Issue | `estimate` |
| --- | ---: |
| `DEV-15` | 5 |
| `DEV-28` | 5 |
| `DEV-39` | 8 |

Expected: all three responses report Low and the listed estimate.

### Task 6: Verify The Final Linear State

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-difficulty-priority-design.md`
- Modify: none

**Interfaces:**
- Consumes: all successful mutation responses from Tasks 2 through 5.
- Produces: final evidence that the approved classification is present without collateral metadata changes.

- [ ] **Step 1: Fetch a fresh final snapshot**

Repeat the `linear_list_issues` call from Task 1 with the same filters and fields.

Expected: 35 issues and `hasNextPage: false`.

- [ ] **Step 2: Compare every issue with the approved table**

Verify exact distributions:

```text
priority: Urgent=9 High=15 Medium=8 Low=3 NoPriority=0
estimate: 2=1 3=5 5=21 8=8 Unestimated=0
```

Expected: each individual `DEV-*` value matches the specification, not only the aggregate counts.

- [ ] **Step 3: Verify preserved metadata**

Compare the final snapshot with Task 1. Confirm team, project, status, assignee, and labels did not change. Query any issue whose response is ambiguous with `linear_get_issue` before reporting completion.

Expected: 18 issues remain assigned to Juan, 17 to Avi, all remain in Backlog, and only priority plus estimate changed.
