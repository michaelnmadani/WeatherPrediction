(function () {
  "use strict";

  const METRIC_LABELS = {
    high_temp: "High Temp",
    low_temp: "Low Temp",
    wind_speed: "Wind Speed",
    humidity: "Humidity",
    rain: "Rain",
  };

  const METRIC_NEAR_LABELS = {
    high_temp: "within 2°C",
    low_temp: "within 2°C",
    wind_speed: "within 1 km/h",
    humidity: "within 5%",
    rain: "within 1 mm",
  };

  const METRIC_WIDE_LABELS = {
    high_temp: "within 4°C",
    low_temp: "within 4°C",
    wind_speed: "within 10 km/h",
    humidity: "within 10%",
    rain: "within 5 mm",
  };

  const DATA_URL = "data/results/summary.json";

  // DOM refs
  const $loading = document.getElementById("loading");
  const $noData = document.getElementById("no-data");
  const $dashboard = document.getElementById("dashboard");
  const $overallScore = document.getElementById("overall-score");
  const $scoreDate = document.getElementById("score-date");
  const $scoreStddev = document.getElementById("score-stddev");
  const $summaryDate = document.getElementById("summary-date");
  const $summaryBody = document.querySelector("#summary-table tbody");
  const $regionBody = document.querySelector("#region-table tbody");
  const $dateSelect = document.getElementById("date-select");
  const $historyBody = document.querySelector("#history-table tbody");

  async function loadSummary() {
    // Cache-bust for freshness
    const resp = await fetch(DATA_URL + "?t=" + Date.now());
    if (!resp.ok) throw new Error("No summary data available");
    return resp.json();
  }

  async function loadDayResult(date) {
    const resp = await fetch("data/results/" + date + ".json?t=" + Date.now());
    if (!resp.ok) return null;
    return resp.json();
  }

  function pctClass(pct) {
    if (pct >= 80) return "badge-green";
    if (pct >= 60) return "badge-yellow";
    if (pct >= 40) return "badge-orange";
    return "badge-red";
  }

  function diffClass(metric, diff) {
    if (diff === null || diff === undefined) return "";
    var thresholds = {
      high_temp: [2, 4],
      low_temp: [2, 4],
      wind_speed: [1, 10],
      humidity: [5, 10],
      rain: [1, 5],
    };
    var t = thresholds[metric];
    if (diff <= t[0]) return "diff-good";
    if (diff <= t[1]) return "diff-ok";
    return "diff-bad";
  }

  function renderSummary(latest) {
    var summary = latest.summary;
    $summaryDate.textContent = "Date: " + latest.date;
    $summaryBody.innerHTML = "";

    var metrics = ["high_temp", "low_temp", "wind_speed", "humidity", "rain"];
    metrics.forEach(function (m) {
      var s = summary[m];
      if (!s) return;

      var tr = document.createElement("tr");
      tr.innerHTML =
        '<td><strong>' + METRIC_LABELS[m] + "</strong></td>" +
        '<td><span class="badge ' + pctClass(s.exact_pct) + '">' + s.exact_pct + "%</span></td>" +
        '<td><span class="badge ' + pctClass(s.near_pct) + '">' + s.near_pct + "%" + "</span>" +
        '<br><span class="meta">' + METRIC_NEAR_LABELS[m] + "</span></td>" +
        '<td><span class="badge ' + pctClass(s.wide_pct) + '">' + s.wide_pct + "%" + "</span>" +
        '<br><span class="meta">' + METRIC_WIDE_LABELS[m] + "</span></td>" +
        "<td>" + s.mean_diff + " " + s.unit + "</td>" +
        "<td>" + s.std_dev + " " + s.unit + "</td>";

      $summaryBody.appendChild(tr);
    });
  }

  function renderRegionTable(result) {
    $regionBody.innerHTML = "";
    if (!result || !result.accuracy || !result.accuracy.comparisons) return;

    var comps = result.accuracy.comparisons;
    var metrics = ["high_temp", "low_temp", "wind_speed", "humidity", "rain"];

    comps.forEach(function (c) {
      var tr = document.createElement("tr");
      var cells = "<td><strong>" + c.region + "</strong></td>";

      metrics.forEach(function (m) {
        var d = c.metrics[m];
        if (!d || d.forecast === null || d.actual === null) {
          cells += "<td>--</td>";
          return;
        }
        var dc = diffClass(m, d.diff);
        cells +=
          "<td>" +
          d.forecast + " / " + d.actual +
          ' / <span class="' + dc + '">' + d.diff + "</span></td>";
      });

      tr.innerHTML = cells;
      $regionBody.appendChild(tr);
    });
  }

  function renderHistory(results) {
    $historyBody.innerHTML = "";
    var metrics = ["high_temp", "low_temp", "wind_speed", "humidity", "rain"];

    results.forEach(function (r) {
      var tr = document.createElement("tr");
      var cells =
        "<td>" + r.date + "</td>" +
        '<td><strong class="' +
        (r.overall_score >= 80 ? "diff-good" : r.overall_score >= 60 ? "diff-ok" : "diff-bad") +
        '">' + r.overall_score + "%</strong></td>";

      metrics.forEach(function (m) {
        var s = r.summary ? r.summary[m] : null;
        if (!s) {
          cells += "<td>--</td>";
          return;
        }
        cells += '<td><span class="badge ' + pctClass(s.wide_pct) + '">' + s.wide_pct + "%</span></td>";
      });

      tr.innerHTML = cells;
      $historyBody.appendChild(tr);
    });
  }

  async function init() {
    try {
      var data = await loadSummary();

      if (!data.results || data.results.length === 0) {
        $loading.hidden = true;
        $noData.hidden = false;
        return;
      }

      var latest = data.results[0];

      // Score card
      $overallScore.textContent = latest.overall_score;
      $scoreDate.textContent = "Latest: " + latest.date;
      $scoreStddev.textContent = "Avg Std Dev: " + latest.avg_std_dev;

      // Summary table
      renderSummary(latest);

      // Date selector
      $dateSelect.innerHTML = "";
      data.results.forEach(function (r) {
        var opt = document.createElement("option");
        opt.value = r.date;
        opt.textContent = r.date;
        $dateSelect.appendChild(opt);
      });

      // Load region details for latest day
      var dayResult = await loadDayResult(latest.date);
      renderRegionTable(dayResult);

      $dateSelect.addEventListener("change", async function () {
        var selected = $dateSelect.value;
        var result = await loadDayResult(selected);
        renderRegionTable(result);
      });

      // History table
      renderHistory(data.results);

      // Show dashboard
      $loading.hidden = true;
      $dashboard.hidden = false;
    } catch (e) {
      console.error("Failed to load data:", e);
      $loading.hidden = true;
      $noData.hidden = false;
    }
  }

  init();
})();
