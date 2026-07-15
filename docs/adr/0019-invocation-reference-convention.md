# ADR-0019: Invocation-Reference Convention — Unqualified Skill Names

## Status
Accepted (attended grill with the maintainer, 2026-07-15; amends the AUD-006 check-11 rationale)

## Context

capivaOS ships its pipeline as Claude Code **skills** (`skills/<name>/SKILL.md`). Claude Code surfaces
a plugin skill under its **unqualified** name — you type `/sprint` — and only prefixes it to
`/plugin:name` (`/capiva:sprint`) when the bare name **collides** with a built-in command. Among
capiva's skills only `init` collides (with the built-in `/init`), so only it appears as `/capiva:init`;
the other thirteen appear bare (`/sprint`, `/grill-spec`, …). In the VS Code extension the command
menu lists the unqualified names and does **not** match a typed `/capiva:sprint` for a non-colliding
skill.

The harness documented the opposite. Every user-facing and in-product surface instructed
`/capiva:<skill>`, and **`harness_lint` check 11 (added by AUD-006) mechanically enforced it** — it
flagged a bare `/sprint` in a hook deny message as "un-namespaced," on the rationale that deny messages
should match the doc surface. That doc surface was itself the qualified form. The net effect: a new
user (especially in the extension) types `/capiva:sprint`, gets "no matching command," and concludes
the plugin is broken. A multi-hour false investigation in the 2026-07-15 session (chasing a manifest
"0 skills" theory, then install scope) traced back to exactly this: the plugin was never broken; the
documented invocation syntax was wrong, and the lint was anchored to the wrong form.

DIST-003 already corrected the user-facing docs (README + troubleshooting). This ADR settles the
convention for the remaining engine surfaces and, critically, for the lint that enforces it — because
the enforcement, not just the prose, was pointing the wrong way.

### Options Considered

**Option A: Keep `/capiva:` qualified as canonical everywhere**
- Append an extension hint to messages ("in the VS Code extension, type `/sprint`"); lint unchanged.
- Pro: unambiguous; the qualified form is collision-proof and works in the terminal.
- Con: every in-product message still *leads* with the form that fails in the extension menu — the
  exact trap, merely annotated. The lint keeps mandating the misleading form.

**Option B: Unqualified `/sprint` canonical for in-product references (chosen)**
- Standardize deny messages + skill descriptions on the bare form; relax the lint to validate
  *resolution* rather than mandate the prefix; note the collision case (`/capiva:init`).
- Pro: matches what users actually type in both the CLI and the extension for the common (no-collision)
  case; removes the trap at its source; keeps the lint's real value (catching dead/typo references).
- Con: a bare name is ambiguous *if* an adopter installs another plugin that ships a colliding skill
  name — then that skill needs qualifying. Rare, and self-correcting (the collision forces the prefix,
  as with `init`).

**Option C: Per-surface rule (bare in messages, qualified in prose docs)**
- Pro: most precise.
- Con: the most rules to encode and lint; a reader moving between a deny message and a doc sees two
  forms for the same skill. Rejected as over-complex for the benefit.

### Lint mechanism sub-decision

Relaxing the enforcement is not symmetric across surfaces:
- **Docs / skill descriptions (check 1)**: prose is safe to scan — a bare `/sprint` that resolves to a
  skill directory is accepted; an unknown `/discovery` is still flagged. Full resolution-based check.
- **Hook Python (check 11)**: a general `/word` scan of Python is *not* false-positive-safe — it would
  flag path segments like `/dev/null`. So check 11 is narrowed to flag only `/capiva:<name>` (qualified)
  references whose `<name>` is not a real skill — the `capiva:` prefix is unambiguous (paths never
  contain it). Bare typos in hook Python are deliberately not scanned; the doc surface (check 1) covers
  the readable references. This limit was accepted explicitly in the grill.

## Decision

**Option B.** Skill references in the harness's in-product surfaces use the **unqualified** name
(`/sprint`); the `/capiva:` prefix appears only where a name collides with a built-in (`/capiva:init`).
`phase_guard` deny/guidance messages and the skill frontmatter `description:` fields are converted.
`harness_lint`'s `/capiva:`-namespace mandate is **relaxed to resolution**: check 1 accepts any
reference that resolves (bare skill, `/capiva:<skill>`, or built-in) and still flags unknown commands;
check 11 is narrowed to catch unresolved `/capiva:<name>` references in hooks (false-positive-safe).
This **amends AUD-006**, whose check 11 enforced the prefix — that rationale (consistency with the doc
surface) is obsolete now that the doc surface is unqualified.

The ~90 canonical `/capiva:` references in prose docs and skill *bodies* are left as-is — they are
valid (both forms resolve) and are internal cross-references, not the first-run trap; DIST-003's note
explains the rule to readers. This ADR does not mandate a sweep.

## Consequences

- The first-run trap is removed at its source: a user hitting a guard denial is sent to `/sprint`,
  which resolves in both the CLI and the extension.
- Both forms remain valid — the relaxed lint accepts `/capiva:sprint` and `/sprint` alike — so existing
  docs and any adopter habit keep working; the change is additive-tolerant, not a hard cutover.
- `harness_lint` keeps its dead-reference value on the doc surface (check 1) and on qualified hook refs
  (check 11); it no longer manufactures findings for the correct bare form. The self-test encodes the
  new behavior (resolvable `/plan` passes; unknown `/discovery` and stale `/capiva:sprnt` are caught).
- Accepted residual: a bare skill name collides if an adopter ships a same-named skill from another
  plugin; Claude Code then requires the prefix for disambiguation (the `init` precedent). Documented,
  not prevented.
- Accepted limit: bare typos inside hook Python are not lint-caught (no safe scan); the risk is low
  (deny-message strings are small and reviewed) and the doc surface is covered.
- Revisit when: Claude Code changes how the extension surfaces plugin commands, or a real cross-plugin
  skill-name collision appears in practice.
