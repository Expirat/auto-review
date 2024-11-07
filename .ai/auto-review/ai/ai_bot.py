# Apache License
# Version 2.0, January 2004
# Author: Eugene Tkachenko

from abc import ABC, abstractmethod
from ai.line_comment import LineComment
import re

class AiBot(ABC):
    
    __no_response = "No critical issues found"
    __problems="errors, issues, potential crashes, security issues or unhandled exceptions"
    __chat_gpt_ask_long="""
As a senior engineer overseeing code quality, I need a structured review of code issues within specific git diffs and the full file context. For each identified problem, please respond in the following format:

```
line_number of the issue: description of the problem, highlighting the cause and effect
suggestion: Suggested code fix with an example if possible
```

Please utilize GitHub comment formatting (like code blocks) to illustrate any suggested fixes. e.g.

```ruby
    your suggestion code
```

If no issues are found, respond only with `{no_response}`.

Here are the inputs:

- Git diffs:
  ```
  {diffs}
  ```
- Full code context:
  ```
  {code}
  ```

--- 

This version makes it explicit what you’re looking for and provides a clear structure for the response. Let me know if you'd like any more refinement!
"""

    @abstractmethod
    def ai_request_diffs(self, code, diffs) -> str:
        pass

    @staticmethod
    def build_ask_text(code, diffs) -> str:
        return AiBot.__chat_gpt_ask_long.format(
            problems = AiBot.__problems,
            no_response = AiBot.__no_response,
            diffs = diffs,
            code = code,
        )

    @staticmethod
    def is_no_issues_text(source: str) -> bool:
        target = AiBot.__no_response.replace(" ", "")
        source_no_spaces = source.replace(" ", "")
        return source_no_spaces.startswith(target)
    
    @staticmethod
    def split_ai_response(input) -> list[LineComment]:
        if not input:
            return []

        # Regex to match "line_number : " at the start of each comment
        comment_pattern = re.compile(r'^(\d+)\s*:\s*(.*)', re.MULTILINE)
        models = []
        current_comment_text = ""
        current_line = None

        for match in comment_pattern.finditer(input):
            # If we have a previous comment, save it before starting a new one
            if current_line is not None:
                models.append(LineComment(line=current_line, text=current_comment_text.strip()))

            # Extract line number and initial comment text from the regex match
            current_line = int(match.group(1))
            current_comment_text = match.group(2).strip()

            # Look ahead for text following this match until the next "line_number :"
            start_index = match.end()
            end_index = input.find(f"\n{match.group(1)} : ", start_index)
            if end_index == -1:  # No more line numbers, so capture to end of text
                current_comment_text += "\n" + input[start_index:].strip()
            else:
                current_comment_text += "\n" + input[start_index:end_index].strip()

        # Append the final comment if any
        if current_line is not None:
            models.append(LineComment(line=current_line, text=current_comment_text.strip()))

        return models
