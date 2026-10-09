# ADR-003: Pipeline batch manual antes de un scheduler

- **Estado:** aceptado
- **Contexto:** el objetivo inicial es enseñar el ciclo ETL y mantener bajo el costo operativo.
- **Opciones:** ejecución manual CLI, cron, Airflow/Dagster.
- **Decisión:** comenzar con un comando batch explícito y modo offline; evaluar scheduling solo cuando exista una necesidad de frescura y operación.
- **Consecuencias:** menor complejidad y mayor reproducibilidad local; no ofrece orquestación automática todavía.
