# Third-party notices

SourcePilot's project license does not replace third-party licenses. Third-party authors retain their copyrights and applicable license terms.

## shadcn/ui patterns

SourcePilot's Button and Dialog files identify shadcn/ui patterns; its class helper uses a common composition idiom. The development record describes locally composed primitives. The upstream MIT notice is retained conservatively for any incorporated upstream material in `apps/web/components/ui/button.tsx`, `apps/web/components/ui/dialog.tsx` and `apps/web/lib/utils.ts`. This acknowledgment does not establish substantial copying or an original upstream revision.

The local files include SourcePilot-specific styling and behavior recorded in commit `556ab052d309a62917f5b5ed1f3a7c0c5aa70810` on 11 November 2026. This date identifies the local implementations, not an upstream revision.

Upstream: [shadcn/ui](https://github.com/shadcn-ui/ui), [MIT license](https://github.com/shadcn-ui/ui/blob/main/LICENSE.md).

## Lucide and Feather artwork

SourcePilot imports icons from `lucide-react` 1.70.0. Icons are also depicted in the repository's application screenshots. Lucide's notice and the included notice for Feather-derived icons are reproduced below. These notices apply to that artwork, not to SourcePilot's original code or fictional supplier data.

Upstream: [Lucide 1.70.0](https://github.com/lucide-icons/lucide/tree/1.70.0), [complete ISC and Feather MIT license](https://github.com/lucide-icons/lucide/blob/1.70.0/LICENSE).

## Dependencies installed separately

Package manifests and lockfiles describe dependencies obtained separately by users. This source repository does not vendor PyMuPDF/MuPDF, Psycopg, axe-core, node_modules, Python environments, or compiled application bundles. Separate installation does not exempt an integrated application from applicable license obligations.

- **PyMuPDF 1.28.2:** [GNU AGPL v3](https://github.com/pymupdf/PyMuPDF/blob/1.28.2/COPYING) or a separate [Artifex commercial license](https://pymupdf.io/licensing). SourcePilot retains PyMuPDF under its AGPL option; SourcePilot does not grant a commercial license to PyMuPDF or MuPDF.
- **Psycopg and psycopg-binary 3.3.6:** [LGPL-3.0-only](https://github.com/psycopg/psycopg/blob/3.3.6/LICENSE.txt).
- **axe-core 4.13.0**, used by accessibility tests: [MPL-2.0](https://github.com/dequelabs/axe-core/blob/v4.13.0/LICENSE).
- **class-variance-authority 0.7.1:** [Apache-2.0](https://github.com/joe-bell/cva/blob/v0.7.1/LICENSE).

These entries are not substitutes for upstream license texts, source-delivery obligations or notices when distributing dependencies or compiled bundles. Such distributions must retain the licenses/notices of the actual included packages and satisfy applicable source and library-replacement rights, including those for bundled native libraries. Other dependencies retain the licenses shipped with their packages; this file is not a complete bundle license inventory.

## Reproduced upstream notices

### shadcn/ui - MIT

MIT License

Copyright (c) 2023 shadcn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


### Lucide 1.70.0 and Feather-derived icons

ISC License

Copyright (c) 2026 Lucide Icons and Contributors

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

---

The following Lucide icons are derived from the Feather project:

airplay, alert-circle, alert-octagon, alert-triangle, aperture, arrow-down-circle, arrow-down-left, arrow-down-right, arrow-down, arrow-left-circle, arrow-left, arrow-right-circle, arrow-right, arrow-up-circle, arrow-up-left, arrow-up-right, arrow-up, at-sign, calendar, cast, check, chevron-down, chevron-left, chevron-right, chevron-up, chevrons-down, chevrons-left, chevrons-right, chevrons-up, circle, clipboard, clock, code, columns, command, compass, corner-down-left, corner-down-right, corner-left-down, corner-left-up, corner-right-down, corner-right-up, corner-up-left, corner-up-right, crosshair, database, divide-circle, divide-square, dollar-sign, download, external-link, feather, frown, hash, headphones, help-circle, info, italic, key, layout, life-buoy, link-2, link, loader, lock, log-in, log-out, maximize, meh, minimize, minimize-2, minus-circle, minus-square, minus, monitor, moon, more-horizontal, more-vertical, move, music, navigation-2, navigation, octagon, pause-circle, percent, plus-circle, plus-square, plus, power, radio, rss, search, server, share, shopping-bag, sidebar, smartphone, smile, square, table-2, tablet, target, terminal, trash-2, trash, triangle, tv, type, upload, x-circle, x-octagon, x-square, x, zoom-in, zoom-out

The MIT License (MIT) (for the icons listed above)

Copyright (c) 2013-present Cole Bemis

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
