"""Transcript augmentation and manual editing support."""

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional

from .config import VideoConfig
from ...utils.security import (
    get_safe_editor, 
    safe_subprocess_run, 
    validate_file_path,
    SecurityError,
    CommandInjectionError
)


class TranscriptAugmenter:
    """Handle manual transcript augmentation and finalization."""

    def __init__(self, config: VideoConfig):
        """Initialize transcript augmenter.

        Args:
            config: Video configuration
        """
        self.config = config

    def open_in_editor(self, file_path: Path) -> None:
        """Open a file in the system default editor securely.

        Args:
            file_path: Path to file to open
            
        Raises:
            SecurityError: If editor command is unsafe
            CommandInjectionError: If no safe editor is available
        """
        # Validate file path for security
        try:
            validated_path = validate_file_path(file_path, must_exist=True)
        except Exception as e:
            raise SecurityError(f"Invalid file path: {e}")
        
        system = platform.system()
        
        try:
            if system == "Windows":
                # Use os.startfile for Windows (safer than subprocess for this use case)
                os.startfile(str(validated_path))
            elif system == "Darwin":
                # Use safe subprocess for macOS
                safe_subprocess_run(["open", str(validated_path)])
            else:
                # Get safe editor for Linux/Unix
                editor = get_safe_editor()
                safe_subprocess_run([editor, str(validated_path)])
        except (SecurityError, CommandInjectionError) as e:
            raise SecurityError(f"Failed to open file safely: {e}")
        except subprocess.TimeoutExpired:
            raise SecurityError("Editor command timed out")
        except Exception as e:
            raise SecurityError(f"Unexpected error opening file: {e}")

    def augment(
        self,
        transcript_path: Path,
        output_path: Optional[Path] = None,
        auto_save: bool = False,
    ) -> Path:
        """Augment a transcript with manual edits.

        Args:
            transcript_path: Path to cleaned transcript
            output_path: Optional final output path
            auto_save: If True, skip editor and just copy to output

        Returns:
            Path to final augmented transcript
            
        Raises:
            SecurityError: If file paths are invalid or unsafe
            FileNotFoundError: If transcript file doesn't exist
        """
        # Validate transcript path for security
        try:
            transcript_path = validate_file_path(transcript_path, must_exist=True)
        except Exception as e:
            raise SecurityError(f"Invalid transcript path: {e}")

        if not auto_save:
            # Open in editor for manual annotation
            print("\n── Manual Annotation ──")
            print("The transcript will open in your editor.")
            print("Add your annotations, then save and close.")
            print("Press Enter to continue...")
            input()
            
            try:
                self.open_in_editor(transcript_path)
            except SecurityError as e:
                print(f"⚠️  Security Error: {e}")
                print("Please edit the file manually and press Enter when done.")
            
            print("\nPress Enter when you have finished editing...")
            input()

        # Read the (possibly edited) content
        final_content = transcript_path.read_text(encoding="utf-8")

        # Determine and validate output path
        if output_path is None:
            output_path = transcript_path.parent / f"{transcript_path.stem}_final{transcript_path.suffix}"
        else:
            output_path = Path(output_path)
            # Validate output path (allow creation of new files)
            try:
                output_path = validate_file_path(output_path, must_exist=False)
            except Exception as e:
                raise SecurityError(f"Invalid output path: {e}")
            
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Check for overwrite
        if output_path.exists() and not auto_save:
            response = input(f"\n{output_path.name} already exists. Overwrite? [y/N]: ")
            if response.lower() not in ["y", "yes"]:
                # Save to scratch instead
                fallback = transcript_path.parent / f"{transcript_path.stem}_fallback{transcript_path.suffix}"
                fallback.write_text(final_content, encoding="utf-8")
                print(f"Saved to: {fallback}")
                return fallback

        # Write final transcript
        output_path.write_text(final_content, encoding="utf-8")
        print(f"\n✓ Final transcript written to: {output_path}")
        
        return output_path
