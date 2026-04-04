---
name: carbon-web-components
description: guide to implement @carbon/web-components (IBM Carbon Design System), help user create web UIs using Carbon custom elements (cds-*) for enterprise-grade, accessible interfaces
---

# Carbon Web Components — Component Library Skill

## What is @carbon/web-components?

`@carbon/web-components` is IBM's Carbon Design System implemented as Custom Elements v1 + Shadow DOM v1 web components. All components use the `cds-` prefix. Framework-agnostic, works with vanilla HTML, React, Angular, Vue, etc.

---

## Installation

**npm:**
```bash
npm install --save @carbon/web-components
```
Then import individual component modules:
```js
import '@carbon/web-components/es/components/button/index.js';
import '@carbon/web-components/es/components/dropdown/index.js';
```

**CDN (no bundler needed):**
```html
<script type="module" src="https://1.www.s81c.com/common/carbon/web-components/version/v2.51.1/button.min.js"></script>
```
Each component has its own CDN file: `accordion.min.js`, `button.min.js`, `checkbox.min.js`, `dropdown.min.js`, `modal.min.js`, `notification.min.js`, `tabs.min.js`, `text-input.min.js`, etc.

**Recommended font (IBM Plex Sans):**
```css
body { font-family: 'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif; }
```

**Hide unregistered components to avoid flash:**
```css
cds-button:not(:defined) { visibility: hidden; }
```

---

## Core Philosophy

- All components use the `cds-` prefix (Carbon Design System)
- Attributes use `kebab-case`; JS properties use `camelCase`
- Theming via `data-carbon-theme` attribute: `white` (default), `g10`, `g90`, `g100`
- Shadow DOM encapsulation — style via CSS custom properties or `::part()`
- Custom events follow the pattern `cds-<component>-<action>` (e.g. `cds-modal-closed`)

---

## Components Reference

### Accordion

```html
<cds-accordion>
  <cds-accordion-item title="Panel A">Panel A content</cds-accordion-item>
  <cds-accordion-item title="Panel B" open>Panel B content (open by default)</cds-accordion-item>
  <cds-accordion-item title="Panel C" disabled>Panel C (disabled)</cds-accordion-item>
</cds-accordion>
```

Key attributes on `cds-accordion`: `size` (sm|md|lg), `alignment` (start|end), `is-flush`  
Key attributes on `cds-accordion-item`: `title`, `open`, `disabled`  
Events: `cds-accordion-item-beingtoggled`, `cds-accordion-item-toggled`

---

### Button

```html
<!-- Kinds -->
<cds-button>Primary</cds-button>
<cds-button kind="secondary">Secondary</cds-button>
<cds-button kind="tertiary">Tertiary</cds-button>
<cds-button kind="ghost">Ghost</cds-button>
<cds-button kind="danger">Danger</cds-button>
<cds-button kind="danger-tertiary">Danger Tertiary</cds-button>
<cds-button kind="danger-ghost">Danger Ghost</cds-button>

<!-- Sizes: xs, sm, md, lg (default), xl, 2xl -->
<cds-button size="sm">Small</cds-button>
<cds-button size="xl">XLarge</cds-button>

<!-- As link -->
<cds-button href="https://www.carbondesignsystem.com">Navigate</cds-button>

<!-- Disabled -->
<cds-button disabled>Disabled</cds-button>

<!-- Icon-only button with tooltip -->
<cds-button tooltip-text="Add item" tooltip-position="bottom">
  <svg slot="icon" focusable="false" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="16" height="16">
    <path d="M17 15V8h-2v7H8v2h7v7h2v-7h7v-2z"/>
  </svg>
</cds-button>

<!-- Button set -->
<cds-button-set>
  <cds-button kind="secondary">Cancel</cds-button>
  <cds-button>Save</cds-button>
</cds-button-set>
```

Key attributes: `kind`, `size`, `href`, `disabled`, `tooltip-text`, `tooltip-position` (top|right|bottom|left), `tooltip-alignment` (start|center|end), `is-expressive`

---

### Breadcrumb

```html
<cds-breadcrumb>
  <cds-breadcrumb-item>
    <cds-link href="/">Home</cds-link>
  </cds-breadcrumb-item>
  <cds-breadcrumb-item>
    <cds-link href="/section">Section</cds-link>
  </cds-breadcrumb-item>
  <cds-breadcrumb-item aria-current="page">Current page</cds-breadcrumb-item>
</cds-breadcrumb>
```

---

### Checkbox

```html
<cds-checkbox-group legend-text="Group label" helper-text="Optional helper text">
  <cds-checkbox label-text="Option A" value="a"></cds-checkbox>
  <cds-checkbox label-text="Option B" value="b" checked></cds-checkbox>
  <cds-checkbox label-text="Option C" value="c" disabled></cds-checkbox>
</cds-checkbox-group>

<!-- Single checkbox -->
<cds-checkbox label-text="I agree to the terms" value="agree"></cds-checkbox>

<!-- Indeterminate -->
<cds-checkbox label-text="Select all" indeterminate></cds-checkbox>
```

Key attributes: `label-text`, `value`, `checked`, `disabled`, `indeterminate`, `invalid`, `warn`, `readonly`, `hide-label`

---

### Dropdown

```html
<cds-dropdown
  title-text="Select an option"
  label="Choose one"
  value="option-a">
  <cds-dropdown-item value="option-a">Option A</cds-dropdown-item>
  <cds-dropdown-item value="option-b">Option B</cds-dropdown-item>
  <cds-dropdown-item value="option-c" disabled>Option C (disabled)</cds-dropdown-item>
</cds-dropdown>

<!-- Inline variant -->
<cds-dropdown type="inline" title-text="Sort by" value="newest">
  <cds-dropdown-item value="newest">Newest first</cds-dropdown-item>
  <cds-dropdown-item value="oldest">Oldest first</cds-dropdown-item>
</cds-dropdown>
```

Key attributes on `cds-dropdown`: `title-text`, `label`, `value`, `size` (sm|md|lg), `type` (inline), `disabled`, `direction` (top|bottom), `invalid`, `invalid-text`, `warn`, `warn-text`, `helper-text`  
Events: `cds-dropdown-beingselected`, `cds-dropdown-selected`

---

### Multi Select

```html
<cds-multi-select title-text="Select options" label="Choose items">
  <cds-multi-select-item value="a">Option A</cds-multi-select-item>
  <cds-multi-select-item value="b" selected>Option B</cds-multi-select-item>
  <cds-multi-select-item value="c">Option C</cds-multi-select-item>
</cds-multi-select>
```

---

### Form

`cds-form` is a thin wrapper that adds Carbon styling to a native `<form>`. Use `cds-form-group` for logical groupings of fields (renders a `<fieldset>`).

```html
<cds-form id="my-form">
  <cds-stack gap="7">

    <!-- Group checkboxes under a legend -->
    <cds-form-group legend-text="Notifications">
      <cds-checkbox default-checked>Email alerts</cds-checkbox>
      <cds-checkbox>SMS alerts</cds-checkbox>
      <cds-checkbox disabled>Push notifications (disabled)</cds-checkbox>
    </cds-form-group>

    <cds-text-input label="Full name" placeholder="Jane Doe"></cds-text-input>

    <cds-button type="submit">Submit</cds-button>

  </cds-stack>
</cds-form>
```

Key attributes on `cds-form-group`: `legend-text`  
Key attributes on `cds-form`: inherits all native `<form>` attributes (`action`, `method`, etc.)  
Note: `cds-checkbox` accepts its label as **slot content** (e.g. `<cds-checkbox>Label</cds-checkbox>`) **or** via `label-text` attribute.

CDN: `form.min.js`

---

### Form Elements

**Text Input:**
```html
<cds-text-input
  label="Email address"
  placeholder="you@example.com"
  type="email"
  helper-text="We'll never share your email."
  value="">
</cds-text-input>

<!-- Invalid state -->
<cds-text-input
  label="Username"
  invalid
  invalid-text="Username is already taken.">
</cds-text-input>

<!-- Warning state -->
<cds-text-input
  label="Password"
  warn
  warn-text="Password is weak.">
</cds-text-input>

<!-- Read only -->
<cds-text-input label="User ID" readonly value="user-123"></cds-text-input>
```

Key attributes: `label`, `placeholder`, `type`, `value`, `disabled`, `readonly`, `invalid`, `invalid-text`, `warn`, `warn-text`, `helper-text`, `size` (sm|md|lg), `hide-label`, `enable-counter`, `max-count`

**Text Area:**
```html
<cds-textarea
  label="Comments"
  placeholder="Enter your comments..."
  helper-text="Max 500 characters"
  rows="4">
</cds-textarea>
```

**Select:**
```html
<cds-select label-text="Country" helper-text="Select your country" placeholder="Choose a country">
  <cds-select-item value="us">United States</cds-select-item>
  <cds-select-item value="uk">United Kingdom</cds-select-item>
</cds-select>
```

**Number Input:**
```html
<cds-number-input
  label="Quantity"
  value="1"
  min="0"
  max="100"
  step="1">
</cds-number-input>
```

**Radio Button:**
```html
<cds-radio-button-group
  legend-text="Select environment"
  name="env"
  value="production">
  <cds-radio-button label-text="Development" value="development"></cds-radio-button>
  <cds-radio-button label-text="Staging" value="staging"></cds-radio-button>
  <cds-radio-button label-text="Production" value="production"></cds-radio-button>
</cds-radio-button-group>
```

**Toggle:**
```html
<cds-toggle label-text="Notifications" checked></cds-toggle>
<cds-toggle label-text="Dark mode" label-a="Off" label-b="On"></cds-toggle>
```

**Search:**
```html
<cds-search
  placeholder="Search..."
  label-text="Search"
  size="md">
</cds-search>
```

**Slider:**
```html
<cds-slider label="Volume" min="0" max="100" value="50" step="1">
  <cds-slider-input type="number"></cds-slider-input>
</cds-slider>
```

**Date Picker:**
```html
<!-- Simple date picker -->
<cds-date-picker>
  <cds-date-picker-input
    kind="single"
    label-text="Date"
    placeholder="mm/dd/yyyy">
  </cds-date-picker-input>
</cds-date-picker>

<!-- Range date picker -->
<cds-date-picker>
  <cds-date-picker-input
    kind="from"
    label-text="Start date"
    placeholder="mm/dd/yyyy">
  </cds-date-picker-input>
  <cds-date-picker-input
    kind="to"
    label-text="End date"
    placeholder="mm/dd/yyyy">
  </cds-date-picker-input>
</cds-date-picker>
```

**Time Picker:**
```html
<cds-time-picker label-text="Start time">
  <cds-time-picker-select slot="time-picker-select-start" aria-label="AM/PM">
    <cds-select-item value="AM">AM</cds-select-item>
    <cds-select-item value="PM">PM</cds-select-item>
  </cds-time-picker-select>
</cds-time-picker>
```

---

### File Uploader

```html
<!-- Button variant (click to browse) -->
<cds-file-uploader
  label-title="Upload files"
  label-description="Max file size is 500 MB. Only .jpg files are supported."
  icon-description="Dismiss file">
  <cds-file-uploader-button
    accept="image/jpeg"
    name="my-upload"
    button-kind="primary"
    size="md"
    multiple>
    Add file
  </cds-file-uploader-button>
</cds-file-uploader>

<!-- Drag-and-drop variant -->
<cds-file-uploader
  label-title="Upload files"
  label-description="Max file size is 1 MB. Supported file types are .jpg and .png.">
  <cds-file-uploader-drop-container
    accept=".jpg .png"
    multiple
    name="drop-upload">
    Drag and drop files here or click to upload
  </cds-file-uploader-drop-container>
</cds-file-uploader>
```

Key attributes on `cds-file-uploader`: `label-title`, `label-description`, `icon-description`, `disabled`  
Key attributes on `cds-file-uploader-button`: `accept`, `name`, `button-kind`, `size`, `multiple`, `disabled`  
Key attributes on `cds-file-uploader-drop-container`: `accept`, `multiple`, `name`, `disabled`  
Key attributes on `cds-file-uploader-item`: `state` (uploading|edit|complete), `invalid`, `size`, `icon-description`, `error-subject`, `error-body`  
Events: `cds-file-uploader-button-changed`, `cds-file-uploader-drop-container-changed`, `cds-file-uploader-item-beingdeleted`, `cds-file-uploader-item-deleted`

CDN: `file-uploader.min.js`

---

### Password Input

A dedicated password input with a built-in show/hide toggle button. It extends `cds-text-input` behavior.

```html
<cds-password-input
  label="Password"
  placeholder="Enter password"
  helper-text="Must be at least 6 characters"
  show-password-visibility-toggle>
</cds-password-input>

<!-- Invalid state -->
<cds-password-input
  label="Password"
  invalid
  invalid-text="Must contain uppercase, lowercase, and a number."
  show-password-visibility-toggle>
</cds-password-input>
```

Key attributes: `label`, `placeholder`, `helper-text` (also slot), `value`, `disabled`, `readonly`, `invalid`, `invalid-text`, `warn`, `warn-text`, `size` (sm|md|lg), `hide-label`, `required`, `pattern`, `autocomplete`, `show-password-visibility-toggle`, `show-password-label`, `hide-password-label`, `tooltip-position`, `tooltip-alignment`, `enable-counter`, `max-count`

CDN: `password-input.min.js`

---

### Combo Box

Filterable single-select dropdown. The user can type to filter items.

```html
<cds-combo-box
  title-text="Select a fruit"
  label="Filter..."
  helper-text="Pick one from the list"
  value="">
  <cds-combo-box-item value="apple">Apple</cds-combo-box-item>
  <cds-combo-box-item value="banana">Banana</cds-combo-box-item>
  <cds-combo-box-item value="cherry">Cherry</cds-combo-box-item>
  <cds-combo-box-item value="date" disabled>Date (disabled)</cds-combo-box-item>
</cds-combo-box>
```

Key attributes on `cds-combo-box`: `title-text`, `label` (placeholder), `value`, `helper-text`, `invalid`, `invalid-text`, `warn`, `warn-text`, `disabled`, `read-only`, `size` (sm|md|lg), `direction` (top|bottom), `allow-custom-value`, `typeahead`  
Events: `cds-combo-box-selected`, `cds-combo-box-beingselected`, `cds-combo-box-toggled`

CDN: `combo-box.min.js`

---

### Content Switcher

Toggle between content sections. Similar to tabs but for in-place content switching.

```html
<cds-content-switcher value="section-1">
  <cds-content-switcher-item value="section-1">First section</cds-content-switcher-item>
  <cds-content-switcher-item value="section-2">Second section</cds-content-switcher-item>
  <cds-content-switcher-item value="section-3" disabled>Third (disabled)</cds-content-switcher-item>
</cds-content-switcher>
```

Key attributes on `cds-content-switcher`: `value`, `size` (sm|md|lg), `selected-index`, `selection-mode` (automatic|manual), `icon`, `low-contrast`  
Key attributes on `cds-content-switcher-item`: `value`, `disabled`, `target` (element ID of target panel)  
Events: `cds-content-switcher-selected`, `cds-content-switcher-beingselected`

CDN: `content-switcher.min.js`

---

### Modal

```html
<!-- Trigger -->
<cds-button id="open-modal">Open modal</cds-button>

<!-- Modal -->
<cds-modal id="my-modal" size="md">
  <cds-modal-header>
    <cds-modal-close-button></cds-modal-close-button>
    <cds-modal-label>Optional label</cds-modal-label>
    <cds-modal-heading>Modal Title</cds-modal-heading>
  </cds-modal-header>
  <cds-modal-body>
    <cds-modal-body-content>
      Modal body content goes here.
    </cds-modal-body-content>
  </cds-modal-body>
  <cds-modal-footer>
    <cds-modal-footer-button kind="secondary" data-modal-close>Cancel</cds-modal-footer-button>
    <cds-modal-footer-button kind="primary">Save</cds-modal-footer-button>
  </cds-modal-footer>
</cds-modal>

<script>
  document.getElementById('open-modal').addEventListener('click', () => {
    document.getElementById('my-modal').setAttribute('open', '');
  });
  document.getElementById('my-modal').addEventListener('cds-modal-closed', () => {
    console.log('Modal closed');
  });
</script>
```

Key attributes on `cds-modal`: `open`, `size` (xs|sm|md|lg), `has-scrolling-content`, `prevent-close-on-click-outside`, `alert`, `full-width`  
`data-modal-close` on a button inside the modal closes it automatically.  
Events: `cds-modal-beingclosed`, `cds-modal-closed`

---

### Notifications

```html
<!-- Inline notification -->
<cds-inline-notification
  kind="success"
  title="Success"
  subtitle="Your changes have been saved."
  open>
</cds-inline-notification>

<!-- Toast notification -->
<cds-toast-notification
  kind="error"
  title="Error"
  subtitle="Something went wrong."
  caption="00:00:00 AM"
  open
  timeout="5000">
</cds-toast-notification>

<!-- Actionable notification (traps focus, requires user action) -->
<cds-actionable-notification
  kind="warning"
  title="Warning"
  subtitle="Your session is about to expire."
  action-button-label="Extend session"
  open>
</cds-actionable-notification>

<!-- Callout (static, non-modal, inline with page content) -->
<cds-callout-notification
  kind="info"
  title="Info"
  open>
  <span slot="subtitle">This is informational content.</span>
</cds-callout-notification>
```

`kind` values: `success`, `error`, `warning`, `info`  
Key attributes: `kind`, `title`, `subtitle` (also slot), `open`, `timeout` (ms, null = persistent), `hide-close-button`, `low-contrast`, `action-button-label` (actionable only)  
Events: `cds-notification-beingclosed`, `cds-notification-closed`

---

### Tabs

```html
<!-- Line tabs (default) -->
<cds-tabs value="tab-1">
  <cds-tab value="tab-1" target="panel-1">Dashboard</cds-tab>
  <cds-tab value="tab-2" target="panel-2">Monitoring</cds-tab>
  <cds-tab value="tab-3" target="panel-3" disabled>Settings</cds-tab>
  <cds-tab-panel id="panel-1">Dashboard content</cds-tab-panel>
  <cds-tab-panel id="panel-2">Monitoring content</cds-tab-panel>
  <cds-tab-panel id="panel-3">Settings content</cds-tab-panel>
</cds-tabs>

<!-- Contained tabs -->
<cds-tabs type="contained" value="tab-1">
  <cds-tab value="tab-1" target="panel-a">Tab 1</cds-tab>
  <cds-tab value="tab-2" target="panel-b">Tab 2</cds-tab>
  <cds-tab-panel id="panel-a">Panel A</cds-tab-panel>
  <cds-tab-panel id="panel-b">Panel B</cds-tab-panel>
</cds-tabs>
```

Events: `cds-tabs-selected`, `cds-tabs-beingselected`

---

### DataTable

```html
<cds-table>
  <cds-table-head>
    <cds-table-header-row>
      <cds-table-header-cell>Name</cds-table-header-cell>
      <cds-table-header-cell>Status</cds-table-header-cell>
      <cds-table-header-cell>Role</cds-table-header-cell>
    </cds-table-header-row>
  </cds-table-head>
  <cds-table-body>
    <cds-table-row>
      <cds-table-cell>Alice Johnson</cds-table-cell>
      <cds-table-cell>Active</cds-table-cell>
      <cds-table-cell>Admin</cds-table-cell>
    </cds-table-row>
    <cds-table-row>
      <cds-table-cell>Bob Smith</cds-table-cell>
      <cds-table-cell>Inactive</cds-table-cell>
      <cds-table-cell>Viewer</cds-table-cell>
    </cds-table-row>
  </cds-table-body>
</cds-table>
```

Key attributes on `cds-table`: `size` (xs|sm|md|lg), `is-sortable`, `zebra`, `use-static-width`

---

### Tag

```html
<cds-tag type="blue">Blue</cds-tag>
<cds-tag type="green">Green</cds-tag>
<cds-tag type="red">Red</cds-tag>
<cds-tag type="purple">Purple</cds-tag>
<cds-tag type="cyan">Cyan</cds-tag>
<cds-tag type="teal">Teal</cds-tag>
<cds-tag type="magenta">Magenta</cds-tag>
<cds-tag type="warm-gray">Warm gray</cds-tag>
<cds-tag type="outline">Outline</cds-tag>

<!-- Dismissible tag -->
<cds-tag type="blue" filter>Dismissible</cds-tag>

<!-- Disabled -->
<cds-tag type="green" disabled>Disabled</cds-tag>
```

---

### Loading / Inline Loading

```html
<!-- Full-page loading overlay -->
<cds-loading description="Loading content..." active></cds-loading>

<!-- Small spinner -->
<cds-loading small active></cds-loading>

<!-- Inline loading (for actions) -->
<cds-inline-loading status="active">Loading...</cds-inline-loading>
<cds-inline-loading status="finished">Done!</cds-inline-loading>
<cds-inline-loading status="error">Error occurred.</cds-inline-loading>
```

`status` values: `inactive`, `active`, `finished`, `error`

---

### Progress Bar

```html
<cds-progress-bar
  label="Uploading file..."
  helper-text="25 of 100 MB"
  value="25"
  max="100">
</cds-progress-bar>

<!-- Indeterminate -->
<cds-progress-bar label="Loading..." status="active"></cds-progress-bar>
```

---

### Progress Indicator

```html
<cds-progress-indicator>
  <cds-progress-step
    label="Personal info"
    state="complete">
  </cds-progress-step>
  <cds-progress-step
    label="Account setup"
    state="current"
    description="Current step">
  </cds-progress-step>
  <cds-progress-step
    label="Review"
    state="incomplete">
  </cds-progress-step>
  <cds-progress-step
    label="Submit"
    state="incomplete"
    disabled>
  </cds-progress-step>
</cds-progress-indicator>
```

`state` values: `complete`, `current`, `incomplete`, `invalid`  
Add `vertical` attribute for vertical layout.

---

### Pagination

```html
<cds-pagination
  page-size="10"
  total-items="100"
  page="1">
</cds-pagination>
```

Events: `cds-pagination-changed-current`, `cds-page-sizes-select-changed`

---

### Link

```html
<cds-link href="https://www.carbondesignsystem.com">Carbon Design System</cds-link>
<cds-link href="#" disabled>Disabled link</cds-link>
<cds-link href="#" inline>Inline link</cds-link>
```

---

### Tooltip / Toggletip

```html
<!-- Tooltip (hover/focus triggered) -->
<cds-tooltip align="bottom" enter-delay-ms="150">
  <button>Hover me</button>
  <cds-tooltip-content>Tooltip text</cds-tooltip-content>
</cds-tooltip>

<!-- Toggletip (click triggered, for interactive content) -->
<cds-toggletip alignment="bottom">
  <p slot="body-text">Toggletip content here.</p>
  <button slot="trigger">Click me</button>
</cds-toggletip>

<!-- Definition tooltip (inline term definition) -->
<cds-definition-tooltip definition="This is the definition." align="bottom">
  Term
</cds-definition-tooltip>
```

---

### Popover

```html
<cds-popover open align="bottom">
  <div>Trigger element</div>
  <cds-popover-content>
    <p>Popover content goes here.</p>
  </cds-popover-content>
</cds-popover>
```

---

### Overflow Menu

```html
<cds-overflow-menu>
  <cds-overflow-menu-body>
    <cds-overflow-menu-item>Option 1</cds-overflow-menu-item>
    <cds-overflow-menu-item>Option 2</cds-overflow-menu-item>
    <cds-overflow-menu-item divider>Delete</cds-overflow-menu-item>
  </cds-overflow-menu-body>
</cds-overflow-menu>
```

---

### Menu / Menu Button

Context menus and trigger-based dropdown menus.

```html
<!-- Menu Button (trigger + dropdown menu) -->
<cds-menu-button label="Actions">
  <cds-menu-item label="Edit"></cds-menu-item>
  <cds-menu-item label="Duplicate"></cds-menu-item>
  <cds-menu-item-divider></cds-menu-item-divider>
  <cds-menu-item label="Delete" kind="danger"></cds-menu-item>
</cds-menu-button>

<!-- Standalone menu (attach to your own trigger) -->
<cds-menu open x="100" y="200">
  <cds-menu-item label="Copy"></cds-menu-item>
  <cds-menu-item label="Paste"></cds-menu-item>
  <cds-menu-item label="Select all" shortcut="⌘A"></cds-menu-item>
</cds-menu>
```

Key attributes on `cds-menu-button`: `label`, `kind` (primary|secondary|ghost|tertiary|danger), `size` (sm|md|lg), `open`, `menu-alignment`  
Key attributes on `cds-menu-item`: `label`, `shortcut`, `kind` (default|danger), `disabled`, `selected`  
Key attributes on `cds-menu`: `open`, `x`, `y`, `size` (sm|md|lg)  
Events: `cds-menu-item-clicked`, `cds-menu-closed`

CDN: `menu.min.js`, `menu-button.min.js`

---

### Icon Button

A button with only an icon (and a tooltip for accessibility).

```html
<cds-icon-button kind="primary" tooltip-text="Add item" tooltip-position="bottom">
  <svg slot="icon" focusable="false" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="16" height="16">
    <path d="M17 15V8h-2v7H8v2h7v7h2v-7h7v-2z"/>
  </svg>
</cds-icon-button>
```

Key attributes: `kind` (primary|secondary|ghost|tertiary|danger), `size` (sm|md|lg), `tooltip-text`, `tooltip-position` (top|right|bottom|left), `tooltip-alignment` (start|center|end), `disabled`, `href`

CDN: `icon-button.min.js`

---

### Tile

Tiles are flexible containers for card-like content.

```html
<!-- Default (static) tile -->
<cds-tile>Some content</cds-tile>

<!-- Clickable tile (navigates on click) -->
<cds-clickable-tile href="/detail">
  <h4>Clickable tile</h4>
  <p>Click to navigate</p>
</cds-clickable-tile>

<!-- Selectable tile (like a radio button) -->
<cds-selectable-tile name="tile-group" value="option-a">
  Option A
</cds-selectable-tile>
<cds-selectable-tile name="tile-group" value="option-b" selected>
  Option B (selected)
</cds-selectable-tile>

<!-- Expandable tile -->
<cds-expandable-tile>
  <cds-tile-above-the-fold-content slot="above-the-fold-content">
    Above the fold content
  </cds-tile-above-the-fold-content>
  <cds-tile-below-the-fold-content>
    Below the fold content (shown when expanded)
  </cds-tile-below-the-fold-content>
</cds-expandable-tile>
```

Key attributes on `cds-tile`: `color-scheme` (light|regular)  
Key attributes on `cds-clickable-tile`: `href`, `disabled`, `color-scheme`  
Key attributes on `cds-selectable-tile`: `name`, `value`, `selected`, `disabled`  
Key attributes on `cds-expandable-tile`: `expanded`, `with-interactive`

CDN: `tile.min.js`

---

### Structured List

Read-only structured list for presenting key/value or tabular data without full table overhead.

```html
<cds-structured-list>
  <cds-structured-list-head>
    <cds-structured-list-header-row>
      <cds-structured-list-header-cell>Column A</cds-structured-list-header-cell>
      <cds-structured-list-header-cell>Column B</cds-structured-list-header-cell>
      <cds-structured-list-header-cell>Column C</cds-structured-list-header-cell>
    </cds-structured-list-header-row>
  </cds-structured-list-head>
  <cds-structured-list-body>
    <cds-structured-list-row>
      <cds-structured-list-cell>Row 1, Cell 1</cds-structured-list-cell>
      <cds-structured-list-cell>Row 1, Cell 2</cds-structured-list-cell>
      <cds-structured-list-cell>Row 1, Cell 3</cds-structured-list-cell>
    </cds-structured-list-row>
    <cds-structured-list-row>
      <cds-structured-list-cell>Row 2, Cell 1</cds-structured-list-cell>
      <cds-structured-list-cell>Row 2, Cell 2</cds-structured-list-cell>
      <cds-structured-list-cell>Row 2, Cell 3</cds-structured-list-cell>
    </cds-structured-list-row>
  </cds-structured-list-body>
</cds-structured-list>

<!-- Selectable variant -->
<cds-structured-list selection>
  <cds-structured-list-body>
    <cds-structured-list-row value="row-1" selected>
      <cds-structured-list-cell>Option 1</cds-structured-list-cell>
    </cds-structured-list-row>
    <cds-structured-list-row value="row-2">
      <cds-structured-list-cell>Option 2</cds-structured-list-cell>
    </cds-structured-list-row>
  </cds-structured-list-body>
</cds-structured-list>
```

Key attributes on `cds-structured-list`: `selection`, `condensed`, `flush`

CDN: `structured-list.min.js`

---

### Ordered / Unordered List

```html
<!-- Unordered list -->
<cds-unordered-list>
  <cds-list-item>Item one</cds-list-item>
  <cds-list-item>Item two
    <cds-unordered-list nested>
      <cds-list-item>Nested item</cds-list-item>
    </cds-unordered-list>
  </cds-list-item>
  <cds-list-item>Item three</cds-list-item>
</cds-unordered-list>

<!-- Ordered list -->
<cds-ordered-list>
  <cds-list-item>First step</cds-list-item>
  <cds-list-item>Second step</cds-list-item>
  <cds-list-item>Third step</cds-list-item>
</cds-ordered-list>
```

CDN: `unordered-list.min.js`, `ordered-list.min.js`

---

### Pagination Nav

Compact page navigation without per-page size controls.

```html
<cds-pagination-nav
  count="10"
  page="3"
  pages-shown="5">
</cds-pagination-nav>
```

Key attributes: `count` (total pages), `page` (current, 0-indexed), `pages-shown`, `loop`  
Events: `cds-pagination-nav-changed`

CDN: `pagination-nav.min.js`

---

### Code Snippet

Display inline or block code with copy-to-clipboard functionality.

```html
<!-- Inline -->
<cds-code-snippet type="inline">npm install @carbon/web-components</cds-code-snippet>

<!-- Multi-line (block) -->
<cds-code-snippet type="multi">
  import '@carbon/web-components/es/components/button/index.js';
  const btn = document.querySelector('cds-button');
</cds-code-snippet>

<!-- Single-line (no expand, scrolls) -->
<cds-code-snippet type="single">docker run -p 3000:3000 my-image:latest</cds-code-snippet>
```

Key attributes: `type` (inline|single|multi), `disabled`, `feedback` (tooltip text after copy), `min-collapsed-number-of-rows`, `max-collapsed-number-of-rows`, `wrap-text`  
Event: `cds-code-snippet-copied`

CDN: `code-snippet.min.js`

---

### Combo Button

A split button: primary action label + a disclosure button that opens a `cds-menu` with secondary actions.

```html
<cds-combo-button label="Primary action">
  <cds-menu>
    <cds-menu-item label="Second action"></cds-menu-item>
    <cds-menu-item label="Third action"></cds-menu-item>
    <cds-menu-item label="Fourth action"></cds-menu-item>
  </cds-menu>
</cds-combo-button>
```

Key attributes (`cds-combo-button`): `label` (primary button text), `disabled`, `size` (sm|md|lg, default lg), `menu-alignment` (top|bottom|top-start|top-end|bottom-start|bottom-end), `tooltip-alignment`, `tooltip-content` (default "Additional actions")

CDN: `combo-button.min.js`

---

### Contained List

A labeled list with optional inset dividers, action slot in header, and clickable/icon items.

```html
<cds-contained-list label="List title" kind="on-page" size="lg">
  <cds-contained-list-item>List item</cds-contained-list-item>
  <cds-contained-list-item>List item</cds-contained-list-item>
  <cds-contained-list-item disabled>Disabled item</cds-contained-list-item>
</cds-contained-list>

<!-- Disclosed (inset border) variant -->
<cds-contained-list label="List title" kind="disclosed">
  <cds-contained-list-item>List item</cds-contained-list-item>
</cds-contained-list>

<!-- Clickable items -->
<cds-contained-list label="Actions">
  <cds-contained-list-item clickable>Clickable item</cds-contained-list-item>
</cds-contained-list>

<!-- With actions slot per item -->
<cds-contained-list label="With actions">
  <cds-contained-list-item>
    Item label
    <cds-icon-button slot="action" label="Dismiss" kind="ghost" size="sm">
      <!-- close icon SVG -->
    </cds-icon-button>
  </cds-contained-list-item>
</cds-contained-list>

<!-- With expandable search in header action slot -->
<cds-contained-list label="Searchable list">
  <cds-search slot="action" expandable placeholder="Search..."></cds-search>
  <cds-contained-list-item>List item 1</cds-contained-list-item>
  <cds-contained-list-item>List item 2</cds-contained-list-item>
</cds-contained-list>
```

Key attributes (`cds-contained-list`): `label` (header text), `kind` (on-page|disclosed, default on-page), `size` (sm|md|lg|xl), `is-inset` (inset dividers)  
Key attributes (`cds-contained-list-item`): `clickable`, `disabled`  
Slots (`cds-contained-list`): `label` (header text), `action` (header action area)  
Slots (`cds-contained-list-item`): `icon`, `action`  
Event: `cds-contained-list-item-click`

CDN: `contained-list.min.js`

---

### Copy Button

A standalone icon button that signals copy-to-clipboard with a tooltip feedback message.

```html
<cds-copy-button feedback="Copied!">Copy to clipboard</cds-copy-button>

<!-- Custom feedback timeout and alignment -->
<cds-copy-button feedback="Done!" feedback-timeout="3000" align="top">
  Copy
</cds-copy-button>
```

Key attributes: `feedback` (tooltip text shown after click, default "Copied!"), `feedback-timeout` (ms, default 2000), `align` (tooltip alignment, default "bottom"), `disabled`, `auto-align`

CDN: `copy-button.min.js`

---

### Heading

Context-aware heading that automatically infers the correct `h1`–`h6` level based on nesting depth of `<cds-section>` wrappers.

```html
<!-- Top level: renders h1 -->
<cds-heading>Page Title</cds-heading>

<!-- Nested sections auto-increment the heading level -->
<cds-section>
  <cds-heading>Section heading (h2)</cds-heading>
  <cds-section>
    <cds-heading>Subsection heading (h3)</cds-heading>
  </cds-section>
</cds-section>

<!-- Override level explicitly -->
<cds-section level="3">
  <cds-heading>Always h3 here</cds-heading>
</cds-section>
```

No required attributes — heading level is computed from context. `<cds-section>` increments the heading counter for all `<cds-heading>` children.

CDN: `heading.min.js`

---

### Data Table — Advanced Features

Extend the basic `<cds-table>` with sorting, selection, expansion, filtering, and batch actions.

#### Sorting

```html
<!-- Enable sorting on all columns -->
<cds-table is-sortable>
  <cds-table-head>
    <cds-table-header-row>
      <cds-table-header-cell>Name</cds-table-header-cell>
      <cds-table-header-cell>Status</cds-table-header-cell>
    </cds-table-header-row>
  </cds-table-head>
  <cds-table-body>
    <cds-table-row>
      <cds-table-cell>Load Balancer 1</cds-table-cell>
      <cds-table-cell>Active</cds-table-cell>
    </cds-table-row>
  </cds-table-body>
</cds-table>

<!-- Enable sorting on individual columns only -->
<cds-table-header-cell is-sortable>Name</cds-table-header-cell>
```

#### Row Selection

```html
<cds-table is-selectable>
  <!-- rows get automatic selection-name values -->
  <cds-table-body>
    <cds-table-row selection-name="row-1">
      <cds-table-cell>Load Balancer 1</cds-table-cell>
    </cds-table-row>
  </cds-table-body>
</cds-table>
```

#### Row Expansion

```html
<cds-table expandable>
  <cds-table-body>
    <cds-table-row expandable>
      <cds-table-cell>Load Balancer 1</cds-table-cell>
    </cds-table-row>
    <cds-table-expanded-row>
      <cds-table-cell colspan="1">Expanded detail content</cds-table-cell>
    </cds-table-expanded-row>
  </cds-table-body>
</cds-table>

<!-- Expand-all button -->
<cds-table expandable batch-expansion> ... </cds-table>
```

#### Toolbar with Filtering

```html
<cds-table>
  <cds-table-toolbar slot="toolbar">
    <cds-table-toolbar-content>
      <cds-table-toolbar-search placeholder="Filter table"></cds-table-toolbar-search>
      <cds-button>Add new</cds-button>
    </cds-table-toolbar-content>
  </cds-table-toolbar>
  <!-- head + body -->
</cds-table>
```

#### Batch Actions

```html
<cds-table is-selectable>
  <cds-table-toolbar slot="toolbar">
    <cds-table-batch-actions>
      <cds-button>Delete</cds-button>
      <cds-button download>Download</cds-button>
    </cds-table-batch-actions>
    <cds-table-toolbar-content>
      <cds-table-toolbar-search placeholder="Filter table"></cds-table-toolbar-search>
    </cds-table-toolbar-content>
  </cds-table-toolbar>
  <!-- head + body -->
</cds-table>
```

Key `cds-table` attributes: `is-sortable`, `is-selectable`, `expandable`, `batch-expansion`, `size` (sm|md|lg|xl), `zebra`, `sticky-header`  
Key `cds-table-header-cell` attributes: `is-sortable`, `sort-direction` (ascending|descending|none)  
Key `cds-table-row` attributes: `expandable`, `selected`, `selection-name`, `selection-value`

CDN: `data-table.min.js`

---

### AI Label

`cds-ai-label` is an AI transparency badge that acts as a toggletip trigger — clicking it opens a callout explaining what AI-generated content is present.

**Default (standalone) variant:**

```html
<cds-ai-label>
  <p slot="body-text">
    This content was generated by AI. Always review AI-generated output before use.
  </p>
  <cds-ai-label-action-button>View details</cds-ai-label-action-button>
</cds-ai-label>
```

**Inline variant** (renders inline with text, shows a side label):

```html
<cds-ai-label kind="inline" ai-text-label="AI-assisted">
  <p slot="body-text">Explanation of the AI involvement.</p>
</cds-ai-label>
```

**Sizes** (`size` attribute): `mini` | `2xs` | `xs` (default) | `sm` | `md` | `lg` | `xl`

**With icon action buttons in the callout:**

```html
<cds-ai-label alignment="bottom-left">
  <p slot="body-text">Generated by watsonx.</p>
  <cds-icon-button slot="actions" kind="ghost" size="sm">
    <svg slot="icon"><!-- thumbs-up SVG --></svg>
  </cds-icon-button>
  <cds-icon-button slot="actions" kind="ghost" size="sm">
    <svg slot="icon"><!-- thumbs-down SVG --></svg>
  </cds-icon-button>
</cds-ai-label>
```

Key attributes (`cds-ai-label`):
- `kind` — `default` (default) | `inline`
- `size` — `mini` | `2xs` | `xs` (default) | `sm` | `md` | `lg` | `xl`
- `ai-text` — text inside badge, default `"AI"`
- `ai-text-label` — supplemental text shown beside badge in `inline` kind
- `alignment` — callout alignment: `top` | `top-left` | `top-right` | `bottom` | `bottom-left` | `bottom-right` | `left` | `left-bottom` | `left-top` | `right` | `right-bottom` | `right-top` (default `"bottom"`)
- `open` — boolean, controls callout visibility
- `revert-active` — boolean, shows a revert button in the callout
- `revert-label` — label for the revert button (default `"Revert to AI"`)
- `button-label` — accessible label for the toggle button

Slots:
- Default slot — content displayed inside the callout popover
- `body-text` — a `<div>` wrapping the callout body text (use `<p>` elements inside)
- `actions` — icon buttons rendered at the bottom of the callout

Child component: `cds-ai-label-action-button` — a styled action button rendered below the body text in the callout.

CDN: `ai-label.min.js`

---

### Skeleton

Skeleton components are animated loading placeholders that represent content before it loads. There are three distinct skeleton elements.

**Skeleton Text** — simulates lines of text:

```html
<!-- Single line -->
<cds-skeleton-text></cds-skeleton-text>

<!-- Paragraph (multiple lines) -->
<cds-skeleton-text paragraph line-count="4" width="75%"></cds-skeleton-text>

<!-- Heading size -->
<cds-skeleton-text heading></cds-skeleton-text>
```

**Skeleton Placeholder** — simulates a rectangular block (image, card, etc.):

```html
<cds-skeleton-placeholder></cds-skeleton-placeholder>
```

Use CSS to control the dimensions:

```html
<cds-skeleton-placeholder style="width: 200px; height: 150px;"></cds-skeleton-placeholder>
```

**Skeleton Icon** — simulates a 16×16 icon:

```html
<cds-skeleton-icon></cds-skeleton-icon>
```

**AI Skeleton variants** — same elements but loaded from `ai-skeleton.min.js`, which renders with the AI gradient shimmer animation instead of the standard grey shimmer:

```html
<!-- Load ai-skeleton.min.js, then use the same element names -->
<cds-skeleton-text paragraph line-count="3"></cds-skeleton-text>
<cds-skeleton-placeholder></cds-skeleton-placeholder>
<cds-skeleton-icon></cds-skeleton-icon>
```

Key attributes (`cds-skeleton-text`):
- `heading` — boolean, renders at heading scale
- `paragraph` — boolean, generates multiple lines
- `line-count` — number of lines when `paragraph` is set (default `3`)
- `width` — width in `px` or `%` for a single line, or max-width for paragraph lines (default `"100%"`)

`cds-skeleton-placeholder` and `cds-skeleton-icon` have no configurable attributes — size them with CSS.

CDN files:
- Standard skeletons: `skeleton-text.min.js`, `skeleton-placeholder.min.js`, `skeleton-icon.min.js`
- AI-styled skeletons: `ai-skeleton.min.js` (registers all three elements with AI shimmer)

---

### UI Shell (App Shell)

```html
<cds-header aria-label="My Application">
  <cds-header-menu-button
    button-label-active="Close menu"
    button-label-inactive="Open menu">
  </cds-header-menu-button>
  <cds-header-name href="/" prefix="IBM">App Name</cds-header-name>
  <cds-header-nav>
    <cds-header-nav-item href="/dashboard">Dashboard</cds-header-nav-item>
    <cds-header-nav-item href="/monitor">Monitor</cds-header-nav-item>
    <cds-header-menu menu-label="Settings">
      <cds-header-menu-item href="/profile">Profile</cds-header-menu-item>
      <cds-header-menu-item href="/account">Account</cds-header-menu-item>
    </cds-header-menu>
  </cds-header-nav>
  <div slot="header-global">
    <cds-header-global-action aria-label="Notifications">
      <!-- icon here -->
    </cds-header-global-action>
  </div>
</cds-header>

<cds-side-nav aria-label="Side navigation" expanded>
  <cds-side-nav-items>
    <cds-side-nav-link href="/dashboard" active>Dashboard</cds-side-nav-link>
    <cds-side-nav-menu title="Monitor">
      <cds-side-nav-menu-item href="/monitor/cpu">CPU</cds-side-nav-menu-item>
      <cds-side-nav-menu-item href="/monitor/memory">Memory</cds-side-nav-menu-item>
    </cds-side-nav-menu>
  </cds-side-nav-items>
</cds-side-nav>

<main id="main-content">
  <!-- page content -->
</main>
```

---

### Grid & Layout

```js
import '@carbon/web-components/es/components/grid/index.js';
```

```html
<!-- 16-column grid, responsive breakpoints: sm (4 col), md (8 col), lg (16 col) -->
<cds-grid>
  <cds-column sm="4" md="4" lg="8">Left column</cds-column>
  <cds-column sm="4" md="4" lg="8">Right column</cds-column>
</cds-grid>

<!-- Condensed gutter (1px) -->
<cds-grid condensed>
  <cds-column lg="4">Col 1</cds-column>
  <cds-column lg="4">Col 2</cds-column>
  <cds-column lg="4">Col 3</cds-column>
  <cds-column lg="4">Col 4</cds-column>
</cds-grid>

<!-- Narrow gutter (16px) -->
<cds-grid narrow>
  <cds-column lg="8">Wide left</cds-column>
  <cds-column lg="8">Wide right</cds-column>
</cds-grid>

<!-- Offset columns -->
<cds-column lg="4" lg-offset="4">Offset by 4</cds-column>
```

`<cds-stack>` for vertical/horizontal stacking with gap:
```html
<cds-stack orientation="horizontal" gap="6">
  <div>Item 1</div>
  <div>Item 2</div>
  <div>Item 3</div>
</cds-stack>
```

---

### Theming

Set on a container or `<body>`:
```html
<body data-carbon-theme="white">  <!-- default -->
<body data-carbon-theme="g10">   <!-- light gray -->
<body data-carbon-theme="g90">   <!-- dark gray -->
<body data-carbon-theme="g100">  <!-- carbon black -->
```

Layer theming (nested contexts):
```html
<cds-layer level="1">
  <!-- components here are themed at layer 1 -->
  <cds-layer level="2">
    <!-- nested layer -->
  </cds-layer>
</cds-layer>
```

---

## CDN Quick Start Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Carbon App</title>
  <!-- Load only the components you need -->
  <script type="module" src="https://1.www.s81c.com/common/carbon/web-components/version/v2.51.1/button.min.js"></script>
  <script type="module" src="https://1.www.s81c.com/common/carbon/web-components/version/v2.51.1/text-input.min.js"></script>
  <script type="module" src="https://1.www.s81c.com/common/carbon/web-components/version/v2.51.1/modal.min.js"></script>
  <style>
    body {
      font-family: 'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif;
      margin: 2rem;
    }
    cds-button:not(:defined),
    cds-text-input:not(:defined),
    cds-modal:not(:defined) { visibility: hidden; }
  </style>
</head>
<body data-carbon-theme="white">
  <cds-text-input label="Name" placeholder="Enter your name"></cds-text-input>
  <cds-button id="open-btn" style="margin-top: 1rem">Open Modal</cds-button>

  <cds-modal id="my-modal">
    <cds-modal-header>
      <cds-modal-close-button></cds-modal-close-button>
      <cds-modal-heading>Hello, Carbon!</cds-modal-heading>
    </cds-modal-header>
    <cds-modal-body>
      <cds-modal-body-content>Welcome to Carbon Web Components.</cds-modal-body-content>
    </cds-modal-body>
    <cds-modal-footer>
      <cds-modal-footer-button kind="secondary" data-modal-close>Cancel</cds-modal-footer-button>
      <cds-modal-footer-button kind="primary">Confirm</cds-modal-footer-button>
    </cds-modal-footer>
  </cds-modal>

  <script>
    document.getElementById('open-btn').addEventListener('click', () => {
      document.getElementById('my-modal').setAttribute('open', '');
    });
  </script>
</body>
</html>
```

---

## Event Handling Patterns

```js
// Modal
document.querySelector('cds-modal').addEventListener('cds-modal-closed', (e) => {
  console.log('Modal closed');
});

// Dropdown selection
document.querySelector('cds-dropdown').addEventListener('cds-dropdown-selected', (e) => {
  console.log('Selected value:', e.detail.item.value);
});

// Tabs selection
document.querySelector('cds-tabs').addEventListener('cds-tabs-selected', (e) => {
  console.log('Selected tab:', e.detail.item.value);
});

// Toggle accordion programmatically
document.querySelector('cds-modal')?.setAttribute('open', '');    // open
document.querySelector('cds-modal')?.removeAttribute('open');    // close
document.querySelector('cds-modal')?.toggleAttribute('open');    // toggle
```

---

## Component → CDN Script Map

| Component | CDN file |
|-----------|----------|
| Accordion | `accordion.min.js` |
| AI Label | `ai-label.min.js` |
| AI Skeleton | `ai-skeleton.min.js` |
| Button | `button.min.js` |
| Breadcrumb | `breadcrumb.min.js` |
| Checkbox | `checkbox.min.js` |
| Code Snippet | `code-snippet.min.js` |
| Combo Box | `combo-box.min.js` |
| Combo Button | `combo-button.min.js` |
| Contained List | `contained-list.min.js` |
| Content Switcher | `content-switcher.min.js` |
| Copy Button | `copy-button.min.js` |
| DataTable | `data-table.min.js` |
| Date Picker | `date-picker.min.js` |
| Dropdown | `dropdown.min.js` |
| File Uploader | `file-uploader.min.js` |
| Form | `form.min.js` |
| Grid | `grid.min.js` |
| Heading | `heading.min.js` |
| Icon Button | `icon-button.min.js` |
| Link | `link.min.js` |
| Loading | `loading.min.js` |
| Menu | `menu.min.js` |
| Menu Button | `menu-button.min.js` |
| Modal | `modal.min.js` |
| Multi Select | `multi-select.min.js` |
| Notification | `notification.min.js` |
| Number Input | `number-input.min.js` |
| Ordered List | `ordered-list.min.js` |
| Overflow Menu | `overflow-menu.min.js` |
| Pagination | `pagination.min.js` |
| Pagination Nav | `pagination-nav.min.js` |
| Password Input | `password-input.min.js` |
| Popover | `popover.min.js` |
| Progress Bar | `progress-bar.min.js` |
| Progress Indicator | `progress-indicator.min.js` |
| Radio Button | `radio-button.min.js` |
| Search | `search.min.js` |
| Select | `select.min.js` |
| Skeleton Icon | `skeleton-icon.min.js` |
| Skeleton Placeholder | `skeleton-placeholder.min.js` |
| Skeleton Text | `skeleton-text.min.js` |
| Slider | `slider.min.js` |
| Structured List | `structured-list.min.js` |
| Tabs | `tabs.min.js` |
| Tag | `tag.min.js` |
| Text Area | `textarea.min.js` |
| Text Input | `text-input.min.js` |
| Tile | `tile.min.js` |
| Time Picker | `time-picker.min.js` |
| Toggle | `toggle.min.js` |
| Tooltip | `tooltip.min.js` |
| TreeView | `tree-view.min.js` |
| UI Shell | `ui-shell.min.js` |
| Unordered List | `unordered-list.min.js` |

CDN base: `https://1.www.s81c.com/common/carbon/web-components/version/v2.51.1/`

---

## Links

- **Storybook**: https://web-components.carbondesignsystem.com
- **GitHub**: https://github.com/carbon-design-system/carbon/tree/main/packages/web-components
- **Carbon Design System**: https://www.carbondesignsystem.com
- **npm**: `@carbon/web-components`
