1. **Optimize Mean Calculation**:
   - Replace `statistics.mean(data)` with `sum(data) / len(data)` in performance-critical paths where the exactness of `statistics.mean` is not strictly necessary and the data list is populated.
   - Python's `statistics.mean` is around 30-90x slower than `sum/len` due to internal exact fractional conversions, especially significant on smaller lists.
   - Files to modify:
     - `sre_agent/tools/analysis/trace/statistical_analysis.py`
     - `sre_agent/tools/analysis/trace/filters.py`
     - `sre_agent/tools/analysis/metrics/statistics.py`
     - `sre_agent/tools/clients/trace.py`
     - `sre_agent/tools/synthetic/demo_data_generator.py`

2. **Run tests & verification**:
   - Use `uv run poe lint` to ensure no linting regressions.
   - Run `uv run poe test-all` to run tests and make sure statistical functions still behave correctly. The `pytest.approx` should handle small floating point differences.

3. **Complete pre commit steps**:
   - Call `pre_commit_instructions` and follow its instructions to ensure proper testing, verification, review, and reflection are done.

4. **Submit**:
   - Submit the PR detailing the performance improvement of using `sum/len` over `statistics.mean`.
