FROM node:20-alpine

WORKDIR /app

COPY package.json vite.config.js tailwind.config.js postcss.config.js ./
COPY index.html ./

RUN npm install

COPY src ./src

EXPOSE 5173

CMD ["npx", "vite", "--host", "0.0.0.0", "--port", "5173"]
