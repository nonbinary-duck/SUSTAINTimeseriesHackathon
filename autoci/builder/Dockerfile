FROM golang:1.26-alpine AS build
WORKDIR /src
RUN apk add --no-cache git
COPY main.go .
RUN go mod init app && \
    go get github.com/moby/moby/client@v0.4.0 github.com/moby/moby/api@v1.54.1 && \
    go mod tidy
RUN go build -o /app-bin main.go

FROM alpine:latest
COPY --from=build /app-bin /usr/local/bin/app-bin
# Dockerfile that's built should be immutable for security purposes (has the ability to copy files from my host)
COPY ../Dockerfile.autoci /app/Dockerfile.autoci

CMD ["app-bin"]