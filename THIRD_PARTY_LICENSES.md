# Third-Party Licenses

NSZees is built on top of several open-source projects, bundled in `bin/` as
part of the portable distribution. This file lists each one, its license, and
attribution, per the terms of those licenses.

NSZees's own source code is not itself covered by this file — see the
project's own license/README for that.

---

## nsz

- **Project:** https://github.com/nicoboss/nsz
- **License:** MIT
- **Used as:** the compression/decompression backend NSZees wraps (both as a
  subprocess via `bin/run_nsz.py` and in-process for NSP/NCA ticket
  inspection). NSZees does not modify nsz's source.

Per nsz's own README: *"This project does NOT incorporate any copyrighted
material such as cryptographic keys. All keys must be provided by the user."*
NSZees follows the same principle — `prod.keys`/`title.keys` must be supplied
by the user and are never bundled or distributed.

```
MIT License

Copyright (c) 2019 Nico Bosshard and Blake Warner

Some code inside NSZ originates from NUT. Blake Warner, as the author of NUT,
permits to license all NUT code used in NSZ to the following MIT license.
This permission isn't bound to this project so that NUT code inside NSZ can
be used and sublicensed like any other MIT licensed code.

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
```

---

## PySide6 / shiboken6 (Qt for Python)

- **Project:** https://www.pyside.org / https://code.qt.io/cgit/pyside/pyside-setup.git
- **License:** LGPL-3.0 (available under LGPLv3, GPLv2, GPLv3, or a
  commercial Qt license; NSZees uses the LGPLv3 terms)
- **Used as:** the GUI toolkit (QtCore, QtGui, QtWidgets only — NSZees
  installs `PySide6-Essentials` + `shiboken6` directly rather than the full
  `PySide6` meta-package, to avoid bundling unused Qt Addons modules such as
  WebEngine, Multimedia, and Qt3D)

NSZees uses the official, unmodified PySide6/shiboken6 wheels from PyPI,
loaded dynamically at runtime (the `.dll` files in `bin/Lib/site-packages/`
are not statically linked into a single executable), which is what makes
LGPL compliance straightforward: a user is free to replace those files with
their own modified build of PySide6/Qt.

Full license text: https://www.gnu.org/licenses/lgpl-3.0.txt
Qt for Python source: https://code.qt.io/cgit/pyside/pyside-setup.git

---

## pycryptodome

- **Project:** https://github.com/Legrandin/pycryptodome
- **License:** BSD 2-Clause and public domain (varies by file)
- **Used as:** AES decryption, required by nsz

```
The source code in PyCryptodome is partially in the public domain
and partially released under the BSD 2-Clause license.

In either case, there are minimal if no restrictions on the redistribution,
modification and usage of the software.

Public domain
=============

All code originating from PyCrypto is free and unencumbered software
released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <http://unlicense.org>

BSD license
===========

All direct contributions to PyCryptodome are released under the following
license. The copyright of each piece belongs to the respective author.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

---

## zstandard (python-zstandard)

- **Project:** https://github.com/indygreg/python-zstandard
- **License:** BSD 3-Clause
- **Used as:** Zstandard compression bindings, required by nsz

```
Copyright (c) 2016, Gregory Szorc
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
may be used to endorse or promote products derived from this software without
specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

---

## enlighten

- **Project:** https://github.com/Rockhopper-Technologies/enlighten
- **License:** Mozilla Public License 2.0 (MPL-2.0)
- **Used as:** progress bar output, required by nsz. NSZees uses it unmodified,
  as a library dependency only — no NSZees or nsz source files are covered by
  MPL-2.0.

Full license text: https://www.mozilla.org/en-US/MPL/2.0/

---

## enlighten's own dependencies

Pulled in transitively by `enlighten`, all used unmodified:

- `blessed`, `wcwidth` — MIT
- `jinxed`, `prefixed`, `ansicon` — MPL-2.0

See https://pypi.org for each project's individual license text.
