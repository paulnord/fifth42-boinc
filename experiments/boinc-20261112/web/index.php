<?php
// Private BOINC homepage preview. Existing scheduler discovery remains intact.
$config = simplexml_load_file(__DIR__.'/../../config.xml');
$project_url = (string)$config->config->master_url;
if (!$project_url) { http_response_code(503); exit('Project configuration unavailable.'); }
$pilot = json_decode(file_get_contents(__DIR__.'/fifthpower-assets/pilot.json'), true);
function fp_escape($text) { return htmlspecialchars((string)$text, ENT_QUOTES, 'UTF-8'); }
header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-cache');
header("Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'self'");
?><!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="FifthPower@home explores small differences between enormous fifth powers using volunteer computers, a lattice sieve and exact arithmetic.">
  <title>FifthPower@home — small differences, enormous powers</title>
  <?php readfile(__DIR__.'/schedulers.txt'); ?>
  <link rel="stylesheet" href="fifthpower-assets/home.css">
  <script src="fifthpower-assets/home.js" defer></script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header wrap">
  <a class="brand" href="./" aria-label="FifthPower at home, home"><span class="brand-mark" aria-hidden="true">5<span>·</span></span><span>FifthPower<span class="at-home">@home</span></span></a>
  <nav aria-label="Main navigation"><a href="#search">The search</a><a href="#result">A difference of 12</a><a href="#participate">Take part</a></nav>
  <a class="account-link" href="home.php">My BOINC account <span aria-hidden="true">↗</span></a>
</header>
<main id="main">
  <section class="hero wrap" aria-labelledby="hero-title">
    <div class="hero-copy">
      <p class="eyebrow"><span class="live-dot" aria-hidden="true"></span> A volunteer computing project in development</p>
      <h1 id="hero-title">Small differences.<br><em>Enormous <br>fifth powers.</em></h1>
      <p class="hero-description">Some enormous numbers come astonishingly close. Help us explore where two fifth powers nearly add up to a third.</p>
      <div class="hero-actions"><a class="button button-mint" href="#result">Meet the number 12 <span aria-hidden="true">↓</span></a><a class="text-link" href="#search">Explore the mathematics <span aria-hidden="true">↗</span></a></div>
      <p class="hero-footnote">The next goal: differences through <strong>100</strong>.<br>The same lattice sieve. Exact integer checks.</p>
    </div>
    <div class="hero-art"><span class="art-label">THE FIFTH-POWER FRONTIER</span><img src="fifthpower-assets/frontier.svg" width="700" height="570" alt="Curving contours of the fifth-power surface, with the near-miss 13, 16, 17 highlighted."><span class="art-coordinate" aria-hidden="true">a⁵ + b⁵ − c⁵ = r</span></div>
  </section>

  <section class="result-section" id="result" aria-labelledby="result-title">
    <div class="wrap">
      <div class="section-heading"><p class="eyebrow">A known result, beautifully close</p><span class="edition">FIELD NOTE / 001</span></div>
      <h2 id="result-title">A million-sized calculation.<br><em>A difference of twelve.</em></h2>
      <div class="equation" aria-label="13 to the fifth plus 16 to the fifth minus 17 to the fifth equals 12"><span>13<sup>5</sup></span><b>+</b><span>16<sup>5</sup></span><b>−</b><span>17<sup>5</sup></span><b>=</b><span class="result-number">12</span></div>
      <div class="result-explanation"><p><strong>371,293 + 1,048,576 − 1,419,857 = 12.</strong><br>Two fifth powers total 1,419,869. A third misses that sum by just twelve.</p><p>This known example was reproduced by both our CPU and Apple GPU control tests, then independently checked. It is a demonstration of the search—not a new discovery.</p></div>
      <div class="residual-window"><div class="window-heading"><span>SMALL DIFFERENCES, MAGNIFIED</span><span>The proposed residual window</span></div><div class="number-line" aria-hidden="true"><span class="tick start">−100</span><span class="tick zero">0</span><span class="tick end">+100</span><span class="result-pin"><i></i><strong>+12</strong></span></div><p>Our proposed goal covers both positive and negative residuals with absolute value at most 100.</p></div>
    </div>
  </section>

  <section class="search-section wrap" id="search" aria-labelledby="search-title">
    <div class="search-intro"><p class="eyebrow">The mathematics</p><h2 id="search-title">A precise search<br>for near equality.</h2><p>We study integer triples whose fifth powers leave a small residual:</p><div class="search-formula">r = a<sup>5</sup> + b<sup>5</sup> − c<sup>5</sup></div><p>Within explicitly defined search bounds, the proposed next stage widens the residual cap to <strong>|r| ≤ 100</strong>. It keeps the existing lattice/sieve algorithm and exact arithmetic.</p></div>
    <ol class="method"><li><span class="step-number">01</span><div><h3>Find promising regions</h3><p>The lattice sieve organizes a vast integer search into bounded packets of candidate positions.</p></div></li><li><span class="step-number">02</span><div><h3>Put spare computing to work</h3><p>Native CPU and GPU applications test those packets. BOINC distributes the work and returns the results.</p></div></li><li><span class="step-number">03</span><div><h3>Check the arithmetic independently</h3><p>Our pilot replays each result with an independent GMP reference, checking exact hits and complete candidate counts.</p></div></li></ol>
  </section>

  <section class="benchmark-section wrap" aria-labelledby="benchmark-title">
    <div><p class="eyebrow">From the first physical M4 pilot</p><h2 id="benchmark-title">Real devices.<br>Measured results.</h2><p>42 test packets. 789.4 million candidate positions per trial. Three runs on each backend, all independently accepted.</p><a class="text-link" href="fifthpower-assets/benchmark.md">Read the benchmark record <span aria-hidden="true">↗</span></a></div>
    <div class="benchmark-chart"><div class="chart-heading"><span>MEDIAN APPLICATION TIME</span><span>Lower is faster</span></div><div class="timing"><div><span>CPU · one thread</span><strong><?= number_format($pilot['CPU_seconds'], 2) ?> s</strong></div><div class="bar-track"><span class="bar bar-cpu"></span></div></div><div class="timing"><div><span>Apple M4 · Metal GPU</span><strong><?= number_format($pilot['GPU_seconds'], 2) ?> s</strong></div><div class="bar-track"><span class="bar bar-gpu"></span></div></div><p class="benchmark-highlight"><strong><?= number_format($pilot['application_speedup'], 2) ?>×</strong><span>GPU application speedup<br><small><?= number_format($pilot['BOINC_speedup'], 2) ?>× including BOINC startup overhead</small></span></p><p class="chart-note">One CPU thread versus the integrated GPU. Short, cached-payload replays; this does not measure sustained or all-core CPU performance.</p></div>
  </section>

  <section class="participate-section" id="participate" aria-labelledby="participate-title"><div class="wrap participate-grid"><div><p class="eyebrow">A small beginning. A much larger search.</p><h2 id="participate-title">Bring your curiosity.<br><em>And a little computing.</em></h2><p>We are testing a private BOINC pilot before a broader launch. Invited testers can use their existing project account and connection.</p><div class="participate-actions"><a class="button button-dark" href="home.php">Open your BOINC account <span aria-hidden="true">↗</span></a><a class="text-link" href="https://github.com/paulnord/fifth42-boinc">Explore the prototype <span aria-hidden="true">↗</span></a></div></div><div class="pilot-panel"><span class="pilot-badge">PRIVATE PILOT</span><h3>Your project connection</h3><label for="project-address">Project URL for invited testers</label><div class="copy-row"><input id="project-address" value="<?= fp_escape($project_url) ?>" readonly spellcheck="false"><button id="copy-project" type="button">Copy</button></div><p id="copy-status" role="status">Keep your existing project tunnel open while attaching and reporting work.</p><div class="pilot-links"><a href="home.php">Account</a><a href="server_status.php">Server status</a><a href="https://boinc.berkeley.edu/download.php">Get BOINC</a></div><p class="pilot-scope">The current pilot replays verified test packets. It credits no production search coverage. The cap-100 search is a planned goal.</p></div></div></section>
</main>
<footer class="site-footer wrap"><a class="brand" href="./">FifthPower<span class="at-home">@home</span></a><p>Small differences. Shared discovery.</p><span>Private homepage preview · November 2026</span></footer>
</body></html>
