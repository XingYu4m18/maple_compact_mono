# Third-party notices

## Maple Mono

The bundled font files are modified derivatives of Maple Mono NF CN 7.9.

Copyright 2022 The Maple Mono Project Authors.

- Project: https://github.com/subframe7536/maple-font
- Pinned release: https://github.com/subframe7536/maple-font/releases/tag/v7.9
- License: SIL Open Font License 1.1, reproduced in `OFL.txt`.
- Upstream input archive and font hashes: `upstream.lock.json`.

Modifications: independently named family; Latin and NF outlines horizontally scaled by 5/6; 1200-unit full-width outlines translated by -100 with advances reduced to 1000; removal of outdated hinting instructions; preservation of cmap, glyph order, GSUB and vertical metrics. These changes are not endorsed by upstream authors.

## Resource Han Rounded / Source Han Sans

Maple Mono's CN component is based on Resource Han Rounded, itself derived from Source Han Sans.

Copyright © 2018–2022 Cyano Hao.

Portions © 2014–2021 Adobe, with Reserved Font Name “Source”.

- Project: https://github.com/CyanoHao/Resource-Han-Rounded
- Font license and upstream notices: `licenses/ResourceHanRounded-LICENSE.md`.

The derived family name `Maple Compact NF CN` does not use the Reserved Font Name “Source”. Upstream code is not bundled; its MIT notice is preserved in the copied upstream license document for completeness.

## Nerd Fonts icons

The input is the already-patched Maple Mono NF CN release, whose build configuration specifies Nerd Fonts 3.4.0. This project does not add or remove icon sets; the existing NF glyphs are transformed with the narrow glyphs.

Copyright (c) 2014 Ryan L McIntyre and the respective icon-set authors.

- Project: https://github.com/ryanoasis/nerd-fonts/tree/v3.4.0
- General licensing: `licenses/NerdFonts-LICENSE.txt`.
- Upstream icon-source inventory: `licenses/NerdFonts-license-audit.md`.
- Per-source notices available in that release are reproduced under `licenses/nerd_fonts/` (Codicons, Font Awesome, Material Design Icons, Octicons, Pomicons, Powerline Extra Symbols and Powerline Symbols).

The icons retain their respective copyright, attribution and licensing conditions. The Nerd Fonts audit is a copy of upstream's inventory, not a claim that every unrelated font listed in that inventory is bundled in this repository. No endorsement by Microsoft, Font Awesome, Adobe or other upstream authors is implied. Brand icons remain subject to their owners' trademark rights.

## Comparison images

The comparison images show Sarasa Mono SC, Maple Mono NF CN, and this project's derivative at the same nominal size. Sarasa Mono SC is used only to render comparison text; no Sarasa font binaries are distributed.

- Sarasa Gothic: https://github.com/be5invis/Sarasa-Gothic
- License: SIL Open Font License 1.1. Rendered-document output is not required by the OFL to use the font's license.
