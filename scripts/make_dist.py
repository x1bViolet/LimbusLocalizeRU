import os
import pathlib
import hashlib
import json
import shutil


def get_file_checksum(file_path: pathlib.Path, algorithm: str = "md5") -> str:
    hash_alg = hashlib.new(algorithm)
    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            hash_alg.update(chunk)
    return hash_alg.hexdigest().upper()


def validate_json_file(file_path: pathlib.Path) -> bool:
    try:
        with file_path.open("r", encoding="utf-8-sig") as file:
            json.load(file)
        return True
    except json.JSONDecodeError:
        return False


def main() -> None:
    metadata = {"version": os.environ.get("LOCALIZATION_VERSION"), "files": []}

    localization_path = pathlib.Path(__file__).parents[1] / "localize"
    dist_path = pathlib.Path(__file__).parents[1] / "dist"
    if not dist_path.exists():
        dist_path.mkdir()

    invalid_files = []
    for file in localization_path.glob("**/*.json"):
        if not validate_json_file(file):
            invalid_files.append(file)
            continue

        result_path = (dist_path / file.relative_to(localization_path)).parent
        result_path.mkdir(parents=True, exist_ok=True)

        shutil.copy(file, result_path / file.name)
        metadata["files"].append(
            {
                "path": file.relative_to(localization_path).as_posix(),
                "checksum": get_file_checksum(file),
            }
        )

    if invalid_files:
        raise ValueError(f"Invalid JSON files: {', '.join(map(str, invalid_files))}")

    with (dist_path / "metadata.json").open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)

    print("Localization distribution created successfully.")


if __name__ == "__main__":
    main()
