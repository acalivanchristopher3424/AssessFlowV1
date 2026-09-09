# AssessFlow V1

## Local tests

Run the completed grading and SQLite database milestones with:

```bash
.venv/bin/python -m unittest omr.test_structured_results omr.test_database omr.test_sheet_layout
```

The database tests create an isolated temporary SQLite database. They verify
that classrooms, students, assessments, answer keys, grading attempts, and
per-question grading results can be saved and retrieved without changing the
production database location. The sheet-layout test generates a 50-question,
A–L answer sheet and checks alignment plus single, blank, and multiple marks.
