import time

from gitutil.commands import GitCommand
from gitutil.configure import Configuration
from os.path import splitext
import os
from githubutil.github import GithubOperator
import json
from datetime import datetime, timedelta
import re
import logging
import hashlib
from shutil import copyfile


def md5_hash(file_name):
    hash_util = hashlib.md5()
    with open(file_name, 'rb') as afile:
        buf = afile.read()
        hash_util.update(buf)
    return hash_util.hexdigest()


class TranslateUtil:
    _git_path = ""
    _github_token = ""
    _configure = None

    def __init__(self, config_file, github_token, git_path="git"):
        """
        Initialization.

        :param config_file: Name of the repository config file.
        :type config_file: str
        :param github_token: Github token
        :type github_token: str
        :param git_path: Executable git path.
        :type git_path: str
        """
        self._git_path = git_path
        self._configure = Configuration(config_file)
        self._github_token = github_token

    def _filter_file_type(self, repository_name, file_name_list):
        """
        Only files with extensions in the list will left.
        :param repository_name: Repository name (in the config file)
        :type repository_name: str
        :param file_name_list:
        :type file_name_list: list
        :rtype: list
        """
        ext_list = self._configure.get_valid_extensions(repository_name)
        result = []
        for file_name in file_name_list:
            _, ext = splitext(file_name)
            if ext in ext_list:
                result.append(file_name)
        return result

    def _get_git_commander(self, repo):
        return GitCommand(repo, self._git_path)

    def _get_repo_path(self, repository_name, branch_name):
        self._configure.repository = repository_name
        branch_item = self._configure.get_branch(repository_name, branch_name)
        return branch_item["path"]

    @staticmethod
    def __is_ignore(file_name, ignore_list):
        result = False
        for pattern in ignore_list:
            if re.match(pattern, file_name):
                result = True
                break
        return result

    def _remove_ignore_files(self, file_list, repository, branch):
        ignore_list = self._configure.get_ignore_re_list(repository, branch)
        result_list = [item for item in file_list if not self.__is_ignore(item, ignore_list)]
        return result_list

    def _get_clean_files(self, repository, branch, path):
        """
        Get file list in specified path.

        :param path: Relative path of the files we want.
        :type path: str
        :rtype: list
        """

        file_list = self._get_git_commander(
            self._get_repo_path(repository, branch)
        ).list_files()
        file_list = self._filter_file_type(repository, file_list)
        path_sep = path.split(os.sep)
        result = [file_name[len(path):]
                  for file_name in file_list
                  if file_name.split(os.sep)[:len(path_sep)] == path_sep]
        return result

    def list_branches(self, repository_name):
        return self._configure.list_branch(repository_name)

    def wait_for_limit(self, core_limit=10, search_limit=10):
        github_client = GithubOperator(self._github_token)
        github_client.check_limit(core_limit, search_limit)

    def _md5Hash(self, fd):
        line = fd.readline()
        hash = hashlib.md5()
        while (line):
            hash.update(line)
            line = fd.readline()
        return hash.hexdigest()

    def _is_same(self, source_file, target_file):
        source_fd = open(source_file, "rb")
        target_fd = open(target_file, "rb")
        same = self._md5Hash(source_fd) == self._md5Hash(target_fd)
        source_fd.close()
        target_fd.close()
        return same

    def _is_generated(self, source_file):
        fd = open(source_file, 'r', encoding='UTF-8')
        line_num, generated = 0, False
        for line in fd:
            line_num = line_num + 1
            if line_num > 2:
                break
            if line.find('WARNING: THIS IS AN AUTO-GENERATED FILE, DO NOT EDIT.') >= 0:
                generated = True
                break
        fd.close()
        return generated

    def find_new_files(self, repository_name, branch_name, language):
        """
        Find files which is in the source path, but not in the
        target path, and return it as a List of string.
        If the translated document is exactly the same as the original document,
        it is considered untranslated.

        :param branch_name:
        :param repository_name:
        :rtype: list of str
        :param language: Language name (in the configure file)
        :type language: str
        """
        repo_base_path = self._configure.get_branch(repository_name, branch_name)["path"]

        target_path = self._configure.get_languages(
            repository_name, language)["path"]
        source_path = self._configure.get_source(
            repository_name)["path"]

        # List files in source/language path
        source_list = self._get_clean_files(repository_name,
                                            branch_name, source_path)
        target_list = self._get_clean_files(repository_name,
                                            branch_name, target_path)

        # return the different files list
        target_set = set(target_list)
        translated_set = set()
        for source_file in source_list:
            full_source_file = os.sep.join([repo_base_path, source_path, source_file])
            if self._is_generated(full_source_file):
                translated_set.add(source_file)
                continue
            if source_file in target_set:
                full_target_file = os.sep.join([repo_base_path, target_path, source_file])
                if not self._is_same(full_source_file, full_target_file):
                    translated_set.add(source_file)
        result = list(set(source_list) - translated_set)
        result.sort()
        return self._remove_ignore_files(result, repository_name, branch_name)

    def cache_issues(self, query, file_name, search_limit=30):
        """

        :param search_limit:
        :param query: Github query string
        :param file_name: Save search result into a json file

        record = {"query": query,
            "timestamp": 1234567
            items:
            [
                {
                "number": 1234,
                "title": "Issue Title",
                labels: ["version/1.12", "translating"]
                },
            ]
        }
        """
        github_client = GithubOperator(self._github_token)
        issue_list = github_client.search_issue(query, search_limit)
        result = []
        for issue in issue_list:
            issue_item = {
                "number": issue.number,
                "title": issue.title,
                "labels": []
            }
            for label in issue.labels:
                issue_item["labels"].append(label.name)
            result.append(issue_item)
        with open(file_name, "w") as handle:
            json.dump(result, handle, indent=2)
        return len(result)

    def find_updated_files(self, repository_name, branch_name, language):
        """
        Find files match this criteria:
        - Both in source and target.
        - Last commit of source file is later than the last commit of target file

        and return it as a List of string.

        :param repository_name: Repository name (In the config file)
        :param branch_name: Branch name (In the config file)

        :rtype: dict
        :param language: Language name (in the configure file)
        :type language: str
        """

        repository_path = self._configure.get_branch(repository_name,
                                                     branch_name)["path"]
        git_cmd = self._get_git_commander(repository_path)

        target_path = self._configure.get_languages(repository_name,
                                                    language)["path"]
        source_path = self._configure.get_source(repository_name)["path"]

        # get files both in source and target.
        source_list = self._get_clean_files(repository_name,
                                            branch_name, source_path)
        target_list = self._get_clean_files(repository_name,
                                            branch_name, target_path)
        same_files = list(set(source_list) & set(target_list))

        result = {}
        for file_name in same_files:
            source_last_commit = \
                git_cmd.get_last_commit(source_path + file_name)
            target_commit = \
                git_cmd.get_last_commit(target_path + file_name)
            target_time = git_cmd.get_hash_time(target_commit)
            source_base_commit = git_cmd.get_file_hash_before(
                source_path + file_name, target_time)
            if source_base_commit != source_last_commit:
                diff = git_cmd.get_diff_by_hash(
                    source_path + file_name,
                    source_last_commit, source_base_commit)
                result[file_name] = diff
        return result

    def find_deleted_files(self, repository_name, branch_name, language):
        """
        Find files which is in the target path, but not in the
        source path, and return it as a List of string.

        :param branch_name:
        :param repository_name:
        :rtype: list of str
        :param language: Language name (in the configure file)
        :type language: str
        """

        repo_base_path = self._configure.get_branch(repository_name, branch_name)["path"]

        target_path = self._configure.get_languages(
            repository_name, language)["path"]
        source_path = self._configure.get_source(
            repository_name)["path"]

        # List files in source/language path
        source_list = self._get_clean_files(repository_name,
                                            branch_name, source_path)
        target_list = self._get_clean_files(repository_name,
                                            branch_name, target_path)

        # return the different files list
        source_set = set(source_list)
        deleted_set = set()
        for target_file in target_list:
            if target_file not in source_set:
                deleted_set.add(target_file)
        result = sorted(deleted_set)
        return self._remove_ignore_files(result, repository_name, branch_name)

    def find_moved_files_in_deleted_files(self, repository_name, branch_name, language, deleted_files):
        """
        Find files which is moved in deleted file list.

        :param branch_name:
        :param repository_name:
        :param language: Language name (in the configure file)
        """
        repo_base_path = self._configure.get_branch(repository_name, branch_name)["path"]
        git_cmd = self._get_git_commander(repo_base_path)
        source_path = self._configure.get_source(repository_name)["path"]

        repository_data = self._configure.get_repository(repository_name)
        task_repo_name = "{}/{}".format(
            repository_data["github"]["task"]["owner"],
            repository_data["github"]["task"]["repository"]
        )

        github_client = GithubOperator(self._github_token)
        moved_files = {}
        for file_name in deleted_files:
            file_full_path = source_path + file_name
            pull_id = git_cmd.get_last_pr_number(file_full_path)
            if pull_id == -1:
                continue
            is_moved, new_path = github_client.is_moved_file(task_repo_name, pull_id, file_full_path)
            if is_moved:
                moved_files[new_path] = file_name

        return moved_files

    def get_default_label(self, repository_name, branch, language):
        """
        A new issue will be labeled with these labels.
        :param repository_name:
        :param branch:
        :param language:
        :return:
        """
        labels = self._configure.get_branch(repository_name, branch)["labels"]
        labels += self._configure.get_languages(repository_name, language)["labels"]
        return labels

    def get_priority_labels(self, repository_name, file_name):
        """
        Find right priority labels by regular matching,  the first matched labels will be returned.
        :param repository_name:
        :param file_name:
        :return:
        """
        priority_matches = self._configure.get_repository(repository_name)["priorities"]
        for priority_match in priority_matches:
            for pattern in priority_match["patterns"]:
                if re.match(pattern, file_name):
                    return priority_match["labels"]
        return labels

    def get_search_label(self, repository_name, branch, language):
        """
        Find dupe issues with these labels.
        :param repository_name:
        :param branch:
        :param language:
        :return:
        """
        labels = self._configure.get_branch(repository_name, branch)["labels"].copy()
        labels += self._configure.get_languages(repository_name, language)["labels"]
        return labels

    def create_issue(self, github_repository, title, body, labels=None,
                     search_labels=None,
                     search_cache="",
                     search_online=False):
        """

        :param labels: Labels for new issue
        :type labels: list of str
        :param search_online: Search duplicated issues online
        :param github_repository: Name of the repository.
        :param title: Title of the new issue.

        :param body: Body of the new issue.
        :param search_labels: Search duplicated issues with title & labels.
        :type search_labels: list of str
        :param search_cache: Search in the cache file
        :type search_cache: str
        :rtype: github.Issue.Issue
        """
        if search_labels is None:
            search_labels = []
        if labels is None:
            labels = []
        dupe = False
        if len(search_cache) > 0:
            with open(search_cache, "r") as handler:
                obj = json.load(handler)
                for issue_record in obj:
                    if issue_record["title"] == title:
                        if len(search_labels) == 0:
                            dupe = True
                            break
                        else:
                            if set(search_labels).issubset(issue_record["labels"]):
                                dupe = True
                            break

        github_client = GithubOperator(self._github_token)
        if search_online:
            search_cmd = "repo:{} state:open is:issue in:title {}".format(github_repository, title)
            if len(search_labels) > 0:
                search_cmd = "{} {}".format(search_cmd,
                                            " ".join(
                                                ["label:{}".format(i) for i in search_labels])
                                            )
            issue_list = github_client.search_issue(search_cmd)
            for issue in issue_list:
                if issue.title == title:
                    dupe = True
        if dupe:
            return None
        new_issue = github_client.create_issue(github_repository, title, body)
        # Add labels
        for label_name in labels:
            new_issue.add_to_labels(label_name)
        return new_issue

    def gen_source_url(self, repo, branch, file_name):
        """

        :param repo:
        :param branch:
        :param file_name:
        """
        prefix = self._configure.get_branch(repo, branch)["url_prefix"]["source"]
        middle = ""
        if file_name[:1] != "/":
            middle = "/"
        return "{}{}{}".format(prefix, middle, file_name)

    def gen_target_url(self, repo, branch, file_name):
        """

        :param repo:
        :param branch:
        :param file_name:
        """
        prefix = self._configure.get_branch(repo, branch)["url_prefix"]["target"]
        middle = ""
        if file_name[:1] != "/":
            middle = "/"
        return "{}{}{}".format(prefix, middle, file_name)

    def gen_web_url(self, repo, branch, file_name):
        """

        :param repo:
        :param branch:
        :param file_name:
        """
        prefix = self._configure.get_branch(repo, branch)["url_prefix"]["web"]
        middle = ""
        if file_name[:1] != "/":
            middle = "/"
        return "{}{}{}".format(prefix, middle, file_name)

    def sync_pr_state_to_task_issue(self, repository, branch, language, days=5, search_limit=30):
        pr_list = self._get_code_pr_and_files(
            repository, branch, language, days, search_limit
        )
        pr_file_list = self._clean_pr_files(pr_list, repository, language)
        result = []
        for pr_record in pr_file_list:
            result += self._sync_task_with_file_name(repository, branch, language, pr_record)
        return result

    def _get_code_pr_and_files(self, repository,
                               branch, language, days=5,
                               search_limit=30):
        """
        Find recent PRs with specified language.

        :param days:
        :return:
        :param repository: Repository name
        :param branch: Branch name
        :param language: Language
        :param search_limit:
        :return:
        """
        after_date = datetime.now() - timedelta(days=days)
        after_date = after_date.strftime("%Y-%m-%d")
        base = self._configure.get_branch(repository, branch)["target_branch"]

        repository_data = self._configure.get_repository(repository)
        code_repo = "{}/{}".format(
            repository_data["github"]["code"]["owner"],
            repository_data["github"]["code"]["repository"],
        )
        prefix = self._configure.get_languages(repository, language)["path"]
        labels = self._configure.get_languages(repository, language)["target_labels"]
        query = "repo:{} type:pr {} created:>{}".format(
            code_repo,
            " ".join(["label:{}".format(label) for label in labels]),
            after_date
        )
        logging.warning(query)
        github_client = GithubOperator(self._github_token)
        pr_list = github_client.search_issue(query, search_limit)
        result = []
        for item in pr_list:
            pr = item.as_pull_request()
            if pr.base.ref != base:
                continue
            file_name_list = []
            for file_record in pr.get_files():
                file_name_list.append(file_record.filename)
            file_name_list = self._filter_file_type(repository, file_name_list)
            file_name_list = [file_name for file_name in file_name_list if file_name.startswith(prefix)]
            record = {
                "url": pr.html_url,
                "number": pr.number,
                "files": file_name_list,
                "merged": pr.is_merged(),
                "base": pr.base.ref,
                "head": pr.head.ref,
                "owner": pr.user.login,
                "comments": [],
                "object": pr
            }
            # get comments
            for comment in pr.get_issue_comments():
                if comment.body.startswith("`[trans-bot:"):
                    record["comments"].append(comment.body)
            result.append(record)
        return result

    def _clean_pr_files(self, pr_list, repository, language):
        target_path = self._configure.get_languages(repository, language)["path"]

        result = []
        for pr in pr_list:
            pr_merged = False
            for comment in pr["comments"]:
                if comment.startswith("`[trans-bot:merged]`"):
                    pr_merged = True
                if comment.startswith("`[trans-bot:N/A]`"):
                    pr_merged = True
            if pr_merged:
                continue
            time.sleep(2)
            if len(pr["files"]) != 1:
                body_pattern = "Thank you @{}, I can only process the PR with 1 file included, "
                body = "`[trans-bot:N/A]`\n\n" + body_pattern.format(pr["owner"]) + \
                       "will not be reported to the task issues."
                pr["object"].create_issue_comment(body)
                continue
            path_sep = target_path.split(os.sep)
            file_list = []
            for file_name in pr["files"]:
                if file_name.split(os.sep)[:len(path_sep)] == path_sep:
                    file_list.append(file_name[len(target_path):])
            pr["file_name"] = file_list[0]
            result.append(pr.copy())
        return result

    def _remove_status_label(self, repository, issue_item):
        for status in ["pushed", "merged", "pending", "working"]:
            status_label = self._configure.get_status_label(repository, status)
            if status_label in issue_item["labels"]:
                issue_item["object"].remove_from_labels(status_label)

    def _sync_task_with_file_name(self, repository, branch, language, pr):
        search_labels = self.get_search_label(repository, branch, language)
        repository_data = self._configure.get_repository(repository)
        task_repo_name = "{}/{}".format(
            repository_data["github"]["task"]["owner"],
            repository_data["github"]["task"]["repository"]
        )
        file_name = pr["file_name"]
        query = "repo:{} state:open type:issue in:title {} {}".format(
            task_repo_name,
            " ".join(["label:{}".format(i) for i in search_labels]),
            file_name
        )
        logging.warning(query)
        github_client = GithubOperator(self._github_token)
        issue_list = github_client.search_issue(query)
        result = []
        for issue in issue_list:
            if issue.title != file_name:
                continue
            issue_item = {
                "title": issue.title,
                "number": issue.number,
                "url": issue.html_url,
                "labels": [],
                "object": issue,
            }
            if issue.assignee is not None:
                issue_item["owner"] = issue.assignee.login
            else:
                body_pattern = "Thank you @{}, the [related task issue]({}) has no assignee. "
                body = "`[trans-bot:N/A]`\n\n" + body_pattern.format(pr["owner"], issue_item["url"]) + \
                       "will not be reported to the task issues"
                pr["object"].create_issue_comment(body)
                continue
            for label in issue.labels:
                issue_item["labels"].append(label.name)
            issue_working = self._configure.get_status_label(
                repository, "working") in issue_item["labels"]
            issue_pushed = self._configure.get_status_label(
                repository, "pushed") in issue_item["labels"]
            same_user = issue_item["owner"] == pr["owner"]
            if not same_user:
                body_pattern = "Thank you @{}, the [related task issue]({}) had been assigned to others. "
                body = "`[trans-bot:N/A]`\n\n" + body_pattern.format(pr["owner"], issue_item["url"]) + \
                       "will not be reported to the task issues"
                pr["object"].create_issue_comment(body)
                result.append(pr["url"])
                continue
            if pr["merged"]:
                body_pattern = "Thank you @{}, the [related task issue]({}) had been updated."
                if issue_pushed:
                    issue.create_comment("/merged")
                else:
                    self._remove_status_label(repository, issue_item)
                    issue.add_to_labels(self._configure.get_status_label(repository, "pushed"))
                    time.sleep(1)
                    issue.create_comment("/merged")
                body = "`[trans-bot:merged]`\n\n" + body_pattern.format(pr["owner"], issue_item["url"])
                pr["object"].create_issue_comment(body)

                result.append(pr["url"])
                continue
            body_pattern = "Thank you @{}, the [related task issue]({}) had been updated."
            body = "`[trans-bot:pushed]`\n\n" + body_pattern.format(pr["owner"], issue_item["url"])
            if issue_pushed:
                continue
            if not issue_working:
                self._remove_status_label(repository, issue_item)
                issue.add_to_labels(self._configure.get_status_label(repository, "working"))
                time.sleep(1)
            pr["object"].create_issue_comment(body)
            issue.create_comment("/pushed")
            result.append(pr["url"])
        return result

    def copy_version(self, repository, from_version, to_version, target_lang):
        config = self._configure
        source_repo_base_path = config.get_branch(repository, from_version)["path"]
        target_repo_base_path = config.get_branch(repository, to_version)["path"]
        source_lang_path = self._configure.get_source(repository)["path"]
        target_lang_path = self._configure.get_languages(repository, target_lang)["path"]

        source_repo_source_files = set(self._get_clean_files(repository,
                                                             from_version, source_lang_path))
        source_repo_target_files = set(self._get_clean_files(repository,
                                                             from_version, target_lang_path))
        source_same_files = (source_repo_source_files & source_repo_target_files)
        dest_repo_source_files = set(self._get_clean_files(repository,
                                                           to_version, source_lang_path))
        same_list = source_same_files & dest_repo_source_files
        for same_file_name in same_list:
            source_file = "{}/{}{}".format(
                source_repo_base_path,
                source_lang_path,
                same_file_name
            )
            target_file = "{}/{}{}".format(
                target_repo_base_path,
                source_lang_path,
                same_file_name
            )
            source_hash = md5_hash(source_file)
            target_hash = md5_hash(target_file)

            if source_hash == target_hash:
                source_trans_file = "{}/{}{}".format(
                    source_repo_base_path,
                    target_lang_path,
                    same_file_name
                )
                target_trans_file = "{}/{}{}".format(
                    target_repo_base_path,
                    target_lang_path,
                    same_file_name
                )
                print(target_hash, source_file)
                new_path = os.path.dirname(target_trans_file)
                if not os.path.exists(new_path):
                    os.makedirs(new_path)
                copyfile(source_trans_file, target_trans_file)

    def set_milestone_by_label(self, repository_name, label_list, milestone,
                               core_limit=10, search_limit=10):
        repository_data = self._configure.get_repository(repository_name)
        task_repo_name = "{}/{}".format(
            repository_data["github"]["task"]["owner"],
            repository_data["github"]["task"]["repository"]
        )
        github_client = GithubOperator(self._github_token)
        label_query = " ".join(["label:" + item for item in label_list])
        query = "type:issue -milestone:{} repo:{} {}".format(milestone, task_repo_name, label_query)
        logging.info(query)
        issue_list = github_client.search_issue(query, search_limit)

        count = 0
        for issue in issue_list:
            count += 1
            if count % core_limit == 0:
                github_client.check_limit(core_limit, search_limit)
            github_client.set_issue_milestone(task_repo_name,
                                              issue, milestone)
        return count
