"""Product Contract v1: the explicit product-to-Wingman attachment seam."""

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any


PRODUCT_CONTRACT_VERSION = 1
SUPPORTED_PRODUCT_CONTRACT_VERSIONS = frozenset(
    {PRODUCT_CONTRACT_VERSION}
)


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

PRODUCT_ID_PATTERN = re.compile(
    r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
)
PRODUCT_METADATA_KEY_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]*$"
)

MetadataNormalizer = Callable[[Any], Any]
KnowledgeEnricher = Callable[
    [dict[str, Any]],
    dict[str, Any],
]
RetrievalInterpreter = Callable[..., Mapping[str, Any]]
BriefingPlanner = Callable[[str], Mapping[str, Any]]
BriefingGenerator = Callable[..., Mapping[str, Any]]


class ProductCapability(str, Enum):
    """Current product-neutral behavior exposed by shared composition."""

    SOURCE_GROUNDED_CHAT = "source_grounded_chat"
    SOURCE_INGESTION = "source_ingestion"
    EVIDENCE_RETRIEVAL = "evidence_retrieval"
    BRIEFING = "briefing"
    SOURCE_LIBRARY = "source_library"


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


def preserve_metadata_value(value):
    """Default declaration rule: preserve the caller-owned value exactly."""
    return value


@dataclass(frozen=True)
class SourceMetadataField:
    """One declared product-owned source metadata extension."""

    key: str
    label: str
    placeholder: str = ""
    normalizer: MetadataNormalizer = preserve_metadata_value

    def __post_init__(self):
        validate_product_metadata_key(self.key)
        if not isinstance(
            self.label,
            str,
        ) or not self.label.strip():
            raise ValueError(
                "Product metadata field labels cannot be empty."
            )
        if not isinstance(self.placeholder, str):
            raise ValueError(
                "Product metadata placeholders must be strings."
            )
        if not callable(self.normalizer):
            raise ValueError(
                "Product metadata normalizers must be callable."
            )


@dataclass(frozen=True)
class RecordDeclaration:
    """One product-owned record shape emitted during enrichment."""

    record_type: str
    fields: tuple[str, ...]

    def __post_init__(self):
        validate_product_metadata_key(self.record_type)
        fields = tuple(self.fields)
        object.__setattr__(self, "fields", fields)
        if not fields:
            raise ValueError(
                "Product record declarations must name fields."
            )
        for field in fields:
            validate_product_metadata_key(field)
        if "type" in fields:
            raise ValueError(
                "Record fields must not repeat the framework type key."
            )
        if len(fields) != len(set(fields)):
            raise ValueError(
                "Product record declaration fields must be unique."
            )


@dataclass(frozen=True)
class RecordComposition:
    """Product-owned record declarations and enrichment callback."""

    declarations: tuple[RecordDeclaration, ...]
    enrich_knowledge: KnowledgeEnricher

    def __post_init__(self):
        declarations = tuple(self.declarations)
        object.__setattr__(self, "declarations", declarations)
        if not declarations:
            raise ValueError(
                "Product record declarations cannot be empty."
            )
        record_types = [
            declaration.record_type
            for declaration in declarations
        ]
        if len(record_types) != len(set(record_types)):
            raise ValueError(
                "Product record types must be unique."
            )
        if not callable(self.enrich_knowledge):
            raise ValueError(
                "Product record enrichment must be callable."
            )


@dataclass(frozen=True)
class RetrievalComposition:
    """Product-owned interpretation that produces a neutral plan."""

    interpret_query: RetrievalInterpreter

    def __post_init__(self):
        if not callable(self.interpret_query):
            raise ValueError(
                "Product retrieval interpretation must be callable."
            )


@dataclass(frozen=True)
class BriefingComposition:
    """Product-owned briefing planning and generation policy."""

    plan_briefing: BriefingPlanner
    generate_briefing: BriefingGenerator

    def __post_init__(self):
        if not callable(self.plan_briefing):
            raise ValueError(
                "Product briefing planning must be callable."
            )
        if not callable(self.generate_briefing):
            raise ValueError(
                "Product briefing generation must be callable."
            )


@dataclass(frozen=True)
class ProductContract:
    """Authoritative immutable Product Contract v1 definition."""

    product_key: str
    product_name: str
    call_sign: str
    page_title: str
    page_icon: str
    default_domain: str
    source_metadata_fields: tuple[SourceMetadataField, ...] = ()
    terminal_title: str = "WINGMAN"
    terminal_welcome: str = "Welcome."
    contract_version: int = 0
    capabilities: frozenset[ProductCapability] = frozenset()
    records: RecordComposition | None = None
    retrieval: RetrievalComposition | None = None
    briefing: BriefingComposition | None = None
    chat_label: str = ""
    library_label: str = ""
    briefing_label: str = ""

    def __post_init__(self):
        metadata_fields = tuple(self.source_metadata_fields)
        object.__setattr__(
            self,
            "source_metadata_fields",
            metadata_fields,
        )
        field_keys = [
            field.key for field in metadata_fields
        ]
        if len(field_keys) != len(set(field_keys)):
            raise ValueError(
                "Product source metadata field keys must be unique."
            )

        if (
            type(self.contract_version) is not int
            or self.contract_version not in (
                SUPPORTED_PRODUCT_CONTRACT_VERSIONS
            )
        ):
            raise ValueError(
                "Incompatible Product Contract version: "
                f"{self.contract_version!r}; supported versions: "
                f"{sorted(SUPPORTED_PRODUCT_CONTRACT_VERSIONS)}."
            )

        if not isinstance(
            self.product_key,
            str,
        ) or not PRODUCT_ID_PATTERN.fullmatch(self.product_key):
            raise ValueError(
                "Product IDs must use lower-case letters, digits, "
                "and single hyphens."
            )

        required_values = (
            self.product_name,
            self.call_sign,
            self.page_title,
            self.default_domain,
            self.terminal_title,
            self.terminal_welcome,
            self.chat_label,
            self.library_label,
            self.briefing_label,
        )
        if any(
            not isinstance(value, str) or not value.strip()
            for value in required_values
        ):
            raise ValueError(
                "Product Contract identity, defaults, and UI "
                "declarations cannot be empty."
            )
        if not isinstance(self.page_icon, str):
            raise ValueError(
                "Product page icons must be strings."
            )

        capabilities = frozenset(self.capabilities)
        object.__setattr__(self, "capabilities", capabilities)
        if not capabilities or any(
            not isinstance(capability, ProductCapability)
            for capability in capabilities
        ):
            raise ValueError(
                "Product capabilities must be declared with "
                "ProductCapability values."
            )

        if not isinstance(self.records, RecordComposition):
            raise ValueError(
                "Product record declarations and enrichment are required."
            )
        if not isinstance(
            self.retrieval,
            RetrievalComposition,
        ):
            raise ValueError(
                "Product retrieval composition is required."
            )

        briefing_enabled = (
            ProductCapability.BRIEFING in capabilities
        )
        if briefing_enabled and not isinstance(
            self.briefing,
            BriefingComposition,
        ):
            raise ValueError(
                "Products with briefing capability must declare "
                "briefing composition."
            )
        if not briefing_enabled and self.briefing is not None:
            raise ValueError(
                "Briefing composition requires briefing capability."
            )

        if (
            ProductCapability.SOURCE_GROUNDED_CHAT
            in capabilities
            and ProductCapability.EVIDENCE_RETRIEVAL
            not in capabilities
        ):
            raise ValueError(
                "Source-grounded chat requires evidence retrieval."
            )
        if (
            ProductCapability.BRIEFING in capabilities
            and ProductCapability.EVIDENCE_RETRIEVAL
            not in capabilities
        ):
            raise ValueError(
                "Briefing capability requires evidence retrieval."
            )

    @property
    def product_id(self):
        """Stable internal identity with explicit display separation."""
        return self.product_key

    @property
    def display_name(self):
        """User-facing name retained separately from the internal ID."""
        return self.product_name

    def supports(self, capability):
        """Return whether this definition declares one capability."""
        return capability in self.capabilities


@dataclass(frozen=True)
class ProductConfiguration:
    """Deprecated Airframe-era input adapter for Product Contract v1."""

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
        if any(
            not isinstance(value, str) or not value.strip()
            for value in required_values
        ):
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

    def to_product_contract(
        self,
        *,
        contract_version,
        capabilities,
        records,
        retrieval,
        chat_label,
        library_label,
        briefing_label,
        briefing=None,
    ):
        """Complete this legacy input as one authoritative v1 contract."""
        return ProductContract(
            contract_version=contract_version,
            product_key=self.product_key,
            product_name=self.product_name,
            call_sign=self.call_sign,
            page_title=self.page_title,
            page_icon=self.page_icon,
            default_domain=self.default_domain,
            source_metadata_fields=self.source_metadata_fields,
            terminal_title=self.terminal_title,
            terminal_welcome=self.terminal_welcome,
            capabilities=capabilities,
            records=records,
            retrieval=retrieval,
            briefing=briefing,
            chat_label=chat_label,
            library_label=library_label,
            briefing_label=briefing_label,
        )


@dataclass(frozen=True)
class ProductContext:
    """One immutable, scoped selection of a validated product."""

    product: ProductContract

    def __post_init__(self):
        if not isinstance(self.product, ProductContract):
            raise TypeError(
                "Product Context requires a validated Product Contract."
            )

    @property
    def product_id(self):
        return self.product.product_id

    def require(self, capability):
        """Fail before shared work when a capability is unavailable."""
        if not isinstance(capability, ProductCapability):
            raise TypeError(
                "Product capability checks require ProductCapability."
            )
        if not self.product.supports(capability):
            raise ValueError(
                f"Product {self.product_id!r} does not declare "
                f"capability {capability.value!r}."
            )
        return self


class ProductRegistry:
    """Immutable, deterministic registry of explicit product definitions."""

    __slots__ = ("_products", "_product_ids")

    def __setattr__(self, name, value):
        if hasattr(self, name):
            raise AttributeError(
                "Product Registry is immutable after construction."
            )
        object.__setattr__(self, name, value)

    def __init__(self, products: Iterable[ProductContract]):
        definitions = tuple(products)
        registered = {}
        for product in definitions:
            if not isinstance(product, ProductContract):
                raise TypeError(
                    "Product registration requires Product Contract "
                    "definitions."
                )
            product_id = product.product_id
            if product_id in registered:
                raise ValueError(
                    f"Duplicate product ID: {product_id!r}."
                )
            registered[product_id] = product
        self._product_ids = tuple(sorted(registered))
        self._products = MappingProxyType(
            {
                product_id: registered[product_id]
                for product_id in self._product_ids
            }
        )

    @property
    def product_ids(self):
        return self._product_ids

    def require(self, product_id):
        """Resolve one known product or fail with an actionable error."""
        try:
            return self._products[product_id]
        except KeyError as error:
            known = ", ".join(self._product_ids) or "none"
            raise KeyError(
                f"Unknown product {product_id!r}; registered products: "
                f"{known}."
            ) from error

    def create_context(self, product_id):
        """Create a fresh immutable context for one explicit selection."""
        return ProductContext(self.require(product_id))
