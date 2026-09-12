class WriterBoundary:
    """Safety boundary for the LangFlow Writer Agent.

    Google Sheets/Current Date tools belong only behind this boundary.
    """
    def can_write(self, validated_record: dict, confirmed: bool) -> bool:
        return validated_record.get("status_data") == "Lengkap" and confirmed

    def build_write_plan(self, validated_record: dict, confirmed: bool) -> dict:
        if not self.can_write(validated_record, confirmed):
            raise ValueError("Write blocked: record must be complete and explicitly confirmed.")
        return {"operation": "CREATE", "record": validated_record}
