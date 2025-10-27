from typing import Dict, Any, List, Optional
import os
import json
from string import Template


def export_plotly_dashboard_html(path: str, summary: Dict[str, Any], title: str = "LLM Benchmark Dashboard", raw_records: Optional[List[Dict[str, Any]]] = None) -> None:
    """
    Generates a self-contained HTML dashboard with Plotly charts using a CDN (no Python dependency at runtime).
    Charts included (by agent):
      - Score average (with std as error bars)
      - Latency (avg with p50/p95 lines)
      - Throughput (req/s)
      - OK rate (%)
      - Grades (stacked counts)
      - Tokens/Chars averages (per agent)
      - Latency boxplot per agent (requires raw_records)
      - Per-scenario score by agent (computed from summary.by_agent_case)
      - Model selection (best model) section with composite ranking
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
    score_std = [float(get_metric(a, ["score", "std"], 0.0)) for a in agents]
    lat_avg = [float(get_metric(a, ["latency", "avg"], 0.0)) for a in agents]
    lat_p50 = [float(get_metric(a, ["latency", "p50"], 0.0)) for a in agents]
    lat_p95 = [float(get_metric(a, ["latency", "p95"], 0.0)) for a in agents]
    lat_std = [float(get_metric(a, ["latency", "std"], 0.0)) for a in agents]
    throughput = [float(get_metric(a, ["throughput_rps"], 0.0)) for a in agents]
    ok_rate = [float(get_metric(a, ["ok_rate"], 0.0)) * 100.0 for a in agents]
    g_exc = [int(get_metric(a, ["grades", "excelente"], 0)) for a in agents]
    g_apr = [int(get_metric(a, ["grades", "aprobado"], 0)) for a in agents]
    g_ins = [int(get_metric(a, ["grades", "insuficiente"], 0)) for a in agents]
    tokens_avg = [float(get_metric(a, ["response", "tokens_avg"], 0.0)) for a in agents]
    chars_avg = [float(get_metric(a, ["response", "chars_avg"], 0.0)) for a in agents]
    cost_avg = [float(get_metric(a, ["cost", "avg"], 0.0)) for a in agents]

    summary_json = json.dumps(summary, ensure_ascii=False)
    raw_json = json.dumps(raw_records or [], ensure_ascii=False)

    template = Template(
        """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>$TITLE</title>
  <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; }
    .row { display: flex; flex-wrap: wrap; gap: 24px; }
    .card { flex: 1 1 480px; border: 1px solid #eee; border-radius: 8px; padding: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
    h2 { margin-top: 0; }
    .meta { color: #666; font-size: 0.9em; margin-bottom: 12px; }
    .winner { background: #f0fff4; border-color: #34d399; }
    .monospace { font-family: Menlo, Consolas, monospace; }
    table { border: 1px solid #eee; }
    th, td { border-bottom: 1px solid #eee; padding: 4px 6px; text-align: left; }
  </style>
</head>
<body>
  <h1>$TITLE</h1>
  <div class="meta">Auto-generated from summary JSON. Charts by agent. Includes model selection.</div>

  <div class="row">
    <div class="card winner"><h2>Best Model (Composite)</h2><div id="winner"></div></div>
  </div>

  <div class="row">
    <div class="card"><h2>Score (avg)</h2><div id="score_avg"></div></div>
    <div class="card"><h2>Latency (avg, p50, p95) [s]</h2><div id="latency"></div></div>
  </div>
  <div class="row">
    <div class="card"><h2>Throughput (req/s)</h2><div id="throughput"></div></div>
    <div class="card"><h2>OK Rate (%)</h2><div id="ok_rate"></div></div>
  </div>
  <div class="row">
    <div class="card"><h2>Grades (counts)</h2><div id="grades"></div></div>
    <div class="card"><h2>Response size (tokens / chars)</h2><div id="resp_size"></div></div>
  </div>

  <div class="row">
    <div class="card"><h2>Latency Boxplot (per agent)</h2><div id="lat_box"></div></div>
  </div>

  <div class="row">
    <div class="card" style="flex: 1 1 100%"><h2>Per-Scenario Score by Agent</h2><div id="scenario_scores"></div></div>
  </div>

  <script>
    const SUMMARY = $SUMMARY_JSON;
    const RAW = $RAW_JSON;
    const agents = $AGENTS;

    const scoreAvg = $SCORE_AVG;
    const scoreStd = $SCORE_STD;
    const latAvg = $LAT_AVG;
    const latP50 = $LAT_P50;
    const latP95 = $LAT_P95;
    const latStd = $LAT_STD;
    const throughput = $THROUGHPUT;
    const okRate = $OK_RATE;
    const gExc = $G_EXC;
    const gApr = $G_APR;
    const gIns = $G_INS;
    const tokensAvg = $TOKENS_AVG;
    const charsAvg = $CHARS_AVG;
    const costAvg = $COST_AVG;

    // Try to compute composite decision client-side if server didn't include it
    function computeComposite(summary) {
      const byAgent = summary.by_agent || {};
      const agentList = Object.keys(byAgent);
      if (agentList.length === 0) return null;
      // default weights (must match python default)
      const weights = {score_avg:0.4, ok_rate:0.2, latency_avg:0.15, latency_p95:0.10, throughput_rps:0.10, score_std:0.03, latency_std:0.02, tokens_avg:0.0};
      // collect arrays
      function m(agent, path, defv){
        let cur = byAgent[agent];
        for (const p of path) { cur = (cur||{})[p]; }
        return (typeof cur === 'number') ? cur : defv;
      }
      const raw = {
        score_avg: agentList.map(a=>m(a,['score','avg'],0)),
        ok_rate: agentList.map(a=>m(a,['ok_rate'],0)),
        latency_avg: agentList.map(a=>m(a,['latency','avg'],0)),
        latency_p95: agentList.map(a=>m(a,['latency','p95'],0)),
        throughput_rps: agentList.map(a=>m(a,['throughput_rps'],0)),
        score_std: agentList.map(a=>m(a,['score','std'],0)),
        latency_std: agentList.map(a=>m(a,['latency','std'],0)),
        tokens_avg: agentList.map(a=>m(a,['response','tokens_avg'],0)),
      };
      function minMaxNorm(arr, invert){
        if (arr.length === 0) return [];
        const mn = Math.min(...arr), mx = Math.max(...arr);
        const range = (mx - mn);
        const norm = arr.map(v => range === 0 ? 1.0 : (v - mn) / (range));
        const n2 = invert ? norm.map(x=>1-x) : norm;
        return n2.map(x=>Math.max(0, Math.min(1, x)));
      }
      const norm = {
        score_avg: minMaxNorm(raw.score_avg, false),
        ok_rate: minMaxNorm(raw.ok_rate, false),
        latency_avg: minMaxNorm(raw.latency_avg, true),
        latency_p95: minMaxNorm(raw.latency_p95, true),
        throughput_rps: minMaxNorm(raw.throughput_rps, false),
        score_std: minMaxNorm(raw.score_std, true),
        latency_std: minMaxNorm(raw.latency_std, true),
        tokens_avg: minMaxNorm(raw.tokens_avg, true)
      };
      const perAgent = {};
      agentList.forEach((a, idx)=>{
        let comp = 0; const contribs = {};
        Object.entries(weights).forEach(([m,w])=>{ const v = norm[m][idx] || 0; comp += w*v; contribs[m]=w*v; });
        perAgent[a] = {composite: comp, contribs};
      });
      const ranking = agentList.map(a=>({agent:a, score: perAgent[a].composite})).sort((x,y)=>y.score-x.score);
      const winner = ranking.length ? ranking[0].agent : null;
      return {weights, per_agent: perAgent, ranking, winner};
    }

    const decision = SUMMARY.model_selection || computeComposite(SUMMARY) || {winner: null};

    // Winner card content
    (function renderWinner(){
      const el = document.getElementById('winner');
      if (!decision || !decision.winner) { el.innerHTML = '<em>No decision available</em>'; return; }
      const w = decision.winner;
      const rank = decision.ranking || [];
      const rows = rank.map((r,i)=>'<tr><td>'+(i+1)+'</td><td>'+r.agent+'</td><td class="monospace">'+((r.score||0).toFixed(3))+'</td></tr>').join('');
      const expl = decision.explanation || '';
      el.innerHTML =
        '<div><strong>Winner:</strong> ' + w + '</div>' +
        '<div style="margin:6px 0 8px 0">' + expl + '</div>' +
        '<div><strong>Ranking</strong></div>' +
        '<table style="width:100%; border-collapse:collapse">' +
          '<thead><tr><th>#</th><th>Agent</th><th>Composite</th></tr></thead>' +
          '<tbody>' + rows + '</tbody>' +
        '</table>';
    })();


    // Score avg bar
    Plotly.newPlot('score_avg', [
      { x: agents, y: scoreAvg, type: 'bar', name: 'score_avg', marker: {color: '#2a9d8f'} , error_y: {type:'data', array: scoreStd, visible: true}}
    ], {
      margin: {t: 16}, yaxis: {range: [0, 1], title: 'score'}, xaxis: {automargin: true}
    }, {responsive: true});

    // Latency combo: bars avg + lines p50/p95
    Plotly.newPlot('latency', [
      { x: agents, y: latAvg, type: 'bar', name: 'avg', marker: {color: '#457b9d'} },
      { x: agents, y: latP50, type: 'scatter', mode: 'lines+markers', name: 'p50', line: {color: '#e76f51'} },
      { x: agents, y: latP95, type: 'scatter', mode: 'lines+markers', name: 'p95', line: {color: '#f4a261'} }
    ], {
      margin: {t: 16}, yaxis: {title: 'seconds'}, xaxis: {automargin: true}, barmode: 'group'
    }, {responsive: true});

    // Throughput bar
    Plotly.newPlot('throughput', [
      { x: agents, y: throughput, type: 'bar', name: 'req/s', marker: {color: '#264653'} }
    ], {
      margin: {t: 16}, yaxis: {title: 'req/s'}, xaxis: {automargin: true}
    }, {responsive: true});

    // OK rate bar
    Plotly.newPlot('ok_rate', [
      { x: agents, y: okRate, type: 'bar', name: 'ok %', marker: {color: '#8ab17d'} }
    ], {
      margin: {t: 16}, yaxis: {range: [0, 100], title: '%'}, xaxis: {automargin: true}
    }, {responsive: true});

    // Grades stacked
    Plotly.newPlot('grades', [
      { x: agents, y: gExc, type: 'bar', name: 'excelente', marker: {color: '#2a9d8f'} },
      { x: agents, y: gApr, type: 'bar', name: 'aprobado', marker: {color: '#e9c46a'} },
      { x: agents, y: gIns, type: 'bar', name: 'insuficiente', marker: {color: '#e76f51'} }
    ], {
      margin: {t: 16}, barmode: 'stack', yaxis: {title: 'count'}, xaxis: {automargin: true}
    }, {responsive: true});

    // Response size tokens/chars (grouped bars)
    Plotly.newPlot('resp_size', [
      { x: agents, y: tokensAvg, type: 'bar', name: 'tokens_avg', marker: {color: '#1d3557'} },
      { x: agents, y: charsAvg, type: 'bar', name: 'chars_avg', marker: {color: '#a8dadc'} }
    ], {
      margin: {t: 16}, barmode: 'group', yaxis: {title: 'avg'}, xaxis: {automargin: true}
    }, {responsive: true});

    // Latency boxplot per agent (needs RAW)
    if (RAW && RAW.length > 0) {
      const traces = [];
      for (const a of agents) {
        const arr = RAW.filter(r => r.agent === a && typeof r.elapsed_s === 'number' && r.elapsed_s >= 0).map(r => r.elapsed_s);
        traces.push({ y: arr, type: 'box', name: a, boxmean: true });
      }
      Plotly.newPlot('lat_box', traces, { margin: {t: 16}, yaxis: {title: 'seconds'} }, {responsive: true});
    } else {
      document.getElementById('lat_box').innerHTML = '<em>Boxplot unavailable (raw records not provided)</em>';
    }

    // Per-scenario score by agent (from SUMMARY.by_agent_case)
    (function() {
      const byAgentCase = SUMMARY.by_agent_case || {};
      const scenarioAgentScores = {}; // scenario -> agent -> [scores]
      for (const key of Object.keys(byAgentCase)) {
        // key format: "agent::scenario::case"
        const parts = key.split('::');
        if (parts.length < 3) continue;
        const agent = parts[0];
        const scenario = parts[1];
        const data = byAgentCase[key];
        const scoreAvg = (data && data.score && typeof data.score.avg === 'number') ? data.score.avg : 0;
        if (!scenarioAgentScores[scenario]) scenarioAgentScores[scenario] = {};
        if (!scenarioAgentScores[scenario][agent]) scenarioAgentScores[scenario][agent] = [];
        scenarioAgentScores[scenario][agent].push(scoreAvg);
      }
      // For each scenario, average per agent and create a trace series
      const scenNames = Object.keys(scenarioAgentScores).sort();
      const container = document.getElementById('scenario_scores');
      if (scenNames.length === 0) {
        container.innerHTML = '<em>No scenario-level data available</em>';
        return;
      }
      // Build a grouped bar chart: x=agents, a bar series per scenario
      const traces = [];
      for (const scen of scenNames) {
        const scores = agents.map(a => {
          const arr = (scenarioAgentScores[scen][a] || []);
          if (arr.length === 0) return 0;
          return arr.reduce((x,y)=>x+y,0)/arr.length;
        });
        traces.push({ x: agents, y: scores, type: 'bar', name: scen });
      }
      Plotly.newPlot('scenario_scores', traces, { margin: {t: 16}, barmode: 'group', yaxis: {range: [0,1], title: 'score_avg'}, xaxis: {automargin: true} }, {responsive: true});
    })();
  </script>
</body>
</html>
        """
    )

    html = template.substitute(
        TITLE=title,
        SUMMARY_JSON=summary_json,
        RAW_JSON=raw_json,
        AGENTS=json.dumps(agents),
        SCORE_AVG=json.dumps(score_avg),
        SCORE_STD=json.dumps(score_std),
        LAT_AVG=json.dumps(lat_avg),
        LAT_P50=json.dumps(lat_p50),
        LAT_P95=json.dumps(lat_p95),
        LAT_STD=json.dumps(lat_std),
        THROUGHPUT=json.dumps(throughput),
        OK_RATE=json.dumps(ok_rate),
        G_EXC=json.dumps(g_exc),
        G_APR=json.dumps(g_apr),
        G_INS=json.dumps(g_ins),
        TOKENS_AVG=json.dumps(tokens_avg),
        CHARS_AVG=json.dumps(chars_avg),
        COST_AVG=json.dumps(cost_avg),
    )

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
