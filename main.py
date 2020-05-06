from datetime import datetime
from elasticsearch import Elasticsearch
import os
import git
from pathlib import Path

es = Elasticsearch()
file_extensions_to_index = [".js", ".html", ".go", ".xml", ".css"]
git_repo_path = "https://github.com/shaysw/GameOfLife.git"
git_cloning_path = r"C:\clonedGitRepoFromElasticConnector"
git_index_name = "git-index"


def clone_git_repo(output_path):
    if os.path.exists(output_path):
        print('repo already cloned')
        return
    print(f'cloning git repo from {git_repo_path} to {output_path}...')
    Path(output_path).mkdir(parents=True, exist_ok=True)
    git.Git(output_path).clone(git_repo_path)
    print('done cloning git repo')


def should_index_file(file_path):
    _, file_extension = os.path.splitext(file_path)
    return os.path.isfile(file_path) and file_extension in file_extensions_to_index


def get_files_to_index(root_folder_path):
    ans = []
    for path, subdirs, files in os.walk(root_folder_path):
        for name in files:
            file_path = os.path.join(path, name)
            if not should_index_file(file_path):
                continue
            print(f'adding {file_path} to indexed docs')
            ans.append(file_path)
    return ans


def get_docs_from_files(files_to_index):
    docs = []

    for file_path in files_to_index:
        with open(file_path) as f:
            try:
                file_text = f.read()
            except:
                file_text = 'could not read file'
            doc = {
                'author': 'shaysw',
                'filename': file_path,
                'text': file_text,
                'timestamp': datetime.now(),
            }
            docs.append(doc)

    return docs


def delete_git_index():
    es.indices.delete(index=git_index_name, ignore=[400, 404])


def add_files_to_index(files_to_index):
    print('adding files to index...')
    docs = get_docs_from_files(files_to_index)

    for i, doc in enumerate(docs):
        es.index(index=git_index_name, id=i, body=doc)
    print('done adding files to index')


def index_git_repo_in_elastic(output_path):
    if es.indices.exists(index=git_index_name):
        print('index for git already exists')
        return

    print('index for git does not exist, indexing...')
    files_to_index = get_files_to_index(output_path)
    add_files_to_index(files_to_index)
    print(f'indexing done')
    es.indices.refresh(index=git_index_name)


def search_for_text_in_git_repo(text_to_search):
    print(f'searching for "{text_to_search}" in index...')
    res = es.search(index=git_index_name, body={"query": {"match": {"text": text_to_search}}})
    print("Got %d Hits:" % res['hits']['total']['value'])
    for hit in res['hits']['hits']:
        print("%(timestamp)s %(author)s %(filename)s" % hit["_source"])


def cleanup():
    delete_git_index()


if __name__ == '__main__':
    clone_git_repo(git_cloning_path)
    index_git_repo_in_elastic(git_cloning_path)
    search_for_text_in_git_repo("package main")
    cleanup()
