## Build

```bash
errbot-build.sh && cd /tmp/errbot && docker build -t shidaqiu/translate-chatbot:1.1 .
```

## Run Server

```bash
docker run -d --name=istio-slack-bot \
        --restart=always \
        -e BOT_LOG_LEVEL=INFO \ # 日志输出级别
        -e BOT_ADMINS=@1527062125 \ # 管理员的 Slack 名称
        -e REPOSITORY="istio" \ # 配置文件中的 Repository 名称
        -e REPOSITORY_CONFIG_FILE="/errbot/config/repository.yaml" \ # 配置文件名称
        -e MAX_RESULT=10 \ # 单次最大输出数量
        -e MAX_WRITE=500 \ # 单次最大写入数量
        -e TARGET_LANG="zh" \ # 翻译语种名称
        -e BOT_TOKEN="xoxb-" \ # Slack Bot 的 Token
        -e BACKEND="Slack" \ # 指定使用 Slack 后端
        -e CRITICAL_COMMANDS="find_new_files_in,find_updated_files_in,find_deleted_files_in,cache_issue,confirm_recent_new_issues,find_delay_issues" \ # 关键命令列表
        -e OPERATORS="@1527062125" \ # 可以执行关键命令的操作员
        -e PRIVATE_COMMANDS="whatsnew,github_bind,github_whoami" \ # 仅能在私聊窗口中使用的命令
        -v $(pwd)/data:/errbot/data \ # Bot 的存储路径
        -v $(pwd)/config:/errbot/config \ # Bot 的配置路径
        -v $(pwd)/repository:/errbot/repository \ # 代码库路径
        shidaqiu/translate-chatbot:1.1 # 镜像名称
```