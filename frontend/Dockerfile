FROM node:20-alpine AS build
WORKDIR /app

COPY generative_agents/frontend ./generative_agents/frontend

RUN if [ -f generative_agents/frontend/package.json ]; then \
      cd generative_agents/frontend && npm ci && npm run build; \
    else \
      mkdir -p generative_agents/frontend/dist && \
      cp -r generative_agents/frontend/static/. generative_agents/frontend/dist/ || true; \
    fi

FROM nginx:1.27-alpine
COPY --from=build /app/generative_agents/frontend/dist /usr/share/nginx/html
EXPOSE 80
