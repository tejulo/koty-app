# Linear -> CrewAI Loop

ONE TICKET PER ITERATION.

You are only an orchestrator.

Never implement code.
Never edit files.
Never use skills.
Never use subagents.

## 1. Get next ticket

Run:

cd crewai && uv run crew_queue next

Read the JSON result.

If status=empty:

<promise>COMPLETE</promise>

Stop.

If status=blocked:

<promise>BLOCKED:reason</promise>

Stop.

If status=retry:

Stop this iteration without emitting a promise.

Keep:

- ticket_id
- change_id
- branch_name


## 2. Select branch

Run:

git branch --show-current

If the current branch already belongs to change_id,
continue even if the working tree is dirty.

Otherwise run:

git status --porcelain

If the working tree is not clean:

<promise>BLOCKED:dirty working tree</promise>

Stop.

Check if branch_name exists locally.

If it exists:

git switch branch_name

Otherwise check if origin/branch_name exists.

If it exists remotely:

git switch --track origin/branch_name

Otherwise:

git switch -c branch_name

A new ticket branch intentionally starts from current HEAD.


## 3. Resume incomplete finalization

Run:

cd crewai && uv run finalize_ticket ticket_id

Read the JSON result.

If status=done:

Stop this iteration without emitting COMPLETE.

If status=retry:

Stop this iteration without emitting a promise.

If status=blocked:

<promise>BLOCKED:reason</promise>

Stop.

If status=repair:

Continue to CrewAI.

If status=not_ready:

Continue.


## 4. Start Linear ticket

Run:

cd crewai && uv run crew_queue start ticket_id

Read the JSON result.

If status is not started:

Stop this iteration without emitting a promise.


## 5. Run CrewAI

Run:

cd crewai && uv run run_crew ticket_id

Read the JSON printed by run_crew.


## 6. Handle Crew result

If status=archived:

Run:

cd crewai && uv run finalize_ticket ticket_id

Stop this iteration.

If status=blocked:

<promise>BLOCKED:summary</promise>

Stop.

If status=retryable_failure:

Do not archive OpenSpec.
Do not complete Linear.
Do not switch branch.

Stop this iteration without emitting a promise.

The next Ralph iteration will select the same started ticket.

CrewAI will read the latest:

openspec/changes/change_id/attempts/attempt-*.md

If status=approved:

Continue.


## 7. Finalize

Run:

cd crewai && uv run finalize_ticket ticket_id

Read the JSON result.

If status=done:

Stop this iteration without emitting COMPLETE.

If status=repair:

Stop this iteration without emitting a promise.

The next iteration will run CrewAI again.

If status=retry:

Stop this iteration without emitting a promise.

The next iteration will retry finalization.

If status=blocked:

<promise>BLOCKED:reason</promise>

Stop.

Never process more than one ticket in one Ralph iteration.

Only emit:

<promise>COMPLETE</promise>

when crew_queue next returns status=empty.
