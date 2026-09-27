# Requests-Module made by psf added = 27.09.2026

'''
    Copyright (C) 2025, Python Software Foundation
    Author = Python Software Foundation
    Version = 2.32.5 (Last compatible Version for KODI with Python 3.8) / 18.08.2025 - Dropped support for Python 3.8 following its end of support.
    ♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦
    ♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦
    ♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦
        @realvito
        ===== ZULETZT BEARBEITET: 23.05.2026 =====
        ===== Integration des Moduls in das Addon - DMAX Mediathek =====
    ♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦
    ♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦
    ♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦♦
        LINK for new Requests-Module = https://github.com/psf/requests

    Requests
    A simple, yet elegant, HTTP library.

    Apache License
    Version 2.0, January 2004

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
'''

import warnings

import urllib3

from .exceptions import RequestsDependencyWarning

try:
    from charset_normalizer import __version__ as charset_normalizer_version
except ImportError:
    charset_normalizer_version = None

try:
    from chardet import __version__ as chardet_version
except ImportError:
    chardet_version = None


def check_compatibility(urllib3_version, chardet_version, charset_normalizer_version):
    urllib3_version = urllib3_version.split(".")
    assert urllib3_version != ["dev"]  # Verify urllib3 isn't installed from git.

    # Sometimes, urllib3 only reports its version as 16.1.
    if len(urllib3_version) == 2:
        urllib3_version.append("0")

    # Check urllib3 for compatibility.
    major, minor, patch = urllib3_version  # noqa: F811
    major, minor, patch = int(major), int(minor), int(patch)
    # urllib3 >= 1.21.1
    assert major >= 1
    if major == 1:
        assert minor >= 21

    # Check charset_normalizer for compatibility.
    if chardet_version:
        major, minor, patch = chardet_version.split(".")[:3]
        major, minor, patch = int(major), int(minor), int(patch)
        # chardet_version >= 3.0.2, < 6.0.0
        assert (3, 0, 2) <= (major, minor, patch) < (6, 0, 0)
    elif charset_normalizer_version:
        major, minor, patch = charset_normalizer_version.split(".")[:3]
        major, minor, patch = int(major), int(minor), int(patch)
        # charset_normalizer >= 2.0.0 < 4.0.0
        assert (2, 0, 0) <= (major, minor, patch) < (4, 0, 0)
    else:
        warnings.warn(
            "Unable to find acceptable character detection dependency "
            "(chardet or charset_normalizer).",
            RequestsDependencyWarning,
        )


def _check_cryptography(cryptography_version):
    # cryptography < 1.3.4
    try:
        cryptography_version = list(map(int, cryptography_version.split(".")))
    except ValueError:
        return

    if cryptography_version < [1, 3, 4]:
        warning = "Old version of cryptography ({}) may cause slowdown.".format(
            cryptography_version
        )
        warnings.warn(warning, RequestsDependencyWarning)


# Check imported dependencies for compatibility.
try:
    check_compatibility(
        urllib3.__version__, chardet_version, charset_normalizer_version
    )
except (AssertionError, ValueError):
    warnings.warn(
        "urllib3 ({}) or chardet ({})/charset_normalizer ({}) doesn't match a supported "
        "version!".format(
            urllib3.__version__, chardet_version, charset_normalizer_version
        ),
        RequestsDependencyWarning,
    )

# Attempt to enable urllib3's fallback for SNI support
# if the standard library doesn't support SNI or the
# 'ssl' library isn't available.
try:
    try:
        import ssl
    except ImportError:
        ssl = None

    if not getattr(ssl, "HAS_SNI", False):
        from urllib3.contrib import pyopenssl

        pyopenssl.inject_into_urllib3()

        # Check cryptography version
        from cryptography import __version__ as cryptography_version

        _check_cryptography(cryptography_version)
except ImportError:
    pass

# urllib3's DependencyWarnings should be silenced.
from urllib3.exceptions import DependencyWarning

warnings.simplefilter("ignore", DependencyWarning)

# Set default logging handler to avoid "No handler found" warnings.
import logging
from logging import NullHandler

from . import packages, utils
from .__version__ import (
    __author__,
    __author_email__,
    __build__,
    __cake__,
    __copyright__,
    __description__,
    __license__,
    __title__,
    __url__,
    __version__,
)
from .api import delete, get, head, options, patch, post, put, request
from .adapters import HTTPAdapter
from .exceptions import (
    ConnectionError,
    ConnectTimeout,
    FileModeWarning,
    HTTPError,
    JSONDecodeError,
    ReadTimeout,
    RequestException,
    Timeout,
    TooManyRedirects,
    URLRequired,
)
from .models import PreparedRequest, Request, Response
from .sessions import Session, session
from .status_codes import codes

logging.getLogger(__name__).addHandler(NullHandler())

# FileModeWarnings go off per the default.
warnings.simplefilter("default", FileModeWarning, append=True)
