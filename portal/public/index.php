<?php
$frontendUrl = getenv('FRONTEND_PUBLIC_URL') ?: 'http://localhost:8081';
?>
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Портал извлеченных уроков</title>
  <style>
    body { margin: 0; font-family: "Segoe UI", sans-serif; background: #eef3f7; color: #183447; }
    header { background: #123a57; color: #fff; padding: 18px 28px; display: flex; justify-content: space-between; }
    main { display: grid; grid-template-columns: 320px 1fr; min-height: calc(100vh - 60px); }
    aside { background: #163f5f; color: #dbe7f0; padding: 24px; }
    section { padding: 32px; }
    .hero { background: #fff; border-radius: 22px; padding: 28px; border: 1px solid #d6e0e8; }
    .widget-frame { margin-top: 24px; width: 100%; height: 760px; border: 0; border-radius: 24px; background: #fff; }
  </style>
</head>
<body>
  <header>
    <strong>Корпоративный портал / Извлеченные уроки</strong>
    <span>PHP shell</span>
  </header>
  <main>
    <aside>
      <h3>Разделы</h3>
      <p>Общее</p>
      <p><strong>Извлеченные уроки</strong></p>
      <p>Документы</p>
      <p>Цепочка помощи</p>
    </aside>
    <section>
      <div class="hero">
        <h1>Страница раздела "Извлеченные уроки"</h1>
        <p>Ниже встроен фронтовый виджет ассистента. Он работает только в рамках этого раздела.</p>
      </div>
      <iframe class="widget-frame" src="<?php echo htmlspecialchars($frontendUrl . '/demo.html', ENT_QUOTES, 'UTF-8'); ?>" title="Lessons frontend"></iframe>
    </section>
  </main>
</body>
</html>
