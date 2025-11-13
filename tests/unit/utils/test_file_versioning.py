"""
Unit tests for file_versioning utility.

Tests SHA256 checksums, versioned filenames, and file integrity verification.
"""

import pytest

from agentic_neurodata_conversion.utils.file_versioning import (
    compute_sha256,
    create_versioned_file,
    get_all_versions,
    get_versioned_filename,
    verify_file_integrity,
)


@pytest.mark.unit
class TestComputeSHA256:
    """Tests for compute_sha256 function."""

    def test_compute_sha256_empty_file(self, tmp_path):
        """Test SHA256 of empty file."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        checksum = compute_sha256(empty_file)

        # SHA256 of empty file is a known constant
        assert checksum == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_compute_sha256_small_file(self, tmp_path):
        """Test SHA256 of small file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        checksum = compute_sha256(test_file)

        # SHA256 of "hello world" is a known constant
        assert len(checksum) == 64  # SHA256 produces 64 hex chars
        assert checksum == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"

    def test_compute_sha256_large_file(self, tmp_path):
        """Test SHA256 handles large files with chunked reading."""
        large_file = tmp_path / "large.bin"

        # Create file larger than chunk size (4096 bytes)
        data = b"x" * 10000
        large_file.write_bytes(data)

        checksum = compute_sha256(large_file)

        assert len(checksum) == 64
        assert isinstance(checksum, str)

    def test_compute_sha256_binary_file(self, tmp_path):
        """Test SHA256 of binary file."""
        binary_file = tmp_path / "binary.bin"
        binary_data = bytes(range(256))
        binary_file.write_bytes(binary_data)

        checksum = compute_sha256(binary_file)

        assert len(checksum) == 64

    def test_compute_sha256_consistent_results(self, tmp_path):
        """Test SHA256 produces consistent results for same content."""
        test_file = tmp_path / "consistent.txt"
        test_file.write_text("consistent data")

        checksum1 = compute_sha256(test_file)
        checksum2 = compute_sha256(test_file)

        assert checksum1 == checksum2


@pytest.mark.unit
class TestGetVersionedFilename:
    """Tests for get_versioned_filename function."""

    def test_get_versioned_filename_attempt_0(self, tmp_path):
        """Test version 0 returns original path."""
        original = tmp_path / "test.nwb"

        versioned = get_versioned_filename(original, 0)

        assert versioned == original

    def test_get_versioned_filename_attempt_1_no_checksum(self, tmp_path):
        """Test version 1 without checksum."""
        original = tmp_path / "test.nwb"

        versioned = get_versioned_filename(original, 1)

        assert versioned.name == "test_v1.nwb"
        assert versioned.parent == original.parent

    def test_get_versioned_filename_attempt_2_no_checksum(self, tmp_path):
        """Test version 2 without checksum."""
        original = tmp_path / "mouse_001.nwb"

        versioned = get_versioned_filename(original, 2)

        assert versioned.name == "mouse_001_v2.nwb"

    def test_get_versioned_filename_with_checksum(self, tmp_path):
        """Test versioned filename with checksum."""
        original = tmp_path / "test.nwb"
        checksum = "a3f9d1c8b7e6f5a4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0"

        versioned = get_versioned_filename(original, 1, checksum)

        assert versioned.name == "test_v1_a3f9d1c8.nwb"

    def test_get_versioned_filename_preserves_extension(self, tmp_path):
        """Test extension is preserved."""
        original = tmp_path / "data.nwb"

        versioned = get_versioned_filename(original, 3, "abcd1234" * 8)

        assert versioned.suffix == ".nwb"

    def test_get_versioned_filename_complex_name(self, tmp_path):
        """Test with complex filename."""
        original = tmp_path / "mouse_001_session_20240117.nwb"

        versioned = get_versioned_filename(original, 5, "deadbeef" * 8)

        assert versioned.name == "mouse_001_session_20240117_v5_deadbeef.nwb"

    def test_get_versioned_filename_uses_first_8_chars_checksum(self, tmp_path):
        """Test only first 8 chars of checksum are used."""
        original = tmp_path / "test.nwb"
        long_checksum = "abcdefgh12345678xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

        versioned = get_versioned_filename(original, 1, long_checksum)

        assert "_abcdefgh" in versioned.name


@pytest.mark.unit
class TestCreateVersionedFile:
    """Tests for create_versioned_file function."""

    def test_create_versioned_file_copies_content(self, tmp_path):
        """Test versioned file has same content as original."""
        original = tmp_path / "original.nwb"
        original.write_text("test data")

        versioned_path, checksum = create_versioned_file(original, 1)

        assert versioned_path.exists()
        assert versioned_path.read_text() == "test data"

    def test_create_versioned_file_returns_checksum(self, tmp_path):
        """Test checksum is returned."""
        original = tmp_path / "test.nwb"
        original.write_text("content")

        versioned_path, checksum = create_versioned_file(original, 1)

        assert checksum is not None
        assert len(checksum) == 64

    def test_create_versioned_file_without_checksum(self, tmp_path):
        """Test creating versioned file without checksum."""
        original = tmp_path / "test.nwb"
        original.write_text("content")

        versioned_path, checksum = create_versioned_file(original, 1, compute_checksum=False)

        assert versioned_path.exists()
        assert checksum is None

    def test_create_versioned_file_raises_on_missing_file(self, tmp_path):
        """Test error when original file doesn't exist."""
        missing = tmp_path / "missing.nwb"

        with pytest.raises(FileNotFoundError, match="File not found"):
            create_versioned_file(missing, 1)

    def test_create_versioned_file_preserves_metadata(self, tmp_path):
        """Test file metadata is preserved (using copy2)."""
        original = tmp_path / "test.nwb"
        original.write_text("data")
        original_stat = original.stat()

        versioned_path, _ = create_versioned_file(original, 1)

        versioned_stat = versioned_path.stat()
        # copy2 preserves timestamps
        assert versioned_stat.st_mtime == original_stat.st_mtime

    def test_create_versioned_file_different_attempts(self, tmp_path):
        """Test multiple version numbers create different files."""
        original = tmp_path / "test.nwb"
        original.write_text("data")

        v1_path, _ = create_versioned_file(original, 1)
        v2_path, _ = create_versioned_file(original, 2)

        assert v1_path != v2_path
        assert v1_path.exists()
        assert v2_path.exists()


@pytest.mark.unit
class TestVerifyFileIntegrity:
    """Tests for verify_file_integrity function."""

    def test_verify_file_integrity_matching_checksum(self, tmp_path):
        """Test verification succeeds with matching checksum."""
        test_file = tmp_path / "test.nwb"
        test_file.write_text("verified content")

        expected_checksum = compute_sha256(test_file)
        result = verify_file_integrity(test_file, expected_checksum)

        assert result is True

    def test_verify_file_integrity_mismatched_checksum(self, tmp_path):
        """Test verification fails with wrong checksum."""
        test_file = tmp_path / "test.nwb"
        test_file.write_text("content")

        wrong_checksum = "0" * 64
        result = verify_file_integrity(test_file, wrong_checksum)

        assert result is False

    def test_verify_file_integrity_missing_file(self, tmp_path):
        """Test verification fails for missing file."""
        missing = tmp_path / "missing.nwb"

        result = verify_file_integrity(missing, "any_checksum")

        assert result is False

    def test_verify_file_integrity_detects_modification(self, tmp_path):
        """Test verification detects file modification."""
        test_file = tmp_path / "test.nwb"
        test_file.write_text("original")

        original_checksum = compute_sha256(test_file)

        # Modify file
        test_file.write_text("modified")

        result = verify_file_integrity(test_file, original_checksum)

        assert result is False


@pytest.mark.unit
class TestGetAllVersions:
    """Tests for get_all_versions function."""

    def test_get_all_versions_original_only(self, tmp_path):
        """Test with only original file."""
        original = tmp_path / "test.nwb"
        original.write_text("data")

        versions = get_all_versions(original)

        assert len(versions) == 1
        assert versions[0] == original

    def test_get_all_versions_with_versions(self, tmp_path):
        """Test finding versioned files."""
        original = tmp_path / "test.nwb"
        original.write_text("v0")

        v1 = tmp_path / "test_v1.nwb"
        v1.write_text("v1")

        v2 = tmp_path / "test_v2.nwb"
        v2.write_text("v2")

        versions = get_all_versions(original)

        assert len(versions) == 3
        assert original in versions
        assert v1 in versions
        assert v2 in versions

    def test_get_all_versions_sorted_order(self, tmp_path):
        """Test versions are sorted by version number."""
        original = tmp_path / "test.nwb"
        original.write_text("v0")

        # Create in random order
        v3 = tmp_path / "test_v3.nwb"
        v3.write_text("v3")

        v1 = tmp_path / "test_v1.nwb"
        v1.write_text("v1")

        v2 = tmp_path / "test_v2.nwb"
        v2.write_text("v2")

        versions = get_all_versions(original)

        assert versions[0] == original
        assert versions[1] == v1
        assert versions[2] == v2
        assert versions[3] == v3

    def test_get_all_versions_with_checksums(self, tmp_path):
        """Test finding versions with checksum suffixes."""
        original = tmp_path / "test.nwb"
        original.write_text("v0")

        v1 = tmp_path / "test_v1_abc123de.nwb"
        v1.write_text("v1")

        v2 = tmp_path / "test_v2_def456ab.nwb"
        v2.write_text("v2")

        versions = get_all_versions(original)

        assert len(versions) == 3
        assert original in versions
        assert v1 in versions
        assert v2 in versions

    def test_get_all_versions_missing_original(self, tmp_path):
        """Test when original file doesn't exist."""
        original = tmp_path / "test.nwb"

        v1 = tmp_path / "test_v1.nwb"
        v1.write_text("v1")

        versions = get_all_versions(original)

        assert len(versions) == 1
        assert v1 in versions

    def test_get_all_versions_ignores_other_files(self, tmp_path):
        """Test ignores unrelated files."""
        original = tmp_path / "test.nwb"
        original.write_text("v0")

        # Other files that should be ignored
        other1 = tmp_path / "other.nwb"
        other1.write_text("other")

        other2 = tmp_path / "test_backup.nwb"
        other2.write_text("backup")

        v1 = tmp_path / "test_v1.nwb"
        v1.write_text("v1")

        versions = get_all_versions(original)

        assert len(versions) == 2
        assert original in versions
        assert v1 in versions
        assert other1 not in versions
        assert other2 not in versions

    def test_get_all_versions_handles_malformed_version_numbers(self, tmp_path):
        """Test gracefully handles malformed version suffixes."""
        original = tmp_path / "test.nwb"
        original.write_text("v0")

        # Valid versions
        v1 = tmp_path / "test_v1.nwb"
        v1.write_text("v1")

        # Malformed (should default to version 0 in sorting)
        malformed = tmp_path / "test_v_invalid.nwb"
        malformed.write_text("malformed")

        versions = get_all_versions(original)

        # Should still find all files matching pattern
        assert len(versions) == 3
        assert original in versions
        assert v1 in versions
        assert malformed in versions


@pytest.mark.unit
class TestFileVersioningIntegration:
    """Integration tests for complete versioning workflow."""

    def test_complete_versioning_workflow(self, tmp_path):
        """Test complete workflow: create versions, verify integrity, list all."""
        # Step 1: Create original file
        original = tmp_path / "mouse_001.nwb"
        original.write_text("original data")

        # Step 2: Create version 1
        v1_path, v1_checksum = create_versioned_file(original, 1)
        assert v1_path.exists()
        assert verify_file_integrity(v1_path, v1_checksum)

        # Step 3: Modify original (simulate correction)
        original.write_text("corrected data")

        # Step 4: Create version 2
        v2_path, v2_checksum = create_versioned_file(original, 2)
        assert v2_path.exists()
        assert verify_file_integrity(v2_path, v2_checksum)

        # Step 5: List all versions
        all_versions = get_all_versions(original)
        assert len(all_versions) == 3
        assert original in all_versions
        assert v1_path in all_versions
        assert v2_path in all_versions

        # Step 6: Verify checksums are different
        assert v1_checksum != v2_checksum

    def test_versioning_preserves_original(self, tmp_path):
        """Test creating versions doesn't modify original."""
        original = tmp_path / "test.nwb"
        original_content = "original content"
        original.write_text(original_content)

        original_checksum = compute_sha256(original)

        # Create multiple versions
        create_versioned_file(original, 1)
        create_versioned_file(original, 2)
        create_versioned_file(original, 3)

        # Original should be unchanged
        assert original.read_text() == original_content
        assert compute_sha256(original) == original_checksum
