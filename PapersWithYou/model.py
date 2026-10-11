"""Validated input and provider-neutral records."""
from dataclasses import dataclass, asdict, field
from datetime import date
from pathlib import Path
import hashlib
import json
import os
import re
import tempfile

ARXIV_ID = re.compile(r"^(?:\d{4}\.\d{4,5}|[a-zA-Z][a-zA-Z.\-]*/\d{7})(?:v[1-9]\d*)?$")
CATEGORY = re.compile(r"^[a-zA-Z][a-zA-Z.\-]*(?:\.[a-zA-Z]+)?$")


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".part", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


@dataclass
class Profile:
    categories: list[str] = field(default_factory=lambda: ["cs.AI", "cs.LG"])
    keywords: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    since: str = ""
    until: str = ""
    max_results: int = 20
    purpose: str = "research"
    description: str = ""
    output_dir: str = ""
    contact: str = ""
    auto_download: bool = False
    max_file_mb: int = 50
    max_total_mb: int = 250
    ids: list[str] = field(default_factory=list)
    schema_version: int = 1

    def validate(self):
        if self.schema_version != 1:
            raise ValueError("Unsupported profile schema / 지원하지 않는 설정 버전")
        for name in ("categories", "keywords", "exclude", "ids"):
            value = getattr(self, name)
            if not isinstance(value, list) or not all(isinstance(x, str) and x.strip() for x in value):
                raise ValueError(f"{name}: expected a list of nonempty strings")
            if len(value) > 100:
                raise ValueError(f"{name}: at most 100 entries")
        for name in ("since", "until", "purpose", "description", "output_dir", "contact"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"{name}: expected a string")
        if type(self.auto_download) is not bool:
            raise ValueError("auto_download must be boolean")
        for name, low, high in (("max_results",1,100),("max_file_mb",1,250),("max_total_mb",1,1000)):
            v = getattr(self,name)
            if type(v) is not int or not low <= v <= high:
                raise ValueError(f"{name}: {low}..{high}")
        if not self.categories and not self.ids:
            raise ValueError("Choose a category or exact arXiv IDs")
        if not all(CATEGORY.fullmatch(c) for c in self.categories):
            raise ValueError("Invalid arXiv category")
        if not all(ARXIV_ID.fullmatch(i) for i in self.ids):
            raise ValueError("Invalid arXiv ID")
        for v in (self.since,self.until):
            if v: date.fromisoformat(v)
        if self.since and self.until and self.since > self.until:
            raise ValueError("since must be <= until")
        if len(self.contact)>200 or any(c in self.contact for c in "\r\n"):
            raise ValueError("Invalid contact")
        if any(len(x)>500 or any(c in x for c in ('"','\\','\r','\n')) for x in self.keywords+self.exclude):
            raise ValueError('Keyword phrases must be <=500 characters without quotes, backslashes or newlines')
        return self

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**data).validate()

    def save(self, path):
        self.validate()
        atomic_json(path, asdict(self))


@dataclass
class Paper:
    provider: str
    paper_id: str
    version: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    published: str
    updated: str
    landing_url: str
    pdf_url: str
    doi: str = ""
    license_url: str | None = None
    identity_status: str = "provider_link_only"

    @property
    def key(self):
        return f"{self.provider}:{self.paper_id}:{self.version}"

    @property
    def stem(self):
        return self.paper_id.replace("/", "_") + self.version

    def data(self):
        return asdict(self)
