"""Fixed catalogue/media policy shared by request and service boundaries.

These are not runtime settings. Changing price bounds also requires reviewing the
persisted database constraints and writing a migration; never rewrite old migrations.
The shared upload byte cap also applies to images processed outside the catalogue.
"""

from typing import Final

MIN_PRODUCT_PRICE: Final = 100
MAX_PRODUCT_PRICE: Final = 500_000
MAX_IMAGES_PER_PRODUCT: Final = 6
MAX_IMAGE_BYTES: Final = 5 * 1024 * 1024
