## Build image

```sh
$ docker build -t shidaqiu/istio-inspect:0.1 .
```

## Run

```sh
$ docker run -dt --name=istio-inspect \
        --restart=always \
        -e GITHUB_TOKEN=xxx \
        shidaqiu/istio-inspect:0.1
```
