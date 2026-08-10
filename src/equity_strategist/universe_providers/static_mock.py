class StaticMockUniverseProvider:
    """Temporary provider used until a real dynamic provider is added."""

    def get_constituents(
        self,
        provider_identifier: str,
    ) -> tuple[str, ...]:
        raise ValueError(
            f"dynamic universe provider not implemented: {provider_identifier}"
        )
