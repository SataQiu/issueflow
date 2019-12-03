# -*- coding: UTF-8 -*-

from github import Github
import time
import os

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')

REPO_OWNER = "istio"
REPO_NAME = "istio.io"
LABEL_SELECTOR = "translation/chinese"
NEED_OK_TO_TEST_LABEL = "needs-ok-to-test"


def process():
    github_cli = Github(GITHUB_TOKEN)
    repo = github_cli.get_repo(REPO_OWNER + "/" + REPO_NAME)
    open_pulls = repo.get_pulls(state='open')
    for pull in open_pulls:
        # check pull label (must contain LABEL_SELECTOR)
        found_selector_label = False
        found_needs_ok_to_test = False
        labels = pull.get_labels()
        for label in labels:
            if label.name == LABEL_SELECTOR:
                found_selector_label = True
            if label.name == NEED_OK_TO_TEST_LABEL:
                found_needs_ok_to_test = True
        if not found_selector_label:
            continue
        print("info: process ", pull)
        # add /ok-to-test, if needed
        if found_needs_ok_to_test:
            print("info: add /ok-to-test to :", pull)
            pull.create_review(body="/ok-to-test")
        # check comments for /review
        issue_comments = pull.get_issue_comments()
        for comment in issue_comments:
            if "/review" in comment.body:
                assigned = False
                for assign in pull.assignees:
                    if assign == comment.user:
                        assigned = True
                        break
                if not assigned:
                    print("warning: should assign ", pull, " to ", comment.user)
                    # TODO: make this work
                    # pull.add_to_assignees(comment.user.login)


if __name__ == "__main__":
    while True:
        print("info: starting...")
        process()
        print("info: waiting for 30 minutes...")
        time.sleep(1800)
