<!-- last_verified: 2026-06-03 -->
# App Workflows

User journeys inside the application.

## Create and render an avatar video

- User navigates to `/create` (New Avatar Video)
- Types a script, or clicks "Load .txt" to upload one
- Picks a stock avatar from the catalog, or clicks the "Upload custom" tile to supply a
  photo/clip
- Picks a voice from the dropdown
- Clicks **Render video** → `POST /projects` (multipart) persists `script.txt`, the optional
  `avatar.<ext>`, and `project.json` to B2, then schedules the background render
- The studio redirects to `/library?project=<id>` where the in-flight take renders
- See: [New Avatar Video studio](features/create-studio.md), [Render job](features/render.md)

## Watch a render finish and iterate

- On the project detail, a banner shows the take is rendering; the page polls automatically
- When the take completes, the `<video>` player auto-loads it (streamed from a presigned B2 URL)
- The take history lists every take with status + duration
- Click **Render another take** to re-render the same script + avatar (a new take appears)
- Compare takes by playing each from the history; download any completed take
- If a render fails, the error is shown and the user can render another take
- See: [Scoped Library](features/library.md)

## Browse the project library

- User navigates to `/library`
- The grid lists projects scoped to the `avatar-projects/` prefix (newest first), each with
  an avatar/status badge, take count, and total duration
- Selecting a project opens the detail with the inline video player and take history
- Delete removes the entire project folder from B2 after a confirm dialog
- See: [Scoped Library](features/library.md)

## Browse the whole bucket (kept scaffolding)

- User navigates to `/files`
- Tree view of every object in the bucket (including `avatar-projects/` and `uploads/`),
  with preview, download, and delete on hover
- See: [File Browser](features/file-browser.md)

## Upload arbitrary files (kept scaffolding)

- User navigates to `/upload`, drops/selects files (max 100MB), watches per-file progress
- Files land under `uploads/`
- See: [File Upload](features/file-upload.md)

## View the dashboard

- User navigates to `/` (home)
- Stat cards show: total projects, total renders (takes), minutes rendered, storage used
- The renders-per-day chart shows completed renders over the last 7 days
- The recent renders table lists the latest projects with takes, duration, status, created
- See: [Dashboard](features/dashboard.md)
