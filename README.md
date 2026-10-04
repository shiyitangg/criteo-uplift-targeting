# Ad Incrementality & Uplift Targeting (Criteo Uplift Dataset)

**Question:** How much does ad targeting actually increase visits and conversions, and can we get most of the benefit by targeting only the users who respond most?

**Answer:** Ad assignment raised conversions by **+0.115 pp** (0.194% → 0.309%, 95% CI [0.109, 0.122]) and site visits by **+1.03 pp**. A two-model uplift model, evaluated on a randomized holdout, shows the incremental effect is concentrated in a minority of users: targeting the top 20% by predicted uplift captured **~74% of the incremental conversions** (~80% of incremental visits) of targeting everyone.

## Data
[Criteo Uplift Prediction Dataset v2.1](https://ailab.criteo.com/criteo-uplift-prediction-dataset/) (Criteo AI Lab): 13,979,592 users from randomized incrementality tests; 85% treatment / 15% control by design. Features `f0`–`f11` are anonymized; outcomes are `visit`, `conversion` (and `exposure`, the user actually saw an ad).
The file is not committed. Download it, save as `data/criteo-uplift-v2.1.csv.gz` (no need to unzip), and confirm it has 13,979,592 rows.

## Method
1. **SQL (DuckDB)** reads the gzipped CSV directly: arm sizes, null checks, outcome rates, covariate balance (`sql/01_criteo_checks.sql`).
2. **Randomization check** – standardized mean difference for all 12 features (all |SMD| < 0.05). Criteo is not 50/50 by design, so balance on covariates is the right check, not a 50/50 SRM test.
3. **Average treatment effect** on the full data with 95% CIs (two-proportion difference).
4. **Heterogeneity** – treatment effect with 95% CIs within value-based quartile buckets of each feature (`sql/02_criteo_hte_template.sql`). Buckets are cut by value so that tied values stay together and results are reproducible.
5. **Uplift model** – two-model (T-learner) approach: separate gradient-boosting classifiers on treated and control users (scikit-learn `HistGradientBoostingClassifier`); uplift score = P(outcome | treated) − P(outcome | control).
6. **Evaluation on a 40% randomized holdout** using the real treatment labels: actual uplift by predicted-uplift decile and the incremental outcomes captured by treating only the top k% of users.

## Results

**Average treatment effect (full data, treatment − control)**

| Outcome | Control | Treated | Difference | 95% CI | Relative lift |
|---|---|---|---|---|---|
| Visit | 3.82% | 4.85% | +1.034 pp | [1.006, 1.063] | +27.1% |
| Conversion | 0.194% | 0.309% | +0.115 pp | [0.109, 0.122] | +59.4% |

Only ~3.6% of treated users were actually exposed to an ad, so these are **intent-to-treat** effects (effect of being assigned to the ad group), not the effect of seeing an ad.

**Targeting policy on the holdout (share of treat-everyone's incremental outcomes captured)**

| Treat only top… | Visit | Conversion |
|---|---|---|
| 10% of users | ~60% | ~58% |
| 20% of users | ~80% | ~74% |
| 30% of users | ~88% | ~78% |
| 50% of users | ~94% | ~82% |

Visit model: 3M-user sample. Conversion model: 6M-user sample (conversion events are rare, ~0.2–0.3%). Top-decile actual uplift: +5.84 pp for visits (CI [5.15, 6.52]) and +0.63 pp for conversions (CI [0.48, 0.78]).

**Heterogeneity:** visit uplift varies from about 0.05 pp to 9.4 pp across feature buckets, with non-overlapping confidence intervals, so treatment effects are genuinely heterogeneous. Several features take few distinct values, leaving some quartile buckets empty; those rows are not interpretable as four levels.

See `reports/qini_visit.png`, `reports/qini_conversion.png`, and the decile tables in `reports/`.

## Limitations
- **Ranking instability for conversions:** the lowest-scored decile shows a significantly positive uplift (+0.16 pp, CI [0.09, 0.23]), higher than middle deciles, so the two-model approach misranks some users at the extremes. Reported as-is; more regularized or direct-uplift methods are a natural next step.
- **Single holdout split.** The "% captured" figures are point estimates from one split, and the denominator uses the holdout's own average effect (slightly different from the full-data effect). Repeating across random seeds would quantify this.
- **No cost or revenue data**, so the results show targeting *efficiency*, not ROI.
- **Intent-to-treat only** (see above). Features are anonymized and randomly projected, so no business interpretation of individual features is attempted.

## Reproduce
```bash
pip install pandas numpy scipy duckdb scikit-learn matplotlib
mkdir -p reports
python src/criteo_step1_sql.py
python src/criteo_step2_uplift.py data/criteo-uplift-v2.1.csv.gz visit 3000000
python src/criteo_step2_uplift.py data/criteo-uplift-v2.1.csv.gz conversion 6000000
```

## Repository layout
```
sql/01_criteo_checks.sql          validation and outcome queries
sql/02_criteo_hte_template.sql    heterogeneity query by feature bucket
src/criteo_common.py              DuckDB loader
src/criteo_step1_sql.py           SQL checks, covariate balance, heterogeneity
src/criteo_step2_uplift.py        ATE, T-learner uplift model, holdout evaluation
reports/                          figures and result tables
```
