# solver.py
import os
import time
import requests
from playwright.sync_api import sync_playwright
from data_handler import download_and_read_data
from llm_client import LLMClient

class SolverEngine:
    def __init__(self, email, secret):
        self.email = email
        self.secret = secret
        self.llm_client = LLMClient()
        self.start_time = time.time() # Track the starting time of the entire quiz series
        self.MAX_TIME_LIMIT = 175 # 3 minutes is 180s. Use 175s for buffer.

    def _submit_answer(self, quiz_url, submit_url, answer):
        """Posts the answer to the submission endpoint."""
        submission_payload = {
            "email": self.email,
            "secret": self.secret,
            "url": quiz_url,
            "answer": answer
        }

        print(f"Submitting answer for {quiz_url} to {submit_url}")
        try:
            # We must use the submit URL provided in the quiz instructions
            response = requests.post(submit_url, json=submission_payload, timeout=20)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Submission failed or network error: {e}")
            return None

    def _fetch_quiz_details(self, quiz_url):
        """Visits the URL using a headless browser (Playwright) to extract all necessary details."""
        print(f"Fetching details for: {quiz_url}")
        
        # Playwright must run synchronously here as it's called from Flask's synchronous context
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            try:
                page.goto(quiz_url)
                # Wait for the JavaScript content in the #result div to load
                page.wait_for_selector("#result", timeout=10000)
                
                rendered_text = page.locator("#result").inner_text()
                
                # Try to find the data download link from the DOM
                data_link = page.evaluate("document.querySelector('#result a')?.href")
                
                browser.close()
                
                # Use the LLM to parse the text into a clean JSON structure
                return self.llm_client.parse_quiz_instructions(
                    rendered_text, 
                    data_link or "No explicit link found" # Pass the link to the LLM
                )
            except Exception as e:
                browser.close()
                raise RuntimeError(f"Playwright fetching failed: {e}")

    def solve_quiz(self, url):
        """
        The main public method to start the quiz solving chain.
        """
        self._quiz_chain_loop(url)
    
    def _quiz_chain_loop(self, quiz_url):
        """Recursively solves quizzes until the chain is complete or time runs out."""

        if time.time() - self.start_time > self.MAX_TIME_LIMIT:
            print("Time limit exceeded for the entire quiz series. Halting chain.")
            return

        print(f"\n--- Starting Quiz: {quiz_url} (Time remaining: {self.MAX_TIME_LIMIT - (time.time() - self.start_time):.1f}s) ---")
        
        try:
            # 1. FETCH & PARSE INSTRUCTIONS
            quiz_details = self._fetch_quiz_details(quiz_url)
            question = quiz_details.get("question")
            data_url = quiz_details.get("data_url")
            submit_url = quiz_details.get("submit_url")
            
            if not all([question, data_url, submit_url]):
                 raise ValueError("Missing essential quiz details after LLM parsing.")

            # 2. SOURCE DATA
            data_content = download_and_read_data(data_url)
            
            # 3. SOLVE QUESTION
            answer = self.llm_client.solve_quiz_question(question, data_content)
            
            # 4. SUBMIT ANSWER
            submission_result = self._submit_answer(quiz_url, submit_url, answer)
            
            if submission_result is None: return

            correct = submission_result.get("correct", False)
            next_url = submission_result.get("url")
            reason = submission_result.get("reason")

            print(f"Submission Result: Correct={correct}, Reason={reason}")

            if correct:
                if next_url:
                    # Correct answer, proceed to the next quiz
                    print(f"Correct answer! Proceeding to next quiz: {next_url}")
                    self._quiz_chain_loop(next_url)
                else:
                    # Quiz completed
                    print("Quiz series completed successfully!")
            else:
                # Wrong answer: The prompt suggests either re-submitting or skipping to the next URL if provided.
                if next_url:
                    print(f"Wrong answer. Skipping to next quiz: {next_url}")
                    self._quiz_chain_loop(next_url)
                # Note: For robust scoring, you would implement re-solving logic here, checking the time limit carefully.

        except Exception as e:
            print(f"A critical error occurred during the quiz cycle for {quiz_url}: {e}")
            return