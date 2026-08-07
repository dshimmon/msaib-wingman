"""Typed product-neutral document extraction failures."""


class DocumentExtractionError(ValueError):
    """Base error for a document that cannot produce normalized units."""


class NoReadableContentError(DocumentExtractionError):
    """The document is valid enough to inspect but contains no usable text."""


class NoExtractableTextError(NoReadableContentError):
    """A PDF exposed no extractable text through the current adapter."""


class DocumentDecodingError(DocumentExtractionError):
    """A text-based document does not use the supported encoding."""
