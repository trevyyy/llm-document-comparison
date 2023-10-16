# Simmons Wavelength interview task

I have used Anthropic's Claude 2 model for this task. All the code and prompts can be found in `main.py`

I have chosen to chain three prompts for this task:

1. Request 1 asks the model to generate a list of terms common to both documents and terms that have been added or removed in the newer document. This categorisation of terms could be used to reformat the original documents to a more standard format so that they can be compared more easily by humans.
2. Request 2 asks the model to verify its answer. In a way, this is a qualitative evaluation of step one.
3. Request 3 asks the model to see if that are any substantial changes to the sections that are common to both documents.

**An example of the final output can be seen in `example_output.txt`**

To run the project as an interactive demo, install all requirements:

```
pip install -r requirements.txt
```

Launch the browser UI:
```
streamlit run main.py
```

In the UI, add you Anthropic API key, and paste in the two T&Cs documents you'd like to compare.
