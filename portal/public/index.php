<?php
declare(strict_types=1);

/**
 * Точка входа портала: перенаправляет на полноэкранный макет frontend/demo.html
 * без оболочки и iframe — интерфейс совпадает с эталонными макетами.
 */
$frontendUrl = rtrim(getenv('FRONTEND_PUBLIC_URL') ?: 'http://localhost:8081', '/');
$backendUrl = getenv('BACKEND_PUBLIC_URL') ?: 'http://localhost:8000';

$target = $frontendUrl . '/demo.html?' . http_build_query(
    ['backendUrl' => $backendUrl],
    '',
    '&',
    PHP_QUERY_RFC3986
);

header('Location: ' . $target, true, 302);
exit;
