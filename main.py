import ast
import os
import streamlit as st
from dotenv import load_dotenv
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT, APIConnectionError, RateLimitError, APIStatusError
from timeit import default_timer

load_dotenv()
api_key = st.text_input('Anthropic API key', value=os.getenv('ANTHROPIC_API_KEY'))
anthropic = Anthropic(api_key=api_key)


classification_prompt = """You are a system specialized in legal document analysis.
I am going to give you two documents, which are two sets of terms and conditions. Here are the documents:

Document 1: <document1>{DOC_1}</document1>
Document 2: <document2>{DOC_2}</document2>

Your task is to complete these steps:
1. Read and memorize Document 1 and Document 2, which are two sets of terms and conditions.
2. Label the terms in the documents as either similarities, additions, and removals. Make notes of your thought process inside <thinking></thinking> XML tags as you do this. Text within these tags will not be shown to the user.
    - Similarities: terms that are common to both Document 1 and Document 2
    - Additions: terms that are present in Document 2 but not in Document 1
    - Removals: terms that are present in Document 1 but not in Document 2
3. Review Document 1 and Document 2, and make sure you have assigned labelled all terms in the documents as either Similarities, Additions, or Removals. You may now stop your thought process by closing the </thinking> tag.
4. Return a valid JSON. The keys should be "similarities", "additions", and "removals". The values for each should be a list of sentences that summarize the terms:
    - For "similarities", all sentences should start with "Both documents contain"
    - For "additions", all sentences should start with "Document 2 has added"
    - For "removals", all sentences should start with "Document 2 has removed"
"""

verification_prompt = """You are a system specialized in legal document analysis.
I am going to give you two documents, which are two sets of terms and conditions. Here are the documents:

Document 1: <document1>{DOC_1}</document1>
Document 2: <document2>{DOC_2}</document2>

Here is an JSON analysis inside <analysis></analysis> XML tags of the similarities, additions, and removals when comparing Document 2 with Document 1:
<analysis>
{CLASSIFICATION}
</analysis>

Your task is to complete these steps. Perform steps 1, 2, and 3 inside <thinking></thinking> XML tags as you do this. Text within these tags will not be shown to the user.
1. Summarize the JSON analysis in natural language.
2. Read the summary analysis and verify the accuracy of each point by throroughly reading Document 1 and Document 2.
3. Read the summary analysis and decide if it is missing any information by throroughly reading Document 1 and Document 2.
4. Update the original JSON you saw inside the <analysis></analysis> XML tags if necessary; this JSON should be updated based on your review of the analysis' accuracy.
5. Return the updated JSON without the <analysis></analysis> XML tags.
"""

comparison_prompt = """You are a system specialized in legal document analysis.
I am going to give you two documents, which are two sets of terms and conditions. Here are the documents:

Document 1: <document1>{DOC_1}</document1>
Document 2: <document2>{DOC_2}</document2>

Similarities: {SIMILARITIES}

Your task is to complete these steps:
1. Find the exact text in each document for the Similarities mentioned above.
2. For each of the texts you just identified, note any significant differences between Document 1 and Document 2.
3. Return a valid Python list of the dictionaries for each of the Similarities. Each dictionary should have three keys: "document_1_text", "document_2_text", and "difference"
    - "document_1_text": the relevant exact text from Document 1
    - "document_2_text": the relevant exact text from Document 2
    - "difference": the differnce between the Document 1 text and the Document 2 text. If there are no significant differences between Document 1 and Document 2, say there is "No substantive meaningful change".

Within the <example></example> XML tags is an example of how your response should be formatted:
<example>
[
{
"document_1_text": "lorem imspum",
"document_2_text": "lorem imspum",
"difference": "lorem imspum"
}
]
</example>
"""


def convert_to_list(text):
    start = text.index('[')
    end = text.rfind(']') + 1
    try:
        return ast.literal_eval(text[start:end])
    except SyntaxError as e:
        st.error(f'Error parsing LLM response: {e}')
        return []


def convert_to_dict(text):
    start = text.index('{')
    end = text.rfind('}') + 1
    try:
        return ast.literal_eval(text[start:end])
    except SyntaxError as e:
        st.error(f'Error parsing LLM response: {e}')
        return {}


def generate_anthropic_response(user_prompt, start_injection='Here is my response:'):
    try:
        completion = anthropic.completions.create(
            model="claude-2",
            max_tokens_to_sample=10000,
            prompt=f"{HUMAN_PROMPT} {user_prompt}{AI_PROMPT}{start_injection}",
            temperature=0.0
        )
        return completion.completion.strip()
    except APIConnectionError as e:
        st.error("The server could not be reached")
        st.error(e.__cause__)  # an underlying Exception, likely raised within httpx.
    except RateLimitError as e:
        st.error("A 429 status code (RateLimitError) was received")
    except APIStatusError as e:
        st.error("Another non-200-range status code was received")
        st.error(e.status_code)
        st.error(e.response)


# Document inputs
doc_1 = st.text_area('Document 1').strip()
doc_2 = st.text_area('Document 2').strip()


# async def main():
if st.button('Analyze'):

    t0 = default_timer()

    ##################
    # Classify terms #
    ##################

    # Create prompt from template
    prompt = classification_prompt
    prompt = prompt.replace('{DOC_1}', doc_1)
    prompt = prompt.replace('{DOC_2}', doc_2)

    with st.spinner('Analyzing documents to find commonalities and differences...'):
        output = generate_anthropic_response(prompt, start_injection='<thinking>')

    # Remove LLM's thought process
    answer = output.split('</thinking>')[-1]

    # Convert string to dict
    data = convert_to_dict(answer)

    # Print summary
    st.write('---')
    st.subheader('Initial summary')
    for k, v in data.items():
        st.write(f'**{k.capitalize()}**')
        for i in v:
            st.write(f'- {i}')

    #########################
    # Verify classification #
    #########################

    old_data = data

    # Create prompt from template
    prompt = verification_prompt
    prompt = prompt.replace('{DOC_1}', doc_1)
    prompt = prompt.replace('{DOC_2}', doc_2)
    prompt = prompt.replace('{CLASSIFICATION}', str(data))
    with st.spinner('Verifying...'):
        output = generate_anthropic_response(prompt, start_injection='<thinking>')

    # Remove LLM's thought process
    answer = output.split('</thinking>')[-1]

    # Convert string to dict
    data = convert_to_dict(answer)

    # Print summary if changed
    if data != old_data:
        st.write('---')
        st.subheader('Verified summary')
        for k, v in data.items():
            st.write(f'**{k.capitalize()}**')
            for i in v:
                st.write(f'- {i}')

    ########################################
    # Look for differences in shared terms #
    ########################################

    # Create string of commonalities between the documents
    for k, v in data.items():
        data[k] = [f'{i}.' if not i.endswith('.') else i for i in v]
    similarities = ' '.join(data['similarities'])

    # Create prompt from template
    prompt = comparison_prompt
    prompt = prompt.replace('{DOC_1}', doc_1)
    prompt = prompt.replace('{DOC_2}', doc_2)
    prompt = prompt.replace('{SIMILARITIES}', similarities)

    with st.spinner('Checking for changes in common sections...'):
        output = generate_anthropic_response(prompt)

    # Convert string to list
    data_list = convert_to_list(output)

    # Print summary
    st.write('---')
    st.subheader('Common terms')
    for data in data_list:
        for k, v in data.items():
            st.write(f'**{k.capitalize().replace("_", " ")}**')
            st.write(v)
        st.write('---')

    # Log time
    st.write(f'Analysis took {round(default_timer() - t0)}s')
