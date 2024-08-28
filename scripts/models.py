import datetime
import json
import typing
import pydantic


class ReadmeBodyElement(pydantic.BaseModel):
    key: str
    value: str

    def export(self) -> dict:
        return {
            "formatKey": self.key,
            "formatValue": self.value,
        }


class ReadmeText(ReadmeBodyElement):
    key: typing.Literal["Text"] = "Text"


class ReadmeSubTitle(ReadmeBodyElement):
    key: typing.Literal["SubTitle"] = "SubTitle"
    size: int | None = None

    def export(self) -> dict:
        data = super().export()
        if self.size is not None:
            data["formatValue"] = f"<size={self.size}>{data['formatValue']}</size>"
        return data


class ReadmeImage(ReadmeBodyElement):
    key: typing.Literal["Image"] = "Image"


class ReadmeLink(ReadmeBodyElement):
    url: str
    value: str | None = None
    key: typing.Literal["HyperLink"] = "HyperLink"

    def export(self) -> dict:
        if self.value is None:
            value = self.url
        else:
            value = f"<link={self.url}>{self.value}</link>"

        return {
            "formatKey": self.key,
            "formatValue": value,
        }


class ReadmeBody(pydantic.BaseModel):
    list: list[ReadmeBodyElement]

    def export(self) -> str:
        data = {"list": [entry.export() for entry in self.list]}
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


class ReadmeData(pydantic.BaseModel):
    title: str
    text: ReadmeBody
    start_date: datetime.datetime = datetime.datetime.fromisoformat("2023-08-31T00:00:00.000Z")

    def export(self, id_: int, type_: int = 0) -> dict:
        return {
            "id": id_,
            "version": 0,
            "type": type_,
            "startDate": self.start_date.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "endDate": "2024-12-31T23:00:00.000Z",
            "sprNameList": [],
            "title_KR": self.title,
            "content_KR": self.text.export(),
        }


class GitHubRelease(pydantic.BaseModel):
    name: str
    body: str
    published_at: datetime.datetime

    def make_readme(self) -> ReadmeData:
        readme_text: list[ReadmeBodyElement] = []

        for line in self.body.splitlines():
            if line.strip().startswith("#"):
                readme_text.append(
                    ReadmeSubTitle(value=line[1:].strip("# "), size=49)
                )
            else:
                readme_text.append(ReadmeText(value=line))

        return ReadmeData(
            title=self.name,
            text=ReadmeBody(list=readme_text),
            start_date=self.published_at,
        )


class FileMetaData(pydantic.BaseModel):
    path: str
    checksum: str


class MetaData(pydantic.BaseModel):
    version: str
    files: list[FileMetaData] = pydantic.Field(default_factory=list)
