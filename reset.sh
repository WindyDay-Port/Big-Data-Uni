#!/bin/bash
echo "Resetting pipeline..."
rm -f steam_analytics.duckdb
rm -rf data/processed/
rm -rf target/ dbt_packages/
mkdir -p data/processed
echo "Reset complete. Ready for execution"