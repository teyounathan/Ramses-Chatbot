from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import json
import re
from django.http import HttpResponse, JsonResponse
from openai import AzureOpenAI
import os
from dotenv import load_dotenv
from ramses_app.models import Message
import logging



def index(request):
    load_dotenv()
    endpoint = os.getenv('endpoint')

    return render(request, 'ramses_app/index.html', {'endpoint': endpoint})

def bold_text(text):
    # Replace ** with <b> and </b>
    formatted_text = text.replace("**", "<b>", 1)
    while "**" in formatted_text:
        formatted_text = formatted_text.replace("**", "</b>", 1).replace("**", "<b>", 1)
    return formatted_text
 
def remove_references(response):
    # This regex will match patterns like [doc1], [doc2], etc.
    cleaned_response = re.sub(r'\[doc\d+\]', '', response)
    return cleaned_response
 
 
@csrf_exempt
def get_data(request):
    logger = logging.getLogger('chatbot')

    load_dotenv()
    http_proxy =  os.getenv('proxy')
    https_proxy =  os.getenv('proxy')
   
    # if http_proxy:
    #     os.environ['http_proxy'] = http_proxy
    # if https_proxy:
    #     os.environ['https_proxy'] = https_proxy
       
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        conversions = data.get('conversation')  
        userMessage = conversions[len(conversions)-1]['content']

        message = Message(message=userMessage)
        message.save()
        logger.info(f'Received message: {userMessage}')
        
        try:
            endpoint = os.getenv('ENDPOINT_URL')
            deployment = os.getenv('DEPLOYMENT_NAME')  
            search_endpoint = os.getenv('SEARCH_ENDPOINT')  
            search_key = os.getenv('SEARCH_KEY')  
            search_index = os.getenv('SEARCH_INDEX_NAME')  
            subscription_key = os.getenv('AZURE_OPENAI_API_KEY')  
            api_version= os.getenv('API_VERSION')
            
            # Initialize Azure OpenAI client with key-based authentication
            client = AzureOpenAI(  
                azure_endpoint=endpoint,  
                api_key=subscription_key,  
                api_version= api_version,  
            )                  
                                                                               
            personalized_message = "Sorry I can't relate this question with our promotional campaign. Can you ask a question that's related to our 237 MTN Boss campaig ?"#"Y'ello! It seems I couldn't find the information you're looking for in our current dataset. Could you please try rephrasing your query or ask about a different topic? I'm here to help!"
            

            # Prepare the chat prompt  
            chat_prompt = [
                {"role": "system", "content": "In MTN we use Y'ello instead of hello it helps rehenforce our mark and presence and consolidate our collaboration in MTN Cameroon. But say y'ello only at the begining of a conversion or when you are greeted: "},
                {"role": "system", "content": f"If the requested information is not available in the retrieved data, respond with: Y'ello! It seems I couldn't find the information you're looking for in our current dataset. Could you please try rephrasing your query or ask about a different topic? I'm here to help!"},
                {"role": "system", "content": "MTN Cameroon is running a promotional campaign called 'MTN 237 Boss' where 237 Cameroonian subscribers can win utility vehicles. The chatbot should provide information on how to participate, rules, eligibility, and answer frequently asked questions. The tone should be friendly and conversational. The response should be short and concise, give more details only when requested. The chatbot should also be able to handle basic customer inquiries."},
                {"role": "user", "content": "Who are you ?"},
                {"role": "assistant", "content": "I am here to assist you and answer any question you'll like to ask concerning our campaign MTN 237 Boss. Feel free to ask your question."},
                {"role": "user", "content": "What is Poland ?"},
                {"role": "assistant", "content":"Sorry can't relate this question with our promotional campaign. Can you ask a question that's related to our 237 MTN Boss campaig ?"}
                ]
 
            for conversion in conversions:
                chat_prompt.append(conversion)
                           
            # Generate the completion  
            completion = client.chat.completions.create(  
                model=deployment,  
                messages=chat_prompt,    
                max_tokens=1000,  
                temperature=0.5,  
                top_p=0.9,  
                frequency_penalty=0.1,  
                presence_penalty=0.1,  
                stop=None,  
                stream=False,
                extra_body={
                "data_sources": [{
                    "type": "azure_search",
                    "parameters": {
                    "endpoint": f"https://azureaisearchprod.search.windows.net",
                    "index_name": f"{search_index}",
                    "semantic_configuration": "default",
                    "query_type": "semantic",
                    "fields_mapping": {},
                    "in_scope": True,
                    "role_information": f"""
                    In MTN we use Y'ello instead of hello it helps rehenforce our mark and presence and consolidate our collaboration in MTN Cameroon. But say y'ello only at the begining of a conversion or when you are greeted.
                    MTN Cameroon is running a promotional campaign called 'MTN 237 Boss' where 237 Cameroonian subscribers can win utility vehicles. The chatbot should provide information on how to participate, rules, eligibility, and answer frequently asked questions. The tone should be friendly and conversational. The response should be short and concise, give more details only when requested. The chatbot should also be able to handle basic customer inquiries.
                    If the requested information is not available in the retrieved data, respond with: {personalized_message}.
                    When responding make sure not to provide too much information but when you are asked or when you should do so.
                    If you can't relate the user request to anything answer by saying: {personalized_message}.
                    """,
                    "filter": None,
                    "strictness": 3,
                    "top_n_documents": 5,
                    "authentication": {
                        "type": "api_key",
                        "key": f"{search_key}"
                    }
                    }
                }]
                }  
            )
            
            # if response.lower().startswith("The information is not found in the".lower()):
            
            # Get the logger
            logger = logging.getLogger('chatbot')

            response = bold_text(remove_references(completion.choices[0].message.content))
            logger.info(f'Sending response: {response}')
            return JsonResponse({'response': response})
 
        except Exception as e:
            logger.info(f'An unexpected error occurred. Please try again later. {str(e)}')
            # Get the logger
            logger = logging.getLogger('chatbot')
            return JsonResponse({'response': f"An unexpected error occurred. Please try again later."})