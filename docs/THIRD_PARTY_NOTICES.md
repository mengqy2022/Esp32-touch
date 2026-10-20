# Third-party notices / publishing checklist

This file is intentionally a practical notice, not legal advice.

## LVGL

The firmware uses LVGL through ESP-IDF Component Manager:

- Project: https://github.com/lvgl/lvgl
- Version requested: `~8.4.0`
- Upstream license: MIT (see the exact version downloaded by Component Manager)

`managed_components/` is not committed in this package.

## Remote vocabulary data

The built-in Vocab Lab catalog points to:

- https://github.com/grhliu/wordtyper-vocabularies

That repository states that its wordbooks are objectively derived from ECDICT under the MIT License and that protected content from commercial dictionaries / vocabulary books is not included. The firmware downloads these files at user request; the large wordbooks themselves are not bundled in this project archive.

Before public/commercial distribution, keep the upstream attribution and re-check the upstream repository's current `LICENSE` and `NOTICE.md`.

## Baicizhan / 百词斩

The name is mentioned only as the user's product-reference point for learning workflow ideas. This project does **not** bundle or claim affiliation with Baicizhan and does not copy its commercial assets, copyrighted images, proprietary wordbooks, courses, memberships or source code.

## Existing embedded CJK glyph table

`main/font_cn16.c` is an embedded C-source glyph table that already existed in the supplied firmware and is required for Chinese text rendering. The raw desktop font file and font-generation toolchain are deliberately excluded from this GitHub package.

If you plan to publish or commercially redistribute the repository, independently verify that you have redistribution rights for the embedded glyph data. A conservative future improvement is to regenerate this C table from an openly licensed CJK typeface (for example an OFL-licensed Noto CJK font) and retain that font's required license notice.

## Salary Cat artwork and font

The five GIFs in `assets/salary_cat/` were supplied by the device user. Retain their
original markings; this does not assign artwork rights or place them under the
project's MIT code license. See [asset notes](../assets/salary_cat/README.md).
The new salary-only `font_salary16.c` is a Noto Sans SC subset, copyright Adobe,
under [SIL OFL 1.1](../assets/salary_cat/OFL.txt). It does not replace the existing CJK font.

The 2026 calendar references the linked government notice in `tools/work_calendar.json`;
the host does not fetch a holiday service at runtime or read personal calendar events.

## Project-level license (code)

The repository already contains an [MIT LICENSE](../LICENSE); it is retained by
this update. Its copyright attribution still contains a placeholder and should
be completed by the maintainer with the appropriate rights-holder information.

## Windows companion packaging

- Python runtime: Python Software Foundation license and included upstream notices.
- pyserial 3.5: BSD license; see the installed package/upstream license.
- PyInstaller 6.22.3: GPL with its distribution/bundling exception. The exception
  permits distribution of packaged applications under their own licenses; retain
  the applicable packaging/runtime notices when shipping a binary release.
- Build-time dependencies and PyInstaller hooks: inspect the exact resolved
  dependency licenses for the environment used to create each release.
- NVIDIA NVML is accessed from the user's installed GPU driver. This project
  does not bundle the NVIDIA library or a driver installer.

The EXE does not embed a commercial GUI toolkit. Source-level MIT licensing does
not replace notices for the Python runtime or other bundled components.
The generic price JSON contains user-provided assumptions, not an official price
feed or endorsement by a model vendor.
