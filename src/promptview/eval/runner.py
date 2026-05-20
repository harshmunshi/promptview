"""EvalRunner: runs a prompt version against test cases and stores results."""
import time
from typing import List, Optional

from ..storage.models import TestCase, EvalRun, EvalResult
from .scorer import exact_match, similarity_score, llm_judge


class EvalRunner:
    def __init__(self, repo, llm_client=None, judge_client=None):
        """
        repo: PromptRepository
        llm_client: LLMClient used to run the prompt (required for local eval)
        judge_client: LLMClient used for LLM-as-judge (optional, falls back to llm_client)
        """
        self.repo = repo
        self.llm_client = llm_client
        self.judge_client = judge_client or llm_client

    def run(
        self,
        prompt_id: str,
        version_id: Optional[str],
        test_cases: List[TestCase],
        use_judge: bool = False,
        judge_criteria: Optional[List[str]] = None,
        dataset_path: Optional[str] = None,
    ) -> EvalRun:
        """Run eval and persist results. Returns the completed EvalRun."""
        # Get the prompt version
        if version_id:
            version = self.repo.db.get_version(version_id)
        else:
            versions = self.repo.db.list_versions(prompt_id)
            if not versions:
                raise ValueError(f"No versions found for prompt {prompt_id}")
            version = versions[-1]

        provider = self.llm_client.provider if self.llm_client else None
        model = self.llm_client.model if self.llm_client else None

        run = EvalRun.new(
            prompt_id=prompt_id,
            version_id=version.id,
            source='local',
            dataset_path=dataset_path,
            provider=str(provider) if provider else None,
            model=model,
        )

        results = []
        total_latency = 0.0
        total_cost = 0.0
        passed_count = 0

        for tc in test_cases:
            # Persist test case if not already saved (match by input)
            existing = [t for t in self.repo.db.list_test_cases(prompt_id) if t.input == tc.input]
            if not existing:
                self.repo.db.create_test_case(tc)
                saved_tc = tc
            else:
                saved_tc = existing[0]

            actual_output = ""
            latency_ms = 0.0
            tokens_used = 0
            cost_usd = 0.0

            if self.llm_client:
                t0 = time.monotonic()
                try:
                    actual_output = self.llm_client.complete(
                        system=version.raw_content,
                        user=tc.input,
                    )
                except Exception as e:
                    actual_output = f"[ERROR: {e}]"
                latency_ms = (time.monotonic() - t0) * 1000

            # Score
            passed = False
            sim_score = None
            j_score = None
            j_reasoning = None

            if tc.expected_output:
                passed = exact_match(actual_output, tc.expected_output)
                sim_score = similarity_score(actual_output, tc.expected_output)
                # Treat similarity >= 0.8 as pass if exact match fails
                if not passed and sim_score >= 0.8:
                    passed = True

            if use_judge and self.judge_client and actual_output:
                j_score, j_reasoning = llm_judge(
                    actual=actual_output,
                    criteria=judge_criteria,
                    llm_client=self.judge_client,
                    expected=tc.expected_output,
                )
                # If no expected output, pass based on judge score >= 0.6
                if not tc.expected_output:
                    passed = j_score >= 0.6

            if passed:
                passed_count += 1

            total_latency += latency_ms
            total_cost += cost_usd

            result = EvalResult.new(
                eval_run_id=run.id,
                actual_output=actual_output,
                passed=passed,
                test_case_id=saved_tc.id,
                similarity_score=sim_score,
                judge_score=j_score,
                judge_reasoning=j_reasoning,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
            )
            results.append(result)

        # Update run summary
        n = len(test_cases)
        run.total_cases = n
        run.passed = passed_count
        run.avg_latency_ms = total_latency / n if n > 0 else 0.0
        run.avg_cost_usd = total_cost / n if n > 0 else 0.0

        judge_scores = [r.judge_score for r in results if r.judge_score is not None]
        run.avg_judge_score = sum(judge_scores) / len(judge_scores) if judge_scores else None

        # Persist
        self.repo.db.create_eval_run(run)
        for result in results:
            self.repo.db.create_eval_result(result)

        return run
