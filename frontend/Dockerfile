FROM node:20-alpine
WORKDIR /app
ENV VITE_API_PROXY_TARGET=http://api:8000
COPY package*.json ./
RUN npm install
COPY . .
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
