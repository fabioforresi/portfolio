# How to update the website (no technical knowledge needed)

You need VS Code and a free GitHub account. The site updates by itself 1–3 minutes after you
commit and sync.

---

## Add a new project with VS Code (≈ 5 minutes)

### Every time
1. Open the project folder in VS Code (**File → Open Folder…**). Install the suggested *Python* extension if VS Code asks.
2. In the left **Explorer** panel, right-click the **`projects`** folder → **New Folder** and name it **year-and-name**,
   lowercase, no accents, e.g. `2025-my-new-campaign`.
3. Drag your photos from your computer into that new folder (`.jpg`, `.png` or `.webp`).
   They appear in alphabetical order, so name them `01.jpg`, `02.jpg`, `03.jpg`…
   Optional: a file called `cover.jpg` is the picture shown in the overview grid (otherwise the first photo is used).
4. Open `projects/_TEMPLATE/info.txt`, copy everything, then right-click your new folder → **New File** → `info.txt`, paste and change the words after the colons:

        title: 2025 - Project Name
        category: Landscape
        year: 2025
        description: A few words about the project.
        video: https://vimeo.com/123456789

   - `title` is shown exactly as you write it (your convention "year - client - job" works well). `year` appears under the title when someone hovers a cover.
   - `category` must be one of the menu names: Landscape, Architecture, Street, Abstract, Travel.
   - `video` and `description` are optional. Paste a normal YouTube or Vimeo link; add several `video:` lines if needed.
   - Big photos are shrunk automatically. Keep each file under 25 MB.

### Look at it before publishing
Press **Ctrl+Shift+B** (Mac: **Cmd+Shift+B**). A terminal opens and the site is available at
**http://localhost:8000**. Leave it running: every time you save, it rebuilds, so just refresh the browser.
If something is wrong, the terminal tells you in plain words what to fix.
(Stop it with **Ctrl+C**. Other commands are under **Terminal → Run Task…**.)

### Publish
1. Click the **Source Control** icon in the left bar (the branching icon).
2. Write a short message such as `Add Alpine Morning project` in the box.
3. Click **Commit**. If VS Code asks "stage all changes?", click **Yes**. Then **Sync Changes** if it still shows.
4. After 1–3 minutes the website is updated. To follow it, open the **Actions** tab of the repository on GitHub: green ✔ = published, red ✖ = see "If the red cross appears" below.

### First time only
- Install **Python 3.10+** (python.org) and **Git** (git-scm.com), and sign in to GitHub from VS Code when asked (Accounts icon, bottom left).
- Run **Terminal → Run Task… → ⚙ Install (first time only)**.
- Get the repository: **Ctrl+Shift+P → "Git: Clone"**, paste the repository address, choose a folder on your computer.

> Large originals: GitHub refuses single files over 100 MB and the repository gets heavy quickly. Export photos as JPG at about 2500 px on the long side (1–5 MB each) before adding them.

### Without VS Code (browser only)
On GitHub open the folder **`projects`** → **Add file → Upload files** → drag your prepared folder (photos + `info.txt`) → **Commit changes**.

---

## Add more photos to an existing project
Drag the photos into the project folder in VS Code, then Commit and Sync (or, in the browser: project folder → **Add file → Upload files**).
Continue numbering after the last one (`07.jpg`, `08.jpg`…) so they appear at the end.

## Change a text (title, year, description, video)
Open the project's `info.txt` in VS Code, edit, save (Ctrl+S), then Commit and Sync.

## Remove, hide, or reorder
- **Hide for now:** in `info.txt` add the line `draft: yes` (remove it to show the project again).
- **Delete forever:** open the project folder → click the `…` menu at the top right → **Delete directory** → Commit.
- **Order:** the overview is sorted by folder name, newest first. A folder starting with `2025-` appears before `2024-`.
  To move a project up or down, rename its folder (open a file inside it, click the pencil, and edit the path at the top).

## Change name, tagline, menu, e-mail, Instagram, logo
Open **`site.txt`** in VS Code, edit, save, then Commit and Sync.
To use your own logo image (recommended, it is exactly your current one): save it in the **`assets`** folder, then in `site.txt` remove the `#` in front of `logo:` and write its file name, e.g. `logo: logo.png`.
To add a menu section, add its name to the `categories:` line (separated by commas).

---

## If the ✖ red cross appears
Nothing is broken for visitors: the website simply stays as it was before your change.
1. Click the **Actions** tab → click the latest run with the red ✖ → click **Publish website** or **Check**.
2. Look at the red message. It says in plain words what to fix, for example:
   - *category 'Cooking' is not in the menu* → write one of the menu names exactly.
   - *there are no photos in this folder* → upload at least one photo.
   - *this format is not supported* → photos from iPhone (HEIC) must be saved as JPG first.
3. Fix the file as described above and commit again. It will re-run by itself.

Still stuck? Every change can be undone: open the **Commits** history and ask the repository owner to revert the last one.

---

## One-time setup (done once by the repository owner)
1. Create a new GitHub repository and upload all the files of this project.
2. Go to **Settings → Pages → Build and deployment → Source** and choose **GitHub Actions**.
3. Go to **Actions** and wait for "Publish website" to turn green. The address of the site is shown in Settings → Pages.
4. Edit `site.txt` (name, e-mail, Instagram) and replace the example projects with real ones.
5. To give someone else access: **Settings → Collaborators → Add people**.
