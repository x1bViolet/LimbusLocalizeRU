import httpx
import collections
import re

from .models import GitHubRelease, ReadmeData, ReadmeBody, ReadmeBodyElement, ReadmeSubTitle, ReadmeText, ReadmeLink

KEYWORD_SHORTHAND = re.compile(r"\[(?P<keyword_id>[a-zA-Z0-9_]+?)\:'(?P<text>.+?)'\]")


def get_github_releases(repo: str) -> list[GitHubRelease]:
    url = f"https://api.github.com/repos/{repo}/releases"
    response = httpx.get(url)
    response.raise_for_status()

    data = response.json()
    releases = [GitHubRelease(**release) for release in data[::-1]]

    return releases


def get_github_contributors(repo: str) -> list[str]:
    url = f"https://api.github.com/repos/{repo}/contributors"
    response = httpx.get(url)
    response.raise_for_status()

    data = response.json()
    contributors = [contributor["login"] for contributor in data if contributor["type"] == "User"]

    return contributors


def make_readme_contributors(repos: list[str]) -> ReadmeData:
    contributors = []
    for repo in repos:
        contributors += get_github_contributors(repo)
    contributors = sorted(set(contributors))

    content: list[ReadmeBodyElement] = [
        ReadmeSubTitle(value="Участники проекта", size=49),
    ] + [
        ReadmeText(value=f"- {contributor}")
        for contributor in contributors
    ] + [
        ReadmeSubTitle(value="Помочь в переводе", size=49),
        ReadmeLink(url="https://github.com/kimght/LimbusStory", value="GitHub"),
    ]

    return ReadmeData(
        title="Участники проекта",
        text=ReadmeBody(list=content),
    )


def load_keyword_files() -> list[str]:
    with open("config/keyword_files.txt", "r", encoding="utf-8-sig") as file:
        data = file.readlines()

    return [line.strip() for line in data if line.strip()]


def load_keyword_colors() -> dict[str, str]:
    with open("config/keyword_colors.txt", "r", encoding="utf-8-sig") as file:
        data = file.readlines()

    keyword_colors = {}
    for line in data:
        line = line.strip()
        if not line:
            continue

        keyword_id, color = line.split(" ¤ ", 1)
        keyword_colors[keyword_id.strip()] = color.strip()

    return keyword_colors


def make_readme_extra() -> ReadmeData:
    return ReadmeData(
        title="Дополнительно",
        text=ReadmeBody(
            list=[
                ReadmeSubTitle(value="Дополнительно", size=49),
                ReadmeText(value=f"Онлайн читалочка:"),
                ReadmeLink(url="https://kimght.github.io", value="kimght.github.io"),
            ]
        )
    )

def replace_shorthands(text: str, keyword_colors: dict[str, str]) -> str:
    def make_replacement(match: re.Match) -> str:
        keyword_id = match.group("keyword_id")
        text = match.group("text")

        if keyword_id in keyword_colors:
            color = keyword_colors[keyword_id]
        else:
            print(f"Unknown keyword ID: {keyword_id}!")
            color = "#f8c200"

        return (
            f"<sprite name=\"{keyword_id}\">"
            f"<color={color}>"
            f"<u>"
            f"<link=\"{keyword_id}\">"
            f"{text}"
            f"</link>"
            f"</u>"
            f"</color>"
        )

    return KEYWORD_SHORTHAND.sub(make_replacement, text)


def convert_keywords(data: collections.OrderedDict | list, keyword_colors: dict[str, str]) -> None:
    if isinstance(data, collections.OrderedDict):
        items = data.items()
    else:
        items = enumerate(data)

    for key, value in items:
        if isinstance(value, (collections.OrderedDict, list)):
            convert_keywords(value, keyword_colors)
        elif isinstance(value, str):
            data[key] = replace_shorthands(value, keyword_colors)
