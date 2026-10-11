---
name: frontend-page-rules
description: Rules and conventions to follow whenever building or editing frontend pages/components in a React project — covers file/folder structure (one component or page per file, no monolithic files), visual design consistency (spacing, typography, color), accessibility/responsiveness, UI states and forms, performance, and code clarity. This file is the base; if a design.md file exists alongside it, that file extends it with the project's actual theme (typography, colors, tokens), and both must be read and applied together on every page. Use this whenever generating new pages, splitting up existing components, or reviewing frontend code for structure and design quality.
---

# Frontend Page Rules

These are standing rules for building frontend pages in a React project. They apply whether you're scaffolding a new page, adding a feature to an existing one, or refactoring.

## Working with design.md

This file (`SKILL.md`) is the **base**. A `design.md` file in the same folder, when present, is an **extension** that supplies the project's specific theme. The two work together on every page — never ignore one in favor of the other.

- **Always check for `design.md` before styling anything.** Read it first, then apply this skill's rules on top of it.
- **`design.md` decides the look**: typography, color palette, spacing scale, border radius, shadows, tone, and any other visual tokens it defines. Use its values instead of inventing new ones or using the generic defaults in Section 2.
- **`SKILL.md` decides how it's built**: file structure, component splitting, accessibility, responsiveness, state handling, performance, and code clarity. `design.md` does not override these.
- **Anything `design.md` doesn't mention falls back to this file's defaults.** If it defines colors but not spacing, use its colors and the spacing scale from Section 2.
- **If the two conflict, don't silently pick one.** The usual cases: a `design.md` color combination fails contrast requirements, or a style choice would make a mobile layout unusable. In those cases, keep `design.md`'s intent as close as possible, satisfy the accessibility/functionality rule, and tell the user what was adjusted and why so they can decide.
- If there is no `design.md`, use the defaults in this file and mention that none was found.

## 1. File & Folder Structure

**Never pack multiple pages or unrelated components into one file.** Each page gets its own file, and each non-trivial component gets its own file too.

Default layout:
```
src/
├── pages/          # one file per route/page (e.g. LoginPage.jsx, DashboardPage.jsx)
├── components/      # reusable UI pieces, one per file
│   └── ui/          # small generic building blocks (Button.jsx, Input.jsx, Card.jsx)
├── hooks/           # custom hooks (useAuth.js, useFetch.js)
├── utils/           # pure helper functions, grouped by concern (formatDate.js, validators.js)
├── lib/ or api/      # API/data-fetching logic, separate from UI
└── styles/           # shared design tokens if not using a utility framework
```

Rules of thumb for splitting:
- If a page file is doing layout AND business logic AND API calls, pull the logic and API calls out into hooks/`lib` files.
- A "complicated function" — anything with non-trivial branching, more than ~20-30 lines, or logic reused in more than one place — goes in its own file under `utils/` or `hooks/`, not inline in the component.
- A component gets split out of its parent page as soon as it's reused, or once it starts managing its own state/logic distinct from the page's.
- Name files after what they export (`UserCard.jsx` exports `UserCard`), so the file tree itself is navigable without opening files.
- Keep one default export per file for pages/components; avoid dumping several unrelated components in a single file "for convenience."

## 2. Visual & Design Consistency

Follow the "Working with design.md" section above: if a `design.md` exists, its tokens are used; otherwise use the defaults below.

Establish a small set of design tokens up front and reuse them everywhere — don't let each page invent its own spacing, colors, or type sizes.

- **Spacing**: pick a scale (e.g. 4/8/12/16/24/32/48/64px) and only use values from it. If using Tailwind, stick to the default spacing scale rather than arbitrary values.
- **Typography**: one or two type families max, with a defined scale (e.g. sizes for h1–h3, body, caption). Don't mix ad-hoc font sizes across pages.
- **Color**: define a palette (4-6 core colors: background, surface, text, primary/accent, border, error/success) as tokens/CSS variables, and reference those tokens instead of hardcoding hex values inline.
- **Components over duplication**: if the same visual pattern (button style, card, form field) appears on more than one page, it's a shared component — not copy-pasted markup.
- Avoid generic/templated defaults unless they genuinely fit the product: the cream-background-serif-terracotta-accent look, identical rounded cards with the same soft shadow on everything, ALL-CAPS tracked-out eyebrow labels, and arrows appended to every button/link. Make deliberate choices about palette and type suited to what the page is actually for, rather than reaching for the same "safe" template every time.
- Keep one clear visual hierarchy per page — one element carries the most visual weight; the rest stays quiet and disciplined.

## 3. Accessibility & Responsiveness

- Use semantic HTML first (`<button>`, `<nav>`, `<main>`, `<label>`, headings in order) before reaching for generic `<div>`s with click handlers.
- Every interactive element must be keyboard-reachable and show a visible focus state — never remove `outline` without providing a replacement focus style.
- Form inputs always have an associated `<label>` (or `aria-label` where a visible label isn't appropriate).
- Maintain sufficient color contrast for text against its background (roughly WCAG AA — 4.5:1 for body text).
- Build mobile-first or at minimum verify every page down to a small mobile viewport (~375px wide) — no fixed-width layouts that break on narrow screens.
- **Any responsive nav bar must actually work on mobile, not just look right.** If a hamburger/menu icon is shown at mobile widths, it must open and close the nav on tap/click (state toggle wired up, correct z-index so the menu isn't hidden behind other content, and the toggle button itself is a real interactive element — not a static icon with no handler). Test this explicitly at mobile width before considering a nav "done."
- Respect `prefers-reduced-motion` for any non-trivial animation.
- Images and icons that convey meaning get `alt` text; purely decorative ones get `alt=""`.

## 4. States, Forms & Feedback

Every screen or component that depends on data or user action must handle all of its states, not just the happy path.

- **Four states for anything that loads data**: loading (skeleton or spinner, not a blank screen), empty (explain what belongs here and how to add it), error (say what went wrong in plain language and offer a retry or next step), and success. Never leave a state as a blank area or a raw error string.
- **Error messages tell the user what to do next.** "Couldn't load your transactions. Check your connection and try again." beats "Something went wrong."
- **Forms**: validate inline as the user goes, keep their input when a submission fails, disable the submit button while a request is in flight so nothing is submitted twice, and show clear confirmation on success.
- **Irreversible or money-related actions**: show the user what is about to happen (amount, recipient, consequence) and ask for confirmation before it happens.
- Every user action that triggers a request gets visible feedback (a pending state on the button, a toast, or an inline message) so the user is never left guessing whether it worked.

## 5. Performance

Assume real users on slow networks and mid-range phones, not a fast dev laptop.

- Lazy-load routes/pages (`React.lazy` + `Suspense`) so the first load only ships what the first screen needs.
- Size and compress images appropriately, use modern formats where possible, give images explicit width/height to prevent layout shift, and lazy-load images below the fold.
- Avoid heavy dependencies for small jobs; before adding a library, check whether plain JS or an existing dependency already covers it.
- Don't fetch the same data repeatedly or on every keystroke: debounce search inputs, and avoid unnecessary re-renders from state kept higher in the tree than it needs to be.
- Show something useful quickly (layout and skeletons first, data when it arrives) rather than waiting to render everything at once.
- Test at least once with network throttling on (browser dev tools "Slow 4G") for any page that loads data.

## 6. Code Clarity & Comments

Write code so an intermediate developer (comfortable with JS basics, still learning React patterns) can follow it without looking things up.

- Prefer clear, descriptive names over clever or terse ones — `isMenuOpen` over `flag`, `handleNavToggle` over `fn1`. Spell out words rather than abbreviating unless the abbreviation is extremely standard (`props`, `ref`, `idx`).
- Favor straightforward, readable syntax over dense one-liners — e.g. a plain `if`/`else` or a named helper function over a deeply nested ternary or chained ops that pack several operations into one line.
- Add a comment wherever the "why" isn't obvious from the code itself: non-obvious state, workarounds, effect dependencies, regex, math/conditionals with several branches. Skip comments that just restate what the line already says (no `// increment count` above `count++`).
- At the top of a non-trivial component or hook, a one- or two-line comment describing what it's responsible for is helpful, especially once files are split up per Section 1.
- When in doubt, write it the way you'd want it explained to someone a few weeks into learning React — not the most compact way to express it.

## 7. Before finishing a page

Quick self-check before considering a page done:
- [ ] Did I check for `design.md` and apply it together with this file's rules?
- [ ] Does every data-dependent view handle loading, empty, error, and success states?
- [ ] Do forms keep input on failure, block double-submits, and confirm success?
- [ ] Is anything heavy loaded up front that could be lazy-loaded? Does the page behave on a throttled connection?
- [ ] Is this page in its own file under `pages/`, with logic/API calls pulled into `hooks/`/`utils/`/`lib/` rather than inlined?
- [ ] Are spacing, type, and color values coming from the shared tokens/scale, not one-off values?
- [ ] Does it work and look reasonable at mobile width?
- [ ] Can I tab through every interactive element and see where focus is?
- [ ] If there's a nav bar, does the mobile hamburger menu actually open/close when tapped?
- [ ] Are names descriptive and syntax kept simple enough for an intermediate dev to follow, with comments on anything non-obvious?
- [ ] Any component used more than once — is it actually a shared component now?
