---
name: oat-ui
description: guide to implement oat-ui, help user create a simple web UI using semantic html tag for a quick web prototype
---

# Oat UI — Component Library Skill

## What is Oat?
Oat (`@knadh/oat`) is an ultra-lightweight, zero-dependency, semantic HTML + CSS + minimal JS UI library. ~6KB CSS + 2.2KB JS gzipped. No framework, no build step, no Node.js ecosystem required.

---

## Installation

**CDN (quickest):**
```html
<link rel="stylesheet" href="https://unpkg.com/@knadh/oat/oat.min.css">
<script src="https://unpkg.com/@knadh/oat/oat.min.js" defer></script>
```

**npm:**
```bash
npm install @knadh/oat
```
```js
import '@knadh/oat/oat.min.css';
import '@knadh/oat/oat.min.js';
```

**Download:**
```shell
wget https://raw.githubusercontent.com/knadh/oat/refs/heads/gh-pages/oat.min.css
wget https://raw.githubusercontent.com/knadh/oat/refs/heads/gh-pages/oat.min.js
```

---

## Core Philosophy

- **Semantic-first**: Native elements (`<button>`, `<input>`, `<dialog>`, `<details>`) are styled directly — no classes needed for basics.
- **ARIA-driven variants**: Use `data-variant="..."` and `role="..."` for semantic intent.
- **Zero JS for most things**: Accordions, switches, tooltips, dialogs work with pure HTML.
- **WebComponents** for a few dynamic pieces: `<ot-dropdown>`, `<ot-tabs>`.

---

## Dark Mode

Add `data-theme="dark"` to `<body>`. Oat auto-detects system preference. Toggle via JS:
```js
document.documentElement.setAttribute('data-theme', 'dark'); // or 'light'
```

---

## Components Reference

### Typography
All text elements styled automatically — no classes needed.
```html
<h1>Heading 1</h1> ... <h6>Heading 6</h6>
<p>Paragraph with <strong>bold</strong>, <em>italic</em>, <a href="#">link</a></p>
<code>inline code</code>
<pre><code>code block</code></pre>
<blockquote>Quote</blockquote>
<ul><li>Item</li></ul>
<ol><li>Item</li></ol>
```

---

### Accordion
Native `<details>`/`<summary>` — no JS needed. Group with `name` attribute.
```html
<details>
  <summary>Question</summary>
  <p>Answer content here.</p>
</details>

<!-- Grouped (radio-like): -->
<details name="group"><summary>Item 1</summary><p>...</p></details>
<details name="group"><summary>Item 2</summary><p>...</p></details>
```

---

### Alert
Use `role="alert"` with `data-variant` for styling.
```html
<div role="alert" data-variant="success"><strong>Success!</strong> Saved.</div>
<div role="alert" data-variant="warning"><strong>Warning!</strong> Review needed.</div>
<div role="alert" data-variant="error"><strong>Error!</strong> Something failed.</div>
<div role="alert"><strong>Info</strong> Default alert.</div>
```

---

### Avatar
Use `<figure data-variant="avatar">` with `<img>`, `<abbr>` (initials), or icon. Sizes: `.small`, `.large`.
```html
<figure data-variant="avatar" aria-label="Jane Doe">
  <img src="/avatar.png" alt="" />
</figure>
<figure data-variant="avatar" aria-label="Jane Doe">
  <abbr title="Jane Doe">JD</abbr>
</figure>

<!-- Avatar group: -->
<figure data-variant="avatar" role="group" aria-label="Team">
  <figure data-variant="avatar" aria-label="Alice"><img src="/a.png" alt="" /></figure>
  <figure data-variant="avatar" aria-label="Bob"><img src="/b.png" alt="" /></figure>
</figure>
```

---

### Badge
```html
<span class="badge">Default</span>
<span class="badge secondary">Secondary</span>
<span class="badge outline">Outline</span>
<span class="badge success">Success</span>
<span class="badge warning">Warning</span>
<span class="badge danger">Danger</span>
```

---

### Breadcrumb
```html
<nav aria-label="Breadcrumb">
  <ol class="unstyled hstack" style="font-size: var(--text-7)">
    <li><a href="/" class="unstyled">Home</a></li>
    <li aria-hidden="true">/</li>
    <li><a href="/section" class="unstyled" aria-current="page"><strong>Current</strong></a></li>
  </ol>
</nav>
```

---

### Button
`<button>` styled by default. Variants via `data-variant`, styles via class.
```html
<button>Primary</button>
<button data-variant="secondary">Secondary</button>
<button data-variant="danger">Danger</button>
<button class="outline">Outline</button>
<button class="ghost">Ghost</button>
<button disabled>Disabled</button>

<!-- Sizes: -->
<button class="small">Small</button>
<button class="large">Large</button>

<!-- As link: -->
<a href="#" class="button">Link Button</a>

<!-- Button group: -->
<menu class="buttons">
  <li><button class="outline">Left</button></li>
  <li><button class="outline">Center</button></li>
  <li><button class="outline">Right</button></li>
</menu>
```

---

### Card
```html
<article class="card">
  <header>
    <h3>Title</h3>
    <p>Description</p>
  </header>
  <p>Content here.</p>
  <footer class="hstack">
    <button class="outline">Cancel</button>
    <button>Save</button>
  </footer>
</article>
```

---

### Dialog
Zero JS required. Uses native `<dialog>` with `commandfor`/`command` attributes.
```html
<button commandfor="my-dialog" command="show-modal">Open</button>
<dialog id="my-dialog" closedby="any">
  <form method="dialog">
    <header><h3>Title</h3><p>Description.</p></header>
    <div><p>Dialog body content.</p></div>
    <footer>
      <button type="button" commandfor="my-dialog" command="close" class="outline">Cancel</button>
      <button value="confirm">Confirm</button>
    </footer>
  </form>
</dialog>
```
Listen to close event:
```js
document.querySelector('#my-dialog').addEventListener('close', (e) => {
  console.log(e.target.returnValue); // "confirm"
});
```

---

### Dropdown *(WebComponent)*
Wrap in `<ot-dropdown>`. Use `popovertarget` on trigger, `popover` on target. Menu items use `role="menuitem"`.
```html
<ot-dropdown>
  <button popovertarget="my-menu" class="outline">
    Options ▾
  </button>
  <menu popover id="my-menu">
    <button role="menuitem">Profile</button>
    <button role="menuitem">Settings</button>
    <hr>
    <button role="menuitem">Logout</button>
  </menu>
</ot-dropdown>

<!-- Popover (non-menu): -->
<ot-dropdown>
  <button popovertarget="confirm-pop" class="outline">Delete</button>
  <article class="card" popover id="confirm-pop">
    <header><h4>Are you sure?</h4></header>
    <footer>
      <button class="outline small" popovertarget="confirm-pop">Cancel</button>
      <button data-variant="danger" class="small" popovertarget="confirm-pop">Delete</button>
    </footer>
  </article>
</ot-dropdown>
```

---

### Form Elements
All form elements styled automatically. Wrap inputs in `<label>` for association. Use `data-field` for layout.
```html
<form>
  <label data-field>
    Name
    <input type="text" placeholder="Your name" />
  </label>

  <label data-field>
    Email
    <input type="email" placeholder="you@example.com" />
  </label>

  <label data-field>
    Password
    <input type="password" aria-describedby="hint" />
    <small id="hint" data-hint>Minimum 8 characters.</small>
  </label>

  <div data-field>
    <label>Role</label>
    <select aria-label="Select role">
      <option>Admin</option>
      <option>Editor</option>
    </select>
  </div>

  <label data-field>
    Message
    <textarea placeholder="Your message..."></textarea>
  </label>

  <label data-field>
    <input type="checkbox" /> I agree
  </label>

  <fieldset class="hstack">
    <legend>Preference</legend>
    <label><input type="radio" name="pref"> Option A</label>
    <label><input type="radio" name="pref"> Option B</label>
  </fieldset>

  <label data-field>
    Volume
    <input type="range" min="0" max="100" value="50" />
  </label>

  <button type="submit">Submit</button>
</form>

<!-- Input group: -->
<fieldset class="group">
  <input type="text" placeholder="Search" />
  <button>Go</button>
</fieldset>

<!-- Validation error: -->
<div data-field="error">
  <label for="email">Email</label>
  <input type="email" id="email" aria-invalid="true" aria-describedby="err" />
  <div id="err" class="error" role="status">Please enter a valid email.</div>
</div>
```

---

### Grid
12-column CSS grid. Classes: `.container`, `.row`, `.col-{1-12}`, `.offset-{n}`, `.col-end`.
```html
<div class="container">
  <div class="row">
    <div class="col-4">col-4</div>
    <div class="col-4">col-4</div>
    <div class="col-4">col-4</div>
  </div>
  <div class="row">
    <div class="col-6">col-6</div>
    <div class="col-6">col-6</div>
  </div>
  <div class="row">
    <div class="col-4 offset-2">offset-2</div>
    <div class="col-4">col-4</div>
  </div>
</div>
```

---

### Meter
Native `<meter>` element — browser colors based on low/high/optimum.
```html
<meter value="0.8" min="0" max="1" low="0.3" high="0.7" optimum="1"></meter>
<meter value="0.5" min="0" max="1" low="0.3" high="0.7" optimum="1"></meter>
<meter value="0.2" min="0" max="1" low="0.3" high="0.7" optimum="1"></meter>
```

---

### Pagination
Reuses `.buttons` menu — no special markup.
```html
<nav aria-label="Pagination">
  <menu class="buttons">
    <li><a href="#" class="button outline small">← Prev</a></li>
    <li><a href="#" class="button outline small">1</a></li>
    <li><a href="#" class="button small" aria-current="page">2</a></li>
    <li><a href="#" class="button outline small">3</a></li>
    <li><a href="#" class="button outline small">Next →</a></li>
  </menu>
</nav>
```

---

### Progress
Native `<progress>` element.
```html
<progress value="60" max="100"></progress>
<progress value="30" max="100"></progress>
```

---

### Sidebar Layout
Use `data-sidebar-layout` on container (typically `<body>`), `<aside data-sidebar>` for sidebar, `<main>` for content.
```html
<body data-sidebar-layout>
  <!-- Optional top nav: -->
  <nav data-topnav>
    <button data-sidebar-toggle aria-label="Toggle menu">☰</button>
    <span>App Name</span>
  </nav>

  <aside data-sidebar>
    <nav>
      <ul>
        <li><a href="/" aria-current="page">Home</a></li>
        <li>
          <details open>
            <summary>Settings</summary>
            <ul>
              <li><a href="/general">General</a></li>
              <li><a href="/billing">Billing</a></li>
            </ul>
          </details>
        </li>
      </ul>
    </nav>
    <footer><button class="outline" style="width:100%">Logout</button></footer>
  </aside>

  <main>
    Main content area.
  </main>
</body>
```

| Attribute | Element | Purpose |
|---|---|---|
| `data-sidebar-layout` | Container | Grid wrapper (sidebar + main) |
| `data-sidebar-layout="always"` | Container | Always-collapsible (toggle on all screen sizes) |
| `data-topnav` | `<header>` | Full-width top nav |
| `data-sidebar` | `<aside>` | Sticky sidebar |
| `data-sidebar-toggle` | `<button>` | Toggle sidebar open/closed |

---

### Skeleton
Loading placeholders with shimmer. Use `.line` for text, `.box` for images.
```html
<div role="status" class="skeleton line"></div>
<div role="status" class="skeleton box"></div>

<!-- Skeleton card: -->
<article style="display:flex; gap:var(--space-3); padding:var(--space-6)">
  <div role="status" class="skeleton box"></div>
  <div style="flex:1; display:flex; flex-direction:column; gap:var(--space-1)">
    <div role="status" class="skeleton line"></div>
    <div role="status" class="skeleton line" style="width:60%"></div>
  </div>
</article>
```

---

### Spinner
Use `aria-busy="true"` on any element. Size via `data-spinner="small|large"`. Overlay via `data-spinner="overlay"`.
```html
<div aria-busy="true" data-spinner="small"></div>
<div aria-busy="true"></div>
<div aria-busy="true" data-spinner="large"></div>
<button aria-busy="true" data-spinner="small" disabled>Loading</button>

<!-- Overlay on card: -->
<article class="card" aria-busy="true" data-spinner="large overlay">
  Card content dimmed while loading.
</article>
```

---

### Switch
Add `role="switch"` to a checkbox input.
```html
<label><input type="checkbox" role="switch"> Notifications</label>
<label><input type="checkbox" role="switch" checked> Dark mode</label>
<label><input type="checkbox" role="switch" disabled> Disabled</label>
```

---

### Table
Styled automatically. Wrap in `.table` container for horizontal scroll on small screens.
```html
<div class="table">
  <table>
    <thead>
      <tr><th>Name</th><th>Email</th><th>Status</th></tr>
    </thead>
    <tbody>
      <tr>
        <td>Alice</td>
        <td>alice@example.com</td>
        <td><span class="badge success">Active</span></td>
      </tr>
    </tbody>
  </table>
</div>
```

---

### Tabs *(WebComponent)*
Wrap in `<ot-tabs>`. Use `role="tablist"`, `role="tab"`, `role="tabpanel"`.
```html
<ot-tabs>
  <div role="tablist">
    <button role="tab">Account</button>
    <button role="tab">Password</button>
    <button role="tab">Notifications</button>
  </div>
  <div role="tabpanel">
    <h3>Account Settings</h3>
    <p>Manage your account here.</p>
  </div>
  <div role="tabpanel">
    <h3>Password Settings</h3>
    <p>Change your password here.</p>
  </div>
  <div role="tabpanel">
    <h3>Notification Settings</h3>
    <p>Configure notifications here.</p>
  </div>
</ot-tabs>
```

---

### Toast
Call `ot.toast(message, title?, options?)`.
```js
ot.toast('Saved successfully', 'Success', { variant: 'success' });
ot.toast('Something went wrong', 'Error', { variant: 'danger', placement: 'top-left' });
ot.toast('Please review', 'Warning', { variant: 'warning', placement: 'bottom-right' });
ot.toast('New notification', 'Info', { placement: 'top-center' });
```

**Options:**
| Option | Default | Values |
|---|---|---|
| `variant` | `''` | `'success'`, `'danger'`, `'warning'` |
| `placement` | `'top-right'` | `top-left`, `top-center`, `top-right`, `bottom-left`, `bottom-center`, `bottom-right` |
| `duration` | `4000` | ms; `0` = persistent |

**Custom HTML toast:**
```js
ot.toast.el(document.querySelector('#my-template'), { duration: 8000 });

// Dynamic element:
const el = document.createElement('output');
el.className = 'toast';
el.setAttribute('data-variant', 'warning');
el.innerHTML = '<h6 class="toast-title">Warning</h6><p>Custom content.</p>';
ot.toast.el(el);
```

**Clear toasts:**
```js
ot.toast.clear();             // all
ot.toast.clear('top-right');  // specific placement
```

---

### Tooltip
Use standard `title` attribute on any element. Replaced elements (`<img>`, `<iframe>`) need a parent wrapper.
```html
<button title="Save your changes">Save</button>
<a href="#" title="View your profile">Profile</a>

<!-- Image needs wrapper: -->
<span title="An oat logo"><img src="/logo.svg" height="32" /></span>
```

---

## Utility Classes

### Layout
```
hstack          — horizontal flex row (gap + align-items: center)
vstack          — vertical flex column
justify-between / justify-end / justify-center / items-center
gap-{n}         — flex/grid gap
mt-{n}          — margin-top
mb-{n}          — margin-bottom
```

### Text
```
text-light / text-lighter   — muted foreground colors
unstyled                    — remove default link/list styles
```

### Sizing (on buttons, avatars)
```
small / large
```

See full list in [utilities.css](https://github.com/knadh/oat/blob/master/src/css/utilities.css).

---

## Theming (CSS Variables)

Override in your own CSS file (included **after** Oat):
```css
:root {
  --background: rgb(255 255 255);
  --foreground: rgb(9 9 11);
  --card: rgb(255 255 255);
  --card-foreground: rgb(9 9 11);
  --primary: rgb(24 24 27);
  --primary-foreground: rgb(250 250 250);
  --secondary: rgb(244 244 245);
  --secondary-foreground: rgb(24 24 27);
  --muted: rgb(244 244 245);
  --muted-foreground: rgb(113 113 122);
  --faint: rgb(250 250 250);
  --faint-foreground: rgb(161 161 170);
  --accent: rgb(244 244 245);
  --accent-foreground: rgb(24 24 27);
  --danger: rgb(223 81 76);
  --danger-foreground: rgb(250 250 250);
  --success: rgb(76 175 80);
  --success-foreground: rgb(250 250 250);
  --warning: rgb(255 140 0);
  --warning-foreground: rgb(9 9 11);
  --border: rgb(212 212 216);
  --input: rgb(212 212 216);
  --ring: rgb(24 24 27);
}

/* Dark mode overrides: */
[data-theme="dark"] {
  --background: rgb(9 9 11);
  /* ... */
}
```

---

## Composable Recipes

### Split Button
```html
<ot-dropdown>
  <menu class="buttons">
    <li><button class="outline">Save</button></li>
    <li>
      <button class="outline" popovertarget="save-actions" aria-label="More options">▾</button>
    </li>
  </menu>
  <menu popover id="save-actions">
    <button role="menuitem">Save draft</button>
    <button role="menuitem">Save and publish</button>
  </menu>
</ot-dropdown>
```

### Form Card
```html
<article class="card">
  <header><h3>Profile</h3><p class="text-light">Update your info</p></header>
  <div class="mt-4">
    <label data-field>Name <input type="text" /></label>
    <label data-field>Email <input type="email" /></label>
    <label data-field><input type="checkbox" role="switch" checked> Notifications</label>
  </div>
  <footer class="hstack justify-end mt-4">
    <button class="outline">Cancel</button>
    <button>Save</button>
  </footer>
</article>
```

### Empty State
```html
<article class="card align-center">
  <h3>Nothing here yet</h3>
  <p class="text-light">Why don't you create something?</p>
  <footer class="hstack justify-center mt-4">
    <button>Create New</button>
  </footer>
</article>
```

### Stats Card
```html
<article class="card">
  <header class="hstack justify-between items-center">
    <h4>Revenue</h4>
    <span class="badge success">+12%</span>
  </header>
  <h2>$42,200</h2>
  <p class="text-light">vs last month</p>
  <progress value="72" max="100"></progress>
</article>
```

---

## WebComponents Summary

| Component | Tag | Notes |
|---|---|---|
| Dropdown | `<ot-dropdown>` | Popover menus, uses native Popover API |
| Tabs | `<ot-tabs>` | Tab panels with keyboard nav |

---

## Links
- **GitHub**: https://github.com/knadh/oat
- **Docs**: https://oat.ink
- **Demo**: https://oat.ink/demo
- **npm**: `@knadh/oat`
