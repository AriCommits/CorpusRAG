"""
Test cases for database management security, specifically Zip Slip vulnerability (CWE-22).
"""

import io
import os
import tarfile
import tempfile
from pathlib import Path

import pytest


def _extract_tar_safely(tar: tarfile.TarFile, target_dir: str) -> None:
    """
    Safely extract tar archive members with path traversal validation.

    Prevents Zip Slip (CWE-22) attacks by validating that each extracted
    member is within the target directory.

    Args:
        tar: Open TarFile object
        target_dir: Target directory for extraction

    Raises:
        ValueError: If a member path would escape the target directory
    """
    target_dir = os.path.normpath(os.path.abspath(target_dir))

    for member in tar.getmembers():
        # Resolve the member path
        member_path = os.path.normpath(os.path.abspath(
            os.path.join(target_dir, member.name)
        ))

        # Ensure the resolved path is within target_dir
        if not member_path.startswith(target_dir + os.sep) and member_path != target_dir:
            raise ValueError(
                f"Attempted path traversal detected: member '{member.name}' "
                f"would be extracted to {member_path} (outside {target_dir})"
            )

        tar.extract(member, target_dir)


class TestZipSlipPrevention:
    """Test that tar extraction is protected against path traversal attacks."""

    def test_normal_extraction(self):
        """Normal tar extraction should work correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a tar with normal file
            tar_buffer = io.BytesIO()
            with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
                info = tarfile.TarInfo(name='normal_file.txt')
                info.size = 13
                tar.addfile(info, io.BytesIO(b'Hello, World!'))

            tar_buffer.seek(0)
            with tarfile.open(fileobj=tar_buffer) as tar:
                _extract_tar_safely(tar, temp_dir)

            # Verify file was extracted
            extracted_file = Path(temp_dir) / 'normal_file.txt'
            assert extracted_file.exists()
            assert extracted_file.read_text() == 'Hello, World!'

    def test_parent_directory_traversal_blocked(self):
        """Extraction of ../../../etc/passwd should be blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a tar with path traversal attempt
            tar_buffer = io.BytesIO()
            with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
                info = tarfile.TarInfo(name='../../../etc/passwd')
                info.size = 9
                tar.addfile(info, io.BytesIO(b'malicious'))

            tar_buffer.seek(0)
            with tarfile.open(fileobj=tar_buffer) as tar:
                # Should raise ValueError for path traversal attempt
                with pytest.raises(ValueError, match="path traversal"):
                    _extract_tar_safely(tar, temp_dir)

    def test_absolute_path_blocked(self):
        """Extraction of absolute paths should be blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a tar with absolute path
            tar_buffer = io.BytesIO()
            with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
                info = tarfile.TarInfo(name='/etc/passwd')
                info.size = 9
                tar.addfile(info, io.BytesIO(b'malicious'))

            tar_buffer.seek(0)
            with tarfile.open(fileobj=tar_buffer) as tar:
                # Should raise ValueError for absolute path
                with pytest.raises(ValueError, match="path traversal"):
                    _extract_tar_safely(tar, temp_dir)

    def test_dot_dot_traversal_blocked(self):
        """Extraction with .. components should be blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a tar with .. in the path
            tar_buffer = io.BytesIO()
            with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
                info = tarfile.TarInfo(name='subdir/../../../secret.txt')
                info.size = 6
                tar.addfile(info, io.BytesIO(b'secret'))

            tar_buffer.seek(0)
            with tarfile.open(fileobj=tar_buffer) as tar:
                # Should raise ValueError for path traversal
                with pytest.raises(ValueError, match="path traversal"):
                    _extract_tar_safely(tar, temp_dir)

    def test_nested_safe_extraction(self):
        """Nested directories within the target should be extracted safely."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a tar with nested directory structure
            tar_buffer = io.BytesIO()
            with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
                info = tarfile.TarInfo(name='subdir/nested/file.txt')
                info.size = 5
                tar.addfile(info, io.BytesIO(b'hello'))

            tar_buffer.seek(0)
            with tarfile.open(fileobj=tar_buffer) as tar:
                _extract_tar_safely(tar, temp_dir)

            # Verify nested file was extracted
            nested_file = Path(temp_dir) / 'subdir' / 'nested' / 'file.txt'
            assert nested_file.exists()
            assert nested_file.read_text() == 'hello'
