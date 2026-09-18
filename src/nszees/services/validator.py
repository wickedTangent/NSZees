"""Auto-validation state machine for NSP/NSZ files.

Orchestrates the workflow:
1. Container Check (instant Python validation for NSP only)
2. Quick Verify (nsz --quick-verify subprocess)

Returns validation state to control UI (enable/disable compress, show warnings).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from nszees.checks import check_pfs0_container
from nszees.nsz import NszRunner
from .key_inspector import inspect_key_requirement
from .nca_signature import check_package_signature


@dataclass
class ValidationResult:
    """Result of file validation workflow.
    
    Attributes:
        container_valid: True if PFS0 structure is valid
        container_error: Error message if container check failed, None otherwise
        quick_verify_passed: True if nsz --quick-verify succeeded, None if not run
        quick_verify_output: Output from quick verify command
        can_compress: True if primary transform action should be enabled
        can_force_compress: True if force-compress should be offered
        primary_action: "compress" for NSP, "decompress" for NSZ
        required_key_name: Required master key name if ticket metadata is available
        required_key_present: True if required key is present in root prod.keys, False if missing
        signature_checked: True if the NCA header signature check ran (only after a passing quick verify)
        signature_valid: True if the NCA header matches Nintendo's signing key, False if not, None if not checked
        warnings: List of warning messages to display
    """
    container_valid: bool
    container_error: Optional[str]
    quick_verify_passed: Optional[bool]
    quick_verify_output: Optional[str]
    can_compress: bool
    can_force_compress: bool
    primary_action: str
    required_key_name: Optional[str]
    required_key_present: Optional[bool]
    signature_checked: bool
    signature_valid: Optional[bool]
    warnings: list[str]


class FileValidator:
    """Auto-validation state machine for NSP/NSZ files.
    
    Runs container check + quick verify and returns state for UI control.
    
    Example:
        >>> validator = FileValidator()
        >>> result = validator.validate("game.nsp")
        >>> if not result.can_compress:
        ...     print("Compression disabled:", result.warnings)
        >>> elif result.can_force_compress:
        ...     print("Quick verify failed, force compress available")
    """
    
    def __init__(self):
        """Initialize validator with nsz wrapper."""
        self.nsz_runner = NszRunner()
    
    def validate(self, filepath: str) -> ValidationResult:
        """Run auto-validation workflow on an NSP/NSZ file.
        
        Workflow:
        1. Container Check (instant)
           - If fails: disable compress, skip quick verify
        2. Quick Verify (subprocess)
           - If fails: warn but allow force compress
        
        Args:
            filepath: Path to NSP/NSZ file to validate
            
        Returns:
            ValidationResult with validation state and UI control flags
        """
        warnings = []
        path = Path(filepath)
        suffix = path.suffix.lower()

        if suffix not in {".nsp", ".nsz", ".xci", ".xcz"}:
            return ValidationResult(
                container_valid=False,
                container_error=f"Unsupported file type: {suffix or '(none)'}",
                quick_verify_passed=None,
                quick_verify_output=None,
                can_compress=False,
                can_force_compress=False,
                primary_action="compress",
                required_key_name=None,
                required_key_present=None,
                signature_checked=False,
                signature_valid=None,
                warnings=["Select an NSP, NSZ, XCI, or XCZ file."],
            )

        is_compressed = suffix in {".nsz", ".xcz"}
        primary_action = "decompress" if is_compressed else "compress"

        # Step 1: Container Check (PFS0 structural check, NSP only).
        # NSZ/XCZ are already-compressed containers with their own format, and
        # XCI uses HFS0 (not PFS0) - both skip straight to nsz's quick verify.
        if suffix == ".nsp":
            container_valid, container_error = check_pfs0_container(filepath)
        else:
            container_valid, container_error = True, None
        
        if not container_valid:
            # Container check failed - disable all compression
            return ValidationResult(
                container_valid=False,
                container_error=container_error,
                quick_verify_passed=None,
                quick_verify_output=None,
                can_compress=False,
                can_force_compress=False,
                primary_action=primary_action,
                required_key_name=None,
                required_key_present=None,
                signature_checked=False,
                signature_valid=None,
                warnings=[f"Container validation failed: {container_error}"]
            )

        key_requirement = inspect_key_requirement(path, self.nsz_runner.app_root)
        if key_requirement.required_key_name and key_requirement.required_key_present is True:
            warnings.append(f"Required key available: {key_requirement.required_key_name}")
        elif key_requirement.required_key_name and key_requirement.required_key_present is False:
            warnings.append(f"Required key missing: {key_requirement.required_key_name}")
        
        # Step 2: Quick Verify
        quick_verify_passed = None
        quick_verify_output = None
        
        try:
            result = self.nsz_runner.quick_verify(Path(filepath))
            quick_verify_output = result.stdout + result.stderr
            quick_verify_passed = result.ok
            
            if not quick_verify_passed:
                if is_compressed:
                    warnings.append(
                        f"Quick verification failed (exit code {result.return_code}). "
                        "Fix verification issues before decompression."
                    )
                else:
                    warnings.append(
                        f"Quick verification failed (exit code {result.return_code}). "
                        "You can still compress using 'Force Compress'."
                    )
        except Exception as e:
            if is_compressed:
                warnings.append(f"Quick verification error: {e}.")
            else:
                warnings.append(f"Quick verification error: {e}. You can still compress using 'Force Compress'.")
            quick_verify_passed = False
            quick_verify_output = str(e)
        
        # Determine compression availability
        # - can_compress: normal compress (only if quick verify passed)
        # - can_force_compress: force compress (available if container valid but quick verify failed)
        can_compress = quick_verify_passed is True
        can_force_compress = (not quick_verify_passed) and container_valid and (not is_compressed)

        # Step 3: NCA header signature check (informational only - runs after a
        # successful quick verify). A failure here means the file was likely
        # repackaged from its original retail form, not that it's corrupt.
        signature_checked = False
        signature_valid = None
        if quick_verify_passed:
            signature_result = check_package_signature(path, self.nsz_runner.app_root)
            signature_checked = signature_result.checked
            signature_valid = signature_result.valid
            if signature_checked and signature_valid is False:
                warnings.append(
                    "File was repackaged (NCA header signature does not match Nintendo's key)"
                )

        return ValidationResult(
            container_valid=True,
            container_error=None,
            quick_verify_passed=quick_verify_passed,
            quick_verify_output=quick_verify_output,
            can_compress=can_compress,
            can_force_compress=can_force_compress,
            primary_action=primary_action,
            required_key_name=key_requirement.required_key_name,
            required_key_present=key_requirement.required_key_present,
            signature_checked=signature_checked,
            signature_valid=signature_valid,
            warnings=warnings
        )
