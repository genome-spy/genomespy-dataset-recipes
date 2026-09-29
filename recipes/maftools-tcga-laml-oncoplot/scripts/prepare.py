#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# /// script
# requires-python = "==3.14.*"
# dependencies = ["pandas==3.0.3", "numpy==2.4.6"]
# ///
"""Acquire pinned example inputs and verify byte-preserving recipe outputs."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def verify(raw: bytes, record: dict[str, Any], label: str) -> None:
    """Reject changed or truncated input before accepting it."""
    if len(raw) != record["fileSizeBytes"]:
        raise ValueError(f"{label}: byte size differs from provenance")
    if hashlib.sha256(raw).hexdigest() != record["sha256"]:
        raise ValueError(f"{label}: SHA-256 differs from provenance")


def write_atomic(path: Path, raw: bytes) -> None:
    """Expose only complete verified files to other processes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(raw)
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def read_source(record: dict[str, Any], source_dir: Path) -> bytes:
    """Read a verified cached source or download its exact recorded identity."""
    path = source_dir / record["filename"]
    if path.exists():
        raw = path.read_bytes()
    else:
        request = Request(record["url"], headers={"Accept-Encoding": "identity"})
        with urlopen(request, timeout=60) as response:
            raw = response.read(record["fileSizeBytes"] + 1)
    verify(raw, record, record["filename"])
    if not path.exists():
        write_atomic(path, raw)
    return raw


def bundle(inputs: dict[str, bytes], settings: dict[str, Any]) -> dict[str, Any]:
    """Assemble deterministic mutation, CNV, clinical, and pathway plot tables."""
    import pandas as pd  # type: ignore[import-untyped]

    def read(name: str) -> Any:
        content = inputs[name]
        if name.endswith(".gz"):
            content = gzip.decompress(content)
        return pd.read_csv(io.BytesIO(content), sep="\t")

    def records(frame: Any) -> list[dict[str, Any]]:
        return json.loads(frame.to_json(orient="records"))

    maf = read("tcga_laml.maf.gz")
    samples = read("tcga_laml_annot.tsv").rename(
        columns={"Tumor_Sample_Barcode": "sample"}
    )
    samples["sample"] = samples["sample"].str[: settings["sampleIdLength"]]
    samples["FAB_classification"] = samples.FAB_classification.fillna("Unknown")
    variants = maf[
        maf.Variant_Classification.isin(settings["nonsynonymousClasses"])
    ].copy()
    variants["sample"] = variants.Tumor_Sample_Barcode.str[: settings["sampleIdLength"]]
    variants["gene"] = variants.Hugo_Symbol
    pathways = settings["pathways"]
    wanted = {gene for members in pathways.values() for gene in members}
    selected = variants[variants.gene.isin(wanted)]
    events = []
    for (sample, gene), changes in selected.groupby(["sample", "gene"]):
        alternate_c = bool(changes.Tumor_Seq_Allele2.eq("C").any())
        events.append(
            {
                "sample": sample,
                "gene": gene,
                "class": changes.Variant_Classification.iloc[0]
                if len(changes) == 1
                else "Multi_Hit",
                "alt_c": alternate_c,
                "feature": "Alternate allele C" if alternate_c else None,
            }
        )
    lesions = read("all_lesions.conf_99.txt")
    calls = []
    seen = set()
    for kind, filename in [
        ("Amp", "amp_genes.conf_99.txt"),
        ("Del", "del_genes.conf_99.txt"),
    ]:
        peaks = read(filename)
        for band in peaks.columns[1:]:
            genes = sorted(
                {str(g) for g in peaks[band].iloc[3:].dropna() if "|" not in str(g)}
            )
            for lesion in lesions.to_dict(orient="records"):
                if (
                    not lesion["Unique Name"].startswith(kind)
                    or "CN values" in lesion["Unique Name"]
                ):
                    continue
                if (
                    lesion["Descriptor"].strip() != band
                    or lesion["Wide Peak Limits"].split("(")[0].strip()
                    != peaks[band].iloc[2]
                ):
                    continue
                for sample in lesions.columns[9:]:
                    if not sample.startswith("TCGA-") or lesion[sample] not in (1, 2):
                        continue
                    sample_id = sample[: settings["sampleIdLength"]]
                    for gene in genes:
                        if (sample_id, gene) not in seen:
                            calls.append(
                                {"sample": sample_id, "gene": gene, "class": kind}
                            )
                            seen.add((sample_id, gene))
    copy_number = [r for r in calls if r["gene"] in wanted]
    presence = {(r["sample"], r["gene"]) for r in events + copy_number}
    frequencies = Counter(gene for _sample, gene in presence)
    pathway_order = sorted(
        pathways,
        key=lambda p: (-max(frequencies[g] for g in pathways[p]), -len(pathways[p]), p),
    )
    gene_order = [
        g
        for p in pathway_order
        for g in sorted(pathways[p], key=lambda g: (-frequencies[g], g))
    ]
    fab = dict(zip(samples["sample"], samples.FAB_classification, strict=True))
    fab_sizes = Counter(fab.values())
    ordered_samples = sorted(
        fab,
        key=lambda s: (
            -fab_sizes[fab[s]],
            fab[s],
            tuple(-int((s, g) in presence) for g in gene_order),
            s,
        ),
    )
    positions = {s: i for i, s in enumerate(ordered_samples)}
    samples["sample_order"] = samples["sample"].map(positions)
    means = selected.groupby("gene").i_TumorVAF_WU.mean()
    qvalues = read("LAML_sig_genes.txt.gz").set_index("gene").q
    gene_rows = []
    matrix: list[dict[str, Any]] = []
    pathway_events: list[dict[str, Any]] = []
    bounds = []
    for pathway in pathway_order:
        start = len(matrix)
        for gene in [g for g in gene_order if g in pathways[pathway]]:
            mean = means.get(gene)
            q = qvalues.get(gene)
            record = {
                "gene": gene,
                "pathway": pathway,
                "vaf": None if pd.isna(mean) else float(mean),
                "neglog_q": -math.log10(float(q)) if q is not None and q > 0 else None,
                "altered_percent": round(100 * frequencies[gene] / len(samples), 1),
            }
            gene_rows.append(record)
            matrix.append(record)
        affected = sorted({s for s, g in presence if g in pathways[pathway]})
        matrix.append(
            {
                "gene": pathway,
                "pathway": pathway,
                "altered_percent": 100 * len(affected) / len(samples),
            }
        )
        pathway_events.extend(
            {
                "sample": s,
                "sample_order": positions[s],
                "gene": pathway,
                "class": "Pathway",
            }
            for s in affected
        )
        bounds.append({"pathway": pathway, "start": start, "end": len(matrix) - 1})
    row_positions = {r["gene"]: i for i, r in enumerate(matrix)}
    for record in matrix + pathway_events:
        record["row"] = row_positions[record["gene"]]
        if "altered_percent" in record:
            record["percent_label"] = f"{record['altered_percent']:g}%"
    for record in events + copy_number:
        record.update(
            sample_order=positions[record["sample"]], row=row_positions[record["gene"]]
        )
    mutations = Counter(
        zip(variants["sample"], variants.Variant_Classification, strict=True)
    )
    cn_counts = Counter((r["sample"], r["class"]) for r in calls)
    burden = [
        {
            "sample": s,
            "class": kind,
            "count": counts[(s, kind)],
            "sample_order": positions[s],
        }
        for counts in (mutations, cn_counts)
        for s, kind in sorted(counts)
    ]
    totals: Counter[str] = Counter()
    for record in burden:
        totals[record["sample"]] += record["count"]
    spectrum: list[dict[str, Any]] = []
    complement = {"A": "T", "T": "A", "G": "C", "C": "G"}
    for sample, changes in maf[maf.Variant_Type == "SNP"].groupby(
        "Tumor_Sample_Barcode"
    ):
        counts: Counter[str] = Counter()
        for ref, alt in zip(
            changes.Reference_Allele, changes.Tumor_Seq_Allele2, strict=True
        ):
            if ref in complement and alt in complement and ref != alt:
                if ref in ("A", "G"):
                    ref, alt = complement[ref], complement[alt]
                counts[f"{ref}>{alt}"] += 1
        s = sample[: settings["sampleIdLength"]]
        spectrum.extend(
            {
                "sample": s,
                "sample_order": positions[s],
                "substitution": kind,
                "percent": 100 * count / sum(counts.values()),
            }
            for kind, count in sorted(counts.items())
        )
    return {
        "samples": records(samples),
        "events": records(pd.DataFrame(events)),
        "copy_number": records(pd.DataFrame(copy_number)),
        "genes": gene_rows,
        "gene_order": gene_order,
        "matrix_rows": matrix,
        "pathway_events": pathway_events,
        "pathway_bounds": bounds,
        "altered_samples": len({s for s, _g in presence}),
        "sample_domain": [0, len(samples) - 1],
        "burden": records(pd.DataFrame(burden)),
        "burden_limit": max(totals.values()),
        "spectrum": spectrum,
        "provenance": settings["bundleProvenance"],
    }


def main() -> None:
    """Prepare pinned LAML outputs or verify existing artifacts offline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--source-dir", type=Path, default=ROOT / "download")
    args = parser.parse_args()
    provenance = json.loads((ROOT / "provenance.json").read_text())
    if args.verify_only:
        outputs = {
            key: (ROOT / record["path"]).read_bytes()
            for key, record in provenance["outputs"].items()
        }
    else:
        acquired = {
            s["id"]: read_source(s, args.source_dir) for s in provenance["sources"]
        }
        outputs = {
            key: acquired[record["sourceId"]]
            for key, record in provenance["outputs"].items()
            if "sourceId" in record
        }
        outputs["combined"] = gzip.compress(
            json.dumps(
                bundle(acquired, provenance["parameters"]),
                separators=(",", ":"),
                allow_nan=False,
            ).encode(),
            mtime=0,
        )
    for key, raw in outputs.items():
        verify(raw, provenance["outputs"][key], key)
    if not args.verify_only:
        for key, raw in outputs.items():
            write_atomic(ROOT / provenance["outputs"][key]["path"], raw)


if __name__ == "__main__":
    main()
