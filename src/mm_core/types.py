"""Shared type definitions for MetaMessage web integrations."""

from typing import TypeVar


T = TypeVar("T")


CONTENT_TYPE_METAMESSAGE = "application/metamessage"


class MMEncoderError(Exception):
    """Error during MetaMessage encoding."""

    def __init__(self, message: str, cause: Exception = None):
        super().__init__(message)
        self.cause = cause


class MMDecoderError(Exception):
    """Error during MetaMessage decoding."""

    def __init__(self, message: str, cause: Exception = None):
        super().__init__(message)
        self.cause = cause


class MMRequest:
    """Request model for MetaMessage data."""
    data: dict


class MMResponse:
    """Response model for MetaMessage data."""

    data: dict