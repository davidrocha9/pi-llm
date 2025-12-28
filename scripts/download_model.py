#!/usr/bin/env python3
"""Download the GGUF model from HuggingFace Hub."""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def download_model(
    repo_id: str = "unsloth/gemma-3-1b-it-GGUF",
    filename: str | None = "gemma-3-1b-it.Q4_K_M.gguf",
    output_dir: str = "models",
    auto: bool = False,
) -> Path | None:
    """Download a GGUF model from HuggingFace Hub.

    Args:
        repo_id: HuggingFace repository ID.
        filename: Name of the GGUF file to download.
        output_dir: Directory to save the model.

    Returns:
        Path to the downloaded model file.
    """
    try:
        from huggingface_hub import hf_hub_download, list_repo_files
    except ImportError:
        print("Error: huggingface_hub not installed.")
        print("Run: pip install huggingface_hub")
        sys.exit(1)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {filename} from {repo_id}...")
    print(f"This may take a while (~800MB)...")

    try:
        model_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=output_path,
        )
        print(f"\n✓ Model downloaded successfully!")
        print(f"  Location: {model_path}")
        return Path(model_path)

    except Exception as first_err:
        # Attempt to list files in the repository and suggest alternatives
        print(f"\n✗ Download failed: {first_err}")
        print("Attempting to list available files in the repository...")
        try:
            files = list_repo_files(repo_id)
        except Exception as e:
            print(f"Failed to list repository files: {e}")
            sys.exit(1)

        gguf_files = [f for f in files if f.lower().endswith(".gguf")]
        if not gguf_files:
            print("No .gguf files found in the repository. Available files:")
            for f in files:
                print(f"  - {f}")
            sys.exit(1)

        print("Found the following .gguf files:")
        for f in gguf_files:
            print(f"  - {f}")

        # If auto is requested, pick a preferred .gguf and download it
        if auto:
            preferred_order = [
                "Q4_K_M",
                "Q4_K_S",
                "Q4_0",
                "Q4_1",
                "Q3_K_M",
                "Q2_K",
            ]

            def pick_preferred(candidates: list[str]) -> str:
                # Find the first candidate that contains a preferred token
                lower_candidates = [c.lower() for c in candidates]
                for pref in preferred_order:
                    for orig, low in zip(candidates, lower_candidates):
                        if pref.lower() in low:
                            return orig
                # Fallback to the first candidate
                return candidates[0]

            chosen = pick_preferred(gguf_files)
            print(f"Auto-selected: {chosen}")
            try:
                model_path = hf_hub_download(repo_id=repo_id, filename=chosen, local_dir=output_path)
                print(f"\n✓ Model downloaded successfully!\n  Location: {model_path}")
                return Path(model_path)
            except Exception as e:
                print(f"Auto-download failed for {chosen}: {e}")
                print("You can re-run the script specifying --filename or try a different repo.")
                sys.exit(1)

        # Return None so caller can decide next steps (interactive/manual)
        print("Rerun the script with --filename <file.gguf> or --auto to auto-select a .gguf file.")
        return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download GGUF model from HuggingFace Hub"
    )
    parser.add_argument(
        "--repo",
        default="unsloth/gemma-3-1b-it-GGUF",
        help="HuggingFace repository ID (default: unsloth/gemma-3-1b-it-GGUF)",
    )
    parser.add_argument(
        "--filename",
        default="gemma-3-1b-it.Q4_K_M.gguf",
        help="GGUF filename to download (default: gemma-3-1b-it.Q4_K_M.gguf)",
    )
    parser.add_argument(
        "--output",
        default="models",
        help="Output directory (default: models)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatically pick and download a preferred .gguf file from the repo if the specified filename fails",
    )

    args = parser.parse_args()
    download_model(args.repo, args.filename or None, args.output, auto=args.auto)


if __name__ == "__main__":
    main()
