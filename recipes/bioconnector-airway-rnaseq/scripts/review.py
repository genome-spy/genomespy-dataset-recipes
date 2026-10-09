# SPDX-License-Identifier: CC0-1.0
# /// script
# requires-python = "==3.14.*"
# dependencies = []
# ///
"""Prepare the fixed Airway teaching analysis independently of the Python library."""

from __future__ import annotations

import gzip
import io
import json
from typing import Any


def prepare_review(sources: dict[str, bytes], parameters: dict[str, Any]) -> bytes:
    """Return deterministic JSON for the accepted paired-analysis contract."""
    import numpy as np  # type: ignore[import-not-found]
    import pandas as pd  # type: ignore[import-untyped]
    import statsmodels.stats.multitest as mt  # type: ignore[import-not-found]
    from scipy.stats import ttest_rel  # type: ignore[import-untyped]

    metadata = pd.read_csv(io.BytesIO(sources["metadata"]))
    counts = pd.read_csv(io.BytesIO(sources["counts"]), index_col="ensgene")
    samples = metadata.id.tolist()
    average = counts[samples].mean(axis=1)
    selected = counts.loc[average >= parameters["minimumMean"]].sort_index()
    paired = metadata.pivot(index="celltype", columns="dex", values="id")
    paired = paired.loc[metadata.celltype.drop_duplicates()]
    transformed = np.log2(selected[samples] + 1.0)
    treated = transformed[paired.treated.tolist()].to_numpy()
    control = transformed[paired.control.tolist()].to_numpy()
    effect = np.mean(treated - control, axis=1)
    probability = np.asarray(
        ttest_rel(treated, control, axis=1, nan_policy="omit").pvalue, dtype=float
    )
    invalid = ~np.isfinite(probability)
    probability[invalid] = np.where(np.isclose(effect[invalid], 0.0), 1.0, 0.0)
    adjusted = mt.fdrcorrection(probability, alpha=parameters["fdrAlpha"])[1]
    frame = pd.DataFrame(
        dict(
            ensgene=selected.index,
            base_mean=average.loc[selected.index].to_numpy(),
            log2fc=effect,
            pvalue=probability,
            padj=adjusted,
        )
    )
    for source, target in [("pvalue", "neglog10_pvalue"), ("padj", "neglog10_padj")]:
        frame[target] = -np.log10(frame[source].clip(lower=1e-300, upper=1.0))
    frame["log10_base_mean"] = np.log10(frame.base_mean)
    significant = (frame.pvalue < parameters["pvalueCutoff"]) & (
        frame.log2fc.abs() >= parameters["effectCutoff"]
    )
    frame["direction"] = "n.s."
    frame.loc[significant & (frame.log2fc > 0), "direction"] = "up in dex"
    frame.loc[significant & (frame.log2fc <= 0), "direction"] = "down in dex"
    frame = frame.nlargest(parameters["maximumGenes"], "base_mean")
    frame = frame.sort_values("log10_base_mean")
    extent = float(np.ceil(frame.log2fc.abs().max() * 2) / 2)
    upper = float(np.ceil(frame.neglog10_pvalue.quantile(0.995) / 5) * 5)
    frame["neglog10_pvalue_plot"] = frame.neglog10_pvalue.clip(upper=upper)
    domains = {
        "ma_x": [
            float(np.floor(frame.log10_base_mean.min() * 2) / 2),
            float(np.ceil(frame.log10_base_mean.max() * 2) / 2),
        ],
        "ma_y": [-extent, extent],
        "volcano_x": [-extent, extent],
        "volcano_y": [0.0, upper],
        "pvalue_cutoff": [-float(np.log10(parameters["pvalueCutoff"]))],
    }
    frame["gene_symbol"] = frame.ensgene.map(parameters["geneSymbols"])
    for kind in ["volcano", "ma"]:
        frame[kind + "_label"] = frame.gene_symbol.where(
            frame.gene_symbol.isin(parameters[kind + "Labels"])
        )
    frame["gene_id"] = frame.ensgene
    frame["symbol"] = frame.gene_symbol.fillna("")
    frame["baseMean"] = frame.base_mean
    for sample in samples:
        frame[sample] = frame.ensgene.map(counts[sample])
    rows = frame.astype(object).where(frame.notna(), None).to_dict(orient="records")
    payload = {
        # Keep legacy metadata strings for compatibility; recipe provenance
        # records the actual pinned remote inputs and execution environment.
        "provenance": parameters["bundleProvenance"],
        "domains": domains,
        "samples": [
            {
                "sample": r["id"],
                "cell": r["celltype"],
                "condition": r["dex"].capitalize(),
            }
            for r in metadata.to_dict(orient="records")
        ],
        "genes": rows,
    }
    return gzip.compress(
        json.dumps(payload, separators=(",", ":"), allow_nan=False).encode(), mtime=0
    )
