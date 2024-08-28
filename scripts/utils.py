import httpx

from .models import GitHubRelease, ReadmeData, ReadmeBody, ReadmeBodyElement, ReadmeSubTitle, ReadmeText, ReadmeLink


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
        ReadmeLink(url="https://github.com/kimght/LimbusStory", value="Помочь в переводе"),
    ]

    return ReadmeData(
        title="Участники проекта",
        text=ReadmeBody(list=content),
    )


def make_readme_extra() -> ReadmeData:
    return ReadmeData(
        title="Дополнительно",
        text=ReadmeBody(
            list=[
                ReadmeSubTitle(value="Дополнительно", size=49),
                ReadmeLink(url="https://kimght.github.io", value="Онлайн читалочка"),
            ]
        )
    )