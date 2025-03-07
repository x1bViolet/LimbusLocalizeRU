import os
import pathlib
import hashlib
import json
import shutil
import collections

from .models import MetaData, FileMetaData
from .utils import (
    get_github_releases,
    make_readme_contributors,
    make_readme_extra,
    load_keyword_colors,
    load_keyword_files,
    convert_keywords,
)


def get_file_checksum(file_path: pathlib.Path, algorithm: str = "md5") -> str:
    hash_alg = hashlib.new(algorithm)
    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            hash_alg.update(chunk)
    return hash_alg.hexdigest()


def validate_json_file(file_path: pathlib.Path) -> bool:
    try:
        with file_path.open("r", encoding="utf-8-sig") as file:
            json.load(file)
        return True
    except json.JSONDecodeError:
        return False


def dist_localization_data(metadata: MetaData, dist_path: pathlib.Path) -> None:
    invalid_files = []

    localization_path = pathlib.Path(__file__).parents[1] / "localize"
    keyword_colors = load_keyword_colors()
    keyword_files = load_keyword_files()

    for file in (localization_path / "RU").glob("**/*.json"):
        if not file.is_file():
            continue

        if not validate_json_file(file):
            invalid_files.append(file)
            continue

        result_path = (dist_path / file.relative_to(localization_path)).parent
        result_path.mkdir(parents=True, exist_ok=True)

        if file.name in keyword_files:
            content = file.read_text(encoding="utf-8-sig")
            content = json.loads(content, object_pairs_hook=collections.OrderedDict)
            convert_keywords(content, keyword_colors)

            with (result_path / file.name).open("w", encoding="utf-8-sig") as f:
                json.dump(content, f, ensure_ascii=False, indent=4)

        else:
            shutil.copy(file, result_path / file.name)

        metadata.files.append(
            FileMetaData(
                path=file.relative_to(localization_path).as_posix(),
                checksum=get_file_checksum(file)
            )
        )

    if invalid_files:
        raise ValueError(f"Invalid JSON files: {', '.join(map(str, invalid_files))}")


def dist_sprites(metadata: MetaData, dist_path: pathlib.Path) -> None:
    sprites_path = pathlib.Path(__file__).parents[1] / "sprites"

    for file in sprites_path.glob("**/*"):
        if not file.is_file():
            continue

        result_path = (dist_path / "Readme" / "Sprites" / file.relative_to(sprites_path)).parent
        result_path.mkdir(parents=True, exist_ok=True)

        shutil.copy(file, result_path / file.name)

        metadata.files.append(
            FileMetaData(
                path=(pathlib.Path("Readme/Sprites") / file.relative_to(sprites_path)).as_posix(),
                checksum=get_file_checksum(file)
            )
        )


def dist_extra_files(metadata: MetaData, dist_path: pathlib.Path) -> None:
    extra_files_path = pathlib.Path(__file__).parents[1] / "extra"

    for file in extra_files_path.glob("**/*"):
        if not file.is_file():
            continue

        result_path = (dist_path / "Readme" / file.relative_to(extra_files_path)).parent
        result_path.mkdir(parents=True, exist_ok=True)

        shutil.copy(file, result_path / file.name)

        metadata.files.append(
            FileMetaData(
                path=(pathlib.Path("Readme") / file.relative_to(extra_files_path)).as_posix(),
                checksum=get_file_checksum(file)
            )
        )


def dist_readme(metadata: MetaData, dist_path: pathlib.Path) -> None:
    readme_path = pathlib.Path(__file__).parents[1] / "readme"

    with open(readme_path / "readme_template.json", "r", encoding="utf-8-sig") as file:
        readme_template = json.load(file)

    contributors = make_readme_contributors([
        "kimght/LimbusStory",
        "kimght/LimbusLocalizeRU",
    ])

    readme_template["noticeList"].append(contributors.export(1193, 1))

    extra = make_readme_extra()
    readme_template["noticeList"].append(extra.export(1194, 1))

    releases_info = get_github_releases("kimght/LimbusCompanyRuMTL")
    releases_notices = []
    for i, release in enumerate(releases_info, 2911):
        readme_data = release.make_readme()
        releases_notices.append(readme_data.export(i + 1))

    readme_template["noticeList"].extend(releases_notices[::-1])
    result_path = dist_path / "Readme"
    result_path.mkdir(parents=True, exist_ok=True)

    with open(result_path / "Readme.json", "w", encoding="utf-8-sig") as file:
        json.dump(readme_template, file, ensure_ascii=False, indent=4)

    metadata.files.append(
        FileMetaData(
            path="Readme/Readme.json",
            checksum=get_file_checksum(result_path / "Readme.json")
        )
    )


def main() -> None:
    metadata = MetaData(version=os.environ.get("LOCALIZATION_VERSION", "1.0.0"))

    dist_path = pathlib.Path(__file__).parents[1] / "dist"
    if not dist_path.exists():
        dist_path.mkdir()

    dist_localization_data(metadata, dist_path)
    dist_sprites(metadata, dist_path)
    dist_extra_files(metadata, dist_path)
    dist_readme(metadata, dist_path)

    with (dist_path / "metadata.json").open("w", encoding="utf-8") as file:
        json.dump(metadata.model_dump(), file, indent=2)

    print("Localization distribution created successfully.")


if __name__ == "__main__":
    main()
