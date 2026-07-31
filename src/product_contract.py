"""Declared boundary for product configuration supplied to Wingman."""

import re
from dataclasses import dataclass


FRAMEWORK_SOURCE_METADATA_FIELDS = frozenset(
    {
        "can_remove",
        "can_reprocess",
        "concept_count",
        "content_hash",
        "display_name",
        "domain",
        "embedding_count",
        "file_name",
        "file_type",
        "id",
        "knowledge_object_count",
        "knowledge_path",
        "mime_type",
        "original_available",
        "original_path",
        "record_count",
        "reprocessed_at",
        "source_id",
        "source_kind",
        "source_url",
        "status",
        "uploaded_at",
    }
)

PRODUCT_METADATA_KEY_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]*$"
)


def validate_product_metadata_key(key):
    """Reject ambiguous or framework-owned product metadata keys."""
    if not isinstance(
        key,
        str,
    ) or not PRODUCT_METADATA_KEY_PATTERN.fullmatch(key):
        raise ValueError(
            "Product metadata keys must use lower-case "
            "snake_case and begin with a letter."
        )
    if key in FRAMEWORK_SOURCE_METADATA_FIELDS:
        raise ValueError(
            "Product metadata cannot replace framework-owned "
            f"source field {key!r}."
        )
    return key


@dataclass(frozen=True)
class SourceMetadataField:
    """One product-owned source metadata field shown by an interface."""

    key: str
    label: str
    placeholder: str = ""

    def __post_init__(self):
        validate_product_metadata_key(self.key)
        if not isinstance(
            self.label,
            str,
        ) or not self.label.strip():
            raise ValueError(
                "Product metadata field labels cannot be empty."
            )


@dataclass(frozen=True)
class ProductConfiguration:
    """Minimal identity and presentation values injected by a product."""

    product_key: str
    product_name: str
    call_sign: str
    page_title: str
    page_icon: str
    default_domain: str
    source_metadata_fields: tuple[SourceMetadataField, ...] = ()
    terminal_title: str = "WINGMAN"
    terminal_welcome: str = "Welcome."

    def __post_init__(self):
        required_values = (
            self.product_key,
            self.product_name,
            self.call_sign,
            self.page_title,
            self.default_domain,
            self.terminal_title,
            self.terminal_welcome,
        )
        if any(not isinstance(value, str) or not value.strip()
               for value in required_values):
            raise ValueError(
                "Product configuration identity values cannot be empty."
            )

        field_keys = [
            field.key for field in self.source_metadata_fields
        ]
        if len(field_keys) != len(set(field_keys)):
            raise ValueError(
                "Product source metadata field keys must be unique."
            )
