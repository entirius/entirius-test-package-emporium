# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Enricher picture checks demo (seed.sh Step 4d): what a ComfyUI picture check leaves behind, without a ComfyUI.

Run via:
    docker exec -i <service> python manage.py shell < scripts/seed-comfy.py

Two `comfy` workers on the channel `default-europe`, each with one finished run:
- `demo.packshot_check` (output `metrics`, dry run): a result for every main picture of the channel, the verdicts
  from a made-up "white background" score, and the run's counts. Its template "Packshot check" puts it in the PIM
  grid's AI menu.
- `demo.packshot_whiten` (output `picture`): one pending derived picture of ENT-C005's main picture (the source
  padded onto a white square), the proposal a picture workflow makes, with the add / replace choice on accept.

Both workers are `external`: the spawn beat takes only internal ones, and the metric registered here lives only in
this shell, so an internal worker would fail its options check in the beat every 15 minutes. Nothing here calls
ComfyUI. The CMS docs guide `picture-checks` captures these rows.

Idempotent: an existing `demo.packshot_check` worker means the demo is in place, nothing is written.
"""

import io
import random

from django.core.files.base import ContentFile
from django_enrichment.enums import TaskLane, TaskStatus, WorkerMode
from django_enrichment.kinds import comfy
from django_enrichment.kinds.base import ProposalDraft
from django_enrichment.models import ComfyResult, EnrichmentTask, TaskTemplate, Worker
from django_enrichment.services import runner_service, worker_service
from django_pim.models import ProductPicture
from django_pim.services import enrichment_adapter as pim
from PIL import Image, ImageOps

CHANNEL = "default-europe"
CHECK, WHITEN = "demo.packshot_check", "demo.packshot_whiten"
METRIC = "demo_white_background"
DERIVED_SKU = "ENT-C005"
RUN_HASH = "demo"
THRESHOLDS = [
    {"min": 0.9, "action": "escalate", "reason": "replace_size"},
    {"min": 0.3, "action": "set"},
    {"min": 0.15, "action": "review"},
]


def verdict_of(score: float) -> tuple[str, str]:
    for threshold in THRESHOLDS:
        if score >= threshold["min"]:
            return threshold["action"], threshold.get("reason", "")
    return comfy.PASS, ""


def save_worker(key: str, label: str, options: dict) -> Worker:
    worker = Worker(key=key, label=label, kind=comfy.KIND, mode=WorkerMode.EXTERNAL.value, target_module="pim")
    worker.options = {"channel": CHANNEL, "input_node": "1", "auto_spawn": False, **options}
    return worker_service.save_worker(worker)


def finished_task(worker: Worker, refs: list[str], counts: dict) -> EnrichmentTask:
    return EnrichmentTask.objects.create(
        type=worker.key,
        status=TaskStatus.DONE.value,
        lane=TaskLane.QUEUE.value,
        scope_spec={"mode": "list", "module": "pim", "refs": refs},
        counts=counts,
    )


def record(worker: Worker, task: EnrichmentTask, row: dict, verdict: str, reason: str, metrics: dict) -> None:
    ComfyResult.objects.create(
        subject_ref=row["subject_ref"],
        input_sha1=row["sha1"],
        worker_key=worker.key,
        run_hash=RUN_HASH,
        source=comfy.SOURCE_WORKFLOW,
        metrics=metrics,
        score=metrics.get("score"),
        verdict=verdict,
        reason=reason,
        worker_version=worker.version,
        task=task,
    )


def seed_checks(rows: list[dict]) -> None:
    worker = save_worker(
        CHECK,
        "Packshot check (demo)",
        {
            "workflow": "comfy/packshot_check.json",
            "metric": METRIC,
            "thresholds": THRESHOLDS,
            "feature": "packshot",
            "escalate_feature": "packshot_check",
            "dry_run": True,
            "window": "22:00-06:00",
        },
    )
    TaskTemplate.objects.create(key="demo-packshot-check", label="Packshot check", worker=worker, position=90)
    rng = random.Random(7)  # noqa: S311 — demo scores, fixed seed for the same shots every run
    judged = []
    for row in rows:
        score = round(rng.random(), 3)
        verdict, reason = verdict_of(score)
        judged.append((row, verdict, reason, {"score": score, "white_share": round(rng.random(), 2)}))
    counts = {comfy.CHECKED: len(judged)}
    for _, verdict, _, _ in judged:
        counts[verdict] = counts.get(verdict, 0) + 1
    task = finished_task(worker, [row["subject_ref"] for row in rows], counts)
    for row, verdict, reason, metrics in judged:
        record(worker, task, row, verdict, reason, metrics)
    print(f"seed-comfy: {len(judged)} checks, counts {counts}")


def padded_png(row: dict) -> bytes:
    link = ProductPicture.objects.select_related("picture").get(pk=int(row["picture_ref"]))
    with link.picture.image.open("rb") as handle, Image.open(handle) as source:
        square = ImageOps.pad(source.convert("RGB"), (1024, 1024), color="white", centering=(0.5, 0.5))
    canvas = Image.new("RGB", (1200, 1200), "white")
    canvas.paste(square, (88, 88))
    out = io.BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()


def seed_derived(rows: list[dict]) -> None:
    row = next(row for row in rows if row["subject_ref"] == DERIVED_SKU)
    worker = save_worker(
        WHITEN, "Packshot whitening (demo)", {"workflow": "comfy/packshot_whiten.json", "output": "picture"}
    )
    task = finished_task(worker, [DERIVED_SKU], {comfy.CHECKED: 1, comfy.PROPOSE_PICTURE: 1})
    record(worker, task, row, comfy.PROPOSE_PICTURE, "", {})
    locator = {"channel": CHANNEL, "source_picture_ref": row["picture_ref"], "operation": WHITEN, "variant": 1}
    value = {"op": comfy.DERIVED_OP, "operation": WHITEN, "preset": "", "variant": 1, "of": 1}
    png = ContentFile(padded_png(row), name=f"{WHITEN}.png")
    draft = ProposalDraft(comfy.PICTURE_KIND, locator, value, subject_label=DERIVED_SKU, media_file=png)
    runner_service.intake_subject(worker, task, DERIVED_SKU, [draft])
    print(f"seed-comfy: derived picture proposed for {DERIVED_SKU}")


if Worker.objects.filter(key=CHECK).exists():
    print("seed-comfy: demo present")
else:
    comfy.register_comfy_metric(METRIC, lambda picture, output: {"score": 0.0})
    pictures = pim.main_pictures(channel=CHANNEL)
    seed_checks(pictures)
    seed_derived(pictures)
