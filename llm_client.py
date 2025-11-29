# llm_client.py
import os
import json
from openai import OpenAI

class LLMClient:
    def __init__(self):
        # Initialize OpenAI client with API key from the .env file
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # System prompt to force structured JSON output for instruction parsing
        self.parsing_prompt_system = (
            "You are a robust text parser. Your task is to extract structured information "
            "from the provided human-readable quiz instructions and data URL. "
            "You MUST output a single JSON object that strictly adheres to the schema. "
            "ONLY output the JSON object."
        )

    def parse_quiz_instructions(self, rendered_text, data_link):
        """Uses the LLM to convert messy quiz text into structured details."""
        parsing_user_prompt = (
            f"Analyze the following text and links:\n\n-- TEXT --\n{rendered_text}\n\n"
            f"-- DATA LINK --\n{data_link}\n\n"
            "Extract the main 'question', the file 'data_url' (use the provided link if available), "
            "the 'submit_url' for posting the answer, and the required 'submit_format' (e.g., 'number', 'string', 'boolean')."
            "Output the result as a JSON object: "
            '{"question": "...", "data_url": "...", "submit_url": "...", "submit_format": "..."}'
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", # Use a capable, fast model
                messages=[
                    {"role": "system", "content": self.parsing_prompt_system},
                    {"role": "user", "content": parsing_user_prompt}
                ],
                response_format={"type": "json_object"} # Enforce JSON
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            # Raise a specific error to halt the process if parsing fails
            raise RuntimeError(f"LLM instruction parsing failed: {e}")

    def solve_quiz_question(self, question, data_content):
        """Uses the LLM to analyze the data and answer the question."""
        solving_user_prompt = (
            f"Solve the following quiz question based on the provided data.\n\n"
            f"-- QUESTION --\n{question}\n\n"
            f"-- SOURCE DATA --\n{data_content}\n\n"
            "Analyze the data and calculate the final answer. "
            "Output ONLY the final answer value (number, string, or boolean) without any extra explanation, formatting, or quotes."
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a specialized data analysis engine. Output ONLY the final result of the calculation."},
                    {"role": "user", "content": solving_user_prompt}
                ]
            )
            # The LLM is instructed to output the raw answer value
            raw_answer = response.choices[0].message.content.strip()
            
            # Attempt to convert the answer to the required type
            try:
                if '.' in raw_answer: return float(raw_answer)
                return int(raw_answer)
            except ValueError:
                if raw_answer.lower() in ('true', 'false'): return raw_answer.lower() == 'true'
                return raw_answer # Default to string if type conversion fails
        except Exception as e:
            raise RuntimeError(f"LLM solving failed: {e}")