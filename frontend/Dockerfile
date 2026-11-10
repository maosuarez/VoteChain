FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Next evaluates rewrites at build time: the API address is fixed here.
ARG VOTECHAIN_API_URL=http://api:8000
ARG NEXT_PUBLIC_EXPLORER_URL=http://127.0.0.1:8000/explorer/
ENV VOTECHAIN_API_URL=$VOTECHAIN_API_URL \
    NEXT_PUBLIC_EXPLORER_URL=$NEXT_PUBLIC_EXPLORER_URL
RUN npm run build
ENV NODE_ENV=production
EXPOSE 3000
CMD ["npm", "start"]
