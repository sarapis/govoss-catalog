# /ospos images

Written by the MANUAL `ospos/fetch_images.py`; `build_ospos.py` only reads this folder and
copies it to `site/ospo-img/` (this file and any `.json` stay behind), so the page makes no
third-party request.

- `logo/<host>.png` - each office's own site icon, from Google's favicon service, used to
  identify the office on its card. A logo that looks wrong is deleted (or replaced by a better
  file of the same name) by hand; the script never overwrites one without `--refresh`.
  An office with no file shows its initials.
- `flag/<code>.svg` - [flag-icons](https://github.com/lipis/flag-icons) 7.2.3, the 4x3 set,
  MIT (`flag/LICENSE-flag-icons.txt`, published with them). Greece's `EL` is `gr.svg`.
