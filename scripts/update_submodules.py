import os
import configparser
import httpx
from base64 import b64decode


def get_env_variables() -> tuple[str, str, str]:
    github_token = os.getenv("GITHUB_TOKEN")
    repo_owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")

    if not all([github_token, repo_owner, repo_name]):
        raise ValueError(
            "One or more environment variables (GITHUB_TOKEN, REPO_OWNER, REPO_NAME) are missing."
        )

    return github_token, repo_owner, repo_name


def fetch_gitmodules(github_token: str, repo_owner: str, repo_name: str) -> str:
    api_url = (
        f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/.gitmodules"
    )
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    response = httpx.get(api_url, headers=headers)
    if response.status_code != 200:
        raise Exception(
            f"Failed to fetch .gitmodules file from {repo_owner}/{repo_name}. Error: {response.text}"
        )

    gitmodules_content = b64decode(response.json()["content"]).decode("utf-8")
    return gitmodules_content


def parse_gitmodules(gitmodules_content: str) -> dict[str, dict[str, str]]:
    config = configparser.ConfigParser()
    config.read_string(gitmodules_content)

    submodules = {}
    for section in config.sections():
        path = config.get(section, "path")
        url = config.get(section, "url")
        branch = config.get(section, "branch", fallback="main")
        submodules[path] = {"url": url, "branch": branch}

    return submodules


def get_latest_commit_sha(submodule_info: dict[str, str], github_token: str) -> str:
    url = submodule_info["url"]
    branch = submodule_info["branch"]

    url_parts = url.split("/")
    submodule_owner = url_parts[-2]
    submodule_name = url_parts[-1].replace(".git", "")

    api_url = f"https://api.github.com/repos/{submodule_owner}/{submodule_name}/branches/{branch}"

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    response = httpx.get(api_url, headers=headers)
    if response.status_code != 200:
        raise Exception(
            f"Failed to get latest commit for submodule {submodule_name} on branch {branch}. Error: {response.text}"
        )

    latest_commit_sha = response.json()["commit"]["sha"]
    return latest_commit_sha


def create_tree_with_submodule_updates(
    submodules: dict[str, dict[str, str]],
    base_tree_sha: str,
    github_token: str,
    repo_owner: str,
    repo_name: str,
) -> str:
    tree = []
    for path, submodule_info in submodules.items():
        latest_commit_sha = get_latest_commit_sha(submodule_info, github_token)
        tree.append(
            {
                "path": path,
                "mode": "160000",  # Git mode for submodule
                "type": "commit",
                "sha": latest_commit_sha,
            }
        )

    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/git/trees"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {"base_tree": base_tree_sha, "tree": tree}

    response = httpx.post(api_url, headers=headers, json=data)
    if response.status_code != 201:
        raise Exception(
            f"Failed to create tree with updated submodules. Error: {response.text}"
        )

    return response.json()["sha"]


def create_commit(
    tree_sha: str, parent_sha: str, github_token: str, repo_owner: str, repo_name: str
) -> str:
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/git/commits"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {
        "message": "build: update submodules",
        "author": {
            "name": "github-actions[bot]",
            "email": "github-actions[bot]@users.noreply.github.com",
        },
        "tree": tree_sha,
        "parents": [parent_sha],
    }

    response = httpx.post(api_url, headers=headers, json=data)
    if response.status_code != 201:
        raise Exception(f"Failed to create commit. Error: {response.text}")

    return response.json()["sha"]


def update_branch_to_commit(
    commit_sha: str,
    github_token: str,
    repo_owner: str,
    repo_name: str,
    branch: str = "main",
):
    api_url = (
        f"https://api.github.com/repos/{repo_owner}/{repo_name}/git/refs/heads/{branch}"
    )
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {"sha": commit_sha}

    response = httpx.patch(api_url, headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(
            f"Failed to update branch {branch} to new commit. Error: {response.text}"
        )


def main() -> None:
    github_token, repo_owner, repo_name = get_env_variables()

    gitmodules_content = fetch_gitmodules(github_token, repo_owner, repo_name)
    submodules = parse_gitmodules(gitmodules_content)

    api_url = (
        f"https://api.github.com/repos/{repo_owner}/{repo_name}/git/ref/heads/main"
    )
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    response = httpx.get(api_url, headers=headers)
    if response.status_code != 200:
        raise Exception(
            f"Failed to get current main branch commit SHA. Error: {response.text}"
        )

    parent_sha = response.json()["object"]["sha"]

    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/git/commits/{parent_sha}"
    response = httpx.get(api_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to get current tree SHA. Error: {response.text}")

    base_tree_sha = response.json()["tree"]["sha"]
    new_tree_sha = create_tree_with_submodule_updates(
        submodules, base_tree_sha, github_token, repo_owner, repo_name
    )
    new_commit_sha = create_commit(
        new_tree_sha, parent_sha, github_token, repo_owner, repo_name
    )
    update_branch_to_commit(new_commit_sha, github_token, repo_owner, repo_name)

    print("Successfully updated submodules and committed changes.")


if __name__ == "__main__":
    main()
