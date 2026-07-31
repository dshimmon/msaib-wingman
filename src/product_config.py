"""Atlas-owned values injected through the shared product boundary."""

from product_contract import (
    ProductConfiguration,
    SourceMetadataField,
)


ATLAS_PRODUCT = ProductConfiguration(
    product_key="atlas",
    product_name="Academic Wingman",
    call_sign="Atlas",
    page_title="Atlas | Wingman",
    page_icon="🪿",
    default_domain="General",
    terminal_title="MSAIB WINGMAN",
    terminal_welcome="Welcome aboard, Maverick.",
    source_metadata_fields=(
        SourceMetadataField(
            key="program",
            label="Program",
            placeholder="Optional",
        ),
        SourceMetadataField(
            key="academic_year",
            label="Academic year",
            placeholder="Optional",
        ),
    ),
)
