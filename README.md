# AssessFlow V1

## Local tests

Run the completed grading and SQLite database milestones with:

```bash
.venv/bin/python -m unittest omr.test_structured_results omr.test_database
```

The database tests create an isolated temporary SQLite database. They verify
that classrooms, students, assessments, answer keys, grading attempts, and
per-question grading results can be saved and retrieved without changing the
sample scans or the production database location.
