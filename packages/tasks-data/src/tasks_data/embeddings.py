"""Optional HTTP embeddings adapter. No text-generation endpoint is used."""

from __future__ import annotations

import hashlib
import json
import math
import os
from typing import Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .essay_bank import _unit


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HttpEmbedder:
    """POST {model, input} to base_url/embeddings; expect indexed float vectors.

    Configure a service you already have access to. This class does not create
    accounts, start compute, download weights, or generate essays. API keys are
    read from the named environment variable only when a request is made.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        revision: str = "unspecified",
        api_key_env: str | None = None,
        query_prefix: str = "",
        document_prefix: str = "",
        timeout: float = 30,
        batch_size: int = 64,
    ):
        if not isinstance(base_url, str):
            raise ValueError("An embedding API base URL is required")
        parsed = urlsplit(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "Use an HTTP(S) base URL without credentials, query or fragment"
            )
        if parsed.scheme == "http" and parsed.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError(
                "Use HTTPS for remote embedding services, or a localhost tunnel"
            )
        for value, label in ((model, "model"), (revision, "revision")):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Embedding {label} must be nonempty")
        if any(not isinstance(v, str) for v in (query_prefix, document_prefix)):
            raise ValueError("Embedding prefixes must be strings")
        if api_key_env is not None and (
            not isinstance(api_key_env, str) or not api_key_env.strip()
        ):
            raise ValueError("api_key_env must be the name of an environment variable")
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (float, int))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("timeout must be a positive number")
        if type(batch_size) is not int or batch_size < 1:
            raise ValueError("batch_size must be a positive integer")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.revision = revision
        self.api_key_env = api_key_env
        self.query_prefix = query_prefix
        self.document_prefix = document_prefix
        self.timeout = timeout
        self.batch_size = batch_size
        config = {
            "base_url": self.base_url,
            "model": model,
            "revision": revision,
            "query_prefix": query_prefix,
            "document_prefix": document_prefix,
        }
        digest = hashlib.sha256(
            json.dumps(config, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        self.identity = "http-embeddings-v1:" + digest
        self._opener = build_opener(_NoRedirect())

    def embed(self, texts: Sequence[str], *, role: str) -> list[list[float]]:
        if role not in {"query", "document"}:
            raise ValueError("Embedding role must be query or document")
        if not isinstance(texts, (list, tuple)) or any(
            not isinstance(t, str) or not t.strip() for t in texts
        ):
            raise ValueError("Embedding input must be a list of nonempty strings")
        if not texts:
            return []
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key_env is not None:
            key = os.environ.get(self.api_key_env)
            if not key or not key.strip():
                raise ValueError(
                    "The configured embedding API key environment variable is empty"
                )
            if "\n" in key or "\r" in key:
                raise ValueError("Invalid embedding API key")
            headers["Authorization"] = "Bearer " + key
        prefix = self.query_prefix if role == "query" else self.document_prefix
        output: list[list[float]] = []
        dimension: int | None = None
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            body = json.dumps(
                {
                    "model": self.model,
                    "input": [prefix + t for t in batch],
                    "encoding_format": "float",
                },
                ensure_ascii=False,
            ).encode("utf-8")
            request = Request(
                self.base_url + "/embeddings", data=body, headers=headers, method="POST"
            )
            try:
                with self._opener.open(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read())
            except HTTPError as error:
                raise RuntimeError(
                    f"Embedding service returned HTTP {error.code}"
                ) from None
            except (URLError, TimeoutError, OSError):
                raise RuntimeError("Embedding service request failed") from None
            except (ValueError, UnicodeError):
                raise ValueError("Embedding service returned invalid JSON") from None
            if (
                not isinstance(payload, dict)
                or not isinstance(payload.get("data"), list)
                or len(payload["data"]) != len(batch)
            ):
                raise ValueError("Embedding response count does not match input")
            ordered = {}
            for item in payload["data"]:
                if (
                    not isinstance(item, dict)
                    or type(item.get("index")) is not int
                    or item["index"] not in range(len(batch))
                    or item["index"] in ordered
                ):
                    raise ValueError(
                        "Embedding response indices are missing, repeated or invalid"
                    )
                vector = list(_unit(item.get("embedding")))
                if dimension is not None and len(vector) != dimension:
                    raise ValueError("Embedding response dimensions differ")
                dimension = len(vector)
                ordered[item["index"]] = vector
            output.extend(ordered[i] for i in range(len(batch)))
        return output
