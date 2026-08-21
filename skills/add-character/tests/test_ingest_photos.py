"""ingest_photos.py — tests. Stdlib unittest, synthetic universe + transcript in a tempdir.

The load-bearing behaviour is the REFUSAL, not the extraction. Ordered by how badly
each one bit us for real:
  1. an image already owned by ANOTHER entity is refused, because the transcript
     had not flushed and four photos of one man were about to be written into a
     different man's stack (nation-of-fire, 2026-08-21)
  2. numbering CONTINUES an existing stack rather than overwriting 01
  3. --batch reaches further back when the newest paste is the wrong one
"""
import base64
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "ingest_photos.py"


def transcript(path: Path, batches):
    """Write a fake harness transcript. `batches` is oldest-first."""
    lines = []
    for imgs in batches:
        content = [{"type": "image",
                    "source": {"media_type": "image/png",
                               "data": base64.b64encode(b).decode()}} for b in imgs]
        lines.append(json.dumps({"message": {"role": "user", "content": content}}))
        lines.append(json.dumps({"message": {"role": "assistant", "content": "ok"}}))
    path.write_text("\n".join(lines))


def run(uroot, entity, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(uroot), entity, *extra],
        capture_output=True, text=True)


class IngestPhotos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.u = Path(self.tmp.name) / "uni"
        (self.u / "reference").mkdir(parents=True)
        (self.u / "universe.json").write_text("{}")
        self.t = Path(self.tmp.name) / "t.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_refuses_an_image_owned_by_another_entity(self):
        shared = b"\x89PNG-person-A"
        a = self.u / "reference" / "person-a" / "photos"
        a.mkdir(parents=True)
        (a / "01.png").write_bytes(shared)
        transcript(self.t, [[shared]])
        r = run(self.u, "person-b", "--transcript", str(self.t))
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("already belong to", r.stderr)
        self.assertIn("person-a", r.stderr)
        self.assertFalse((self.u / "reference" / "person-b" / "photos").exists())

    def test_force_overrides_the_guard(self):
        shared = b"\x89PNG-shared"
        a = self.u / "reference" / "person-a" / "photos"
        a.mkdir(parents=True)
        (a / "01.png").write_bytes(shared)
        transcript(self.t, [[shared]])
        r = run(self.u, "person-b", "--transcript", str(self.t), "--force")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.u / "reference" / "person-b" / "photos" / "01.png").exists())

    def test_numbering_continues_an_existing_stack(self):
        d = self.u / "reference" / "someone" / "photos"
        d.mkdir(parents=True)
        (d / "01.jpg").write_bytes(b"old-1")
        (d / "02.jpg").write_bytes(b"old-2")
        transcript(self.t, [[b"new-a", b"new-b"]])
        r = run(self.u, "someone", "--transcript", str(self.t))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((d / "03.png").exists())
        self.assertTrue((d / "04.png").exists())
        self.assertEqual((d / "01.jpg").read_bytes(), b"old-1")

    def test_batch_reaches_an_older_paste(self):
        transcript(self.t, [[b"older-one"], [b"newest-one"]])
        r = run(self.u, "someone", "--transcript", str(self.t), "--batch", "2")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(
            (self.u / "reference" / "someone" / "photos" / "01.png").read_bytes(), b"older-one")

    def test_dry_run_writes_nothing(self):
        transcript(self.t, [[b"an-image"]])
        r = run(self.u, "someone", "--transcript", str(self.t), "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("would write", r.stdout)
        self.assertFalse((self.u / "reference" / "someone" / "photos").exists())

    def test_refuses_when_the_transcript_has_no_images(self):
        self.t.write_text(json.dumps({"message": {"role": "user", "content": "just text"}}))
        r = run(self.u, "someone", "--transcript", str(self.t))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no pasted images", r.stderr)


if __name__ == "__main__":
    unittest.main()
