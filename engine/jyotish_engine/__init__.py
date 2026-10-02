"""Jyotish engine: deterministic Vedic astrology calculations.

The engine is pure and side-effect free apart from reading the ephemeris
kernel. Every public result carries the engine version and the settings used,
so any chart can be reproduced exactly.
"""

__version__ = "0.1.0"

ENGINE_VERSION = __version__
