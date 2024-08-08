import httpx

from .models import GitHubRelease


def get_github_releases(repo: str) -> list[GitHubRelease]:
    url = f"https://api.github.com/repos/{repo}/releases"
    response = httpx.get(url)
    response.raise_for_status()

    data = response.json()
    releases = [GitHubRelease(**release) for release in data[::-1]]

    return releases
