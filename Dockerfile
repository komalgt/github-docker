FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

# FROM ... AS prod should also use uppercase AS
FROM node:20-alpine AS prod

WORKDIR /app

COPY --from=build /app /app

RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# The app is listening on port 3000
EXPOSE 3000

CMD ["npm", "start"]
