"""
Auth0 configuration loaded from environment variables.

This module expects the following environment variables to be set (use
`.env` for local development; see `.env.example`):

- AUTH0_DOMAIN
- CLIENT_ID
- CLIENT_SECRET
- REDIRECT_URI
- AUDIENCE
- ALGORITHMS (comma-separated, e.g. RS256)

The module validates presence of these values at import time and will raise a
clear RuntimeError listing any missing variables so the app fails fast in
misconfigured environments.
"""

import os
from dotenv import load_dotenv

# Load .env for local development (no-op if not present)
load_dotenv()

# Read required Auth0 settings from environment and validate
missing = []

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
if not AUTH0_DOMAIN:
	missing.append("AUTH0_DOMAIN")

CLIENT_ID = os.getenv("CLIENT_ID")
if not CLIENT_ID:
	missing.append("CLIENT_ID")

CLIENT_SECRET = os.getenv("CLIENT_SECRET")
if not CLIENT_SECRET:
	missing.append("CLIENT_SECRET")

REDIRECT_URI = os.getenv("REDIRECT_URI")
if not REDIRECT_URI:
	missing.append("REDIRECT_URI")

AUDIENCE = os.getenv("AUDIENCE")
if not AUDIENCE:
	missing.append("AUDIENCE")

_algos = os.getenv("ALGORITHMS")
if not _algos:
	missing.append("ALGORITHMS")
else:
	ALGORITHMS = [a.strip() for a in _algos.split(",") if a.strip()]

if missing:
	raise RuntimeError(
		"Missing required Auth0 environment variables: " + ", ".join(missing) +
		".\nCopy or fill `.env.example` and set these variables for local development."
	)