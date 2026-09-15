#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Extract one matched HCC1954 Wakhan run; never execute the archived HTML."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import re
import shutil
import tarfile
import time
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = "wakhan_haplotagged"
Row = dict[str, Any]


def fingerprint(path: Path) -> Row:
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"fileSizeBytes": path.stat().st_size, "sha256": digest}


def verify(path: Path, lock: Row) -> None:
    actual = fingerprint(path)
    assert actual == {k: lock[k] for k in actual}, f"Changed input/output: {path}"


def open_with_retry(request: Request) -> Any:
    """Open a download, tolerating brief upstream or network failures."""
    for attempt in range(5):
        try:
            return urlopen(request, timeout=120)
        except (HTTPError, URLError) as error:
            if isinstance(error, HTTPError) and error.code not in {
                429,
                500,
                502,
                503,
                504,
            }:
                raise
            if attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))
    raise AssertionError("Unreachable")


def fetch(source: Row, destination: Path) -> None:
    if not destination.exists():
        temporary = destination.with_suffix(destination.suffix + ".part")
        form_data = source.get("formData")
        body = urlencode(form_data).encode() if form_data else None
        offset = temporary.stat().st_size if temporary.exists() else 0
        resumable = source.get("resumable", False)
        if resumable:
            expected_size = source["fileSizeBytes"]
            chunk_size = source["chunkSizeBytes"]
            while offset < expected_size:
                end = min(offset + chunk_size, expected_size) - 1
                request = Request(
                    source["url"],
                    headers={
                        "User-Agent": "GenomeSpy recipe",
                        "Range": f"bytes={offset}-{end}",
                    },
                )
                with open_with_retry(request) as response, temporary.open(
                    "ab"
                ) as out:
                    content_range = response.headers.get("Content-Range", "")
                    assert response.status == 206 and content_range.startswith(
                        f"bytes {offset}-{end}/"
                    ), "Server did not honor the requested download range"
                    shutil.copyfileobj(response, out)
                assert temporary.stat().st_size == end + 1, "Incomplete download chunk"
                offset = end + 1
        else:
            request = Request(
                source["url"],
                data=body,
                headers={"User-Agent": "GenomeSpy recipe"},
            )
            with open_with_retry(request) as response, temporary.open(
                "wb"
            ) as out:
                shutil.copyfileobj(response, out)
        verify(temporary, source)
        temporary.replace(destination)
    verify(destination, source)


def inputs(provenance: Row, archive: Path | None) -> dict[str, Path]:
    sources = provenance["sources"]
    result = {}
    for source in sources[1:]:
        path = ROOT / "download" / source["filename"]
        fetch(source, path)
        result[source["id"]] = path
    locks = sources[0]["members"]
    selected = ROOT / "work" / "inputs"
    selected.mkdir(parents=True, exist_ok=True)
    if not all((selected / m["localName"]).exists() for m in locks):
        if archive is None:
            archive = ROOT / "download" / sources[0]["filename"]
            fetch(sources[0], archive)
        else:
            verify(archive, sources[0])
        wanted = {m["path"]: m for m in locks}
        with tarfile.open(archive, "r|gz") as tar:
            for member in tar:
                if member.name in wanted:
                    assert member.isfile(), member.name
                    lock = wanted[member.name]
                    stream = tar.extractfile(member)
                    assert stream is not None
                    with stream, (selected / lock["localName"]).open("wb") as out:
                        shutil.copyfileobj(stream, out)
    for lock in locks:
        path = selected / lock["localName"]
        verify(path, lock)
        result[lock["id"]] = path
    return result


def plot(path: Path) -> tuple[list[Row], Row]:
    text = path.read_text()
    matches = list(re.finditer(r'Plotly.newPlot\(\s*"[^"]+",\s*', text))
    assert len(matches) == 1, "Expected one literal Plotly figure"
    tail = text[matches[0].end() :]
    data, offset = json.JSONDecoder().raw_decode(tail)
    layout, _ = json.JSONDecoder().raw_decode(tail[offset:].lstrip(", \r\n"))
    return data, layout


def has_alt(genotype: str) -> bool:
    """Require a completely called genotype and at least one alternate allele."""
    alleles = re.split(r"[/|]", genotype)
    return (
        bool(alleles)
        and all(a.isdigit() for a in alleles)
        and any(int(a) > 0 for a in alleles)
    )


def variants(path: Path) -> tuple[list[Row], list[Row], dict[str, int], Row]:
    records: dict[str, Row] = {}
    lengths: dict[str, int] = {}
    counts: Counter[str] = Counter()
    sample_index = -1
    for line in path.read_text().splitlines():
        if line.startswith("##contig="):
            match = re.fullmatch(r"##contig=<ID=(chr\w+),length=(\d+)>", line)
            assert match
            lengths[match[1]] = int(match[2])
        elif line.startswith("#CHROM"):
            names = line.split("\t")
            assert SAMPLE in names[9:], "Target sample is missing"
            sample_index = names.index(SAMPLE)
        elif not line.startswith("#"):
            assert sample_index >= 9
            fields = line.split("\t")
            sample = dict(
                zip(fields[8].split(":"), fields[sample_index].split(":"), strict=True)
            )
            counts["sourceRecords"] += 1
            if not has_alt(sample["GT"]):
                counts["excludedGenotype"] += 1
                continue
            if fields[6] != "PASS":
                counts["excludedFilter"] += 1
                continue
            info = {
                key: value if sep else "true"
                for key, sep, value in (x.partition("=") for x in fields[7].split(";"))
            }
            records[fields[2]] = dict(
                chrom=fields[0],
                pos=int(fields[1]),
                id=fields[2],
                alt=fields[4],
                info=info,
                sample=sample,
            )
    counts["retainedRecords"] = len(records)
    links: list[Row] = []
    points: list[Row] = []
    seen: set[str] = set()
    for record in records.values():
        if record["id"] in seen:
            continue
        info, sample = record["info"], record["sample"]
        source_type = info["SVTYPE"]
        sv_class = "BND" if source_type == "sBND" else source_type
        chrom2, pos2, mate_id = record["chrom"], record["pos"], "unavailable"
        if source_type == "BND":
            mate_id = info["MATE_ID"]
            # Both ends must pass the target-sample genotype rule.
            assert mate_id in records, f"Missing or filtered BND mate: {mate_id}"
            mate = records[mate_id]
            assert mate["info"]["MATE_ID"] == record["id"]
            chrom2, pos2 = mate["chrom"], mate["pos"]
            partner = re.search(r"[\[\]]([^:\[\]]+):(\d+)[\[\]]", record["alt"])
            assert partner and (partner[1], int(partner[2])) == (chrom2, pos2)
            reciprocal = re.search(r"[\[\]]([^:\[\]]+):(\d+)[\[\]]", mate["alt"])
            assert reciprocal and (reciprocal[1], int(reciprocal[2])) == (
                record["chrom"],
                record["pos"],
            )
            seen.add(mate_id)
        elif source_type in {"DEL", "DUP", "INV"}:
            pos2 = int(info["END"])
        else:
            assert source_type in {"INS", "sBND"}, source_type
        for chrom, pos in [(record["chrom"], record["pos"]), (chrom2, pos2)]:
            assert chrom in lengths and 1 <= pos <= lengths[chrom]
        row: Row = dict(
            chrom1=record["chrom"],
            start1=record["pos"] - 1,
            chrom2=chrom2,
            start2=pos2 - 1,
            position1=record["pos"],
            position2=pos2,
            svClass=sv_class,
            sourceSvType=source_type,
            variantId=record["id"],
            mateId=mate_id,
            orientation=info.get("STRANDS", "unavailable"),
            haplotype=info.get("HP", "unavailable"),
            phaseSet=info.get("PHASESETID", "unavailable"),
            genotype=sample["GT"],
            sample=SAMPLE,
            variantReads=sample.get("DV", "unavailable"),
            referenceReads=sample.get("DR", "unavailable"),
            vaf=sample.get("VAF", "unavailable"),
            haplotypeVaf=sample.get("hVAF", "unavailable"),
            detailedType=info.get("DETAILED_TYPE", "unavailable"),
        )
        (points if source_type in {"INS", "sBND"} else links).append(row)
    return links, points, lengths, dict(counts)


def segments(path: Path, hp: int, lengths: dict[str, int]) -> list[Row]:
    result: list[Row] = []
    for line in path.read_text().splitlines():
        if line.startswith("#"):
            continue
        chrom, start, end, coverage, cn, confidence, ids = line.split("\t")
        row: Row = dict(
            chrom=chrom,
            start=max(0, int(start) - 1),
            end=int(end),
            sourceStart=int(start),
            sourceEnd=int(end),
            haplotype=f"HP{hp}",
            copyNumber=float(cn),
            medianCoverage=float(coverage),
            confidence=float(confidence),
            breakpointIds=ids,
        )
        assert 0 <= row["start"] < row["end"] <= lengths[chrom]
        assert row["copyNumber"] >= 0 and 0 <= row["confidence"] <= 1
        if result and result[-1]["chrom"] == chrom:
            assert result[-1]["end"] == row["start"]
        result.append(row)
    return result


def loh_regions(
    path: Path, lengths: dict[str, int], masked: list[Row]
) -> tuple[list[Row], Row]:
    """Read Wakhan LOH calls and omit portions where its depth is masked."""

    source: list[Row] = []
    for line in path.read_text().splitlines():
        if line.startswith("#"):
            continue
        chrom, start_text, end_text = line.split("\t")
        start, end = int(start_text), int(end_text)
        assert chrom in lengths and 0 <= start < end <= lengths[chrom]
        if source and source[-1]["chrom"] == chrom:
            assert source[-1]["end"] <= start
        source.append(dict(chrom=chrom, start=start, end=end))

    displayed: list[Row] = []
    for row in source:
        fragments = [(row["start"], row["end"])]
        for mask in masked:
            if mask["chrom"] != row["chrom"]:
                continue
            remaining = []
            for start, end in fragments:
                if mask["end"] <= start or mask["start"] >= end:
                    remaining.append((start, end))
                else:
                    if start < mask["start"]:
                        remaining.append((start, mask["start"]))
                    if mask["end"] < end:
                        remaining.append((mask["end"], end))
            fragments = remaining
        displayed.extend(
            dict(
                chrom=row["chrom"],
                start=start,
                end=end,
                sourceStart=row["start"],
                sourceEnd=row["end"],
                feature="LOH",
                basis="Wakhan loh_regions.bed; masked overlap omitted",
            )
            for start, end in fragments
        )

    source_bases = sum(row["end"] - row["start"] for row in source)
    displayed_bases = sum(row["end"] - row["start"] for row in displayed)
    return displayed, dict(
        sourceIntervals=len(source),
        displayedIntervals=len(displayed),
        sourceBases=source_bases,
        displayedBases=displayed_bases,
        maskedOverlapBases=source_bases - displayed_bases,
        policy="Use Wakhan LOH calls, excluding source depth-mask overlap",
    )


def omit_masked_copy_number_segments(
    source: list[Row], masked: list[Row]
) -> tuple[list[Row], Row]:
    """Omit CN-zero placeholders that current Wakhan renders as mask gaps."""

    mask_by_interval = {
        (row["chrom"], row["start"], row["end"]): row for row in masked
    }
    omitted: list[Row] = []
    displayed: list[Row] = []
    for row in source:
        overlapping = [
            mask
            for mask in masked
            if mask["chrom"] == row["chrom"]
            and mask["end"] > row["start"]
            and mask["start"] < row["end"]
        ]
        if not overlapping:
            displayed.append(row)
            continue

        key = (row["chrom"], row["start"], row["end"])
        assert len(overlapping) == 1 and key in mask_by_interval
        assert row["copyNumber"] == 0 and row["medianCoverage"] == 0
        omitted.append(row)

    assert len(omitted) == 2 * len(masked)
    assert Counter(row["haplotype"] for row in omitted) == {
        "HP1": len(masked),
        "HP2": len(masked),
    }
    return displayed, dict(
        sourceIntervals=len(source),
        displayedIntervals=len(displayed),
        maskedPlaceholdersOmitted=len(omitted),
        policy="Omit exact mask-matching CN-zero placeholders",
    )


def bins(traces: list[Row], lengths: dict[str, int]) -> list[Row]:
    hp1, hp2, baf = [
        next(t for t in traces if t.get("name") == name and t.get("mode") == "markers")
        for name in ["HP-1", "HP-2", "BAF"]
    ]
    assert hp1["x"] == hp2["x"] == baf["x"]
    assert hp1["text"] == hp2["text"] == baf["text"]
    assert len(hp1["x"]) == len(hp1["y"]) == len(hp2["y"]) == len(baf["y"])
    result, chromosome, offset, previous = [], 1, 0, -1
    for i, value in enumerate(hp1["text"]):
        source_start = int(value)
        if source_start < previous:
            offset += lengths[f"chr{chromosome}"]
            chromosome += 1
        chrom = f"chr{chromosome}"
        assert hp1["x"][i] == offset + source_start, "Plot coordinate/assembly mismatch"
        start = max(0, source_start - 1)
        assert start % 50000 == 0
        end = min(start + 50000, lengths[chrom])
        a, b, f = hp1["y"][i], -hp2["y"][i], baf["y"][i]
        assert all(math.isfinite(x) for x in (a, b, f))
        assert a >= 0 and b >= 0 and 0 <= f <= 0.5
        result.append(
            dict(
                chrom=chrom,
                start=start,
                end=end,
                sourceStart=source_start,
                hp1=a,
                hp2=b,
                baf=f,
                coverageStatus="masked" if a == b == 3300 else "reported",
                bafStatus="Zero in source; SNP support unavailable"
                if f == 0
                else "Reported bin mean",
            )
        )
        previous = source_start
    assert chromosome == 22
    return result


def canonical_drivers(path: Path) -> dict[str, Row]:
    """Aggregate NCG canonical drivers and their literature support."""

    evidence: dict[str, list[Row]] = {}
    canonical: set[str] = set()
    with path.open() as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            symbol = row["symbol"]
            evidence.setdefault(symbol, []).append(row)
            if row["type"] == "Canonical Cancer Driver":
                canonical.add(symbol)

    result: dict[str, Row] = {}
    for symbol in canonical:
        rows = evidence[symbol]
        entrez_ids = {row["entrez"] for row in rows}
        roles = {
            (row["NCG_oncogene"], row["NCG_tsg"])
            for row in rows
            if row["NCG_oncogene"] and row["NCG_tsg"]
        }
        assert len(entrez_ids) == len(roles) == 1
        oncogene, tumour_suppressor = roles.pop()
        if (oncogene, tumour_suppressor) == ("1", "0"):
            role = "Oncogene"
        elif (oncogene, tumour_suppressor) == ("0", "1"):
            role = "Tumour suppressor"
        else:
            assert (oncogene, tumour_suppressor) == ("0", "0")
            role = "Dual or unclassified"
        publications = {row["pubmed_id"] for row in rows if row["pubmed_id"]}
        result[symbol] = dict(
            entrez=int(entrez_ids.pop()),
            ncgClass="Canonical cancer driver",
            driverRole=role,
            supportCount=len(publications),
        )
    return result


def reference_annotations(
    paths: dict[str, Path], lengths: dict[str, int]
) -> tuple[list[Row], list[Row]]:
    bands = []
    with gzip.open(paths["cytobands"], "rt") as stream:
        for chrom, start, end, band, stain in csv.reader(stream, delimiter="\t"):
            if chrom in lengths:
                assert 0 <= int(start) < int(end) <= lengths[chrom]
                bands.append(
                    dict(
                        chrom=chrom,
                        start=int(start),
                        end=int(end),
                        band=band,
                        stain=stain,
                    )
                )
    drivers = canonical_drivers(paths["ncg"])
    assert len(drivers) == 591, "Unexpected NCG canonical driver count"
    genes: dict[tuple[str, str, str], Row] = {}
    with gzip.open(paths["refseq"], "rt") as stream:
        for fields in csv.reader(stream, delimiter="\t"):
            _, accession, chrom, strand, start, end = fields[:6]
            symbol = fields[12]
            if (
                symbol not in drivers
                or chrom not in lengths
                or not accession.startswith("NM_")
            ):
                continue
            key = (symbol, chrom, strand)
            if key in genes:
                row = genes[key]
                row["start"], row["end"] = (
                    min(row["start"], int(start)),
                    max(row["end"], int(end)),
                )
            else:
                genes[key] = dict(
                    chrom=chrom,
                    start=int(start),
                    end=int(end),
                    symbol=symbol,
                    strand=strand,
                    **drivers[symbol],
                )
    assert {row["symbol"] for row in genes.values()} == set(drivers), (
        "Missing NCG gene in RefSeq"
    )
    chrom_order = {chrom: index for index, chrom in enumerate(lengths)}
    ordered_genes = sorted(
        genes.values(), key=lambda row: (chrom_order[row["chrom"]], row["start"])
    )
    return bands, ordered_genes


def write_table(name: str, rows: list[Row]) -> Row:
    assert rows
    path = ROOT / "output" / name
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)
    return {"path": "output/" + name, **fingerprint(path), "recordCount": len(rows)}


def validate_source_plot(traces: list[Row], cn: list[Row]) -> Row:
    """Compare all BED intervals with the independently serialized Plotly lines."""
    masked_differences, confidence_differences = 0, 0
    for hp in (1, 2):
        trace = next(
            t
            for t in traces
            if t.get("name") == f"HP-{hp}" and t.get("mode") == "lines"
        )
        rows = [row for row in cn if row["haplotype"] == f"HP{hp}"]
        assert len(rows) * 3 == len(trace["text"])
        for i, row in enumerate(rows):
            j = i * 3
            assert row["sourceStart"] == int(trace["text"][j])
            assert row["end"] == int(trace["text"][j + 1])
            confidence, state = trace["customdata"][j]
            if state != row["copyNumber"]:
                # HP2's sentinel is mapped to CN 34 in HTML customdata, but
                # its actual line y remains 3300. Neither is a measured CN.
                assert row["copyNumber"] == 0 and abs(trace["y"][j]) == 3300
                masked_differences += 1
            confidence_differences += confidence != row["confidence"]
    return dict(
        intervalsCompared=len(cn),
        maskedStateDifferences=masked_differences,
        confidenceDifferences=confidence_differences,
        policy=(
            "BED is authoritative outside exact masks; "
            "current Wakhan renders masked CN as gaps; "
            "HTML supplies binned depth and BAF"
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    provenance = json.loads((ROOT / "provenance.json").read_text())
    if args.verify_only:
        for lock in provenance["outputs"].values():
            verify(ROOT / lock["path"], lock)
        print("All accepted output fingerprints match.")
        return
    for directory in ["download", "work", "output"]:
        (ROOT / directory).mkdir(exist_ok=True)
    paths = inputs(provenance, args.archive)
    links, points, lengths, counts = variants(paths["vcf"])
    # Pinned to GenomeSpy's GRCh38 chr1–22/X/Y lengths, checked independently.
    lengths_digest = hashlib.sha256(
        json.dumps(lengths, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert lengths_digest == provenance["parameters"]["chromosomeLengthsSha256"]
    log = paths["log"].read_text()
    assert "grch38_chr.fasta" in log and "--contigs chr1-22" in log
    assert "HCC1954.haplotagged.bam" in log and "HCC1954BL" in log
    assert "--breakpoints severus/somatic_SVs/severus_somatic.vcf" in log
    with paths["ranks"].open() as stream:
        rank = next(csv.DictReader(stream, delimiter="\t"))
    assert rank["repository_name"] == provenance["parameters"]["solution"]
    assert rank["solution_rank"] == "1"
    traces, layout = plot(paths["figure"])
    coverage = bins(traces, lengths)
    masked: list[Row] = []
    for row in coverage:
        if row["coverageStatus"] == "masked":
            if (
                masked
                and masked[-1]["chrom"] == row["chrom"]
                and masked[-1]["end"] == row["start"]
            ):
                masked[-1]["end"] = row["end"]
            else:
                masked.append(
                    dict(
                        chrom=row["chrom"],
                        start=row["start"],
                        end=row["end"],
                        status=(
                            "Wakhan centromeric/blacklisted mask "
                            "(source sentinel 3300); "
                            "CN zeros here are not evidence of deletion"
                        ),
                    )
                )
    source_cn = segments(paths["hp1"], 1, lengths) + segments(
        paths["hp2"], 2, lengths
    )
    cn, cn_mask_validation = omit_masked_copy_number_segments(source_cn, masked)
    loh, loh_validation = loh_regions(paths["loh"], lengths, masked)
    bands, genes = reference_annotations(paths, lengths)
    # Preserve missing source tails and unanalysed sex chromosomes explicitly.
    gaps = []
    for chrom, length in lengths.items():
        ends = [r["end"] for r in cn if r["chrom"] == chrom]
        start = max(ends, default=0)
        if start < length:
            gaps.append(
                dict(
                    chrom=chrom,
                    start=start,
                    end=length,
                    status="Outside Wakhan autosome analysis"
                    if not ends
                    else "No CN segment in source tail",
                )
            )
    outputs = {}
    for name, rows in [
        ("coverage-baf.tsv", coverage),
        ("masked-regions.tsv", masked),
        ("copy-number-segments.tsv", cn),
        ("loh-segments.tsv", loh),
        ("sv-links.tsv", links),
        ("sv-sites.tsv", points),
        ("cytobands.tsv", bands),
        ("genes.tsv", genes),
        ("unavailable-cn.tsv", gaps),
    ]:
        outputs[name] = write_table(name, rows)
    support_by_gene = {row["symbol"]: row["supportCount"] for row in genes}
    support_counts = sorted(support_by_gene.values())
    validation = dict(
        sourcePlotComparison=validate_source_plot(traces, source_cn),
        svFiltering=counts,
        svLinks=len(links),
        svSites=len(points),
        sourceSvTypes=dict(Counter(row["sourceSvType"] for row in links + points)),
        wakhanSvClasses=dict(Counter(row["svClass"] for row in links + points)),
        coverageBins=len(coverage),
        maskedBins=sum(r["coverageStatus"] == "masked" for r in coverage),
        bafZeroBins=sum(r["baf"] == 0 for r in coverage),
        coverageMax={
            hp: max(r[hp] for r in coverage if r["coverageStatus"] == "reported")
            for hp in ["hp1", "hp2"]
        },
        copyNumberMax={
            hp: max(r["copyNumber"] for r in cn if r["haplotype"] == hp)
            for hp in ["HP1", "HP2"]
        },
        copyNumberMasks=cn_mask_validation,
        loh=loh_validation,
        sourcePlotCoverageRange=layout["yaxis2"]["range"],
        chromosomeLengthsMatchVcfAndPlot=True,
        geneAnnotations=dict(
            canonicalGenes=len(support_by_gene),
            genomicLoci=len(genes),
            supportCount=dict(
                definition="Distinct PubMed IDs in NCG evidence rows",
                minimum=min(support_counts),
                median=support_counts[len(support_counts) // 2],
                percentile90=support_counts[int(0.9 * (len(support_counts) - 1))],
                maximum=max(support_counts),
                distinctValues=len(set(support_counts)),
            ),
            allCanonicalGenesMappedToRefSeq=True,
            pseudoautosomalGenesWithTwoLoci=["CRLF2", "P2RY8"],
            knownGenes={
                row["symbol"]: f"{row['chrom']}:{row['start'] + 1}-{row['end']}"
                for row in genes
                if row["symbol"] in {"ERBB2", "MYC"}
            },
        ),
    )
    report = {"outputs": outputs, "validation": validation}
    (ROOT / "work" / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    for name, lock in provenance["outputs"].items():
        assert outputs[name] == lock, f"Output changed: {name}"
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
