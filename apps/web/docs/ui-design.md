# Sentinel UI refinement

Issue: [#173](https://github.com/Dijo-404/sentinel/issues/173).
Owned root: `apps/web/`.

## Direction

Sentinel is a payment operations workspace. Its audience needs to distinguish
case evidence, a proposed action, an approved action, and a verified outcome.
The interface gives those tasks a quiet, consistent frame and keeps financial
state labels intact.

The initial design search returned a professional navy/blue palette and a
minimal enterprise style. Its marketing-first layout and new font pairing were
rejected for the portals. The implementation retains Sentinel's existing fonts
and simulator, shares the portal structure, and reserves strong color for actions
and meaningful states.

## Visual system

| Role             | Dark theme | Light theme |
| ---------------- | ---------- | ----------- |
| Canvas           | `#101B2D`  | `#F3F6FA`   |
| Surface          | `#162338`  | `#FFFFFF`   |
| Text             | `#EDF3FC`  | `#18283F`   |
| Secondary text   | `#ADBBD0`  | `#4E6078`   |
| Primary action   | `#8CB6FF`  | `#245CBB`   |
| Verified outcome | `#79D7B0`  | `#187451`   |

`src/app/tokens.css` owns semantic colors, control radii, theme aliases, and
motion timing. Existing token names remain compatible with the older screens.
Space Grotesk carries headings and metrics; Inter carries body text, navigation,
and controls. JetBrains Mono remains available for references and shortcuts.
Normal labels use sentence case. Data charts consume theme tokens.

Spacing follows a 4px rhythm. Controls have an 8px radius, content panels a 10px
radius, and account panels a 16px radius. Panels use quiet borders; shadows are
reserved for overlays and account surfaces. Primary actions use blue. Verified
states use green, with a text label that explains the state.

## Layout

Content remains left aligned. A persistent sidebar holds workspace identity,
navigation, and the account. The utility bar holds current-page context, search,
mode, density, shortcuts, and theme. Dashboard headings sit directly on the canvas;
metrics and task content sit below them.

```text
Desktop
+----------------+-------------------------------------------+
| Sentinel       | Workspace / Page     Search    Utilities |
| Workspace      +-------------------------------------------+
|                | Greeting                                  |
| Navigation     | Page heading                    Actions   |
|                | Description                               |
|                | Metric     Metric     Metric     Metric   |
|                | Work table / chart / case content         |
| Account        |                                           |
+----------------+-------------------------------------------+

Mobile
+----------------------------------+
| Menu       Sentinel              |
+----------------------------------+
| Search                           |
| Mode                  Utilities  |
| Heading                          |
| Description / Actions            |
| Metrics and task content         |
+----------------------------------+
```

The account shell shares branding and layout across sign-in, signup, recovery,
verification, workspace selection, invitations, and denied-access pages. Its
workflow explanation appears on desktop; mobile gives the form priority.

## Interaction and accessibility

- A skip link moves keyboard focus to portal content.
- The mobile drawer receives focus, contains Tab navigation, closes with Escape,
  restores focus to Menu, and unlocks scrolling when closed or resized to desktop.
- Keyboard shortcuts use a native modal dialog for focus and background handling.
- Theme and density preferences keep their existing persistence behavior.
- The native pointer replaces the animated custom pointer.
- Reduced motion renders landing headlines, section content, and the problem
  statement immediately; normal reveals use shorter, smaller movement.
- Form labels, password-manager attributes, role scope, server validation,
  unavailable states, and financial controls retain their existing behavior.

## Verification and previews

- `make -C apps/web check`: TypeScript and 356 tests in 57 files passed.
- `npm --prefix apps/web run build`: Next.js production build passed.
- `make check`: repository metadata and 21 repository tests passed.
- Prettier 3.10.1 and `git diff --check` passed for the changed files.
- The local production preview passed 104 browser checks with zero runtime errors:
  public/account routes and six role dashboards at 375, 768, 1024, and 1440px in
  both themes; 844px landscape and 200% text checks for each portal; operator queue
  presentation and an explicit unavailable-peer response.
- Keyboard checks covered drawer entry, focus containment, Escape/focus return,
  native shortcut-dialog background handling, and saved compact density.
- A separate reduced-motion check confirmed four section headings and five problem
  phrases are opaque before scrolling. Sampled normal text contrast ranged from
  5.77:1 to 15.47:1; sampled field borders measured 3.49:1 dark and 3.12:1 light.
  These are specific samples, not a complete accessibility certification.

See [browser results](ui-review-results.json),
[desktop account screen](ui-review/account-dark.png),
[light operations dashboard](ui-review/operations-light.png), and
[mobile signup](ui-review/signup-mobile.png).

## Evidence boundary

Verification commands and browser results are recorded in the PR. Browser review
uses local synthetic identity and explicitly intercepted metric payloads. The
unavailable-peer path is also exercised. No real provider, live model, external
pilot, or browser-to-credit assembly is established by this visual review.

Contract: `sentinel.task-contracts.v1`.
SHA-256: `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
