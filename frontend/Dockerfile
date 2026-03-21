FROM nginx:alpine

COPY . /usr/share/nginx/html/
RUN echo 'server { \
  listen 80; \
  server_name localhost; \
  root /usr/share/nginx/html; \
  index demo.html index.html; \
  location / { try_files $uri $uri/ /demo.html; } \
}' > /etc/nginx/conf.d/default.conf

CMD ["nginx", "-g", "daemon off;"]
