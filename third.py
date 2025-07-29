import os
import re
import json
import time
import google.generativeai as genai

'''
extended veriosn of second in which multiple domains are returned and also the answer also taken into consideration
'''


genai.configure(api_key="AIzaSyAjhjE1-c6vcFixyO6lOIHQUE8a15peRd0")
model = genai.GenerativeModel("gemini-1.5-flash")

MEMORY_FILE = "domain_memory.json"

def load_memory():

    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            try:
                memory = json.load(f)
            except json.JSONDecodeError:
                memory = {}
    else:
        memory = {}
    return memory

def save_memory(memory):

    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=4)

def classify_domain(query, memory):

    context = f"Current Memory: {json.dumps(memory)}\nUser Query: {query}\n"
    prompt = (
        "Analyze the user's query and determine if there are existing domain(s) "
        "in the conversation memory that apply. Respond in one of the following formats:\n"
        "  none.                 (if no domain applies)\n"
        "  yes.<domain1,domain2> (if one or more existing domains apply; e.g., yes.finance,travel)\n"
        "  new.<domain1,domain2> (if these should be new domains; e.g., new.health,education)\n"
        f"Context and query:\n{context}"
    )
    
    try:
        response = model.generate_content(prompt)
        llm_output = response.text.strip() if response.text else "none."
    except Exception as e:
        llm_output = "none."
        print("Error classifying domain:", e)
    
   
    pattern = r'^(none|yes|new)\. ?(.*)'
    match = re.match(pattern, llm_output, re.IGNORECASE)
    if match:
        decision = match.group(1).lower()
        domains_str = match.group(2).strip()
     
        domains = [d.strip().lower() for d in domains_str.split(',') if d.strip()] if decision != "none" else []
    else:
        decision = "none"
        domains = []
    return decision, domains

def get_domain_context(decision, domains, memory):

    context_history = []
    if decision in ["yes", "new"]:
        for domain in domains:
            if domain in memory:
                context_history.extend(memory[domain])
    return context_history

def generate_bot_answer(prompt, context_history):

    combined_input = ""
    if context_history:
        combined_input = "\n".join(context_history) + "\n"
    combined_input += f"User: {prompt}\nBot:"

    full_prompt = (
        "You are a chatbot. Use the conversation context to generate a helpful answer.\n"
        f"{combined_input}"
    )
    try:
        response = model.generate_content(full_prompt)
        return response.text.strip() if response.text else "No response generated."
    except Exception as e:
        return f"Error generating answer: {e}"

def update_domain_memory(query, answer, memory):

    qa_pair = f"User: {query}\nBot: {answer}"
    context = f"Current Memory: {json.dumps(memory)}\nNew Q&A Pair:\n{qa_pair}\n"
    prompt = (
        "Analyze the new Q&A pair along with the current memory and decide to which domain(s) it belongs. "
        "Respond in the following format:\n"
        "  yes.<domain1,domain2>  (if it matches existing domain(s))\n"
        "  new.<domain1,domain2>  (if it should belong to new domain(s))\n"
        f"Context:\n{context}"
    )
    try:
        response = model.generate_content(prompt)
        llm_output = response.text.strip() if response.text else "new.general"
    except Exception as e:
        llm_output = "new.general"
        print("Error updating domain memory:", e)
    

    pattern = r'^(yes|new)\. ?(.*)'
    match = re.match(pattern, llm_output, re.IGNORECASE)
    if match:
        decision = match.group(1).lower()
        domains_str = match.group(2).strip()
        domains = [d.strip().lower() for d in domains_str.split(',') if d.strip()]
    else:
        decision, domains = "new", ["general"]
    

    for domain in domains:
        if domain not in memory:
            memory[domain] = [qa_pair]
        else:
            memory[domain].append(qa_pair)
    

    save_memory(memory)
    return domains

def main():
    print("Chatbot with Domain Memory Started.")
    memory = load_memory()
    
    while True:
        query = input("You: ").strip()
        if query.lower() == "end":
            print("Chat ended.")
            break
        

        decision, domains = classify_domain(query, memory)
        print(f"[DEBUG] Domain classification: decision='{decision}', domains={domains}")
        
       
        context_history = get_domain_context(decision, domains, memory)
        
    
        answer = generate_bot_answer(query, context_history)
        print(f"Bot: {answer}")
        

        time.sleep(10)
        
   
        updated_domains = update_domain_memory(query, answer, memory)
        print(f"[DEBUG] Updated memory under domain(s): {updated_domains}\n")
        
if __name__ == "__main__":
    main()
