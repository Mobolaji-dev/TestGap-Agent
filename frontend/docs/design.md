---
name: agentflow-design
description: Use this skill when you need to apply AgentFlow's sophisticated, futuristic command center design. This includes its dark color scheme with primary purple accents, a clean sans-serif and monospace typography system, and subtle rounded corners for UI elements. Focus on UI/UX design elements and applying this specific visual language to interfaces.
packages:
  - name: clsx
    purpose: Tiny utility for conditionally joining class names
    kind: dependency
    curated: true
  - name: tailwind-merge
    purpose: Merge Tailwind classes without style conflicts
    kind: dependency
    curated: true
  - name: class-variance-authority
    purpose: Type-safe component style variants (CVA)
    kind: dependency
    curated: true
  - name: react-icons
    purpose: Icon library covering Phosphor, Lucide, Feather and more
    kind: dependency
    curated: true
  - name: react-select
    purpose: To implement customizable and accessible select dropdowns for user input.
    kind: dependency
    curated: false
  - name: zustand
    purpose: For managing application state in a simple and scalable way.
    kind: dependency
    curated: false
  - name: react-table
    purpose: To build advanced, sortable, and filterable data tables.
    kind: dependency
    curated: false
---
```yaml
brand: AgentFlow
mood: A sophisticated, futuristic command center for orchestrating complex AI tasks.
scheme: dark

colors:
  primary: "#818cf8"
  primary-bright: "#a5b4fc"
  primary-deep: "#6b72f0"
  on-primary: "#ffffff"
  ink: "#ffffff"
  ink-soft: "#a0a7b8"
  on-ink: "#0a0b0d"
  canvas: "#0a0b0d"
  paper: "#0d0f14"
  cloud: "#111318"
  hairline: "#20232b"
  hairline-strong: "#393d47"
  link: "#a5b4fc"
  link-pressed: "#818cf8"
  success: "#34d399"
  accent-cyan: "#22d3ee"

typography:
  display-xl: { fontFamily: "ui-sans-serif", fontSize: 48px, fontWeight: 600, lineHeight: 1.2 }
  heading-lg: { fontFamily: "ui-sans-serif", fontSize: 16px, fontWeight: 500, lineHeight: 1.4 }
  body-lg: { fontFamily: "ui-sans-serif", fontSize: 16px, fontWeight: 400, lineHeight: 1.5 }
  body-md: { fontFamily: "ui-sans-serif", fontSize: 14px, fontWeight: 500, lineHeight: 1.5 }
  body-sm: { fontFamily: "ui-sans-serif", fontSize: 13px, fontWeight: 400, lineHeight: 1.6 }
  caption-lg: { fontFamily: "ui-sans-serif", fontSize: 11px, fontWeight: 600, lineHeight: 1.5, letterSpacing: 0.8px, textTransform: uppercase }
  caption-md: { fontFamily: "ui-sans-serif", fontSize: 10px, fontWeight: 600, lineHeight: 1.5, letterSpacing: 0.5px, textTransform: uppercase }
  caption-sm: { fontFamily: "ui-sans-serif", fontSize: 9px, fontWeight: 400, lineHeight: 1.5 }
  button-md: { fontFamily: "ui-sans-serif", fontSize: 13px, fontWeight: 500, lineHeight: 1, letterSpacing: 1px, textTransform: uppercase }
  code-md: { fontFamily: "ui-monospace", fontSize: 13px, fontWeight: 400, lineHeight: 1.5 }

rounded:
  none: 0px
  sm: 4px
  md: 8px
  lg: 10px
  xl: 12px
  pill: 9999px

spacing:
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  xxxl: 64px
  section: 80px

shadows:
  none: "none"
  soft-lift: "none"
  card: "none"
  modal: "none"

motion:
  duration-fast: "150ms"
  duration-base: "200ms"
  duration-slow: "2000ms"
  ease-standard: "cubic-bezier(0.4, 0, 0.2, 1)"
  ease-emphasized: "cubic-bezier(0.4, 0, 0.6, 1)"
  transition-colors: "color {motion.duration-fast} {motion.ease-standard}, background-color {motion.duration-fast} {motion.ease-standard}, border-color {motion.duration-fast} {motion.ease-standard}"

components:
  card:
    backgroundColor: "{colors.cloud}"
    rounded: "{rounded.lg}"
    padding: "{spacing.md}"
    border: "1px solid {colors.hairline}"
    shadow: "{shadows.none}"
    cursor: "pointer"
  card-hover:
    border: "1px solid {colors.hairline-strong}"
    backgroundColor: "{colors.paper}"
  button-primary:
    backgroundColor: "{colors.cloud}"
    textColor: "{colors.ink}"
    border: "1px solid {colors.hairline}"
    rounded: "{rounded.md}"
    padding: "16px 24px"
    typography: "{typography.button-md}"
    cursor: "pointer"
  button-primary-hover:
    backgroundColor: "{colors.paper}"
    borderColor: "{colors.hairline-strong}"
  input-text:
    backgroundColor: "{colors.cloud}"
    textColor: "{colors.ink}"
    placeholderColor: "{colors.ink-soft}"
    rounded: "{rounded.xl}"
    padding: "{spacing.md} {spacing.lg}"
    border: "1px solid {colors.hairline}"
    typography: "{typography.body-lg}"
    cursor: "text"
  input-text-focus:
    borderColor: "{colors.primary}"
  navigation-item:
    backgroundColor: "transparent"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.md}"
    padding: "{spacing.xs} {spacing.sm}"
    typography: "{typography.body-md}"
    cursor: "pointer"
  navigation-item-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
  badge:
    backgroundColor: "{colors.success}"
    textColor: "{colors.on-ink}"
    rounded: "{rounded.sm}"
    padding: "2px 6px"
    typography: "{typography.caption-md}"
```

## Visual Theme & Atmosphere
The AgentFlow design system projects a feeling of sophisticated control and futuristic power. It's a dark, focused environment reminiscent of a high-tech command center or a specialized developer tool. The atmosphere is serious and efficient, designed for users who are orchestrating complex, autonomous AI tasks. The aesthetic choices—a deep, dark palette, glowing accents, and precise, grid-like layouts—all serve to minimize distraction and maximize focus on the core functionality. The overall mood is one of confidence, precision, and cutting-edge technology, making the user feel like a supervisor in direct control of powerful agents.

Key Characteristics:
*   **Dark-Mode Native:** The entire interface is built on a dark theme, using a hierarchy of deep blues and blacks like `{colors.canvas}` and `{colors.paper}` to create depth and structure without relying on light.
*   **Flat & Technical:** The design is resolutely flat, with `{shadows.none}` applied universally. Emphasis and hierarchy are achieved through color contrast, typography, and subtle borders using `{colors.hairline}`, not through skeuomorphic depth.
*   **Glowing Accents:** Chromatic color is used sparingly but effectively. The vibrant `{colors.primary}` and `{colors.link}` act as glowing signifiers for active states and interactive elements, cutting through the dark background.
*   **Grid Visualization:** A subtle, non-intrusive grid pattern on the main `{colors.canvas}` background reinforces the technical, analytical nature of the platform, suggesting precision and order.
*   **Spacious & Composed:** Ample whitespace, governed by a clear `{spacing.*}` scale, prevents the dense interface from feeling cluttered. Elements are carefully aligned, creating a calm, composed, and readable layout.
*   **Systematic Typography:** A clear typographic hierarchy, from the commanding `{typography.display-xl}` to the functional `{typography.caption-md}`, ensures information is parsed quickly and easily.
*   **Iconographic Communication:** Simple, single-color icons are used to communicate status and capabilities, with hues like `{colors.success}` and `{colors.accent-cyan}` providing instant visual cues.

## Color Usage Rules
The color palette is deliberately minimal to maintain a focused and professional atmosphere. An AI agent should almost exclusively compose interfaces using this core set: `{colors.canvas}`, `{colors.paper}`, and `{colors.cloud}` for surfaces; `{colors.ink}` and `{colors.ink-soft}` for text; and `{colors.primary}` as the single, potent brand accent.

*   **Surfaces:** The visual hierarchy is built on three levels of darkness. The base layer is always `{colors.canvas}`, the darkest shade. Secondary panels, like the main navigation sidebar, should use `{colors.paper}`. Tertiary, interactive surfaces like cards, buttons, and input fields should use `{colors.cloud}`, the lightest of the dark tones, to signal interactivity.
*   **Text:** The default text color for all content is `{colors.ink}` (`#ffffff`) to ensure maximum readability against the dark surfaces. For secondary or descriptive text, use `{colors.ink-soft}` to de-emphasize it without losing clarity. Text on a light background, such as a `{colors.success}` badge, should use `{colors.on-ink}`.
*   **Primary Accent:** The brand color, `{colors.primary}`, must be used with extreme restraint. It is reserved for indicating a single, primary active state per view (e.g., the current page in the navigation) or a key user-centric element like an avatar. It should appear at most twice in any given viewport to maintain its impact. It must not be used for general decoration.
*   **Links & Interactivity:** Interactive text elements should use `{colors.link}`. On hover or press, they can transition to `{colors.primary}` to provide clear feedback. This creates a consistent interactive language across the UI.
*   **Status Indicators:** Use the dedicated accent colors for at-a-glance status information. `{colors.success}` is for positive states like "Active" or "Complete". `{colors.accent-cyan}` is reserved for specific conceptual icons.
*   **Borders:** Subtle separation between elements is achieved with `{colors.hairline}`. For interactive elements on hover or focus, the border can be strengthened to `{colors.hairline-strong}` or changed to `{colors.primary}` to draw attention.
*   **Flatness is Law:** This is a flat design system. No shadows should be used. Hierarchy and emphasis are derived from the careful application of the color and typography tokens. Never add a box-shadow; use `{shadows.none}`.
*   **No New Colors:** Never introduce a color that is not already defined in the tokens. The existing palette is complete and sufficient. Reusing existing tokens is always preferable to inventing new ones.

## Typography Hierarchy
The AgentFlow brand uses a single, highly versatile font family, `ui-sans-serif`, for nearly all text, ensuring a consistent and modern feel. This system font is used for both headings (via roles like `{typography.display-xl}`) and body copy (via roles like `{typography.body-lg}`). For code snippets and technical identifiers, the `ui-monospace` family is used via the `{typography.code-md}` token. This strict separation maintains readability and reinforces the technical context.

| Role             | Token                    | Use                                                                 |
| ---------------- | ------------------------ | ------------------------------------------------------------------- |
| Display XL       | `{typography.display-xl}`  | The main page headline (e.g., "Meet AgentFlow"). Use only once per page. |
| Heading LG       | `{typography.heading-lg}`  | Sub-headings for distinct content sections (e.g., "Autonomous Execution"). |
| Body Large       | `{typography.body-lg}`     | Primary descriptive text and paragraphs. Also used for main input fields. |
| Body Medium      | `{typography.body-md}`     | Navigation links, primary button text, and other key interactive labels. |
| Body Small       | `{typography.body-sm}`     | Text within cards, item descriptions, and other secondary content areas. |
| Caption Large    | `{typography.caption-lg}`  | Uppercased section titles like "NAVIGATION" and "EXAMPLE TASKS".       |
| Caption Medium   | `{typography.caption-md}`  | Small, uppercased status labels and badges (e.g., "SYSTEM ACTIVE").    |
| Caption Small    | `{typography.caption-sm}`  | The smallest, tertiary-level text, such as user role descriptions.      |
| Button Medium    | `{typography.button-md}`   | For all primary and secondary buttons, featuring uppercase styling.    |
| Code Medium      | `{typography.code-md}`     | For displaying code, file paths, or other technical machine-readable text. |

**Typography Principles:**
1.  **Hierarchy Through Scale and Weight:** With a single primary font, hierarchy is created by disciplined changes in `fontSize` and `fontWeight`. A `{typography.display-xl}` heading is immediately distinguishable from `{typography.body-lg}` text.
2.  **Case and Spacing for Function:** `textTransform: uppercase` and `letterSpacing` are functional tools, not decorative ones. They are reserved for caption and button roles (`{typography.caption-lg}`, `{typography.button-md}`) to signal their specific UI purpose.
3.  **Contrast is Paramount:** All text must have high contrast against its background. `{colors.ink}` on `{colors.canvas}` is the default and should be maintained. `{colors.ink-soft}` provides a lower-contrast option for less important text but must still meet accessibility guidelines.
4.  **Semantic Font Usage:** Use `ui-sans-serif` for all human-readable content. Reserve the monospace `ui-monospace` strictly for the `{typography.code-md}` token to clearly delineate computer-readable text from narrative copy.

## Component Patterns
Components are the building blocks of the AgentFlow UI, composed from the defined design tokens. They are designed to be clear, interactive, and visually consistent.

**Card**
Cards are used to contain discrete pieces of information, such as the "Example Tasks". They are built with a `{colors.cloud}` background, `{rounded.lg}` corners, and a `{spacing.md}` padding. A subtle `{colors.hairline}` border separates the card from the `{colors.canvas}` background. As cards are interactive, they must use `cursor: pointer`. On hover, the border should change to `{colors.hairline-strong}` and the background may subtly shift to `{colors.paper}`. This transition occurs over `{motion.duration-fast}` using the `{motion.ease-standard}` curve.

**Button**
The primary button style is subtle, not loud. It uses a `{colors.cloud}` background with a `{colors.hairline}` border. The label uses `{typography.button-md}`, which is uppercased and has increased letter spacing. On hover, the background color changes to `{colors.paper}` and the border to `{colors.hairline-strong}`. This color transition is animated using `{motion.transition-colors}`. All buttons are interactive and must have `cursor: pointer`.

**Text Input**
Text inputs are designed to be highly visible and easy to use. They have a `{colors.cloud}` background, a prominent `{rounded.xl}` radius, and generous `{spacing.md} {spacing.lg}` padding. Placeholder text uses `{colors.ink-soft}`, while user-entered text uses `{colors.ink}`. The typography is `{typography.body-lg}` to ensure readability. An input field must always use a `cursor: text`. On focus, the border should animate to `{colors.primary}` over `{motion.duration-fast}` to provide clear feedback that the field is active.

**Navigation Item**
Navigation items in the sidebar provide the primary means of moving through the application. In their default state, they have a transparent background and use `{colors.ink-soft}` for the text label. When an item is active, its background changes to `{colors.primary}` and its text color becomes `{colors.on-primary}`. All navigation items, active or not, are clickable and must use `cursor: pointer`. The transition between states is handled by `{motion.transition-colors}`.

**Badge**
Badges are small, inline tags used to communicate status. They have soft `{rounded.sm}` corners and tight padding. Their color is semantic: a `{colors.success}` background indicates a positive state like "SYSTEM ACTIVE". The text within the badge uses `{typography.caption-md}` and should have a high-contrast color like `{colors.on-ink}`.

## Layout & Spacing
The layout of AgentFlow is structured and disciplined, relying on a consistent spacing scale to create a sense of order and clarity. The entire system is built on a 4px base unit, from which all spacing tokens are derived.

The primary layout structure is a two-column design featuring a fixed-width sidebar on a `{colors.paper}` surface and a main, fluid content area on a `{colors.canvas}` surface. This creates a stable anchor for navigation while allowing content to be the focus. The sidebar's width should be generous enough to comfortably fit navigation labels, typically around 240-280px on desktop.

Spacing between elements, both horizontally and vertically, must adhere to the `{spacing.*}` scale.
*   Use `{spacing.xxs}` and `{spacing.xs}` for tight spacing within components, like the gap between an icon and its text.
*   Use `{spacing.sm}` and `{spacing.md}` for component padding, creating consistent internal margins for cards, buttons, and inputs.
*   Use `{spacing.lg}` and `{spacing.xl}` for creating gutters between components or columns in a grid.
*   Use `{spacing.xxl}` and `{spacing.xxxl}` for separating larger, unrelated content blocks.
*   The `{spacing.section}` token is reserved for the vertical distance between major page sections, establishing the primary rhythm of the page scroll.

The decorative grid pattern in the background of the `{colors.canvas}` serves to reinforce this sense of structure and precision but does not dictate element alignment. Element alignment should follow standard grid and flexbox principles, using the spacing tokens as gap values.

## Do's and Don'ts
**Do's:**
1.  **Do** compose all surfaces from `{colors.canvas}`, `{colors.paper}`, and `{colors.cloud}`; do not introduce new hues or shades.
2.  **Do** use the specified fonts for their designated roles: `ui-sans-serif` for headings and body (`{typography.display-xl}`, `{typography.body-lg}`), and `ui-monospace` only for code (`{typography.code-md}`).
3.  **Do** use only `{spacing.*}` tokens for all padding, margins, and gaps to maintain the rhythmic grid.
4.  **Do** apply `cursor: pointer` to all interactive elements, including links, buttons, cards, and navigation items.
5.  **Do** reserve `{colors.primary}` for a single, critical active state or a user avatar to maximize its visual impact.
6.  **Do** use uppercase and letter-spacing as functional cues, strictly for roles like `{typography.button-md}` and `{typography.caption-lg}`.
7.  **Do** ensure all text has high contrast, defaulting to `{colors.ink}` on dark surfaces.
8.  **Do** make hover and focus states obvious and immediate, using transitions like `{motion.transition-colors}`.

**Don'ts:**
1.  **Don't** ever add a box-shadow unless it maps to a real `{shadows.*}` token. This design is flat; emphasis comes from color and weight, not depth.
2.  **Don't** leave the browser-default arrow cursor on a link, tab, or button; every clickable element must explicitly set its cursor.
3.  **Don't** invent new colors. The provided palette is small and intentional; reuse is paramount.
4.  **Don't** use arbitrary pixel values like `17px` or `25px` for layout; snap to the nearest token on the `{spacing.*}` scale.
5.  **Don't** underline links by default; use the `{colors.link}` color to signify them, adding an underline only on hover if desired.
6.  **Don't** use `{colors.primary}` for decorative text or non-interactive elements. It is a status indicator, not a flourish.
7.  **Don't** use a font weight other than what is specified in the `{typography.*}` tokens; maintain the established visual hierarchy.
8.  **Don't** create slow or complex animations. Interactions should feel instant and responsive, using `{motion.duration-fast}` for feedback.

## Responsive Behavior
The design is responsive and must adapt gracefully across a range of screen sizes. A consistent experience is key, with layout adjustments that preserve hierarchy and usability.

| Breakpoint      | Viewport Width  | Layout Strategy                                                                                               |
| --------------- | --------------- | ------------------------------------------------------------------------------------------------------------- |
| Mobile          | <480px          | Single-column layout. Sidebar collapses into a hamburger icon-button. Hero text size (`{typography.display-xl}`) is reduced. Feature cards stack vertically. |
| Mobile-Large    | 480px – 767px   | Still single-column, but with more generous horizontal margins using `{spacing.lg}`. Sidebar remains collapsed.   |
| Tablet          | 768px – 1023px  | Sidebar may appear as a collapsed icon-only bar, expanding on tap/hover. Main content may use a two-column grid for cards. |
| Desktop         | 1024px – 1279px | The standard two-column layout with a fully visible, fixed sidebar as seen in the screenshots.               |
| Desktop-Large   | ≥1280px         | The standard layout with increased horizontal margins around the main content area to prevent lines from becoming too long. The sidebar width remains fixed. |

**Touch Targets:** On all touch-enabled devices, interactive elements like buttons and navigation items must have a minimum tap target size of 44x44px to ensure usability. This can be achieved through adequate padding (e.g., using `{spacing.md}`) even if the visual element appears smaller.

**Image Behavior:** All images and icons should be responsive, scaling proportionally within their containers. SVG icons are preferred for their scalability and sharpness on all displays.

**Collapsing Strategy:** The primary navigation sidebar is the main element that collapses. On mobile, it should be completely hidden behind a hamburger menu icon, transitioning in from the side when opened. On tablets, an icon-only "rail" is a good intermediate state, saving space while keeping primary navigation accessible.

## Iteration Guide
When building or iterating on UI in the AgentFlow style, an AI agent should follow these steps to ensure consistency and adherence to the brand's principles:

1.  **Establish the Foundation:** Begin every new screen with the correct surface colors. The main content area must use `{colors.canvas}`, and any persistent side panels must use `{colors.paper}`.
2.  **Structure with Typography:** Lay out the information hierarchy using the typography tokens. Start with a single `{typography.display-xl}` for the page title, followed by `{typography.body-lg}` for descriptive text. Use `{typography.caption-lg}` to introduce distinct sections.
3.  **Apply the Spacing Scale:** Use the `{spacing.*}` tokens to create all margins, padding, and layout gaps. Use `{spacing.section}` between large, independent sections of the page to establish a clear vertical rhythm. Do not use arbitrary pixel values.
4.  **Compose with Components:** Build interactive elements like cards and buttons using the specified component recipes. Use `{colors.cloud}` for their background, `{colors.hairline}` for their border, and apply the correct `{rounded.*}` token.
5.  **Implement Interactive States:** Ensure every clickable element has a `cursor: pointer`. Define clear hover and focus states, typically by transitioning border color to `{colors.hairline-strong}` or `{colors.primary}` and background color using `{motion.transition-colors}`.
6.  **Use Color with Purpose:** Apply color tokens semantically. Use `{colors.link}` for links, `{colors.success}` for success badges, and `{colors.primary}` with extreme care for a single, primary active state.
7.  **Maintain Flatness:** Double-check that no element has a box-shadow. The entire design must be flat, referencing `{shadows.none}`. Visual depth is an illusion created by the layering of `{colors.canvas}`, `{colors.paper}`, and `{colors.cloud}`.
8.  **Incorporate Code Styling:** For any technical strings, identifiers, or code snippets, apply the `{typography.code-md}` token to render them in the system's designated monospace font.
9.  **Validate Click Targets:** For every interactive element, confirm that its clickable area is at least 44x44px, especially for mobile views, by adjusting padding tokens as needed.
10. **Review for Consistency:** Before finalizing, review the entire composition. Do all buttons look the same? Is the spacing rhythmic? Is the use of `{colors.primary}` minimal and impactful? Does the typography follow the hierarchy? Reuse existing patterns before creating new ones.

## Suggested Packages

Packages that help implement this skill well. Install them with your package manager (examples use pnpm).

- **clsx** — Tiny utility for conditionally joining class names. `pnpm add clsx`
- **tailwind-merge** — Merge Tailwind classes without style conflicts. `pnpm add tailwind-merge`
- **class-variance-authority** — Type-safe component style variants (CVA). `pnpm add class-variance-authority`
- **react-icons** — Icon library covering Phosphor, Lucide, Feather and more. `pnpm add react-icons`

Also worth considering (verify before installing):

- **react-select** — To implement customizable and accessible select dropdowns for user input.. `pnpm add react-select`
- **zustand** — For managing application state in a simple and scalable way.. `pnpm add zustand`
- **react-table** — To build advanced, sortable, and filterable data tables.. `pnpm add react-table`
