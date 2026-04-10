"""Conflict detection for preprocessed corpus documents.

Identifies clusters of documents covering the same topic that contain
diverging factual signals (years, emails, phone numbers, money amounts,
dates). Produces a human-readable markdown report for manual review.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

_CONFLICT_FIELDS = (
    "latest_year",
    "contact_emails",
    "contact_phones",
    "money_amounts",
    "date_mentions",
)


def detect_cluster_conflicts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group kept documents by topic_key and find clusters with conflicting data.

    A conflict exists when two or more documents in the same topic cluster
    disagree on at least one of: latest_year, contact_emails, contact_phones,
    money_amounts, date_mentions.

    Parameters
    ----------
    records:
        List of metadata dicts from freshness.collect_document_metadata().
        Only records with keep=True are considered.

    Returns
    -------
    list of conflict cluster dicts, sorted by cluster size descending:
        {topic_key, cluster_size, filenames, source_urls,
         conflict_fields, newer_candidate_filename, newer_candidate_year}
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("keep"):
            grouped[record["topic_key"]].append(record)

    cluster_summaries: list[dict[str, Any]] = []

    for topic_key, cluster_records in grouped.items():
        if len(cluster_records) < 2:
            continue

        conflict_fields: list[str] = []
        for field in _CONFLICT_FIELDS:
            normalized_values: set[Any] = set()
            for record in cluster_records:
                value = record.get(field)
                if value in (None, "", []):
                    continue
                if isinstance(value, list):
                    normalized_values.add(tuple(value))
                else:
                    normalized_values.add(value)
            if len(normalized_values) > 1:
                conflict_fields.append(field)

        if not conflict_fields:
            continue

        newer_candidate = max(
            cluster_records,
            key=lambda record: (
                record.get("latest_year") or 0,
                -len(record.get("legacy_url_hits", [])),
                record["filename"],
            ),
        )

        cluster_summaries.append(
            {
                "topic_key": topic_key,
                "cluster_size": len(cluster_records),
                "filenames": [record["filename"] for record in cluster_records],
                "source_urls": [record["source_url"] for record in cluster_records],
                "conflict_fields": sorted(conflict_fields),
                "newer_candidate_filename": newer_candidate["filename"],
                "newer_candidate_year": newer_candidate.get("latest_year"),
            }
        )

    cluster_summaries.sort(
        key=lambda cluster: (-cluster["cluster_size"], cluster["topic_key"])
    )
    return cluster_summaries


def format_conflict_report(
    clusters: list[dict[str, Any]],
    stats: dict[str, Any],
) -> str:
    """Generate a human-readable markdown conflict review report.

    Parameters
    ----------
    clusters:
        Output of detect_cluster_conflicts().
    stats:
        Summary statistics dict with optional keys:
        - ``total_kept``: total number of kept documents
        - ``total_records``: total records processed (kept + filtered)

    Returns
    -------
    str:
        Markdown-formatted report string.
    """
    total_kept = stats.get("total_kept", "unknown")
    total_records = stats.get("total_records", "unknown")
    total_files_in_conflicts = sum(c["cluster_size"] for c in clusters)

    lines: list[str] = [
        "# Conflict Review Report",
        "",
        "## Summary",
        "",
        f"- **Documents processed:** {total_records}",
        f"- **Documents kept:** {total_kept}",
        f"- **Conflict clusters identified:** {len(clusters)}",
        f"- **Files involved in conflicts:** {total_files_in_conflicts}",
        "",
    ]

    if not clusters:
        lines += [
            "No conflicts detected. All topic clusters have consistent data.",
            "",
        ]
        return "\n".join(lines)

    lines += [
        "## Conflict Clusters",
        "",
        "> Clusters are sorted by size (largest first).",
        "> The **newer candidate** is the document most likely to be authoritative.",
        "",
    ]

    for i, cluster in enumerate(clusters, start=1):
        lines += [
            f"### Cluster {i}: `{cluster['topic_key']}`",
            "",
            f"- **Cluster size:** {cluster['cluster_size']} documents",
            f"- **Conflict fields:** {', '.join(cluster['conflict_fields'])}",
            "- **Newer candidate:** `{name}`{year}".format(
                name=cluster["newer_candidate_filename"],
                year=(
                    f" (year: {cluster['newer_candidate_year']})"
                    if cluster.get("newer_candidate_year")
                    else ""
                ),
            ),
            "",
            "**Files in cluster:**",
            "",
        ]
        for filename, url in zip(cluster["filenames"], cluster["source_urls"]):
            lines.append(f"- `{filename}` — {url}")
        lines.append("")

    return "\n".join(lines)
