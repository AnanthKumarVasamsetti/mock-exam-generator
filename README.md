# INTRO
This application generates a mock multiple choice quiz based on the text provided by the user. The application is developped using Flask framework.

# Natural Language Processing
I used Google Cloud Natural Language API to analyze the text submitted. Then, with the help of a code sample provided by Google to detect Subject-Verb-Complement (S-V-C) structures in sentences, I was able to seperate the tokens in the sentence and ask a question. 
## Improvement
Right now, all the S-V-C structures returned by the API call are used ask questions to test the user. One improvement that I am thinking about is to use IBM Bluemix API to find the most relevant sentences in the text, and test only the user on these sentences.

# Wrong Choices' Generator
I used Words API to provide antonyms and/or similar sounding words as wrong choices to "trick" the user.
## Improvement
The use of Words API in this manner limits our choices. An improvement will be to generate better wrong choices using other words
already in the text submitted.

# Reflection & Take Away
I am passionate about machine learning and NLP particularly. I thought about working on a simple project during my winter break to explore the wonder of this exciting field.
Google Cloud NLP is sure a very sofisticated system for analyzing text. While playing around with it, I noticed that it was able to find a lot of syntactic structures (even some that I had to google search in order to understand what they mean :) ).
However, I still believe that more exciting things in NLP are ahead of us!
