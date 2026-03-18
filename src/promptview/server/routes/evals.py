"""API routes for evaluations and test cases."""
from fastapi import APIRouter, HTTPException, Request
from typing import List

from ..schemas import (
    EvalRequest, EvalRunResponse,
    TestCaseCreate, TestCaseResponse,
)
from ...storage.models import TestCase, EvalRun
from ...eval.dataset import build_test_cases, load_jsonl
from ...eval.runner import EvalRunner
from ...llm.client import LLMClient

router = APIRouter()


@router.get("/prompts/{prompt_id}/test-cases", response_model=List[TestCaseResponse])
def list_test_cases(prompt_id: str, request: Request):
    repo = request.app.state.repo
    cases = repo.db.list_test_cases(prompt_id)
    return [TestCaseResponse(
        id=tc.id, prompt_id=tc.prompt_id, input=tc.input,
        expected_output=tc.expected_output, tags=tc.tags, created_at=tc.created_at
    ) for tc in cases]


@router.post("/prompts/{prompt_id}/test-cases", response_model=TestCaseResponse)
def add_test_case(prompt_id: str, body: TestCaseCreate, request: Request):
    repo = request.app.state.repo
    tc = TestCase.new(
        prompt_id=prompt_id,
        input=body.input,
        expected_output=body.expected_output,
        tags=body.tags or []
    )
    repo.db.create_test_case(tc)
    return TestCaseResponse(
        id=tc.id, prompt_id=tc.prompt_id, input=tc.input,
        expected_output=tc.expected_output, tags=tc.tags, created_at=tc.created_at
    )


@router.delete("/prompts/{prompt_id}/test-cases/{tc_id}")
def delete_test_case(prompt_id: str, tc_id: str, request: Request):
    repo = request.app.state.repo
    repo.db.delete_test_case(tc_id)
    return {"status": "deleted"}


@router.get("/prompts/{prompt_id}/evals", response_model=List[EvalRunResponse])
def list_evals(prompt_id: str, request: Request):
    repo = request.app.state.repo
    runs = repo.db.list_eval_runs(prompt_id)
    return [_run_to_response(r) for r in runs]


@router.get("/prompts/{prompt_id}/evals/{run_id}")
def get_eval(prompt_id: str, run_id: str, request: Request):
    repo = request.app.state.repo
    run = repo.db.get_eval_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")
    results = repo.db.list_eval_results(run_id)
    return {
        "run": _run_to_response(run),
        "results": [
            {
                "id": r.id,
                "test_case_id": r.test_case_id,
                "actual_output": r.actual_output,
                "passed": r.passed,
                "similarity_score": r.similarity_score,
                "judge_score": r.judge_score,
                "judge_reasoning": r.judge_reasoning,
                "latency_ms": r.latency_ms,
            }
            for r in results
        ]
    }


@router.post("/prompts/{prompt_id}/eval", response_model=EvalRunResponse)
def run_eval(prompt_id: str, body: EvalRequest, request: Request):
    repo = request.app.state.repo

    # Load test cases
    if body.dataset_path:
        rows = load_jsonl(body.dataset_path)
        cases = build_test_cases(prompt_id, rows)
    elif body.inline_cases:
        cases = [
            TestCase.new(
                prompt_id=prompt_id,
                input=c.get("input", ""),
                expected_output=c.get("expected")
            )
            for c in body.inline_cases
        ]
    else:
        # Use stored test cases
        cases = repo.db.list_test_cases(prompt_id)
        if not cases:
            raise HTTPException(status_code=400, detail="No test cases provided or stored")

    # Build LLM client
    llm_client = None
    if body.provider and body.api_key:
        llm_client = LLMClient(
            provider=body.provider,
            api_key=body.api_key,
            model=body.model or None
        )

    runner = EvalRunner(repo=repo, llm_client=llm_client)
    run = runner.run(
        prompt_id=prompt_id,
        version_id=body.version_id,
        test_cases=cases,
        use_judge=body.use_judge or False,
        judge_criteria=body.judge_criteria,
        dataset_path=body.dataset_path,
    )
    return _run_to_response(run)


def _run_to_response(run: EvalRun) -> EvalRunResponse:
    return EvalRunResponse(
        id=run.id,
        prompt_id=run.prompt_id,
        version_id=run.version_id,
        source=run.source,
        run_at=run.run_at,
        total_cases=run.total_cases,
        passed=run.passed,
        pass_rate=run.pass_rate,
        avg_latency_ms=run.avg_latency_ms,
        avg_cost_usd=run.avg_cost_usd,
        avg_judge_score=run.avg_judge_score,
    )
