## Build image

```sh
$ docker build -t shidaqiu/istio-inspect:1.0 .
```

## Run

```sh
$ docker run -dt --name=istio-inspect \
        --restart=always \
        -e GITHUB_TOKEN=xxx \
        shidaqiu/istio-inspect:1.0
```
