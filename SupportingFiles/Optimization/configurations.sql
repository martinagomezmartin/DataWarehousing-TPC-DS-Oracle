ALTER SESSION SET optimizer_mode = ALL_ROWS;
ALTER SESSION SET optimizer_adaptive_plans = TRUE;
ALTER SESSION SET optimizer_adaptive_statistics = FALSE;
ALTER SESSION SET optimizer_dynamic_sampling = 2;
ALTER SESSION SET star_transformation_enabled = FALSE;
ALTER SESSION SET query_rewrite_enabled = TRUE;
ALTER SESSION SET query_rewrite_integrity = ENFORCED;


ALTER SESSION SET optimizer_dynamic_sampling = 2;


ALTER SESSION SET optimizer_dynamic_sampling = 6;


ALTER SESSION SET star_transformation_enabled = TRUE;

--test changes
SELECT 
    name, 
    value, 
    ismodified 
FROM 
    v$parameter 
WHERE 
    name IN (
        'optimizer_mode',
        'optimizer_adaptive_plans',
        'optimizer_adaptive_statistics',
        'optimizer_dynamic_sampling',
        'star_transformation_enabled',
        'query_rewrite_enabled',
        'query_rewrite_integrity'
    )
ORDER BY 
    name;

