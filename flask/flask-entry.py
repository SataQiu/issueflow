#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from flask import Flask, request
import os
import sys
import traceback
from githubutil import github, action

import logging.handlers

MAX_LOG_BYTES = 1024 * 1024
LOG_LEVEL = os.getenv('LOG_LEVEL', str(logging.INFO)).strip()
PORT = os.getenv("PORT", "80").strip()
TOKEN = os.getenv('GITHUB_TOKEN', "").strip()
WORKFLOW = os.getenv('WORKFLOW', "").strip()
ADMINS = os.getenv('ADMINS', "").strip()
INTERVAL = os.getenv('INTERVAL', "1").strip()


handler = logging.StreamHandler(sys.stdout)
fmt = '%(asctime)s - [%(levelname)s] - %(filename)s:%(lineno)s - %(message)s'

formatter = logging.Formatter(fmt)
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(int(LOG_LEVEL))

app = Flask(__name__)


def log_incoming_comment(data):
    line = "User: {} Issue: {} Comment: {}"
    content = line.format(
        data["sender"]["login"],
        data["issue"]["number"],
        data["comment"]["body"]
    )
    logger.info(content)


@app.route('/healthz', methods = ['GET'])
def healthz():
    client = github.GithubOperator(TOKEN)
    try:
        limit = client.get_limit()
        logger.info("limit: {} remaining: {}".format(limit["core"]["limit"], limit["core"]["remaining"]))
        return "True"
    except Exception as e:
        exstr = traceback.format_exc()
        logger.warn(exstr)
    return "False"


@app.route('/', methods = ['GET', 'POST'])
def webhook():
    if request.method != "POST":
        return "405 Method not allowed"
    
    data = request.get_json(force=True)
    event_type = request.headers["X-GitHub-Event"]
    event_action = data["action"]

    if event_type == "issues":
        logger.info("issue action:{} {}".format(data["action"], data["issue"]["number"]))
        if event_action != "opened":
            return "Action '{}' is not supported".format(event_action)
        subject = {
            "repo": data["repository"]["id"],
            "issue_id": data["issue"]["number"],
            "sender": data["sender"]["login"],
            "command": "opened"
        }
        action.execute(
            "config.yaml", TOKEN, WORKFLOW,
            ADMINS.split(","), "on_issue",
            subject, float(INTERVAL)
        )
        return "Event 'issue' had been processed."

    if event_type == "issue_comment":
        log_incoming_comment(data)
        if event_action not in ["created", "edited"]:
            return "Action '{}' is not supported".format(event_action)
        subject = {
            "repo": data["repository"]["id"],
            "issue_id": data["issue"]["number"],
            "sender": data["sender"]["login"],
            "command": data["comment"]["body"]
        }
        action.execute(
            "config.yaml", TOKEN, WORKFLOW,
            ADMINS.split(","), "on_comment",
            subject, float(INTERVAL)
        )
        return "Event 'issue_comment' had been processed."
    
    return "Current event '{}' is not supported.".format(event_type)


if __name__ == "__main__":
    app.run(debug=True)
