<?php
$frontendUrl = getenv('FRONTEND_PUBLIC_URL') ?: 'http://localhost:8081';
$backendUrl = getenv('BACKEND_PUBLIC_URL') ?: 'http://localhost:8000';
?>
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Портал извлеченных уроков</title>
  <meta name="description" content="Корпоративный портал раздела Извлеченные уроки">
  <style>
    :root {
      --bg: #edf3f7;
      --panel: #ffffff;
      --ink: #163245;
      --muted: #5f7382;
      --nav: #133a57;
      --nav-2: #1a4a70;
      --line: #d7e1e8;
      --accent: #0e6a9e;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background: radial-gradient(circle at top left, #f7fbfe 0%, var(--bg) 38%, #e8f0f6 100%);
      color: var(--ink);
    }
    .topbar {
      background: linear-gradient(90deg, var(--nav), var(--nav-2));
      color: #fff;
      padding: 16px 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      box-shadow: 0 8px 24px rgba(15, 47, 72, 0.14);
    }
    .brand {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .brand strong {
      font-size: 18px;
      letter-spacing: 0.2px;
    }
    .brand span {
      font-size: 13px;
      color: rgba(255, 255, 255, 0.78);
    }
    .topbar-badge {
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.12);
      border: 1px solid rgba(255, 255, 255, 0.16);
      font-size: 13px;
    }
    main {
      display: grid;
      grid-template-columns: 300px 1fr;
      min-height: calc(100vh - 68px);
    }
    aside {
      background: linear-gradient(180deg, #173d5b 0%, #11324b 100%);
      color: #dbe7f0;
      padding: 24px;
    }
    .nav-card {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 18px;
      padding: 18px;
      margin-bottom: 18px;
    }
    .nav-title {
      margin: 0 0 12px;
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: rgba(255, 255, 255, 0.7);
    }
    .nav-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .nav-item {
      padding: 12px 14px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .nav-item.active {
      background: rgba(255, 255, 255, 0.12);
      border-color: rgba(255, 255, 255, 0.16);
      color: #fff;
      font-weight: 600;
    }
    section {
      padding: 28px;
    }
    .hero {
      background: var(--panel);
      border-radius: 24px;
      padding: 28px;
      border: 1px solid var(--line);
      box-shadow: 0 10px 32px rgba(15, 47, 72, 0.08);
    }
    .hero h1 {
      margin: 0 0 12px;
      font-size: clamp(28px, 3vw, 40px);
      line-height: 1.1;
    }
    .hero p {
      margin: 0;
      color: var(--muted);
      max-width: 74ch;
    }
    .portal-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
      margin-top: 20px;
    }
    .tile {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 18px;
      min-height: 126px;
    }
    .tile h3 {
      margin: 0 0 10px;
      font-size: 16px;
    }
    .tile p {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }
    .widget-frame {
      margin-top: 24px;
      width: 100%;
      height: 760px;
      border: 1px solid var(--line);
      border-radius: 24px;
      background: #fff;
      box-shadow: 0 14px 36px rgba(15, 47, 72, 0.08);
    }
    @media (max-width: 980px) {
      main { grid-template-columns: 1fr; }
      aside { order: 2; }
      .portal-grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 640px) {
      .topbar { padding: 14px 18px; flex-direction: column; align-items: flex-start; }
      section, aside { padding: 18px; }
      .widget-frame { height: 720px; }
    }
  </style>
</head>
<body>
  <header class="topbar">
    <div class="brand">
      <strong>Корпоративный портал</strong>
      <span>Раздел "Извлеченные уроки"</span>
    </div>
    <div class="topbar-badge">Portal shell / PHP</div>
  </header>
  <main>
    <aside>
      <div class="nav-card">
        <div class="nav-title">Разделы</div>
        <div class="nav-list">
          <div class="nav-item">Общее</div>
          <div class="nav-item active">Извлеченные уроки</div>
          <div class="nav-item">Документы</div>
          <div class="nav-item">Цепочка помощи</div>
        </div>
      </div>
      <div class="nav-card">
        <div class="nav-title">Контекст</div>
        <p style="margin:0; color: rgba(255,255,255,0.8); line-height:1.5;">
          Портал служит легкой точкой входа в раздел извлеченных уроков и встраивает frontend-виджет ассистента.
        </p>
      </div>
    </aside>
    <section>
      <div class="hero">
        <h1>Страница раздела "Извлеченные уроки"</h1>
        <p>Это легкая PHP-оболочка корпоративной страницы. Она имитирует вход в раздел и встраивает frontend-виджет ассистента, не добавляя лишней серверной логики.</p>
        <div class="portal-grid">
          <div class="tile">
            <h3>Точка входа</h3>
            <p>Одна рабочая страница раздела, откуда пользователь сразу попадает в помощник.</p>
          </div>
          <div class="tile">
            <h3>Режимы</h3>
            <p>Поддерживаются chat, search, document и mail через встроенный frontend-виджет.</p>
          </div>
          <div class="tile">
            <h3>Сессия</h3>
            <p>Контекст диалога живет на стороне frontend и backend, а портал остается только оболочкой.</p>
          </div>
        </div>
      </div>
      <iframe class="widget-frame" src="<?php echo htmlspecialchars($frontendUrl . '/demo.html?backendUrl=' . rawurlencode($backendUrl), ENT_QUOTES, 'UTF-8'); ?>" title="Lessons frontend"></iframe>
    </section>
  </main>
</body>
</html>
