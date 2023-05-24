import argparse
import os
import random
import string
import sys
import webbrowser

import openai
from tqdm import tqdm

openai.api_key = os.environ["OPENAI_KEY"]
PROMPT_TEMPLATE = f"Good code reviews look at the change itself and how it fits into the codebase. They will look through the clarity of the title and description and “why” of the change. They cover the correctness of the code, test coverage, functionality changes, and confirm that they follow the coding guides and best practices. Make a good code review of the following diffs suggesting improvements and refactors based on best practices as SOLID concepts when it's worthy, please stop answering anything until I give you the diff in the conversation."
def add_code_tags(text):
    # Find all the occurrences of text surrounded by backticks
    import re

    matches = re.finditer(r"`(.+?)`", text)

    # Create a list to store the updated text chunks
    updated_chunks = []
    last_end = 0
    for match in matches:
        # Add the text before the current match
        updated_chunks.append(text[last_end : match.start()])

        # Add the matched text surrounded by <code> tags
        updated_chunks.append("<b>`{}`</b>".format(match.group(1)))

        # Update the last_end variable to the end of the current match
        last_end = match.end()

    # Add the remaining text after the last match
    updated_chunks.append(text[last_end:])

    # Join the updated chunks and return the resulting HTML string
    return "".join(updated_chunks)


def generate_comment(diff, chatbot_context):
    # Use the OpenAI ChatGPT to generate a comment on the file changes

    chatbot_context.append(
        {
            "role": "user",
            "content": f"Make a code review of the changes made in this diff: {diff}",
        }
    )
    # Retry up to three times
    retries = 3
    for attempt in range(retries):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=chatbot_context,
                n=1,
                stop=None,
                temperature=0.3,
            )

        except Exception as e:
            if attempt == retries - 1:
                print(f"attempt: {attempt}, retries: {retries}")
                raise e  # Raise the error if reached maximum retries
            else:
                print("OpenAI error occurred. Retrying...")
                continue

    comment = response.choices[0].message.content

    # Update the chatbot context with the latest response
    chatbot_context = [
        {
            "role": "user",
               "content": f"Make a code review of the changes made in this diff: {diff}",
        },
        {
            "role": "assistant",
            "content": comment,
        }
    ]

    return comment, chatbot_context


def create_html_output(title, description, changes, prompt):
    random_string = "".join(random.choices(string.ascii_letters, k=5))
    output_file_name = random_string + "-output.html"

    title_text = f"\nTitle: {title}" if title else ""
    description_text = f"\nDescription: {description}" if description else ""
    chatbot_context = [
        {
            "role": "user",
            "content": f"{prompt}{title_text}{description_text}",
        }
    ]

    # Generate the HTML output
    html_output = "<html>\n<head>\n<style>\n"
    html_output += "body {\n    font-family: Roboto, Ubuntu, Cantarell, Helvetica Neue, sans-serif;\n    margin: 0;\n    padding: 0;\n}\n"
    html_output += "pre {\n    white-space: pre-wrap;\n    background-color: #f6f8fa;\n    border-radius: 3px;\n    font-size: 85%;\n    line-height: 1.45;\n    overflow: auto;\n    padding: 16px;\n}\n"
    html_output += "</style>\n"
    html_output += '<link rel="stylesheet"\n href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/default.min.css">\n <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js"></script>\n'
    html_output += "<script>hljs.highlightAll();</script>\n"
    html_output += "</head>\n<body>\n"
    html_output += "<div style='background-color: #333; color: #fff; padding: 20px;'>"
    html_output += "<h1 style='margin: 0;'>AI code review</h1>"
    html_output += f"<h3>Diff to review: {title}</h3>" if title else ""
    html_output += "</div>"

    # Generate comments for each diff with a progress bar
    with tqdm(total=len(changes), desc="Making code review", unit="diff") as pbar:
        for i, change in enumerate(changes):
            diff = change["diff"]
            comment, chatbot_context = generate_comment(diff, chatbot_context)
            pbar.update(1)
            # Write the diff and comment to the HTML
            html_output += f"<h3>Diff</h3>\n<pre><code>{diff}</code></pre>\n"
            html_output += f"<h3>Comment</h3>\n<pre>{add_code_tags(comment)}</pre>\n"
    html_output += "</body>\n</html>"

    # Write the HTML output to a file
    with open(output_file_name, "w") as f:
        f.write(html_output)

    return output_file_name


def get_diff_changes_from_pipeline():
    # Get the piped input
    piped_input = sys.stdin.read()
    # Split the input into a list of diff sections
    diffs = piped_input.split("diff --git")
    # Create a list of dictionaries, where each dictionary contains a single diff section
    diff_list = [{"diff": diff} for diff in diffs if diff]
    return diff_list


def main():
    title, description, prompt = None, None, None
    changes = get_diff_changes_from_pipeline()
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="AI code review script")
    parser.add_argument("--title", type=str, help="Title of the diff")
    parser.add_argument("--description", type=str, help="Description of the diff")
    parser.add_argument("--prompt", type=str, help="Custom prompt for the AI")
    args = parser.parse_args()
    title = args.title if args.title else title
    description = args.description if args.description else description
    prompt = args.prompt if args.prompt else PROMPT_TEMPLATE
    output_file = create_html_output(title, description, changes, prompt)
    try:
        webbrowser.open(output_file)
    except Exception:
        print(f"Error running the web browser, you can try to open the outputfile: {output_file} manually")

if __name__ == "__main__":
    main()

