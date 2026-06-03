<!-- last_verified: 2026-06-03 -->
# Tech Debt Tracker

Known tech debt items. Agents update this when they discover or create tech debt.

| Description | Impact | Proposed Resolution | Priority | Status |
|---|---|---|---|---|
| `apps/web/src/components/files/file-browser.tsx` is ~338 lines, over the 300-line guideline. Kept starter scaffolding for the full-bucket File Explorer; the structural test only enforces the limit on Python under `app/`, so it does not fail CI. | Low — readability only; component is stable and unmodified from the starter | Extract the breadcrumb/toolbar and the file-row rendering into sub-components if/when the File Explorer is next touched. Logged rather than refactored now to avoid destabilizing kept scaffolding. | Low | Known |
