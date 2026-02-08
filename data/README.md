# TOEFL Essay Data

This folder holds TOEFL essays and human scores used in experiments.

## File format

- **essays_template.csv** — Template (1 sample row). Copy it to `essays.csv` and fill with your data:  
  `cp data/essays_template.csv data/essays.csv`
- **essays.csv** — Your essay data (target: 30 essays). This file is in `.gitignore`, so it is not pushed to the repo.

## Columns

| Column       | Description                                    | Example |
|--------------|------------------------------------------------|---------|
| essay_id     | Unique essay number (1, 2, 3, ...)            | 1       |
| prompt_text  | Essay question / topic text                    | Do you agree or disagree... |
| essay_text   | Student's essay text                           | I strongly agree that... |
| human_score  | Human rater score (0–5)                        | 4       |

## How to fill

1. Copy the template: `cp data/essays_template.csv data/essays.csv`
2. Open `data/essays.csv` (Excel, Google Sheets, or a text editor).
3. Add one essay per row: `essay_id`, `prompt_text`, `essay_text`, `human_score`.
4. `human_score` must be an integer 0–5 according to the TOEFL Independent Writing rubric.
5. Target total: 30 essays (per experiment plan).

## Notes

- In CSV, multi-line text goes in quotes (`"`); line breaks may appear inside the field.
- `data/*.csv` and `data/*.xlsx` are in `.gitignore`, so your real essay data stays local; only the template/sample is committed.
