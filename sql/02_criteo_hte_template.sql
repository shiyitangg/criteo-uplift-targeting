-- Heterogeneous effect by value-based quartile of one feature.
-- {feat} and cut points {q1},{q2},{q3} are filled in by Python.
-- Value-based buckets (not NTILE) so tied values always land in the same bucket -> reproducible.
SELECT CASE WHEN {feat} <= {q1} THEN 1
            WHEN {feat} <= {q2} THEN 2
            WHEN {feat} <= {q3} THEN 3
            ELSE 4 END           AS bucket,
       treatment,
       COUNT(*)                  AS n,
       AVG(visit)                AS visit_rate,
       AVG(conversion)           AS conversion_rate,
       SUM(visit)                AS visit_sum,
       SUM(conversion)           AS conv_sum
FROM criteo
GROUP BY bucket, treatment
ORDER BY bucket, treatment;
