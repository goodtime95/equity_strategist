class ToolError(Exception):
    """Base exception raised by financial tools."""


class AssetNotFoundError(ToolError):
    """Raised when no asset matches the user query."""


class AmbiguousAssetError(ToolError):
    """Raised when several assets could match the user query."""
