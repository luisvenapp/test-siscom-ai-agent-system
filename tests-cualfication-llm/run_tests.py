#!/usr/bin/env python3
import os
import sys
import argparse
from src.core.utils import read_json, ensure_dir, expand_env
from src.core.orchestrator import Orchestrator
from src.reporting.aggregator import aggregate_runs
from src.core.scenario_loader import load_scenarios
from src.core.validator import validate_config, validate_scenarios
from src.reporting.exporters import export_json, export_markdown, export_csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser(description="Run LLM qualification tests")
    parser.add_argument("--config", dest="config_path", default=None, help="Ruta a config.json (opcional)")
    args = parser.parse_args()

    config_path = args.config_path or os.path.join(BASE_DIR, 'config', 'config.json')
    if not os.path.exists(config_path):
        print(f"No se encontró config en {config_path}")
        sys.exit(1)

    config = read_json(config_path)
    config = expand_env(config)

    # Validaciones previas
    cfg_errors = validate_config(config)
    if cfg_errors:
        print("Errores de configuración:")
        for e in cfg_errors:
            print(" -", e)
        sys.exit(2)

    scenarios = load_scenarios(os.path.join(BASE_DIR, config.get("scenarios_dir", "scenarios")))
    scn_errors = validate_scenarios(scenarios)
    if scn_errors:
        print("Errores en escenarios:")
        for e in scn_errors:
            print(" -", e)
        sys.exit(3)

    orch = Orchestrator(config, base_dir=BASE_DIR)
    result = orch.run()

    # Agregación
    summary = aggregate_runs(result["records"])

    reports_dir = os.path.join(BASE_DIR, config.get("reports_dir", "reports"))
    ensure_dir(reports_dir)

    json_path = os.path.join(reports_dir, f"summary__{result['timestamp']}.json")
    md_path = os.path.join(reports_dir, f"summary__{result['timestamp']}.md")
    csv_path = os.path.join(reports_dir, f"summary__{result['timestamp']}.csv")

    export_json(json_path, summary)
    export_markdown(md_path, summary)
    export_csv(csv_path, summary)

    print("Pruebas completadas.")
    print(f"Resumen JSON: {json_path}")
    print(f"Resumen MD: {md_path}")
    print(f"Resumen CSV: {csv_path}")


if __name__ == '__main__':
    main()
