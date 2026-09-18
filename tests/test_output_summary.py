from nszees.services.output_summary import summarise_nsz_output, summarise_validation
from nszees.services.validator import ValidationResult


def test_summarise_compress_output_success():
    stdout = (
        "[OPEN] file.nca 100 bytes at 0x0\n"
        "[ADDING] file.nca 100 bytes to PFS0 at 0x0\n"
        "[EXISTS] file.nca\n"
        "[NCA HASH] deadbeef\n"
        "[VERIFIED] file.nca deadbeef\n"
        "[NSP SHA256] cafebabecafebabe\n"
    )
    summary = summarise_nsz_output(stdout, "", 0)
    assert "file.nca" in summary
    assert "Done" in summary
    assert "[OPEN]" not in summary
    assert "[ADDING]" not in summary
    assert "[EXISTS]" not in summary
    assert "[NCA HASH]" not in summary


def test_summarise_unconfirmed_master_key_warning():
    stdout = "Unconfirmed: crc32(master_key_15) = 4071812001\n"
    summary = summarise_nsz_output(stdout, "", 0)
    assert "15" in summary
    assert "prod.keys may be outdated" in summary


def test_summarise_failure_exit_code():
    summary = summarise_nsz_output("", "", 1)
    assert "Failed" in summary
    assert "exit code 1" in summary


def test_summarise_stderr_included():
    summary = summarise_nsz_output("", "some warning on stderr", 0)
    assert "some warning on stderr" in summary


def _validation_result(**overrides):
    defaults = dict(
        container_valid=True,
        container_error=None,
        quick_verify_passed=True,
        quick_verify_output=None,
        can_compress=True,
        can_force_compress=False,
        primary_action="compress",
        required_key_name=None,
        required_key_present=None,
        signature_checked=False,
        signature_valid=None,
        warnings=[],
    )
    defaults.update(overrides)
    return ValidationResult(**defaults)


def test_summarise_validation_container_invalid():
    result = _validation_result(container_valid=False, container_error="bad magic")
    summary = summarise_validation(result)
    assert "Container invalid" in summary
    assert "bad magic" in summary


def test_summarise_validation_key_present():
    result = _validation_result(required_key_name="master_key_11", required_key_present=True)
    summary = summarise_validation(result)
    assert "Required key present: master_key_11" in summary
