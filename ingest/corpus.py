"""Per-document facts the PDFs don't carry. Source: corpus.md."""

FAMILIES: dict[str, list[str]] = {
    "acs880_primary_firmware_manual": ["ACS880"],
    "acs580_firmware_manual": ["ACS580"],
    "acs580_01_hardware_manual": ["ACS580"],
    "acs880_01_hardware_manual": ["ACS880"],
    "fpno21_profinet_adapter_manual": ["ACS580", "ACS880", "ACQ580"],
    "acs580_technical_catalog": ["ACS580"],
    "acs550_to_acs580_replacement": ["ACS550", "ACS580"],
    "acs580_01_type4x_quickstart": ["ACS580"],
}
