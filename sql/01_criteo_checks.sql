-- Table: criteo (f0..f11, treatment, conversion, visit, exposure). DuckDB / SQLite compatible.

-- Q1. Arm sizes and shares (Criteo is deliberately NOT 50/50)
SELECT treatment,
       COUNT(*) AS n_users,
       ROUND(1.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 4) AS share
FROM criteo
GROUP BY treatment
ORDER BY treatment;

-- Q2. Missing values in outcomes / assignment
SELECT SUM(CASE WHEN treatment IS NULL THEN 1 ELSE 0 END)  AS null_treatment,
       SUM(CASE WHEN conversion IS NULL THEN 1 ELSE 0 END) AS null_conversion,
       SUM(CASE WHEN visit IS NULL THEN 1 ELSE 0 END)      AS null_visit
FROM criteo;

-- Q3. Outcome rates by arm
SELECT treatment,
       COUNT(*)                     AS n,
       SUM(visit)                   AS visits,
       ROUND(AVG(visit), 5)         AS visit_rate,
       SUM(conversion)              AS conversions,
       ROUND(AVG(conversion), 6)    AS conversion_rate,
       ROUND(AVG(exposure), 5)      AS exposure_rate
FROM criteo
GROUP BY treatment
ORDER BY treatment;

-- Q4. Covariate balance: means of a few features by arm (randomization check)
SELECT treatment,
       ROUND(AVG(f0), 4) AS f0_mean, ROUND(AVG(f1), 4) AS f1_mean,
       ROUND(AVG(f2), 4) AS f2_mean, ROUND(AVG(f3), 4) AS f3_mean
FROM criteo
GROUP BY treatment
ORDER BY treatment;
