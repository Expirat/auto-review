# Apache License
# Version 2.0, January 2004
# Original Author: Eugene Tkachenko
#
# Modifications:
# - Implementing geminiAI
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from git import Git 
from pathlib import Path
from log import Log
from env_vars import EnvVars
from repository.github import GitHub
from repository.repository import RepositoryError
import google.generativeai as genai
from ai.ai_bot import AiBot
import re

separator = "\n\n----------------------------------------------------------------------\n\n"
log_file = open('output.txt', 'a')


def main():

    vars = EnvVars()
    vars.check_vars()

    genai.configure(api_key=vars.gemini_ai_token)
    model = genai.GenerativeModel("gemini-1.5-pro") #should we put inside secret github?

    github = GitHub(vars.token, vars.owner, vars.repo, vars.pull_number)

    remote_name = Git.get_remote_name()
    
    # Checkout PR changes
    Log.print_green("Remote is", remote_name)
    changed_files = Git.get_diff_files(remote_name=remote_name, head_ref=vars.head_ref, base_ref=vars.base_ref)
    
    Log.print_green("Found changes in files", changed_files)
    if len(changed_files) == 0: 
        Log.print_red("No changes between branch")

    for file in changed_files:
        Log.print_green("Checking file", file)

        _, file_extension = os.path.splitext(file)
        file_extension = file_extension.lstrip('.')
        if file_extension not in vars.target_extensions:
            Log.print_yellow(f"Skipping, unsuported extension {file_extension} file {file}")
            continue

        try:
            with open(file, 'r') as file_opened:
                file_content = file_opened.read()
        except FileNotFoundError:
            Log.print_yellow("File was removed. Continue.", file)
            continue

        if len( file_content ) == 0: 
            Log.print_red("File is empty")
            continue

        file_diffs = Git.get_diff_in_file(remote_name=remote_name, head_ref=vars.head_ref, base_ref=vars.base_ref, file_path=file)
        if len( file_diffs ) == 0: 
            Log.print_red("Diffs are empty")
        
        # Gemini AI
        Log.print_green(f"Asking Gemini AI. Content Len:{len(file_content)} Diff Len: {len(file_diffs)}")

        gemini_prompt = AiBot.build_ask_text(code=file_content, diffs=file_diffs)

        response = model.generate_content([gemini_prompt])
        log_file.write(f"{separator}{file_content}{separator}{file_diffs}{separator}{response.text}{separator}")

        if AiBot.is_no_issues_text(response.text):
            Log.print_green("File looks good. Continue", file)
        else:
            responses = AiBot.split_ai_response(response.text)
            if len(responses) == 0:
                Log.print_red("Responses where not parsed:", responses)
                result = False
            for response in responses:
                if response.line:
                    result = post_line_comment(github=github, file=file, text=response.text, line=response.line)
                if not result:
                    diff_hunks = extract_diff_hunks(file_diffs)
                    result = post_line_comment_with_diff_hunks(github=github, file=file, text=response.text, line=response.line, diff_hunk=diff_hunks)
                if not result:
                    result = post_general_comment(github=github, file=file, text=response.text)
                if not result:
                    raise RepositoryError("Failed to post any comments.")

def extract_diff_hunks(diff_text, context_lines=3):
    hunks = []
    # Match each hunk starting with @@ and capture the line and surrounding context
    hunk_pattern = re.compile(r'(@@ .+ @@)([\s\S]*?)(?=(^@@|^diff|\Z))', re.MULTILINE)

    for match in hunk_pattern.finditer(diff_text):
        hunk_header = match.group(1)
        hunk_body = match.group(2).strip().splitlines()
        
        # Include a limited number of context lines
        hunk_body_with_context = "\n".join(hunk_body[:context_lines + 1])

        # Format it as the diff_hunk (combine header and limited body)
        diff_hunk = f"{hunk_header}\n{hunk_body_with_context}"
        hunks.append(diff_hunk)

    return hunks

def post_line_comment(github: GitHub, file: str, text:str, line: int):
    Log.print_green("Posting line", file, line, text)
    try:
        git_response = github.post_comment_to_line(
            text=text, 
            commit_id=Git.get_last_commit_sha(file=file), 
            file_path=file, 
            line=line,
        )
        Log.print_yellow("Posted", git_response)
        return True
    except RepositoryError as e:
        Log.print_red("Failed line comment", e)
        return False
    
def post_line_comment_with_diff_hunks(github: GitHub, file: str, text:str, line: int, diff_hunk: str):
    Log.print_green("Posting line", file, line, text)
    try:
        git_response = github.post_comment_to_line_with_diff_hunks(
            text=text, 
            commit_id=Git.get_last_commit_sha(file=file), 
            file_path=file, 
            line=line,
            diff_hunks=diff_hunk
        )
        Log.print_yellow("Posted", git_response)
        return True
    except RepositoryError as e:
        Log.print_red("Failed line comment", e)
        return False

def post_general_comment(github: GitHub, file: str, text:str) -> bool:
    Log.print_green("Posting general", file, text)
    try:
        message = f"{file}\n{text}"
        git_response = github.post_comment_general(message)
        Log.print_yellow("Posted general", git_response)
        return True
    except RepositoryError:
        Log.print_red("Failed general comment")
        return False

if __name__ == "__main__":
    main()

log_file.close()