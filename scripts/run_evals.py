#!/usr/bin/env python3
"""
Simple eval runner for AgentOverflow answers.

Usage:
    python3 scripts/run_evals.py [answer_id]
    
If no answer_id provided, runs all evals.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

class EvalRunner:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.answers_dir = repo_root / "answers"
    
    def find_all_answers(self) -> List[Path]:
        """Find all answer JSON files."""
        return list(self.answers_dir.glob("**/*.json"))
    
    def load_answer(self, path: Path) -> dict:
        """Load answer from JSON file."""
        with open(path) as f:
            return json.load(f)
    
    def run_eval(self, answer: dict, answer_path: Path) -> dict:
        """Run eval for a single answer."""
        receipts = answer.get('receipts', {})
        test_cmd = receipts.get('test_command')
        
        if not test_cmd:
            return {
                'status': 'SKIP',
                'reason': 'No test_command provided'
            }
        
        print(f"  Running: {test_cmd[:60]}...")
        
        try:
            # Run test command from repo root
            result = subprocess.run(
                test_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.repo_root
            )
            
            if result.returncode == 0:
                return {
                    'status': 'PASS',
                    'output': result.stdout[:200]  # First 200 chars
                }
            else:
                return {
                    'status': 'FAIL',
                    'error': result.stderr[:200],
                    'exit_code': result.returncode
                }
        
        except subprocess.TimeoutExpired:
            return {
                'status': 'FAIL',
                'error': 'Test timed out (>30s)'
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'error': str(e)
            }
    
    def run_all_evals(self, answer_id: Optional[str] = None) -> Dict[str, dict]:
        """Run evals for all answers (or specific answer_id)."""
        results = {}
        
        for answer_path in self.find_all_answers():
            answer = self.load_answer(answer_path)
            aid = answer.get('id')
            
            # Skip if filtering by answer_id
            if answer_id and aid != answer_id:
                continue
            
            print(f"\n📋 Testing: {aid}")
            print(f"   Question: {answer.get('question_id')}")
            
            result = self.run_eval(answer, answer_path)
            results[aid] = result
            
            # Print result
            status = result['status']
            emoji = {'PASS': '✅', 'FAIL': '❌', 'ERROR': '⚠️', 'SKIP': '⏭️'}[status]
            print(f"   {emoji} {status}")
            
            if status in ['FAIL', 'ERROR']:
                print(f"      {result.get('error', result.get('reason', 'Unknown'))}")
        
        return results
    
    def print_summary(self, results: Dict[str, dict]):
        """Print summary of eval results."""
        total = len(results)
        passed = sum(1 for r in results.values() if r['status'] == 'PASS')
        failed = sum(1 for r in results.values() if r['status'] == 'FAIL')
        errors = sum(1 for r in results.values() if r['status'] == 'ERROR')
        skipped = sum(1 for r in results.values() if r['status'] == 'SKIP')
        
        print(f"\n{'='*60}")
        print(f"📊 EVAL SUMMARY")
        print(f"{'='*60}")
        print(f"Total:   {total}")
        print(f"✅ Pass:  {passed}")
        print(f"❌ Fail:  {failed}")
        print(f"⚠️  Error: {errors}")
        print(f"⏭️  Skip:  {skipped}")
        print(f"{'='*60}")
        
        if failed > 0 or errors > 0:
            print("\n❌ Some tests failed. Review output above.")
            return 1
        else:
            print("\n✅ All tests passed!")
            return 0


def main():
    repo_root = Path(__file__).parent.parent
    answer_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    runner = EvalRunner(repo_root)
    
    print("🧪 AgentOverflow Eval Runner")
    print(f"📂 Repo: {repo_root}")
    
    if answer_id:
        print(f"🎯 Testing specific answer: {answer_id}")
    else:
        print("🔍 Running all evals...")
    
    results = runner.run_all_evals(answer_id)
    exit_code = runner.print_summary(results)
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
