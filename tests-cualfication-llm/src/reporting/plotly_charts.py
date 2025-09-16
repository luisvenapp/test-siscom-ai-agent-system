from typing import Dict, Any, List, Optional
import os
import json


def export_plotly_dashboard_html(path: str, summary: Dict[str, Any], title: str = "LLM Benchmark Dashboard", raw_records: Optional[List[Dict[str, Any]]] = None) -> None:
    """
    Generates a self-contained HTML dashboard with Plotly charts using a CDN (no Python dependency at runtime).
    Charts included (by agent):
      - Score average
      - Latency (avg with p50/p95 lines)
      - Throughput (req/s)
      - OK rate (%)
      - Grades (stacked counts)
      - Tokens/Chars averages (per agent)
      - Latency boxplot per agent (requires raw_records)
      - Per-scenario score by agent (computed from summary.by_agent_case)
    """
    by_agent = summary.get("by_agent", {})
    agents = list(by_agent.keys())

    def get_metric(agent: str, path_list, default=0.0):
        cur = by_agent.get(agent, {})
        for p in path_list:
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                return default
        return cur if cur is not None else default

    # Build series arrays
    score_avg = [float(get_metric(a, ["score", "avg"], 0.0)) for a in agents]
    lat_avg = [float(get_metric(a, ["latency", "avg"], 0.0)) for a in agents]
    lat_p50 = [float(get_metric(a, ["latency", "p50"], 0.0)) for a in agents]
    lat_p95 = [float(get_metric(a, ["latency", "p95"], 0.0)) for a in agents]
    throughput = [float(get_metric(a, ["throughput_rps"], 0.0)) for a in agents]
    ok_rate = [float(get_metric(a, ["ok_rate"], 0.0)) * 100.0 for a in agents]
    g_exc = [int(get_metric(a, ["grades", "excelente"], 0)) for a in agents]
    g_apr = [int(get_metric(a, ["grades", "aprobado"], 0)) for a in agents]
    g_ins = [int(get_metric(a, ["grades", "insuficiente"], 0)) for a in agents]
    tokens_avg = [float(get_metric(a, ["response", "tokens_avg"], 0.0)) for a in agents]
    chars_avg = [float(get_metric(a, ["response", "chars_avg"], 0.0)) for a in agents]

    summary_json = json.dumps(summary, ensure_ascii=False)
    raw_json = json.dumps(raw_records or [], ensure_ascii=False)

    html = f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
  <script src=\"https://cdn.plot.ly/plotly-2.32.0.min.js\"></script>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    .row {{ display: flex; flex-wrap: wrap; gap: 24px; }}
    .card {{ flex: 1 1 480px; border: 1px solid #eee; border-radius: 8px; padding: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }}
    h2 {{ margin-top: 0; }}
    .meta {{ color: #666; font-size: 0.9em; margin-bottom: 12px; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <div class=\"meta\">Auto-generated from summary JSON. Charts by agent.</div>

  <div class=\"row\">
    <div class=\"card\"><h2>Score (avg)</h2><div id=\"score_avg\"></div></div>
    <div class=\"card\"><h2>Latency (avg, p50, p95) [s]</h2><div id=\"latency\"></div></div>
  </div>
  <div class=\"row\">
    <div class=\"card\"><h2>Throughput (req/s)</h2><div id=\"throughput\"></div></div>
    <div class=\"card\"><h2>OK Rate (%)</h2><div id=\"ok_rate\"></div></div>
  </div>
  <div class=\"row\">
    <div class=\"card\"><h2>Grades (counts)</h2><div id=\"grades\"></div></div>
    <div class=\"card\"><h2>Response size (tokens / chars)</h2><div id=\"resp_size\"></div></div>
  </div>

  <div class=\"row\">
    <div class=\"card\"><h2>Latency Boxplot (per agent)</h2><div id=\"lat_box\"></div></div>
  </div>

  <div class=\"row\">
    <div class=\"card\" style=\"flex: 1 1 100%\"><h2>Per-Scenario Score by Agent</h2><div id=\"scenario_scores\"></div></div>
  </div>

  <script>
    const SUMMARY = {summary_json};
    const RAW = {raw_json};
    const agents = {json.dumps(agents)};

    const scoreAvg = {json.dumps(score_avg)};
    const latAvg = {json.dumps(lat_avg)};
    const latP50 = {json.dumps(lat_p50)};
    const latP95 = {json.dumps(lat_p95)};
    const throughput = {json.dumps(throughput)};
    const okRate = {json.dumps(ok_rate)};
    const gExc = {json.dumps(g_exc)};
    const gApr = {json.dumps(g_apr)};
    const gIns = {json.dumps(g_ins)};
    const tokensAvg = {json.dumps(tokens_avg)};
    const charsAvg = {json.dumps(chars_avg)};

    // Score avg bar
    Plotly.newPlot('score_avg', [
      {{ x: agents, y: scoreAvg, type: 'bar', name: 'score_avg', marker: {{color: '#2a9d8f'}} }}
    ], {{
      margin: {{t: 16}}, yaxis: {{range: [0, 1], title: 'score'}}, xaxis: {{automargin: true}}
    }}, {{responsive: true}});

    // Latency combo: bars avg + lines p50/p95
    Plotly.newPlot('latency', [
      {{ x: agents, y: latAvg, type: 'bar', name: 'avg', marker: {{color: '#457b9d'}} }},
      {{ x: agents, y: latP50, type: 'scatter', mode: 'lines+markers', name: 'p50', line: {{color: '#e76f51'}} }},
      {{ x: agents, y: latP95, type: 'scatter', mode: 'lines+markers', name: 'p95', line: {{color: '#f4a261'}} }}
    ], {{
      margin: {{t: 16}}, yaxis: {{title: 'seconds'}}, xaxis: {{automargin: true}}, barmode: 'group'
    }}, {{responsive: true}});

    // Throughput bar
    Plotly.newPlot('throughput', [
      {{ x: agents, y: throughput, type: 'bar', name: 'req/s', marker: {{color: '#264653'}} }}
    ], {{
      margin: {{t: 16}}, yaxis: {{title: 'req/s'}}, xaxis: {{automargin: true}}
    }}, {{responsive: true}});

    // OK rate bar
    Plotly.newPlot('ok_rate', [
      {{ x: agents, y: okRate, type: 'bar', name: 'ok %', marker: {{color: '#8ab17d'}} }}
    ], {{
      margin: {{t: 16}}, yaxis: {{range: [0, 100], title: '%'}}, xaxis: {{automargin: true}}
    }}, {{responsive: true}});

    // Grades stacked
    Plotly.newPlot('grades', [
      {{ x: agents, y: gExc, type: 'bar', name: 'excelente', marker: {{color: '#2a9d8f'}} }},
      {{ x: agents, y: gApr, type: 'bar', name: 'aprobado', marker: {{color: '#e9c46a'}} }},
      {{ x: agents, y: gIns, type: 'bar', name: 'insuficiente', marker: {{color: '#e76f51'}} }}
    ], {{
      margin: {{t: 16}}, barmode: 'stack', yaxis: {{title: 'count'}}, xaxis: {{automargin: true}}
    }}, {{responsive: true}});

    // Response size tokens/chars (grouped bars)
    Plotly.newPlot('resp_size', [
      {{ x: agents, y: tokensAvg, type: 'bar', name: 'tokens_avg', marker: {{color: '#1d3557'}} }},
      {{ x: agents, y: charsAvg, type: 'bar', name: 'chars_avg', marker: {{color: '#a8dadc'}} }}
    ], {{
      margin: {{t: 16}}, barmode: 'group', yaxis: {{title: 'avg'}}, xaxis: {{automargin: true}}
    }}, {{responsive: true}});

    // Latency boxplot per agent (needs RAW)
    if (RAW && RAW.length > 0) {{
      const traces = [];
      for (const a of agents) {{
        const arr = RAW.filter(r => r.agent === a && typeof r.elapsed_s === 'number' && r.elapsed_s >= 0).map(r => r.elapsed_s);
        traces.push({{ y: arr, type: 'box', name: a, boxmean: true }});
      }}
      Plotly.newPlot('lat_box', traces, {{ margin: {{t: 16}}, yaxis: {{title: 'seconds'}} }}, {{responsive: true}});
    }} else {{
      document.getElementById('lat_box').innerHTML = '<em>Boxplot unavailable (raw records not provided)</em>';
    }}

    // Per-scenario score by agent (from SUMMARY.by_agent_case)
    (function() {{
      const byAgentCase = SUMMARY.by_agent_case || {{}};
      const scenarioAgentScores = {{}}; // scenario -> agent -> [scores]
      for (const key of Object.keys(byAgentCase)) {{
        // key format: "agent::scenario::case"
        const parts = key.split('::');
        if (parts.length < 3) continue;
        const agent = parts[0];
        const scenario = parts[1];
        const data = byAgentCase[key];
        const scoreAvg = (data && data.score && typeof data.score.avg === 'number') ? data.score.avg : 0;
        if (!scenarioAgentScores[scenario]) scenarioAgentScores[scenario] = {{}};
        if (!scenarioAgentScores[scenario][agent]) scenarioAgentScores[scenario][agent] = [];
        scenarioAgentScores[scenario][agent].push(scoreAvg);
      }}
      // For each scenario, average per agent and create a trace series
      const scenNames = Object.keys(scenarioAgentScores).sort();
      const container = document.getElementById('scenario_scores');
      if (scenNames.length === 0) {{
        container.innerHTML = '<em>No scenario-level data available</em>';
        return;
      }}
      // Build a grouped bar chart: x=agents, a bar series per scenario
      const traces = [];
      for (const scen of scenNames) {{
        const scores = agents.map(a => {{
          const arr = (scenarioAgentScores[scen][a] || []);
          if (arr.length === 0) return 0;
          return arr.reduce((x,y)=>x+y,0)/arr.length;
        }});
        traces.push({{ x: agents, y: scores, type: 'bar', name: scen }});
      }}
      Plotly.newPlot('scenario_scores', traces, {{ margin: {{t: 16}}, barmode: 'group', yaxis: {{range: [0,1], title: 'score_avg'}}, xaxis: {{automargin: true}} }}, {{responsive: true}});
    }})();
  </script>
</body>
</html>
"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
