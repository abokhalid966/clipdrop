# ClipDrop

Your own game clipper. It keeps the last 30 seconds of your screen and game
sound in the background. Press a hotkey and the clip is saved instantly. It
shows up on your iPhone over Wi-Fi, where you can watch, rename, edit, shrink
for sharing, delete and save it to Photos.

It also sends any file between your PC and your phone, both ways, and shows
which device each file came from. The app is in English and Arabic.

No NVIDIA app, no accounts, no cloud. Everything stays on your PC.

## Install (once)
1. Run **ClipDrop-Setup-5.0.exe**. If Windows says "Windows protected your PC",
   click **More info** then **Run anyway** (the setup isn't code-signed).
2. Pick a folder (the default is fine), and choose whether you want a Desktop
   icon and to start ClipDrop with Windows. No admin rights needed.
3. The first time, setup downloads its own private Python and FFmpeg
   (about 150 MB) into the ClipDrop folder. Nothing else on your PC changes.
4. A QR code page opens. Scan it with your iPhone (same Wi-Fi), then in
   Safari tap Share -> **Add to Home Screen**.
5. If Windows asks about the firewall, tick **Private networks** and Allow.

**Updating:** run a newer setup over the old one. Your settings, favorites and
clips stay.
**Uninstalling:** Settings -> Apps -> Installed apps -> ClipDrop -> Uninstall.
Your clips in `Videos\ClipDrop` and shared files in
`Downloads\ClipDrop Shared` are kept.
No setup? Unzip the folder and double-click **Install ClipDrop.bat** instead.

## Everyday use
- **Ctrl+F9** saves the last 30 seconds. You hear a ding and see "Clip saved"
  in the corner of the game. Add more hotkeys with other lengths in Settings.
- Or tap **Clip it** on your phone.
- Clips land in `Videos\ClipDrop`, in a folder named after the game.
- **Files** tab: send photos, videos or any file from your phone to the PC, or
  from the PC to your phone (drag and drop, or right-click a file in Windows ->
  Send to -> ClipDrop). Each file shows "From iPhone" or "From PC".
- ClipDrop lives in the tray by the clock. Right-click it for: Open ClipDrop,
  Save clip now, Recording on/off, Connect phone, Open clips folder, Help, Quit.

## Full guide
Open ClipDrop and tap **?** at the top (or tray icon -> Help). It explains
everything: saving clips, connecting your iPhone, auto-send to Photos,
editing, organizing, which video format to pick, every setting, and what to
do if something doesn't work.

## What's new in version 5
- Two-way file sharing between PC and phone, with "From iPhone / From PC"
  badges, filters, and a "Send to PC" iPhone share-menu shortcut.
- Arabic (full right-to-left layout), chosen automatically or in Settings.
- New settings page with categories, search, and "reset this section".
- Safety: other websites can no longer send commands to ClipDrop.

## What's in version 4
- Choose the video format: H.264 (plays everywhere), HEVC (half the size),
  AV1 (smallest, new graphics cards). Settings shows what your PC supports.
- Record always, or only while a game is open.
- Record the whole screen, or only the game window.
- Several hotkeys, each with its own length.
- "Clip saved" message inside the game.
- Pick your speakers, mic and monitor, and set volumes.
- Favorites, search, sorting, select many clips at once, storage bar.
- ClipDrop opens in its own window on your PC.
- A built-in help page.

## If something is off
- Run **start.bat** to see ClipDrop with a window that shows error messages.
- Log file: `%LOCALAPPDATA%\ClipDrop\clipdrop.log`
- Phone can't connect: same Wi-Fi, and allow ClipDrop (pythonw) through the
  firewall on Private networks.

## Releasing a new version (for maintainers)
1. Bump `VERSION` in `clipdrop.py` and `!define VERSION` in `setup.nsi`.
2. Build the setup: `makensis setup.nsi` (NSIS 3).
3. Make `SHA256SUMS.txt`: `sha256sum ClipDrop-Setup-X.Y.exe > SHA256SUMS.txt`.
4. Publish a GitHub release tagged `vX.Y` with both files attached. Put the
   English notes first, then `<!-- ar -->`, then the Arabic notes.
Installed copies find it within a day, show "What's new", check the SHA-256
fingerprint and update themselves.
