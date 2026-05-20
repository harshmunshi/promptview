"""JSONL dataset loading and test case management."""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..storage.models import TestCase


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    """Load a JSONL file. Each line must have at least 'input'. 'expected' is optional."""
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {i}: {e}")
            if 'input' not in row:
                raise ValueError(f"Line {i} missing required 'input' field")
            rows.append(row)
    return rows


def save_jsonl(cases: List[TestCase], path: str) -> None:
    """Save test cases to a JSONL file."""
    with open(path, 'w', encoding='utf-8') as f:
        for tc in cases:
            row: Dict[str, Any] = {'input': tc.input}
            if tc.expected_output:
                row['expected'] = tc.expected_output
            if tc.tags:
                row['tags'] = tc.tags
            f.write(json.dumps(row) + '\n')


def build_test_cases(prompt_id: str, rows: List[Dict[str, Any]]) -> List[TestCase]:
    """Convert raw JSONL rows into TestCase objects."""
    cases = []
    for row in rows:
        tc = TestCase.new(
            prompt_id=prompt_id,
            input=row['input'],
            expected_output=row.get('expected'),
            tags=row.get('tags', [])
        )
        cases.append(tc)
    return cases
