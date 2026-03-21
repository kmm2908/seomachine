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

4. **Commit and push to GitHub** — stage all changes, create a commit with a short message summarising the session (e.g. `Session 6: hub shortcode + image pipeline`), and push to `origin main`

5. **Confirm** — output a brief summary of what was updated and the commit hash so the user can verify before closing
