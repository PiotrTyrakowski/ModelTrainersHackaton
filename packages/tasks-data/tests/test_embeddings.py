import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from tasks_data.embeddings import HttpEmbedder, _NoRedirect


class HttpEmbedderTests(unittest.TestCase):
    def client(self, **kwargs):
        return HttpEmbedder(
            "http://localhost:8080/v1", "test-encoder", revision="fixed-v1", **kwargs
        )

    def reply(self, vectors, indices=None):
        return io.BytesIO(
            json.dumps(
                {
                    "data": [
                        {"index": i, "embedding": v}
                        for i, v in zip(indices or range(len(vectors)), vectors)
                    ]
                }
            ).encode()
        )

    def test_batches_reorders_uses_prefixes_and_never_calls_generation(self):
        client = self.client(
            query_prefix="query: ", document_prefix="passage: ", batch_size=2
        )
        with patch.object(
            client._opener,
            "open",
            side_effect=[self.reply([[0, 2], [2, 0]], [1, 0]), self.reply([[3, 4]])],
        ) as send:
            vectors = client.embed(["pierwsze", "drugie", "trzecie"], role="document")
            self.assertEqual(vectors, [[1, 0], [0, 1], [0.6, 0.8]])
            self.assertEqual(send.call_count, 2)
            requests = [call.args[0] for call in send.call_args_list]
            self.assertTrue(
                all(
                    r.full_url == "http://localhost:8080/v1/embeddings"
                    for r in requests
                )
            )
            self.assertEqual(
                json.loads(requests[0].data)["input"],
                ["passage: pierwsze", "passage: drugie"],
            )
        with patch.object(
            client._opener, "open", return_value=self.reply([[1, 0]])
        ) as send:
            client.embed(["pytanie"], role="query")
            self.assertEqual(
                json.loads(send.call_args.args[0].data)["input"], ["query: pytanie"]
            )

    def test_identity_tracks_encoder_config_but_not_key(self):
        original = self.client()
        variants = [
            self.client(query_prefix="query: "),
            self.client(document_prefix="passage: "),
            HttpEmbedder(original.base_url, original.model, revision="changed"),
            HttpEmbedder(original.base_url, "another-model", revision="fixed-v1"),
            HttpEmbedder("https://example.org/v1", original.model, revision="fixed-v1"),
        ]
        self.assertTrue(all(c.identity != original.identity for c in variants))
        self.assertEqual(
            self.client(api_key_env="EXAMPLE_KEY").identity, original.identity
        )

    def test_key_is_only_in_request_header_and_error_is_redacted(self):
        client = self.client(api_key_env="EXAMPLE_KEY")
        with patch.dict(
            os.environ, {"EXAMPLE_KEY": "private-test-value"}
        ), patch.object(
            client._opener, "open", return_value=self.reply([[1, 0]])
        ) as send:
            client.embed(["pytanie"], role="query")
            request = send.call_args.args[0]
            self.assertEqual(
                request.get_header("Authorization"), "Bearer private-test-value"
            )
            self.assertNotIn("private-test-value", request.data.decode())
            self.assertNotIn("private-test-value", client.identity)
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(
            ValueError, "environment"
        ):
            client.embed(["q"], role="query")
        error = HTTPError(
            client.base_url, 401, "private-test-value", {}, io.BytesIO(b"secret body")
        )
        with patch.dict(
            os.environ, {"EXAMPLE_KEY": "private-test-value"}
        ), patch.object(client._opener, "open", side_effect=error):
            with self.assertRaisesRegex(
                RuntimeError, "^Embedding service returned HTTP 401$"
            ):
                client.embed(["q"], role="query")
        self.assertIsNone(
            _NoRedirect().redirect_request(
                None, None, 302, "redirect", {}, "https://example.org"
            )
        )

    def test_rejects_invalid_response_count_index_vectors_and_batch_dimensions(self):
        client = self.client()
        invalid = [
            {"data": []},
            {"data": [{"index": 1, "embedding": [1, 0]}]},
            {"data": [{"index": True, "embedding": [1, 0]}]},
            {"data": [{"index": 0, "embedding": [0, 0]}]},
            {"data": [{"index": 0, "embedding": [float("nan"), 1]}]},
            {"data": [{"index": 0, "embedding": "not a vector"}]},
        ]
        for payload in invalid:
            with self.subTest(payload=payload), patch.object(
                client._opener,
                "open",
                return_value=io.BytesIO(json.dumps(payload).encode()),
            ), self.assertRaises(ValueError):
                client.embed(["q"], role="query")
        client = self.client(batch_size=1)
        with patch.object(
            client._opener,
            "open",
            side_effect=[self.reply([[1, 0]]), self.reply([[1, 0, 0]])],
        ), self.assertRaisesRegex(ValueError, "dimensions"):
            client.embed(["a", "b"], role="document")
        with patch.object(
            client._opener, "open", side_effect=URLError("test")
        ), self.assertRaisesRegex(RuntimeError, "request failed"):
            client.embed(["q"], role="query")

    def test_rejects_unsafe_url_and_invalid_config_before_request(self):
        for url in [
            "ftp://example.org",
            "https://user:secret@example.org/v1",
            "https://example.org?token=x",
            "http://remote.example.org/v1",
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                HttpEmbedder(url, "model")
        for kwargs in [{"timeout": 0}, {"batch_size": 0}, {"batch_size": True}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.client(**kwargs)


if __name__ == "__main__":
    unittest.main()
