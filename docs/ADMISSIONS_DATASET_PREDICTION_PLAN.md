# Romanian Admissions Dataset and Prediction Plan

> Scope honesty: this is a parked future-work plan, not a completed dataset. The
> current ApprenticeOps run should finish first, then the resulting work should be
> shown for validation. After that validation, this project becomes the next ask:
> collect the historical Romanian admissions data, publish it in a reusable form,
> and only then improve the prediction algorithm.

## 1. Goal

Build a public, provenance-rich dataset for Romanian `Evaluare Nationala` and
high-school admission (`admitere` / computerized allocation) over the longest
useful historical window we can verify, with a target of **at least the last seven
years**.

The immediate outcome is **data we trust**, not a model. The later outcome is a
better admission-cutoff prediction system that can reason about cohort size,
county/city effects, school-level patterns, score distributions, specialization
capacity, and admission pressure.

We should not claim to measure exam difficulty directly. A more defensible claim
is that we can infer **difficulty proxies** from distribution shifts: percentile
movement, mean/median shifts, grade-density changes, county-level movement, and
how those shifts propagate into the lowest admitted average for each high school
and specialization.

## 2. Data We Need

### 2.1 Raw source captures

For every source, preserve the original artifact before cleaning:

- source URL;
- scrape/download timestamp;
- year;
- exam/admission type;
- county, if the source is county-scoped;
- original file or HTML snapshot;
- parser version;
- source schema notes;
- license / reuse note, when available.

Raw data should be append-only. If a parser is wrong, fix the parser and regenerate
the normalized data; do not silently edit the raw capture.

### 2.2 Evaluare Nationala data

Target fields, subject to what each year exposes:

- year;
- candidate rank / `clasament` position;
- county;
- locality / city, if present;
- school / `scoala generala`, if present;
- Romanian grade;
- Mathematics grade;
- mother-tongue grade, where applicable;
- final evaluation average;
- special statuses needed to interpret rows, where present.

This table gives the distribution side of the problem: how strong the cohort was,
how scores are distributed, and how each county/city/school moved relative to
other years.

### 2.3 Admission / repartition data

Target fields:

- year;
- candidate admission rank;
- admission average;
- evaluation average, when exposed separately;
- graduation average, when exposed separately for older rules;
- county;
- candidate locality / school, if present;
- admitted high school;
- admitted specialization;
- profile / track;
- language / bilingual flags, where applicable;
- option/order information, if public and legally reusable;
- rejected / unallocated markers, if exposed.

This table gives the allocation side: which average got into which high school and
specialization, and what the **lowest admitted average** was for each target.

### 2.4 High school and specialization metadata

Target fields:

- high school identifier;
- high school name;
- county;
- locality / city;
- specialization identifier;
- specialization name;
- profile / track;
- number of seats;
- language / intensive-language flags;
- last admitted average by year;
- special constraints, where public.

The metadata matters because prediction is not only about grades. Capacity,
location, profile, language, and historical demand all influence cutoffs.

## 3. Normalized Dataset Shape

The normalized release should use stable tables rather than one giant CSV:

| Table | Purpose |
|---|---|
| `evaluare_results` | Candidate-level evaluation results and ranking distribution. |
| `admission_results` | Candidate-level admission / allocation results. |
| `institutions` | General schools and high schools, with stable names and locations. |
| `specializations` | High-school specialization metadata and seats. |
| `admission_cutoffs` | Derived lowest admitted average per high school / specialization / year. |
| `county_year_stats` | Cohort counts and distribution summaries by county and year. |
| `school_year_stats` | School-level aggregates where source data allows it. |
| `source_audit` | Provenance, hashes, parser versions, row counts, and validation status. |

Candidate identifiers must be handled carefully. If a source exposes personally
identifying data, the public dataset should either exclude it or replace it with a
stable non-reversible row key scoped to the source/year. The dataset should be
useful for analysis without publishing personal data.

## 4. Validation Gates

Data quality is the central risk. Each year/source should pass these checks before
it is used for prediction:

1. **Row-count check:** parsed row counts match official totals or the visible
   source totals.
2. **Score-domain check:** grades are within valid Romanian grading ranges and
   averages are reproducible from component grades where possible.
3. **Rank check:** ranks are monotonic and duplicates are explained by ties or
   source-specific rules.
4. **Cutoff reproducibility:** `admission_cutoffs` can be regenerated from
   `admission_results` and matches the public last-admitted averages.
5. **Capacity check:** admitted counts by high school/specialization do not exceed
   published seats unless the source documents supplements or special cases.
6. **Missingness report:** each table reports missing fields by year and county.
7. **Schema drift report:** parser differences between years are documented, not
   hidden.
8. **Source audit hash:** every normalized row can be traced back to a raw source
   artifact and parser version.

Rows that fail validation should be retained in raw form but excluded from the
analysis-ready release until the failure is explained.

## 5. Analysis Questions

Once the dataset is validated, the first analysis should answer descriptive
questions before prediction:

- How did national and county-level grade distributions move year over year?
- How stable are high-school/specialization cutoffs after controlling for cohort
  size and score distribution?
- Which counties/cities have the largest cutoff volatility?
- How much of a specialization cutoff is explained by previous-year cutoff,
  available seats, county score distribution, and candidate count?
- Can school-level averages predict pressure toward specific high schools or
  profiles?
- Which features are robust across years, and which collapse under backtesting?

The prediction target should be framed as an interval, not only a point estimate:

$$
\hat{c}_{y,h,s} \pm \epsilon
$$

where $\hat{c}_{y,h,s}$ is the predicted cutoff for year $y$, high school $h$, and
specialization $s$, and $\epsilon$ is the uncertainty interval estimated from
historical backtests.

## 6. Prediction Backtesting Plan

Use rolling-year backtests instead of a single train/test split:

1. Train on years up to $Y-1$.
2. Predict cutoffs for year $Y$.
3. Compare predicted vs actual lowest admitted averages.
4. Report error by county, city, high school, specialization, profile, and cutoff
   bracket.
5. Repeat for every year with sufficient history.

Baseline models should be deliberately simple:

- previous-year cutoff;
- three-year moving average;
- previous cutoff plus cohort-size adjustment;
- previous cutoff plus county distribution shift;
- regularized regression / gradient-boosted trees only after the simple baselines
  are beaten on backtests.

If a complex model cannot beat a transparent baseline, that is a result, not a
failure.

## 7. Publication Plan

The intended public outputs are:

- raw-source manifest, without republishing source artifacts if redistribution is
  not allowed;
- normalized CSV/Parquet tables;
- data dictionary;
- validation report;
- known limitations;
- example notebooks;
- release notes by dataset version.

Candidate publication targets:

- Kaggle dataset;
- Hugging Face dataset;
- GitHub release artifacts for versioned provenance.

Before publishing, we need a rights review: public availability does not
automatically mean unrestricted redistribution. If redistribution is unclear, we
can publish parsers, manifests, hashes, and normalized derived aggregates while
documenting how users can reproduce the dataset from official sources.

## 8. Implementation Phases

| Phase | Name | Output | Gate |
|---|---|---|---|
| 0 | Current-run validation | ApprenticeOps work shown to the user and accepted. | User validates the current result. |
| 1 | Source inventory | List of official/public sources by year and data type. | At least seven target years mapped or gaps documented. |
| 2 | One-year pilot | Raw + normalized data for one recent year. | Row counts, cutoffs, and source hashes validate. |
| 3 | Seven-year acquisition | Raw + normalized data for the target historical window. | Validation report passes or failures are explained. |
| 4 | Public dataset package | CSV/Parquet, dictionary, provenance, release notes. | Rights review and reproducibility check pass. |
| 5 | Descriptive analysis | Distribution and cutoff-correlation notebooks. | Results reproduce from published tables. |
| 6 | Prediction algorithms | Backtested baselines and improved models. | Rolling-year backtest beats or explains baseline performance. |

## 9. Immediate Next Step After Current Validation

Start with **Phase 1: Source inventory**. Do not write the scraper first. The first
deliverable should be a table of years, source URLs, data types, access methods,
expected row counts, rights notes, and parser risk. That inventory decides whether
the seven-year target is realistic and which years need special handling.
