# Wrap Session Command

Update project documentation to reflect everything completed or changed in this session. Run this before closing any working session.

## Usage
`/wrap`

## What This Command Does

1. **Review the session** — scan conversation history for any files created, modified, or deleted; any features built, bugs fixed, or decisions made

2. **Update `CLAUDE.md`** — revise any sections that are now inaccurate:
   - Architecture, file paths, or folder structure changes
   - New commands, agents, or scripts added
   - Removed or renamed things
   - Changed behaviours or defaults
   Keep it concise — CLAUDE.md is a reference, not a changelog

3. **Update `STATUS.md`** — this is the main output:
   - Tick off anything completed in this session under "What's Built and Working"
   - Move items from "Needs Testing" to "What's Built and Working" if they were tested and passed
   - Add any new items discovered during the session to the right section
   - Update "Still Needs Human Input" if anything was filled in or newly identified
   - Add anything newly deferred to "Deferred / Future"
   - Update the "Last updated" date at the top

4. **Check for conventions** — review what was done this session and ask: did any problem get solved that should become a standing rule? If yes, add it to `docs/conventions.md` using the format:
   ```
   ## [Short rule title]
   **Why:** [what went wrong]
   **How to apply:** [when this rule kicks in]
   ```
   Only add rules for new classes of problem not already covered in `docs/conventions.md`.

5. **Commit and push to GitHub** — stage all changes, create a commit with a short message summarising the session (e.g. `Session 6: hub shortcode + image pipeline`), and push to `origin main`

6. **Confirm** — output a brief summary of what was updated and the commit hash so the user can verify before closing. If `wordpress/seomachine.php` was committed in this session (or any earlier commit this session), also read the `Version:` line from that file and include it in the confirmation — e.g. **Plugin version: 3.3.1** — so the user can cross-check against wp-admin → Must-Use Plugins

## Multi-window / parallel agent policy

When two or more Claude Code windows are open on this project simultaneously, only one should run `/wrap`. Follow these rules to avoid STATUS.md overwrites:

**Which window wraps:**
- The window doing the most significant work "owns" the wrap for that session
- Sub-agents spawned via the Agent tool within a session are disposable — they do not run `/wrap`; only the parent session does
- If a secondary window finishes its task, the user should tell the primary window what it completed before wrapping, so it can incorporate that into STATUS.md

**Section ownership — if parallel sessions are running concurrently:**
STATUS.md should have clearly named sections per work area. Each window only edits its own section — never another window's section. Example:

```
## GTM Content Pipeline      ← owned by whichever window is working on GTM
## GTB Scheduled Publishing  ← owned by the GTB session
## Research Pipeline         ← owned by the research session
```

This prevents last-write-wins collisions when two wraps happen close together.

**Sequencing:**
- Never run `/wrap` from two windows at the same time
- If both need to wrap, finish the secondary window first, then run `/wrap` on the primary window last so it has the complete picture
