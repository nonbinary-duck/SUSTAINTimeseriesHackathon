FROM golang:1.26-alpine AS build
WORKDIR /src
RUN apk add --no-cache git
COPY main.go .
RUN go mod init app && \
    go get github.com/docker/docker github.com/docker/go-connections/nat && \
    go mod tidy
RUN go build -o /app-bin main.go

FROM alpine:latest
COPY --from=build /app-bin /usr/local/bin/app-bin
CMD ["app-bin"]