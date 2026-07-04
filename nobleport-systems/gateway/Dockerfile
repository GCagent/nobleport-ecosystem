FROM rust:1.94-slim AS build
WORKDIR /src
COPY Cargo.toml ./
COPY src ./src
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/target/release/nobleport-gateway /usr/local/bin/nobleport-gateway
EXPOSE 8080
CMD ["nobleport-gateway"]
