## Build

```bash
flask-build.sh && cd /tmp/flask && docker build -t shidaqiu/translate-issueflow:1.1 .
```

## Run Server

```bash
docker run -d --name=istio-flask-issueflow \
        --restart=always \
        -e GITHUB_TOKEN=xxx \
        -e WORKFLOW=istio \
        -e ADMINS=SataQiu \
        -p 5000:5000 \
        shidaqiu/translate-issueflow:1.1
```

## Export Service By [ultrahook](http://www.ultrahook.com/)

```bash
ultrahook stripe 5000
```

**NB. GitHub webhook must select `application/json`**
