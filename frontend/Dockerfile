FROM nginx:alpine

# Копируем все файлы фронтенда
COPY . /usr/share/nginx/html/

# Создаем конфиг nginx для правильной работы SPA
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    root /usr/share/nginx/html; \
    index demo.html index.html; \
    \
    location / { \
        try_files $uri $uri/ /demo.html; \
    } \
    \
    # Кэширование статических файлов \
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ { \
        expires 1y; \
        add_header Cache-Control "public, immutable"; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
