"""Diff computation between prompt versions."""

import difflib
from .models import DiffHunk, PromptDiff, PromptVersion


def compute_diff(
    prompt_id: str,
    prompt_name: str,
    old_version: PromptVersion,
    new_version: PromptVersion,
) -> PromptDiff:
    old_lines = old_version.raw_content.splitlines(keepends=True)
    new_lines = new_version.raw_content.splitlines(keepends=True)

    hunks = []
    additions = 0
    deletions = 0

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    for group in matcher.get_grouped_opcodes(3):
        hunk_lines = []
        old_start = group[0][1] + 1
        new_start = group[0][3] + 1
        old_count = 0
        new_count = 0

        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                for line in old_lines[i1:i2]:
                    hunk_lines.append(" " + line)
                old_count += i2 - i1
                new_count += i2 - i1
            elif tag in ("replace", "delete"):
                for line in old_lines[i1:i2]:
                    hunk_lines.append("-" + line)
                    deletions += 1
                old_count += i2 - i1
                if tag == "replace":
                    for line in new_lines[j1:j2]:
                        hunk_lines.append("+" + line)
                        additions += 1
                    new_count += j2 - j1
            elif tag == "insert":
                for line in new_lines[j1:j2]:
                    hunk_lines.append("+" + line)
                    additions += 1
                new_count += j2 - j1

        hunks.append(DiffHunk(
            old_start=old_start,
            old_count=old_count,
            new_start=new_start,
            new_count=new_count,
            lines=hunk_lines,
        ))

    return PromptDiff(
        prompt_id=prompt_id,
        prompt_name=prompt_name,
        old_version=old_version.version_number,
        new_version=new_version.version_number,
        hunks=hunks,
        additions=additions,
        deletions=deletions,
    )


def format_diff(diff: PromptDiff) -> str:
    """Render a unified diff string."""
    lines = [
        f"--- {diff.prompt_name} (v{diff.old_version})",
        f"+++ {diff.prompt_name} (v{diff.new_version})",
    ]
    for h in diff.hunks:
        lines.append(
            f"@@ -{h.old_start},{h.old_count} +{h.new_start},{h.new_count} @@"
        )
        lines.extend(l.rstrip("\n") for l in h.lines)
    return "\n".join(lines)
